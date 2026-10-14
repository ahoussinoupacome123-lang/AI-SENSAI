# Sensai – User Stories

Format: *As a type of user, I want to action, so that outcome*, followed by observable acceptance criteria. At least two stories per feature.

Users: **Student** (prepares exams from course PDFs), **Researcher** (extracts answers from reports and papers).

---

## B1 – CLI chatbot (base)

**US-B1.1** As a student, I want to start the tool with a model name, so that I can use the model that fits my computer.
- `python src/chat.py qwen3:4b` uses that model; with no argument the model in `config.json` is used.
- Switching models needs no code change.

**US-B1.2** As a student, I want clear messages when something is wrong, so that I know how to fix it.
- Empty input is ignored with a hint.
- Ollama not running: message says to run `ollama serve`.
- Model not pulled: message gives the exact `ollama pull <model>` command.
- No traceback in any of these cases.

## R1 – Basic RAG

**US-R1.1** As a student, I want to give the tool a PDF, so that its content becomes searchable.
- Text is extracted per page, chunked with overlap, embedded and stored in a local file.
- A message shows the number of pages and chunks.
- A scanned/image-only or unreadable PDF gives a clear error, not a crash.

**US-R1.2** As a student, I want each question answered from the most relevant passages, so that answers are about my document and not general knowledge.
- For each question the top-k chunks by cosine similarity go into the prompt.
- Each chunk keeps its page number.
- A question the PDF does not cover gets an answer saying the document does not cover it.

## T5 – Structured output

**US-T5.1** As a developer, I want the model to answer in a fixed JSON schema (`answer`, `page`, `quote`), so that code can place content reliably.
- The schema is defined in one place in the code.
- A response that violates the schema is rejected and retried (at most 2 retries).

**US-T5.2** As a researcher, I want a failure on one question not to ruin the run, so that I still get the other answers.
- After the retries fail, that question is reported as failed and the file is not modified for it.
- The run continues with the next question.

## M4 – Answers file as a living document

**US-M4.1** As a researcher, I want my questions answered into one Markdown file, so that I get a deliverable and not a chat transcript.
- `answers.md` has one section per question.
- Each section shows the answer, the page number and a short quote.
- The file is readable in any text editor.

**US-M4.2** As a researcher, I want to re-run or add one question without losing the rest, so that I can refine incrementally.
- Re-running question 3 changes only section 3; other sections are byte-for-byte identical (tested).
- A new question appends a new section.

## Quote check (safeguard)

**US-Q.1** As a student, I want to know which answers are not backed by my document, so that I do not study wrong information.
- The quote must appear in the retrieved text (case and extra spaces ignored).
- If it does not, the section is marked "not supported".
- At the end of the run the tool prints the share of supported answers.

**US-Q.2** As a researcher, I want that summary score, so that I can compare two models or settings.
- The same question list run with two models gives two comparable scores.

## EV1 – Automated evaluation and hallucination detection

**US-EV1.1** As a student, I want each answer judged against the passages it was built from, so that I can tell which answers I can trust.
- Each section of `answers.md` shows a verdict (`faithful`, `partial` or `unfaithful`) and a one-line reason.
- An answer that says something the passages do not support is marked `unfaithful`.
- The judge sees only the question, the answer and the retrieved passages.

**US-EV1.2** As a researcher, I want a score for the whole run, so that I can compare two settings (chunk size, top-k, model).
- At the end of the run the tool prints the share of `faithful`, `partial` and `unfaithful` answers.
- Running the same questions with two configurations gives two comparable scores.

**US-EV1.3** As a student, I want to see where the quote check and the judge disagree, so that I know which answers to read myself.
- When the quote check says `supported` but the judge says `unfaithful` (or the reverse), the section is flagged for review.
