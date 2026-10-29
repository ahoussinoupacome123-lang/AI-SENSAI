"""Wiring only: read args and config, ingest once, loop over questions, print the summary.

    python -m src.cli <pdf> <questions.txt> [--only N] [--force] [--output FILE] [--config FILE]
    python -m src.cli <pdf>                  [--force] [--output FILE] [--config FILE]   (interactive)

Without a questions file the tool opens a prompt: type a question, read the sourced answer,
type the next one. Every answer is still written as a section of the answers file.
"""
import argparse
import json
import sys
from pathlib import Path

from src import eval_summary, ingestion, judge, pipeline, writer

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_CONFIG = ("host", "chat_model", "embed_model", "chunk_size", "chunk_overlap", "top_k")


class CliError(Exception):
    """A usage or input problem. The message is printed as 'Error: ...'."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="Answer a list of questions about a PDF and write a sourced answers.md.",
    )
    parser.add_argument("pdf", help="the text PDF to read")
    parser.add_argument("questions", nargs="?",
                        help="text file with one question per line (omit it to ask questions interactively)")
    parser.add_argument("--only", type=int, metavar="N",
                        help="answer only question number N (1-based); other sections stay untouched")
    parser.add_argument("--force", action="store_true",
                        help="rebuild the index even if one exists (use after changing chunk settings)")
    parser.add_argument("--output", help="answers file (default: answers.md next to the PDF)")
    parser.add_argument("--config", default=str(ROOT / "config.json"), help="settings file")
    parser.add_argument("--no-judge", action="store_true", help="disable judge evaluation")
    parser.add_argument("--no-rag", action="store_true", help="disable RAG passage retrieval")
    parser.add_argument("--no-quote-check", action="store_true", help="disable word-for-word quote verification")
    return parser.parse_args(argv)


def load_config(path):
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CliError(f"config file not found: {path}")
    except (OSError, json.JSONDecodeError) as e:
        raise CliError(f"cannot read config file {path}: {e}")
    missing = [key for key in REQUIRED_CONFIG if key not in config]
    if missing:
        raise CliError(f"config file {path} is missing: {', '.join(missing)}")
    if "feature_flags" in config:
        flags = config["feature_flags"]
        flags.setdefault("rag", True)
        flags.setdefault("judge", True)
        flags.setdefault("quote_check", True)
        flags.setdefault("cache", True)
    return config


def read_questions(path):
    """One question per line; blank lines are ignored."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise CliError(f"questions file not found: {path}")
    except (OSError, UnicodeDecodeError) as e:
        raise CliError(f"cannot read questions file {path}: {e}")
    questions = [line.strip() for line in lines if line.strip()]
    if not questions:
        raise CliError(f"no questions found in {path} (write one question per line)")
    return questions


def _not_implemented(error):
    """Name the unfinished function from the traceback, for example 'ollama_client.py:embed'."""
    frame = error.__traceback__
    while frame and frame.tb_next:
        frame = frame.tb_next
    if frame is None:
        return "a required module is not implemented yet"
    code = frame.tb_frame.f_code
    return f"{Path(code.co_filename).name}:{code.co_name} is not implemented yet"


def _disagree(checked):
    """The cheap quote check and the judge contradict each other."""
    verdict = checked.get("verdict")
    return ((checked.get("status") == "supported" and verdict == "unfaithful")
            or (checked.get("status") == "not supported" and verdict == "faithful"))


def answer_question(question, records, config):
    """Retrieve the best chunks and answer, then judge if the pipeline did not already.

    A missing or failing judge never loses the answer: it is just left unevaluated
    (judge not implemented) or marked 'unknown' (judge error).
    Honors feature_flags in config (rag, judge, quote_check).
    """
    flags = config.get("feature_flags", {})
    use_rag = flags.get("rag", True)
    use_judge = flags.get("judge", True)
    use_quote = flags.get("quote_check", True)

    if use_rag:
        checked = dict(pipeline.retrieve_and_answer(question, records, config))
    else:
        checked = dict(pipeline.answer(question, [], config))
        checked.setdefault("status", "no-rag")
        checked.setdefault("page", 0)
        checked.setdefault("quote", "")
        checked.setdefault("chunks", [])

    checked.setdefault("question", question)

    if not use_quote:
        checked["status"] = "skipped"

    if use_judge:
        if "verdict" not in checked:
            try:
                checked.update(judge.evaluate(question, checked.get("answer", ""),
                                              checked.get("chunks", []), config))
            except NotImplementedError:
                pass
            except Exception as e:  # noqa: BLE001 - one judge failure must not stop the run
                checked.update(verdict="unknown", reason=f"judge failed: {e}")
    else:
        checked["verdict"] = "disabled"
        checked["reason"] = "Judge evaluation disabled by feature flag."

    checked.setdefault("disagreement", _disagree(checked) if use_judge and use_quote else False)
    return checked


