"""수동 기록 추가 / 교정 모달 다이얼로그."""

from __future__ import annotations

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from .labels import (
    COIN_LABELS,
    COIN_TOSS_LABELS,
    EVENT_LABELS,
    RESULT_LABELS,
    WCS_OPP_DECK,
    combo_value,
    fill_combo,
    select_value,
)


class ManualDialog(QDialog):
    """수동으로 매치를 입력하거나 기존 매치를 교정하는 다이얼로그."""

    def __init__(self, parent, db, *, match=None,
                 my_deck: str = "", opp_deck: str = "", event_type: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("수동 기록 추가" if match is None else "기록 교정")
        self.setMinimumWidth(340)
        self._match_id = match.id if match else None
        self._db = db
        self._build(match, my_deck, opp_deck, event_type)

    def _build(self, match, my_deck: str, opp_deck: str, event_type: str) -> None:
        names = self._db.decks.list_names()

        self.my_deck_field = QComboBox()
        self.my_deck_field.setEditable(True)
        self.my_deck_field.addItems(names)
        self.my_deck_field.setCurrentText(match.my_deck if match else my_deck)

        self.opp_deck_field = QComboBox()
        self.opp_deck_field.setEditable(True)
        self.opp_deck_field.addItems(names)
        self.opp_deck_field.setCurrentText(
            match.opponent_deck if match else (opp_deck or ""))
        self.opp_deck_field.setPlaceholderText("미정")

        # 자동완성 후보 = 사용자 덱 + DB 카드군 카탈로그(드롭다운은 그대로 사용자 덱만)
        try:
            from ..cardart.localdb import LocalCardDB
            from .completer import make_deck_completer
            _catalog = LocalCardDB().all_display_names()
            self.my_deck_field.setCompleter(
                make_deck_completer(list(names) + _catalog, self))
            self.opp_deck_field.setCompleter(
                make_deck_completer(list(names) + _catalog, self))
        except Exception:
            pass

        self.played_at = QDateTimeEdit(QDateTime.currentDateTime())
        self.played_at.setCalendarPopup(True)
        self.played_at.setDisplayFormat("yyyy-MM-dd HH:mm")
        if match:
            dt = QDateTime.fromString(match.played_at, Qt.ISODate)
            if dt.isValid():
                self.played_at.setDateTime(dt)

        self.coin_toss = QComboBox()
        fill_combo(self.coin_toss, COIN_TOSS_LABELS)
        if match:
            select_value(self.coin_toss, match.coin_toss)

        self.coin = QComboBox()
        fill_combo(self.coin, COIN_LABELS)
        if match:
            select_value(self.coin, match.coin_result)

        self.result = QComboBox()
        fill_combo(self.result, RESULT_LABELS)
        if match:
            select_value(self.result, match.result)

        self.event = QComboBox()
        fill_combo(self.event, EVENT_LABELS)
        if match:
            select_value(self.event, match.event_type)
        elif event_type:
            select_value(self.event, event_type)
        # WCS는 상대 덱 확인 불가 → 상대 덱을 'WCS'로 고정
        self.event.currentIndexChanged.connect(self._sync_wcs_opp_deck)
        self._sync_wcs_opp_deck()

        self.rank = QLineEdit(match.rank_label or "" if match else "")
        self.notes = QLineEdit(match.notes or "" if match else "")

        form = QFormLayout()
        form.addRow("내 덱",     self.my_deck_field)
        form.addRow("상대 덱",   self.opp_deck_field)
        form.addRow("일시",      self.played_at)
        form.addRow("코인토스",  self.coin_toss)
        form.addRow("선/후공",   self.coin)
        form.addRow("결과",      self.result)
        form.addRow("타입",      self.event)
        form.addRow("랭크",      self.rank)
        form.addRow("메모",      self.notes)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(btns)

    def _sync_wcs_opp_deck(self, *_) -> None:
        if combo_value(self.event) == "wcs":
            self.opp_deck_field.setCurrentText(WCS_OPP_DECK)
            self.opp_deck_field.setEnabled(False)
        else:
            if self.opp_deck_field.currentText().strip() == WCS_OPP_DECK:
                self.opp_deck_field.setCurrentText("")
            self.opp_deck_field.setEnabled(True)

    def get_data(self) -> dict:
        played = self.played_at.dateTime().toString(Qt.ISODate)
        is_wcs = combo_value(self.event) == "wcs"
        return {
            "played_at":     played,
            "my_deck":       self.my_deck_field.currentText().strip(),
            "opponent_deck": (WCS_OPP_DECK if is_wcs else
                              self.opp_deck_field.currentText().strip() or "미정"),
            "coin_result":   combo_value(self.coin),
            "coin_toss":     combo_value(self.coin_toss),
            "result":        combo_value(self.result),
            "event_type":    combo_value(self.event),
            "rank_label":    self.rank.text().strip() or None,
            "notes":         self.notes.text().strip() or None,
            "match_id":      self._match_id,
            "season":        played[:7],
        }
