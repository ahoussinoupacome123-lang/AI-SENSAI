#!/usr/bin/env python3
"""Build data/demo.pdf from data/demo_course.txt and check it against the expected answers.

    python scripts/build_demo_pdf.py

The course text is original material written for this project (24 short chapters about
computer networks, one chapter per PDF page). The script
  1. wraps every chapter onto one PDF page and writes data/demo.pdf,
  2. re-reads the PDF with src.ingestion (the same code the product uses),
  3. checks that each key phrase in data/expected_answers.md is on the stated page and on no
     other page, that words keep their spaces, and that the uncovered question is really
     not covered by the text.
Exit code 0 when everything is consistent.
"""
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from pdf_factory import make_text_pdf  # noqa: E402
from src.ingestion import extract_pages  # noqa: E402

DATA = ROOT / "data"
LINE_WIDTH = 84
MAX_LINES = 46
EXPECTED = re.compile(r"^\s*(\d+)\s*\|\s*(?:page\s*(\d+)|none)\s*\|\s*(.*?)\s*$", re.IGNORECASE)
FORBIDDEN_FOR_UNCOVERED = ("invent", "berners", "cern ")


def norm(text):
    return " ".join(text.lower().split())


def build_pages(source):
    pages = []
    for chapter in re.split(r"^=====\s*$", source, flags=re.MULTILINE):
        paragraphs = [p.strip() for p in chapter.strip().split("\n\n") if p.strip()]
        lines = []
        for number, paragraph in enumerate(paragraphs):
            if number:
                lines.append("")
            lines += textwrap.wrap(" ".join(paragraph.split()), LINE_WIDTH)
        if len(lines) > MAX_LINES:
            sys.exit(f"Error: a chapter needs {len(lines)} lines, the page holds {MAX_LINES}: {lines[0]}")
        pages.append("\n".join(lines))
    return pages


def main():
    pages = build_pages((DATA / "demo_course.txt").read_text(encoding="utf-8"))
    pdf = DATA / "demo.pdf"
    make_text_pdf(pdf, pages)
    extracted = extract_pages(pdf)
    print(f"wrote {pdf.relative_to(ROOT)}: {len(extracted)} pages, {sum(len(t) for _, t in extracted)} characters")

    problems = []
    if len(extracted) != len(pages):
        problems.append(f"page count {len(extracted)} != {len(pages)}")
    glued = [n for n, text in extracted if re.search(r"[a-z]{25,}", text)]
    if glued:
        problems.append(f"words without spaces on pages {glued}")

    by_page = {n: norm(text) for n, text in extracted}
    questions = [q.strip() for q in (DATA / "questions.txt").read_text(encoding="utf-8").splitlines() if q.strip()]
    expected = {}
    for line in (DATA / "expected_answers.md").read_text(encoding="utf-8").splitlines():
        match = EXPECTED.match(line)
        if match:
            expected[int(match.group(1))] = (int(match.group(2)) if match.group(2) else None, match.group(3))
    if sorted(expected) != list(range(1, len(questions) + 1)):
        problems.append(f"expected answers cover {sorted(expected)} but there are {len(questions)} questions")

    for number, (page, phrase) in sorted(expected.items()):
        if page is None:
            hits = [w for w in FORBIDDEN_FOR_UNCOVERED if any(w in text for text in by_page.values())]
            status = "ok" if not hits else f"FAIL (text contains {hits})"
            if hits:
                problems.append(f"Q{number}: uncovered question is covered by the text: {hits}")
            print(f"Q{number}: not covered ........ {status}")
            continue
        found = [n for n, text in by_page.items() if norm(phrase) in text]
        ok = found == [page]
        if not ok:
            problems.append(f"Q{number}: phrase {phrase!r} found on pages {found}, expected only [{page}]")
        print(f"Q{number}: page {page:>2} ............ {'ok' if ok else 'FAIL, found on ' + str(found)}")

    print("\nRESULT:", "OK" if not problems else "PROBLEMS")
    for problem in problems:
        print(" -", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
