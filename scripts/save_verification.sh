#!/usr/bin/env bash
# Re-run the checks that need no model and save their output in docs/examples/verification/.
# Usage (from the project root): bash scripts/save_verification.sh
set -u
cd "$(dirname "$0")/.."
PY=${PYTHON:-python}
OUT=docs/examples/verification
mkdir -p "$OUT"
{ echo "# python -m pytest -v   ($(date -Iseconds))"; $PY -m pytest -v 2>&1; } > "$OUT/pytest.txt"
tail -1 "$OUT/pytest.txt"
if [ -f "$OUT/answers_full_run.md" ]; then
  { echo "# python scripts/e2e_check.py $OUT/answers_full_run.md data/expected_answers.md"
    $PY scripts/e2e_check.py "$OUT/answers_full_run.md" data/expected_answers.md; echo "# exit code: $?"; } > "$OUT/e2e_score.txt" 2>&1
  tail -3 "$OUT/e2e_score.txt"
fi