def build_summary(total, answered, failed, output):
    """answered: list of (index, checked); failed: list of (index, message).

    The quote-check and judge statistics come from eval_summary.summarize (M6).
    """
    lines = [f"Done: {len(answered)}/{total} questions answered, {len(failed)} failed -> {output}"]
    if answered:
        text, _ = eval_summary.summarize([checked for _, checked in answered])
        lines += ["", text]
    for index, message in failed:
        lines.append(f"Failed: Q{index} ({message})")
    return "\n".join(lines)


def format_answer(checked):
    """The answer as a few readable lines for the terminal."""
    page = checked.get("page")
    quote = " ".join(str(checked.get("quote", "")).split())
    verdict = checked.get("verdict")
    judge_text = f"{verdict} - {checked['reason']}" if verdict and checked.get("reason") else (verdict or "not evaluated")
    lines = ["", f"Answer: {str(checked.get('answer', '')).strip()}",
             f"Page:   {page if isinstance(page, int) and page > 0 else '-'}",
             f"Quote:  \"{quote}\"" if quote else "Quote:  (none)",
             f"Checks: quote check {checked.get('status')}; judge {judge_text}"]
    if checked.get("disagreement"):
        lines.append("Review: the quote check and the judge disagree, compare with the page before trusting it.")
    return "\n".join(lines)


def next_section_number(output):
    """Continue after the sections already in the answers file, so earlier answers are never overwritten."""
    try:
        found = writer.sections(Path(output).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return 1
    return max(found, default=0) + 1


def interactive(pdf, records, config, output, read=input):
    """Ask questions one at a time at a prompt. Enter 'exit' (or Ctrl+D) to finish."""
    number = next_section_number(output)
    print(f"Answers are saved to {output} (starting at Q{number}).")
    print(f"Ask questions about {pdf.name}. Type 'exit' or press Ctrl+D to quit; Ctrl+C cancels a question.")
    answered, failed = [], []
    while True:
        try:
            question = read("\nquestion> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            print("(empty input, please type a question)")
            continue
        if question.lower() in ("exit", "quit"):
            break
        print("  thinking...")
        try:
            checked = answer_question(question, records, config)
            writer.upsert_section(output, number, checked)
        except KeyboardInterrupt:
            print("\n(question cancelled)")
            continue
        except NotImplementedError as e:
            print(f"Error: {_not_implemented(e)}", file=sys.stderr)
            return 1
        except Exception as e:  # noqa: BLE001 - one failed question must not end the session
            print(f"  failed: {e}")
            failed.append((number, str(e)))
            continue
        print(format_answer(checked))
        answered.append((number, checked))
        number += 1
    if answered or failed:
        print()
        print(build_summary(len(answered) + len(failed), answered, failed, output))
    return 1 if failed and not answered else 0


def main(argv=None, read=input):
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        if args.no_judge or args.no_rag or args.no_quote_check:
            flags = config.setdefault("feature_flags", {})
            if args.no_judge:
                flags["judge"] = False
            if args.no_rag:
                flags["rag"] = False
            if args.no_quote_check:
                flags["quote_check"] = False

        pdf = Path(args.pdf)
        if not pdf.is_file():
            raise CliError(f"PDF not found: {pdf}")
        if args.questions is None and args.only is not None:
            raise CliError("--only needs a questions file (it picks one question from the file)")
        questions = read_questions(args.questions) if args.questions else []
        if args.only is not None and not 1 <= args.only <= len(questions):
            count = len(questions)
            raise CliError(f"--only {args.only} is out of range: the file has "
                           f"{count} question{'' if count == 1 else 's'}")
        output = Path(args.output) if args.output else pdf.with_name("answers.md")
        records = ingestion.ingest(pdf, config, force=args.force)
    except NotImplementedError as e:
        print(f"Error: {_not_implemented(e)}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001 - CliError, IngestionError, Ollama errors
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.questions is None:
        try:
            return interactive(pdf, records, config, output, read=read)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
    print(f"Answers will be written to {output}")
    selected = [(i, q) for i, q in enumerate(questions, start=1) if args.only in (None, i)]
    answered, failed, interrupted = [], [], False
    for position, (index, question) in enumerate(selected, start=1):
        print(f"[{position}/{len(selected)}] Q{index}: {question}")
        try:
            checked = answer_question(question, records, config)
            writer.upsert_section(output, index, checked)
        except KeyboardInterrupt:
            print("\nInterrupted: answers written so far are kept.")
            interrupted = True
            break
        except NotImplementedError as e:
            print(f"Error: {_not_implemented(e)}", file=sys.stderr)
            return 1
        except Exception as e:  # noqa: BLE001 - one failed question must not stop the run
            print(f"  failed: {e}")
            failed.append((index, str(e)))
            continue
        answered.append((index, checked))
        judge_text = checked.get("verdict", "not evaluated")
        print(f"  {checked['status']}, page {checked['page']}, judge: {judge_text}")

    print()
    print(build_summary(len(selected), answered, failed, output))
    if interrupted:
        return 130
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
