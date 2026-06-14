"""덱 관리 뷰 — 체크박스 다중선택 삭제 + 전체삭제 + 엑셀 내보내기/가져오기."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..styles.theme import (
    ACCENT, BORDER, IMPORT_COLOR, LOSE_DARK, PANEL,
    SURFACE, SURFACE2, TEXT, TEXT2, WIN_DARK,
)

_BTN = "border-radius: 8px; padding: 6px 14px; font-weight: bold; color: #fff; border: none;"


class DeckView(QWidget):
    def __init__(self, db) -> None:
        super().__init__()
        self.db = db
        self._loading = False
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── 검색 ──────────────────────────────────────────────────
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  덱 이름 검색...")
        self.search.setStyleSheet(
            f"background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};"
            "border-radius: 8px; padding: 6px 12px; font-size: 13px;")
        self.search.textChanged.connect(self._filter)
        root.addWidget(self.search)

        # ── 추가 행 ───────────────────────────────────────────────
        add_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("새 덱 이름 (예: 스네이크아이)")
        self.name_edit.setStyleSheet(
            f"background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};"
            "border-radius: 8px; padding: 6px 12px;")
        self.add_btn = QPushButton("+ 추가")
        self.add_btn.setStyleSheet(f"background: {ACCENT}; {_BTN}")
        self.mine_check = QCheckBox("내 덱")
        self.mine_check.setChecked(True)
        self.mine_check.setStyleSheet(f"color: {TEXT2};")
        add_row.addWidget(self.name_edit, 1)
        add_row.addWidget(self.mine_check)
        add_row.addWidget(self.add_btn)
        root.addLayout(add_row)

        # ── 안내 텍스트 ───────────────────────────────────────────
        hint = QLabel("'내 덱' 열 체크박스로 내 덱 여부 설정 · '선택' 열 체크 후 선택 삭제")
        hint.setStyleSheet(f"color: {TEXT2}; font-size: 11px;")
        root.addWidget(hint)

        # ── 테이블 (선택 / 덱 이름 / 내 덱) ──────────────────────
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["선택", "덱 이름", "내 덱"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 52)
        self.table.setColumnWidth(2, 72)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {PANEL}; border: 1px solid {BORDER}; }}"
            f"QTableWidget::item {{ padding: 6px 12px; color: {TEXT}; }}"
            f"QHeaderView::section {{ background: {SURFACE}; color: {TEXT2};"
            f"font-size: 11px; border: none; border-bottom: 1px solid {BORDER};"
            "padding: 6px 12px; }}")
        self.table.verticalHeader().setDefaultSectionSize(38)
        root.addWidget(self.table, 1)

        # ── 하단 버튼 ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.del_btn = QPushButton("선택 삭제")
        self.del_btn.setStyleSheet(f"background: #ef4444; {_BTN}")
        self.del_all_btn = QPushButton("전체 삭제")
        self.del_all_btn.setStyleSheet(f"background: {LOSE_DARK}; {_BTN}")
        self.export_btn = QPushButton("⬇ 엑셀 내보내기")
        self.export_btn.setStyleSheet(f"background: {WIN_DARK}; {_BTN}")
        self.import_btn = QPushButton("⬆ 엑셀 가져오기")
        self.import_btn.setStyleSheet(f"background: {IMPORT_COLOR}; {_BTN}")
        btn_row.addWidget(self.del_btn)
        btn_row.addWidget(self.del_all_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.import_btn)
        root.addLayout(btn_row)

        self.add_btn.clicked.connect(self._on_add)
        self.name_edit.returnPressed.connect(self._on_add)
        self.del_btn.clicked.connect(self._on_delete)
        self.del_all_btn.clicked.connect(self._on_delete_all)
        self.export_btn.clicked.connect(self._on_export)
        self.import_btn.clicked.connect(self._on_import)
        self.table.itemChanged.connect(self._on_item_changed)

    def refresh(self) -> None:
        self._loading = True
        try:
            decks = self.db.decks.list()   # is_mine DESC, name ASC
            self.table.setRowCount(len(decks))
            for row, d in enumerate(decks):
                row_bg = QColor(SURFACE) if row % 2 else QColor(SURFACE2)

                # 선택 체크박스 (편집 불가)
                sel_item = QTableWidgetItem()
                sel_item.setCheckState(Qt.Unchecked)
                sel_item.setTextAlignment(Qt.AlignCenter)
                sel_item.setBackground(row_bg)
                sel_item.setFlags(sel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, sel_item)

                # 덱 이름 (더블클릭 인라인 편집 가능)
                name_item = QTableWidgetItem(d.name)
                name_item.setData(Qt.UserRole, d.id)
                name_item.setForeground(QColor(TEXT))
                name_item.setBackground(row_bg)
                name_item.setToolTip("더블클릭하여 이름 편집")
                self.table.setItem(row, 1, name_item)

                # 내 덱 체크박스 (편집 불가 — 클릭으로 토글)
                mine_item = QTableWidgetItem()
                mine_item.setCheckState(Qt.Checked if d.is_mine else Qt.Unchecked)
                mine_item.setTextAlignment(Qt.AlignCenter)
                mine_item.setBackground(row_bg)
                mine_item.setFlags(mine_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, mine_item)
        finally:
            self._loading = False
        self._filter(self.search.text())

    def _filter(self, text: str) -> None:
        q = text.strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            hide = bool(q and item and q not in item.text().lower())
            self.table.setRowHidden(row, hide)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        col = item.column()
        if col == 2:
            # 내 덱 체크박스 토글
            id_item = self.table.item(item.row(), 1)
            if not id_item:
                return
            deck_id = id_item.data(Qt.UserRole)
            if deck_id is None:
                return
            self.db.decks.set_mine(deck_id, item.checkState() == Qt.Checked)
            self.refresh()
        elif col == 1:
            # 덱 이름 인라인 편집
            deck_id = item.data(Qt.UserRole)
            new_name = item.text().strip()
            if deck_id is None or not new_name:
                self.refresh()
                return
            self.db.decks.rename(deck_id, new_name)
            self.refresh()

    def _checked_ids(self) -> list[int]:
        ids = []
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            sel_item = self.table.item(row, 0)
            if sel_item and sel_item.checkState() == Qt.Checked:
                name_item = self.table.item(row, 1)
                if name_item:
                    did = name_item.data(Qt.UserRole)
                    if did is not None:
                        ids.append(did)
        return ids

    def _on_add(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            return
        self.db.decks.add(name, is_mine=self.mine_check.isChecked())
        self.name_edit.clear()
        self.refresh()

    def _on_delete(self) -> None:
        ids = self._checked_ids()
        if not ids:
            QMessageBox.information(self, "선택 없음", "삭제할 덱을 '선택' 열에서 체크해주세요.")
            return
        yes = QMessageBox.StandardButton.Yes
        if QMessageBox.question(
            self, "선택 삭제",
            f"체크된 덱 {len(ids)}개를 삭제할까요?\n(기존 대전 기록은 영향받지 않습니다)",
            yes | QMessageBox.StandardButton.No,
        ) == yes:
            for did in ids:
                self.db.decks.delete(did)
            self.refresh()

    def _on_delete_all(self) -> None:
        count = self.table.rowCount()
        if count == 0:
            return
        yes = QMessageBox.StandardButton.Yes
        if QMessageBox.question(
            self, "전체 삭제",
            f"덱 목록 전체 {count}개를 모두 삭제할까요?\n"
            "이 작업은 되돌릴 수 없습니다. 기존 대전 기록은 영향받지 않습니다.",
            yes | QMessageBox.StandardButton.No,
        ) == yes:
            self.db.decks.delete_all()
            self.refresh()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "덱 목록 저장", "decks.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "덱 목록"
            ws.append(["덱 이름", "내 덱"])
            decks = self.db.decks.list()
            for d in decks:
                ws.append([d.name, "O" if d.is_mine else ""])
            wb.save(path)
            QMessageBox.information(self, "완료", f"{len(decks)}개 덱을 저장했습니다.")
        except ImportError:
            QMessageBox.warning(
                self, "오류",
                "openpyxl이 설치되지 않았습니다.\n.venv/bin/pip install openpyxl")
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", str(e))

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "엑셀 파일 열기", "", "Excel / CSV (*.xlsx *.xls *.csv)")
        if not path:
            return
        try:
            rows = _read_deck_file(path)
        except Exception as e:
            QMessageBox.warning(self, "가져오기 실패", str(e))
            return
        if not rows:
            QMessageBox.information(self, "가져오기", "가져올 덱이 없습니다.")
            return
        added = sum(1 for name, is_mine in rows
                    if name and self.db.decks.add(name, is_mine=is_mine))
        self.refresh()
        QMessageBox.information(self, "완료", f"{added}개 덱을 가져왔습니다.")


def _read_deck_file(path: str) -> list[tuple[str, bool]]:
    """xlsx / xls / csv 에서 (덱 이름, is_mine) 목록을 읽는다."""
    if path.lower().endswith(".csv"):
        import csv
        with open(path, encoding="utf-8-sig", newline="") as f:
            raw = list(csv.reader(f))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        raw = [[str(c.value or "") for c in r] for r in ws.iter_rows()]

    result: list[tuple[str, bool]] = []
    for i, row in enumerate(raw):
        name = row[0].strip() if row else ""
        if i == 0 and name.lower() in ("덱 이름", "덱이름", "deck", "name"):
            continue  # 헤더 행 스킵
        if not name:
            continue
        mine_raw = row[1].strip().upper() if len(row) > 1 else ""
        is_mine = mine_raw in ("O", "TRUE", "1", "Y", "YES", "내덱")
        result.append((name, is_mine))
    return result
