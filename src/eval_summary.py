"""Run summary and quote/judge disagreement flag (M6).

Takes the list of Checked answer dicts produced by pipeline.answer() + judge.evaluate()
and returns a human-readable summary string plus a list of disagreeing records.

Each Checked record is expected to have:
  - status   : "supported" | "not supported"
  - verdict  : "faithful" | "partial" | "unfaithful" | "unknown"
  - question : str
"""


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

    A disagreement is when:
    - status == "supported"  AND verdict == "unfaithful"
    - status == "not supported" AND verdict == "faithful"
    """
    n = len(checked_list)

    if n == 0:
        return "No questions were run.", []

    # Verdict counts
    verdict_counts = {"faithful": 0, "partial": 0, "unfaithful": 0, "unknown": 0}
    supported_count = 0
    disagreements = []

    for rec in checked_list:
        status = rec.get("status", "not supported")
        verdict = rec.get("verdict", "unknown")

        if status == "supported":
            supported_count += 1

        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Flag disagreements between the two quality signals
        is_disagreement = (
            (status == "supported" and verdict == "unfaithful")
            or (status == "not supported" and verdict == "faithful")
        )
        if is_disagreement:
            disagreements.append(rec)

    supported_pct = round(100 * supported_count / n)
    faithful_pct = round(100 * verdict_counts["faithful"] / n)
    partial_pct = round(100 * verdict_counts["partial"] / n)
    unfaithful_pct = round(100 * verdict_counts["unfaithful"] / n)

    lines = [
        f"Run complete – {n} question(s) processed.",
        "",
        "Quote check:",
        f"  Supported    : {supported_count}/{n}  ({supported_pct}%)",
        f"  Not supported: {n - supported_count}/{n}  ({100 - supported_pct}%)",
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
