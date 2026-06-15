"""기록 표 행 배경 — 내 덱(좌) ↔ 상대 덱(우) 카드 아트를 그라데이션 합성.

각 행 배경을 한 장의 배너(폭=뷰포트, 높이=행 높이)로 만들어 캐시하고,
델리게이트가 셀별로 해당 가로 슬라이스를 그린다. 아트가 없으면 덱명 색
그라데이션 폴백, 가독성을 위해 기본 어두운 오버레이를 깐다.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap

from .deck_avatar import _hue_for, thumb_pixmap

_MAX_CACHE = 256
_PLACEHOLDERS = {"미정", "WCS"}


def _draw_cover(p: QPainter, w: int, h: int, pix: QPixmap) -> None:
    scaled = pix.scaled(
        w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation)
    x = (scaled.width() - w) // 2
    y = (scaled.height() - h) // 2
    p.drawPixmap(0, 0, scaled, x, y, w, h)


def _fallback(p: QPainter, w: int, h: int, name: str) -> None:
    hue = _hue_for(name)
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0.0, QColor.fromHsl(hue, 80, 38))
    g.setColorAt(1.0, QColor.fromHsl((hue + 28) % 360, 80, 24))
    p.fillRect(QRectF(0, 0, w, h), g)


def _a(v: int) -> QColor:
    return QColor(0, 0, 0, v)


def _draw_side(p: QPainter, name, pix, x: int, w: int, h: int,
               fade: str) -> None:
    """아트 한 장을 (x,0,w,h)에 제 비율(cover)로 그리고 모든 가장자리를 페더링.

    가로는 안쪽+바깥쪽 모두, 세로는 위/아래를 부드럽게 페이드해 배경에 녹인다.
    """
    if w <= 0:
        return
    layer = QPixmap(w, h)
    layer.fill(Qt.GlobalColor.transparent)
    lp = QPainter(layer)
    lp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    if pix is not None:
        _draw_cover(lp, w, h, pix)
    else:
        _fallback(lp, w, h, name)
    lp.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_DestinationIn)

    # 가로 페더 (양쪽 가장자리 모두 부드럽게)
    hg = QLinearGradient(0, 0, w, 0)
    if fade == "right":   # 내 덱(좌): 바깥=왼쪽, 안쪽=오른쪽
        hg.setColorAt(0.0, _a(0))
        hg.setColorAt(0.18, _a(255))
        hg.setColorAt(0.55, _a(255))
        hg.setColorAt(1.0, _a(0))
    else:                 # 상대(우): 안쪽=왼쪽, 바깥=오른쪽
        hg.setColorAt(0.0, _a(0))
        hg.setColorAt(0.45, _a(255))
        hg.setColorAt(0.82, _a(255))
        hg.setColorAt(1.0, _a(0))
    lp.fillRect(QRectF(0, 0, w, h), hg)

    # 세로 페더 (위/아래)
    vg = QLinearGradient(0, 0, 0, h)
    vg.setColorAt(0.0, _a(0))
    vg.setColorAt(0.16, _a(255))
    vg.setColorAt(0.84, _a(255))
    vg.setColorAt(1.0, _a(0))
    lp.fillRect(QRectF(0, 0, w, h), vg)
    lp.end()
    p.drawPixmap(int(x), 0, layer)


def _build(my_name, my_pix, opp_name, opp_pix, w, h, split=0.5) -> QPixmap:
    pm = QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    art_w = max(1, min(int(h * 1.8), w // 2 + int(h * 0.5)))
    _draw_side(p, my_name, my_pix, 0, art_w, h, "right")        # 내 덱(좌)
    _draw_side(p, opp_name, opp_pix, w - art_w, art_w, h, "left")  # 상대(우)

    # 가독성용 옅은 어두운 오버레이 (가운데 비는 부분은 배경색이 비침)
    p.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, 70))
    p.end()
    return pm


def get_banner(my_name, my_path, opp_name, opp_path, w, h, split,
               pix_cache, banner_cache):
    if w <= 0 or h <= 0:
        return None
    key = (my_name, opp_name, my_path, opp_path, w, h, round(split, 3))
    pm = banner_cache.get(key)
    if pm is None:
        if len(banner_cache) > _MAX_CACHE:
            banner_cache.clear()
        my_pix = thumb_pixmap(my_path, pix_cache)
        opp_pix = thumb_pixmap(opp_path, pix_cache)
        pm = _build(my_name, my_pix, opp_name, opp_pix, w, h, split)
        banner_cache[key] = pm
    return pm


def paint_deck_cols(painter, option, index, art_provider, table,
                    pix_cache, banner_cache, my_col=1, opp_col=2) -> bool:
    """내 덱·상대 덱 두 열에 걸친 VS 배너의 해당 셀 슬라이스를 그린다.

    배너 폭 = (내 덱 + 상대 덱) 열 폭 합. 그라데이션 분기는 내 덱 열 비율.
    """
    if art_provider is None or table is None:
        return False
    x0 = table.columnViewportPosition(my_col)
    w_total = table.columnWidth(my_col) + table.columnWidth(opp_col)
    h = option.rect.height()
    if w_total <= 0 or h <= 0:
        return False
    split = table.columnWidth(my_col) / w_total

    def _name(col):
        return index.sibling(
            index.row(), col).data(Qt.ItemDataRole.DisplayRole) or ""

    def _path(name):
        if not name or name in _PLACEHOLDERS:
            return None
        return art_provider(name)

    my_name, opp_name = _name(my_col), _name(opp_col)
    pm = get_banner(my_name, _path(my_name), opp_name, _path(opp_name),
                    w_total, h, split, pix_cache, banner_cache)
    if pm is None:
        return False
    src = QRect(option.rect.x() - x0, 0, option.rect.width(), h)
    painter.drawPixmap(option.rect, pm, src)
    return True


def state_tint(painter, rect, selected: bool, review: bool) -> None:
    if selected:
        painter.fillRect(rect, QColor(255, 255, 255, 48))
    elif review:
        painter.fillRect(rect, QColor(234, 179, 8, 55))
