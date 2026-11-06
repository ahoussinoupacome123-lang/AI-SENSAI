"""Own answers.md: update exactly one section per question, leave the rest untouched.

File layout (the HTML comments are invisible when the Markdown is rendered):

    # Answers

    <!-- sensai:section 1 -->
    ## Q1. What are the layers of the OSI model?
    **Answer:** ...
    **Page:** 2
    > exact quote from the PDF
    **Quote check:** supported
    **Judge:** faithful - the passage lists the layers
    <!-- /sensai:section 1 -->

Sections are found by their markers, never by asking the model to rewrite the file.
"""
import os
import re
import stat
import tempfile
from pathlib import Path

from src import eval_summary

HEADER = "# Answers\n\n"
SECTION_RE = re.compile(
    r"<!-- sensai:section (\d+) -->\n.*?<!-- /sensai:section \1 -->\n\n?", re.DOTALL
)
REQUIRED_FIELDS = ("question", "answer", "page", "quote", "status")


class WriterError(Exception):
    """The answer cannot be written. The file is left untouched."""


def _validate(index, checked):
    if not isinstance(index, int) or isinstance(index, bool) or index < 1:
        raise WriterError(f"Section number must be a positive integer, got {index!r}.")
    if not isinstance(checked, dict):
        raise WriterError("No answer to write (the question failed).")
    if checked.get("error"):
        raise WriterError(f"Refusing to write a failed answer: {checked['error']}")
    missing = [field for field in REQUIRED_FIELDS if field not in checked]
    if missing:
        raise WriterError(f"Answer is incomplete, missing: {', '.join(missing)}.")


def _one_line(text):
    return " ".join(str(text).split())


def render_section(index, checked):
    """Return the Markdown block of one section, ending with a blank line."""
    page = checked["page"]
    page_text = str(page) if isinstance(page, int) and page > 0 else "-"
    quote = str(checked["quote"]).strip()
    quote_text = "\n".join(f"> {line}" for line in quote.splitlines()) if quote else "_(no quote)_"

    verdict = checked.get("verdict")
    if verdict:
        reason = _one_line(checked.get("reason", ""))
        judge = f"{verdict} - {reason}" if reason else str(verdict)
    else:
        judge = "not evaluated"

    lines = [
        f"<!-- sensai:section {index} -->",
        f"## Q{index}. {_one_line(checked['question'])}",
        "",
        f"**Answer:** {str(checked['answer']).strip()}",
        "",
        f"**Page:** {page_text}",
        "",
        quote_text,
        "",
        f"**Quote check:** {checked['status']}",
        f"**Judge:** {judge}",
    ]
    if checked.get("disagreement"):
        if eval_summary.is_refusal(checked):
            lines.append("**Review needed:** the model says the document does not cover this, but the judge says the passages answer it.")
        else:
            lines.append("**Review needed:** the quote check and the judge disagree.")
    lines.append(f"<!-- /sensai:section {index} -->")
    return "\n".join(lines) + "\n\n"


def sections(text):
    """Return {section_number: block_text} for every section found in the file text."""
    return {int(m.group(1)): m.group(0) for m in SECTION_RE.finditer(text)}


def _target_mode(path):
    """Keep the mode of an existing file; for a new file use the usual default (0666 minus umask).

    mkstemp creates private (0600) files, which would otherwise leak into answers.md.
    """
    if path.exists():
        return stat.S_IMODE(path.stat().st_mode)
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def _write_atomically(path, text):
    """Write to a temp file in the same folder, then rename: never a half-written file."""
    directory = path.parent if str(path.parent) else Path(".")
    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(text.encode("utf-8"))
        os.chmod(tmp_name, _target_mode(path))
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def upsert_section(path, index, checked):
    """Replace section `index` if it exists, otherwise insert it in numeric order.

    Everything else in the file stays byte-for-byte identical. A failed or incomplete
    answer raises WriterError and the file is not touched.
    """
    _validate(index, checked)
    path = Path(path)
    text = path.read_bytes().decode("utf-8") if path.exists() else HEADER
    block = render_section(index, checked)

    matches = list(SECTION_RE.finditer(text))
    same = [m for m in matches if int(m.group(1)) == index]
    later = [m for m in matches if int(m.group(1)) > index]
    if same:
        text = text[:same[0].start()] + block + text[same[0].end():]
    elif later:
        text = text[:later[0].start()] + block + text[later[0].start():]
    else:
        text = text.rstrip("\n") + "\n\n" + block

    _write_atomically(path, text)
