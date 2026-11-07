# Saved verification results

The outputs of the checks, kept in the repository so anyone can read and interpret them without the team. Run on 2026-11-06 on the machine in `machine.txt` (CPU only, 7.6 GiB of RAM) with the committed `config.json` (`qwen3:4b`, `nomic-embed-text`, chunk size 800).

| File | What it is | How to read it |
|---|---|---|
| `machine.txt` | the CPU, RAM and Ollama version of the test machine | context for every timing below |
| `cli_full_run.txt` | the real output of `python -m src.cli data/demo.pdf data/questions.txt`: one line per question, the run summary, and the total time | **8 min 57 s for 9 questions**, 9 of 9 answered, 0 failed |
| `answers_full_run.md` | the `answers.md` that run produced | one section per question with answer, page, quote and both checks |
| `e2e_score.txt` | `scripts/e2e_check.py` comparing that file with `data/expected_answers.md` | **6 of 8 right pages, the uncovered question refused: PASS** |
| `pytest.txt` | `python -m pytest -v`, every test by name | **398 passed**, none needs Ollama |
| `ui_check.txt` | the real-browser checks of the web UI (Chromium, real models) | **63 of 63 passed** |

## Reading the model run honestly

- Q2 (DHCP) gave the right four steps but with page 0, so it **fails the page check**; the two checks disagreed and it was flagged.
- Q6 (SSH port) was **wrongly refused**: the model said the document does not cover it although page 17 does; the judge said `unfaithful` and the answer was flagged.
- Q9 (not in the PDF) was correctly refused and is **not** flagged (a correct refusal no longer raises a false alarm).
- Earlier recorded runs (5 min 31 s and 6 min 42 s) are in [../../RESULTS.md](../../RESULTS.md); the spread comes from free RAM (about 0.5 GiB stays free during a run).

## Negative cases (an expected error, not a success)

The test suite checks that bad input gives a clear error and leaves no damage. Examples, by test name (all in `pytest.txt`):

| Situation | Test |
|---|---|
| a scanned PDF (no text) | `test_scanned_pdf_raises_no_text_error`, `test_scanned_pdf_raises_and_embeds_nothing` |
| a missing or empty file | `test_missing_file_gives_clear_error`, `test_empty_file_gives_clear_error`, `test_missing_pdf_is_a_clear_error` |
| a question the PDF does not cover | the refusal path: `test_empty_quote_is_not_supported`, `test_disputed_refusal_explains_why`; Q9 above |
| a section that cannot be written | `test_failed_or_incomplete_answer_leaves_the_file_untouched`, `test_failure_while_writing_keeps_the_old_file_and_cleans_up` |
| the model never returns valid JSON | `test_always_invalid_raises_answer_error`, `test_one_failed_question_does_not_stop_the_run` |
| a bad question number or file | `test_only_out_of_range_is_a_clear_error`, `test_empty_questions_file_is_a_clear_error` |
| a corrupt saved index | `test_unreadable_or_invalid_index_gives_a_message_that_says_how_to_fix_it` |
| a hostile or oversized web request | `test_a_request_addressed_to_another_host_is_refused`, `test_a_cross_site_post_is_refused`, `test_upload_that_is_too_large_is_refused`, `test_upload_rejects_a_scanned_pdf_with_a_clear_message` |

## Regenerate them

```bash
bash scripts/save_verification.sh            # pytest.txt and e2e_score.txt (no model needed, a few seconds)
# the model run (about 9 minutes) and the browser checks:
python -m src.cli data/demo.pdf data/questions.txt --output /tmp/answers.md
python scripts/e2e_check.py /tmp/answers.md data/expected_answers.md
python WEB-UI/server.py &  python WEB-UI/e2e/ui_check.py       # needs playwright, see docs/TESTING.md
```
