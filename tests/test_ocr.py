"""OCR 분류기 단위 테스트 — 화면/tesseract 없이 실행 가능.

P2 키워드 강화 검증: 토스 화면 문구는 선공·후공이 둘 다 들어 있다는 점을 이용해,
coin ROI와 겹치는 듀얼 중 안내 배너("상대가 효과 대상을 선택하고 있습니다" 류)
오탐을 거부하는지 확인한다. (docs/ocr_recovery_design.md §2 P2)

실행: .venv/bin/python tests/test_ocr.py  (또는 python -m unittest)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mdtracker.ocr.engine import classify_coin_text, classify_toss_text  # noqa: E402


class TestClassifyTossText(unittest.TestCase):
    """토스 선택 화면 분류 (공백 제거 텍스트)."""

    def test_toss_win(self):
        # "선공/후공을 선택해주세요" — 내가 선택 = 토스 승
        self.assertEqual(classify_toss_text("선공/후공을선택해주세요"), "win")
        self.assertEqual(classify_toss_text("선공후공을선택해주세요"), "win")

    def test_toss_loss(self):
        # "대전 상대가 선공/후공을 선택하고 있습니다" — 상대 선택 = 토스 패
        self.assertEqual(
            classify_toss_text("대전상대가선공/후공을선택하고있습니다"), "loss")
        self.assertEqual(
            classify_toss_text("상대가선공후공을선택하고있습니다"), "loss")

    def test_rejects_duel_banner_with_sangdae(self):
        # P2 핵심 회귀: 구 규칙("상대"+"있습니다")은 듀얼 중 배너를 토스 패로 오탐했다.
        # 강화 규칙은 선공·후공이 둘 다 없으면 거부한다.
        self.assertIsNone(
            classify_toss_text("상대가효과대상을선택하고있습니다"))
        self.assertIsNone(
            classify_toss_text("상대가카드를선택하고있습니다"))
        self.assertIsNone(
            classify_toss_text("상대가특수소환하고있습니다"))

    def test_rejects_effect_banner(self):
        self.assertIsNone(classify_toss_text("효과를발동할수있습니다"))

    def test_rejects_coin_result_screen(self):
        # "당신이 선공/후공입니다" = 선후공 확정 화면 → toss 아님
        self.assertIsNone(classify_toss_text("당신이선공입니다"))
        self.assertIsNone(classify_toss_text("당신이후공입니다"))

    def test_rejects_partial_keywords(self):
        # 선공·후공 중 하나만 있으면 거부 (둘 다 필요)
        self.assertIsNone(classify_toss_text("선공을선택해주세요"))
        self.assertIsNone(classify_toss_text("상대가후공을선택하고있습니다"))
        self.assertIsNone(classify_toss_text(""))


class TestClassifyCoinText(unittest.TestCase):
    """선후공 확정 문구 분류: '당신이' AND (선공 XOR 후공)."""

    def test_first(self):
        self.assertEqual(classify_coin_text("당신이선공입니다"), "first")

    def test_second(self):
        self.assertEqual(classify_coin_text("당신이후공입니다"), "second")

    def test_rejects_toss_screen(self):
        # 토스 화면은 선공·후공 둘 다 포함 → XOR 위반으로 거부
        self.assertIsNone(classify_coin_text("선공/후공을선택해주세요"))
        self.assertIsNone(classify_coin_text("당신이선공후공입니다"))

    def test_rejects_without_dangshini(self):
        self.assertIsNone(classify_coin_text("선공입니다"))
        self.assertIsNone(classify_coin_text(""))


if __name__ == "__main__":
    unittest.main()
