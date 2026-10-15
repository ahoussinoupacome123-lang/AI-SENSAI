#!/usr/bin/env python3
"""Compare a generated answers.md with an expected-answers file and score the run (task P7).

    python scripts/e2e_check.py data/answers.md data/expected_answers.md [--min-pages N]

Expected file: one line per question, `number | page P | key phrase` for a covered
question, or `number | none |` for a question the PDF does not cover. Other lines
(titles, comments, blank lines) are ignored.

    1 | page 3 | The OSI model has seven layers
    9 | none |

A covered question passes when the answer cites page P. The quote is also checked:
the key phrase must appear in the answer's quote (case and spaces ignored). An
uncovered question passes when the answer is a refusal ("does not cover this").
Exit code 0 when enough pages are right and every uncovered question is refused.
"""
import argparse
import math
import re
import sys
from pathlib import Path

SECTION = re.compile(r"<!-- sensai:section (\d+) -->\n(.*?)<!-- /sensai:section \1 -->", re.DOTALL)
EXPECTED = re.compile(r"^\s*(\d+)\s*\|\s*(?:page\s*(\d+)|none)\s*\|\s*(.*?)\s*$", re.IGNORECASE)


def norm(text):
    return " ".join(text.lower().split())


def parse_answers(text):
    found = {}
    for match in SECTION.finditer(text):
        body = match.group(2)
        field = lambda name: (re.search(rf"\*\*{name}:\*\*\s*(.*)", body) or [None, ""])[1].strip()
        quote = " ".join(line[2:] for line in body.splitlines() if line.startswith("> "))
        page = field("Page")
        found[int(match.group(1))] = {
            "answer": field("Answer"), "page": int(page) if page.isdigit() else 0, "quote": quote,
            "status": field("Quote check"), "judge": field("Judge"),
        }
    return found


def parse_expected(text):
    expected = {}
    for line in text.splitlines():
        match = EXPECTED.match(line)
        if match:
            expected[int(match.group(1))] = (int(match.group(2)) if match.group(2) else None, match.group(3))
    return expected


def is_refusal(answer):
    return "does not cover" in answer["answer"].lower() or (not answer["quote"] and answer["page"] == 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("answers")
    parser.add_argument("expected")
    parser.add_argument("--min-pages", type=int, help="pages that must be right (default: 70%% of covered)")
    args = parser.parse_args(argv)
    try:
        answers = parse_answers(Path(args.answers).read_text(encoding="utf-8"))
        expected = parse_expected(Path(args.expected).read_text(encoding="utf-8"))
    except OSError as e:
        sys.exit(f"Error: {e}")
    if not expected:
        sys.exit("Error: no expected answers found (format: `1 | page 3 | key phrase`).")

    covered = {n: v for n, v in expected.items() if v[0] is not None}
    pages_ok = quotes_ok = supported = refusals_ok = 0
    print(f"{'Q':>2}  {'expected':<9} {'answered':<9} {'page':<5} {'quote':<6} {'check':<14} judge")
    for n in sorted(expected):
        page, phrase = expected[n]
        a = answers.get(n)
        if a is None:
            print(f"{n:>2}  {'p' + str(page) if page else 'none':<9} {'(missing)':<9} FAIL")
            continue
        if page is None:
            ok = is_refusal(a)
            refusals_ok += ok
            print(f"{n:>2}  {'none':<9} {'refused' if ok else 'ANSWERED':<9} {'ok' if ok else 'FAIL':<5} {'-':<6} {a['status']:<14} {a['judge']}")
            continue
        page_ok = a["page"] == page
        quote_ok = bool(phrase) and norm(phrase) in norm(a["quote"])
        pages_ok += page_ok
        quotes_ok += quote_ok
        supported += a["status"] == "supported"
        print(f"{n:>2}  {'p' + str(page):<9} {'p' + str(a['page']):<9} {'ok' if page_ok else 'FAIL':<5} "
              f"{'ok' if quote_ok else 'FAIL':<6} {a['status']:<14} {a['judge']}")

    uncovered = len(expected) - len(covered)
    need = args.min_pages if args.min_pages is not None else math.ceil(0.7 * len(covered))
    print(f"\ncovered questions: right page {pages_ok}/{len(covered)}, key phrase in quote {quotes_ok}/{len(covered)}, "
          f"quote check supported {supported}/{len(covered)}")
    print(f"uncovered questions: refused {refusals_ok}/{uncovered}")
    passed = pages_ok >= need and refusals_ok == uncovered
    print(f"RESULT: {'PASS' if passed else 'FAIL'} (needs {need} right pages and every uncovered question refused)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
