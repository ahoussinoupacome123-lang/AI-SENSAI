"""Run summary and quote/judge disagreement flag (M6).

Takes the list of Checked answer dicts produced by pipeline.answer() + judge.evaluate()
and returns a human-readable summary string plus a list of disagreeing records.

Each Checked record is expected to have:
  - status   : "supported" | "not supported"
  - verdict  : "faithful" | "partial" | "unfaithful" | "unknown"
  - question : str
  - answer   : str (optional; "The document does not cover this." marks a refusal)
"""

REFUSAL = "the document does not cover this"


def is_refusal(rec):
    """The model said the document does not cover the question, so there is no quote to check."""
    return str(rec.get("answer", "")).strip().lower().startswith(REFUSAL)


def disagrees(rec):
    """The two quality signals contradict each other.

    For an answer with a quote: the quote check and the judge disagree. For a refusal there is
    no quote to check, so a "not supported" status means nothing; the refusal is only flagged
    when the judge says the passages do answer the question (verdict "unfaithful").
    """
    status, verdict = rec.get("status", "not supported"), rec.get("verdict", "unknown")
    if is_refusal(rec):
        return verdict == "unfaithful"
    return ((status == "supported" and verdict == "unfaithful")
            or (status == "not supported" and verdict == "faithful"))


def summarize(checked_list):
    """Return (summary_text, disagreements) for a completed run.

    Parameters
    ----------
    checked_list : list of Checked dicts.
        Each dict must have 'status' and 'verdict' keys.
        Optional 'question' key is used in the disagreements list.

    Returns
    -------
    summary_text : str   – multi-line text the CLI can print.
    disagreements : list of Checked dicts where quote-check and judge disagree.

    A disagreement is when (see disagrees()):
    - status == "supported"  AND verdict == "unfaithful"
    - status == "not supported" AND verdict == "faithful", except for a refusal
    - a refusal that the judge calls "unfaithful"

    The quote-check counts cover the answers that have a quote; refusals are counted apart.
    """
    n = len(checked_list)

    if n == 0:
        return "No questions were run.", []

    # Verdict counts
    verdict_counts = {"faithful": 0, "partial": 0, "unfaithful": 0, "unknown": 0}
    supported_count = 0
    refusals = 0
    disagreements = []

    for rec in checked_list:
        verdict = rec.get("verdict", "unknown")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        if is_refusal(rec):
            refusals += 1
        elif rec.get("status", "not supported") == "supported":
            supported_count += 1
        if disagrees(rec):
            disagreements.append(rec)

    quoted = n - refusals
    supported_pct = round(100 * supported_count / quoted) if quoted else 0
    faithful_pct = round(100 * verdict_counts["faithful"] / n)
    partial_pct = round(100 * verdict_counts["partial"] / n)
    unfaithful_pct = round(100 * verdict_counts["unfaithful"] / n)

    lines = [
        f"Run complete – {n} question(s) processed.",
        "",
        "Quote check:",
    ]
    if quoted:
        lines += [f"  Supported    : {supported_count}/{quoted}  ({supported_pct}%)",
                  f"  Not supported: {quoted - supported_count}/{quoted}  ({100 - supported_pct}%)"]
    if refusals:
        lines.append(f"  Refused (not in the document, no quote to check): {refusals}/{n}")
    lines += [
        "",
        "Judge verdicts:",
        f"  Faithful  : {verdict_counts['faithful']}/{n}  ({faithful_pct}%)",
        f"  Partial   : {verdict_counts['partial']}/{n}  ({partial_pct}%)",
        f"  Unfaithful: {verdict_counts['unfaithful']}/{n}  ({unfaithful_pct}%)",
    ]
    if verdict_counts["unknown"]:
        lines.append(f"  Unknown   : {verdict_counts['unknown']}/{n}")

    if disagreements:
        lines.append("")
        lines.append(f"⚠ {len(disagreements)} answer(s) where quote check and judge disagree – review manually:")
        for rec in disagreements:
            q = rec.get("question", "(no question)")
            lines.append(f"  · [{rec.get('status')} / {rec.get('verdict')}] {q}")
    else:
        lines.append("")
        lines.append("✓ No disagreements between quote check and judge.")

    return "\n".join(lines), disagreements
