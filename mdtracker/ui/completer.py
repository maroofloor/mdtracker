"""덱 이름 입력용 자동완성 헬퍼.

드롭다운 항목은 그대로 두고(사용자 덱만), **완성 후보 모델에만** 카탈로그를
포함시켜 드롭다운이 640개로 폭발하는 것을 막는다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter


def make_deck_completer(names, parent=None) -> QCompleter:
    """names(사용자 덱 + 카탈로그)로 부분일치·대소문자 무시 자동완성 생성."""
    uniq = sorted({n for n in names if n})
    model = QStringListModel(uniq, parent)
    comp = QCompleter(model, parent)
    comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    comp.setFilterMode(Qt.MatchFlag.MatchContains)
    comp.setMaxVisibleItems(12)
    return comp
