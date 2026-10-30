"""Tests for src/eval_summary.py (M6).

Run with: .venv/bin/python -m pytest tests/test_m6_eval_summary.py -v
"""
import sys
import unittest

sys.path.insert(0, ".")
from src.eval_summary import summarize


def _rec(status, verdict, question="q?"):
    return {"status": status, "verdict": verdict, "question": question}


class TestSummarize(unittest.TestCase):

    def test_empty_run_message(self):
        """An empty run prints a message, not a division by zero."""
        text, disagreements = summarize([])
        self.assertIn("No questions", text)
        self.assertEqual(disagreements, [])

    def test_exact_counts_and_percentages(self):
        """5 hand-made records give the exact expected counts and percentages."""
        records = [
            _rec("supported", "faithful"),
            _rec("supported", "faithful"),
            _rec("supported", "partial"),
            _rec("not supported", "unfaithful"),
            _rec("not supported", "unknown"),
        ]
        text, _ = summarize(records)

        # Supported: 3/5 = 60 %
        self.assertIn("3/5", text)
        self.assertIn("60%", text)

        # Faithful: 2/5
        self.assertIn("Faithful  : 2/5", text)

        # Partial: 1/5
        self.assertIn("Partial   : 1/5", text)

        # Unfaithful: 1/5
        self.assertIn("Unfaithful: 1/5", text)

    def test_disagreement_supported_unfaithful(self):
        """supported + unfaithful must be flagged."""
        records = [_rec("supported", "unfaithful", "dangerous question?")]
        _, disagreements = summarize(records)
        self.assertEqual(len(disagreements), 1)
        self.assertEqual(disagreements[0]["question"], "dangerous question?")

    def test_disagreement_not_supported_faithful(self):
        """not supported + faithful must be flagged."""
        records = [_rec("not supported", "faithful", "tricky question?")]
        _, disagreements = summarize(records)
        self.assertEqual(len(disagreements), 1)

    def test_exact_disagreement_list(self):
        """The disagreement list contains exactly the right records."""
        records = [
            _rec("supported", "faithful", "q1"),         # no disagreement
            _rec("supported", "unfaithful", "q2"),       # disagreement
            _rec("not supported", "faithful", "q3"),     # disagreement
            _rec("not supported", "unfaithful", "q4"),   # no disagreement
            _rec("supported", "partial", "q5"),          # no disagreement
        ]
        text, disagreements = summarize(records)

        disagreement_questions = [d["question"] for d in disagreements]
        self.assertIn("q2", disagreement_questions)
        self.assertIn("q3", disagreement_questions)
        self.assertNotIn("q1", disagreement_questions)
        self.assertNotIn("q4", disagreement_questions)
        self.assertNotIn("q5", disagreement_questions)
        self.assertEqual(len(disagreements), 2)

    def test_no_disagreements_message(self):
        """With no disagreements the text says so explicitly."""
        records = [_rec("supported", "faithful"), _rec("not supported", "unfaithful")]
        text, disagreements = summarize(records)
        self.assertIn("No disagreements", text)
        self.assertEqual(disagreements, [])

    def test_disagreements_mentioned_in_text(self):
        """When disagreements exist they appear in the summary text."""
        records = [_rec("supported", "unfaithful", "suspect-q")]
        text, _ = summarize(records)
        self.assertIn("suspect-q", text)
        self.assertIn("disagree", text)

    def test_single_question_no_crash(self):
        """Single question run works."""
        records = [_rec("supported", "faithful")]
        text, _ = summarize(records)
        self.assertIn("1 question", text)

    def test_all_unknown_no_crash(self):
        """All unknown verdicts do not crash."""
        records = [_rec("not supported", "unknown") for _ in range(3)]
        text, _ = summarize(records)
        self.assertIn("Unknown", text)

    def test_correct_refusal_is_not_a_disagreement(self):
        """'Not in the document' has no quote to check: with a faithful judge it is not flagged."""
        refusal = dict(_rec("not supported", "faithful", "uncovered?"), answer="The document does not cover this.")
        text, disagreements = summarize([_rec("supported", "faithful"), refusal])
        self.assertEqual(disagreements, [])
        self.assertIn("No disagreements", text)

    def test_disputed_refusal_is_a_disagreement(self):
        """A refusal the judge calls unfaithful (the passages do answer it) is flagged."""
        refusal = dict(_rec("not supported", "unfaithful", "covered?"), answer="The document does not cover this.")
        _, disagreements = summarize([refusal])
        self.assertEqual([d["question"] for d in disagreements], ["covered?"])

    def test_quote_check_counts_leave_refusals_apart(self):
        """The quote check is counted over answers that have a quote; refusals get their own line."""
        refusal = dict(_rec("not supported", "faithful"), answer="The document does not cover this.")
        text, _ = summarize([_rec("supported", "faithful"), _rec("supported", "faithful"),
                             _rec("not supported", "partial"), refusal])
        self.assertIn("Supported    : 2/3", text)
        self.assertIn("Not supported: 1/3", text)
        self.assertIn("Refused (not in the document, no quote to check): 1/4", text)
        self.assertIn("Faithful  : 3/4", text)

    def test_only_refusals_no_crash(self):
        """A run where every answer is a refusal has no quote-check percentages to divide by zero."""
        refusal = dict(_rec("not supported", "faithful"), answer="The document does not cover this.")
        text, disagreements = summarize([refusal, refusal])
        self.assertIn("Refused (not in the document, no quote to check): 2/2", text)
        self.assertNotIn("Supported    :", text)
        self.assertEqual(disagreements, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
