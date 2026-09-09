from __future__ import annotations

import unittest

from evaluation.answer_verifier import verify_answer


class AnswerVerifierTests(unittest.TestCase):
    def test_fraction_and_decimal_are_equivalent(self) -> None:
        result = verify_answer(r"\frac{4}{5}", "0.8")
        self.assertEqual(result.verdict, "correct")
        self.assertTrue(result.math_equivalent)
        self.assertTrue(result.format_mismatch_but_equivalent)
        self.assertFalse(result.exact_match)

    def test_reordered_radical_expression_is_equivalent(self) -> None:
        result = verify_answer(r"5+6\sqrt{2}", r"6\sqrt{2}+5")
        self.assertEqual(result.verdict, "correct")
        self.assertTrue(result.format_mismatch_but_equivalent)

    def test_wrong_answer_is_rejected(self) -> None:
        result = verify_answer("45", "46")
        self.assertEqual(result.verdict, "incorrect")
        self.assertFalse(result.math_equivalent)

    def test_missing_answer_is_unverified(self) -> None:
        result = verify_answer("45", None)
        self.assertEqual(result.verdict, "unverified")
        self.assertTrue(result.manual_review_recommended)

    def test_multiple_answers_are_flagged_for_review(self) -> None:
        result = verify_answer(r"-\frac{3}{2}, -1, 7", r"7,-1,-\frac{3}{2}")
        self.assertTrue(result.manual_review_recommended)

    def test_latex_thousands_separator_is_not_flagged_as_multiple_answers(self) -> None:
        result = verify_answer("180000", r"180{,}000")
        self.assertEqual(result.verdict, "correct")
        self.assertFalse(result.manual_review_recommended)


if __name__ == "__main__":
    unittest.main()
