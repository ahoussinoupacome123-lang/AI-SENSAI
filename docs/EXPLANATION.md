# Sensai explained from zero

Read this file first. It explains every idea in the project in plain words, with no prior knowledge assumed. If a word in another document confuses you, look it up here.

---

## 1. What are we building?

**Sensai Q&A** is a program that runs on your own computer.

You give it:
1. one **PDF** (for example a 40-page course), and
2. a text file `questions.txt` with one question per line.

It gives you back:
- a file `answers.md` with one section per question. Each section has the **answer**, the **page number** where the answer was found, and a **short quote** copied from the PDF.

Why not just ask ChatGPT? Three reasons:
- ChatGPT has not read *your* PDF and may invent ("hallucinate") an answer.
- Your PDF may be private, so it must not leave your machine.
- Doing it by hand takes hours.

---

## 2. The big problem: a small model cannot read a whole PDF

A language model (LLM) can only look at a limited amount of text at once. That limit is called the **context window**. A 60-page PDF is far too long for a small local model. So we cannot paste the whole PDF in the prompt.

The solution is to **search the PDF first**, find the 3-4 small passages that matter for a question, and give only those to the model. This technique is called **RAG** (Retrieval-Augmented Generation):

> **Retrieve** the right passages, then **Generate** the answer from them.

Everything else in the project is built around this idea.

---

## 3. The vocabulary, one word at a time

**LLM (language model)**: a program that predicts text. You send it text, it sends text back. Ours is `qwen3:4b`. The "3b/4b" means 3 or 4 billion parameters: small enough for a laptop.

**Ollama**: a program that runs LLMs on your computer and exposes them through a local web address, `http://localhost:11434`. Our Python code sends HTTP requests to it with the `requests` library. The subject forbids LangChain and similar frameworks, so we talk to Ollama directly.

**Prompt**: the text we send to the model. **System prompt**: a first message that tells the model how to behave ("you are a careful assistant"). We keep it in a file so we can change it without touching code.

**Token**: a piece of a word (about 3/4 of an English word). Models count text in tokens.

**Streaming**: the model sends its answer piece by piece, so you see it appear progressively instead of waiting for the end.

**History**: the list of earlier messages. The model has no memory, so on each turn we re-send the whole conversation.

**Chunk**: a small piece of the PDF text, for example 800 characters. We cut the PDF into chunks because they are small enough to compare and to fit in a prompt. Each chunk remembers its **page number**. Chunks **overlap** a little (say 150 characters) so a sentence cut at the border still appears whole in one chunk.

**Embedding**: a list of numbers (for example 768 of them) that represents the *meaning* of a text. Two texts with similar meaning get similar lists, even with different words. "How do plants make food?" and "photosynthesis converts light into sugar" end up close together. A special model, `nomic-embed-text`, produces these lists.

**Vector**: just another word for that list of numbers.

**Cosine similarity**: a score from -1 to 1 saying how much two vectors point the same way. Close to 1 means "very similar meaning". Tiny example with 2 numbers:
- question = [1, 0]; chunk A = [0.9, 0.1]; chunk B = [0, 1].
- A points almost the same direction as the question, so its score is about 0.99. B is perpendicular, so its score is 0.
- We pick A. Real vectors have hundreds of numbers, but the idea is identical.

**Vector store**: where we save chunks with their vectors so we do not recompute them. For us it is a simple file (JSON) next to the PDF. No database needed.

**Ingestion**: the one-time preparation of the PDF. Think of it as building the index at the back of a book:
1. extract the text of each page,
2. cut it into overlapping chunks (each keeping its page number),
3. ask the embedding model for one vector per chunk,
4. save chunks + vectors to the store.

You do it once per PDF. After that, questions are fast.

**Retrieval**: for one question, (1) turn the question into a vector, (2) compare it with all chunk vectors using cosine similarity, (3) keep the best **top-k** chunks (k is a setting, for example 4).

**Structured output / JSON schema (feature T5)**: instead of free text, we force the model to answer in a strict shape:

```json
{ "answer": "...", "page": 12, "quote": "exact words from the PDF" }
```

Ollama has a `format` parameter that accepts a JSON schema and constrains the output. Why? Because our code must *use* the answer (put it in a file). Free prose is hard to parse; JSON is easy.

**Retry**: small models sometimes still break the shape. We validate the JSON; if it is wrong we ask again (at most 2 more times). If it keeps failing we report an error for that question and do **not** touch the file.

**Artifact / living document (feature M4)**: `answers.md` is a *deliverable*, not a chat transcript. It is updated section by section. **Upsert** means "update if the section exists, add if it does not". Re-running question 3 must change only section 3; every other byte of the file stays the same.

**Hallucination**: the model states something false or not in the source with confidence. It is the main danger of document Q&A.

**Quote check**: our simple defence. After the model answers, plain code checks that the `quote` really appears (word for word, ignoring extra spaces and case) in the retrieved chunks. If not, the answer is flagged "not supported" in the file. It is deterministic: no second model, no guessing. Limit: it proves the quote exists, not that the answer is a correct reading of it. We say this honestly in the keynote.

**LLM judge (feature EV1)**: a second model call that reads the question, the retrieved passages and the answer, and returns a verdict: `faithful` (everything is supported by the passages), `partial` (some claims are) or `unfaithful` (contradicted or unsupported), with a one-line reason. It reads the whole answer, so it can catch a real quote that is misread, which the quote check cannot. It is the same small model that wrote the answer, so it can be lenient: that is why we keep the quote check as an independent anchor.

**Disagreement flag**: when the quote check and the judge contradict each other (quote `supported` but judge `unfaithful`, or quote `not supported` but judge `faithful`), the section is marked "Review needed". A correct refusal has no quote, so it is not flagged; a refusal is flagged only when the judge says the passages do answer the question. It is how a wrong refusal is caught.

**Thinking mode**: `qwen3:4b` reasons silently before it answers (about 10 seconds). In plain chat we leave that on. When we force a JSON schema we turn it off (`think=false`) and use temperature 0: tested, thinking plus a schema can return an empty answer or hang for minutes.

**Refusal**: when the passages do not contain the answer, the model must say "The document does not cover this." with an empty quote instead of guessing. A refusal has no quote, so its quote check shows "not supported".

**Atomic write**: the writer saves the file to a temporary name and then renames it, so a crash can never leave a half-written `answers.md`.

---

## 4. One full run, step by step

```
report.pdf ──ingest──► index.json   (chunks + page numbers + vectors)

questions.txt, for each question:
   1. embed the question               -> vector
   2. find the top 4 closest chunks    -> text + pages
   3. build a prompt: system prompt + the 4 chunks + the question
   4. ask qwen3:4b, forcing the JSON schema -> {answer, page, quote}
   5. validate the JSON (retry if invalid)
   6. quote check: is the quote inside the chunks?  -> supported / not supported
   7. judge: is the answer faithful to the chunks?  -> faithful / partial / unfaithful
   8. writer updates ONLY this question's section in answers.md
end: print the summary (answered / failed, quote check, judge, answers to review)
```

If the PDF does not contain the answer, the system prompt tells the model to say "The document does not cover this" with an empty quote. That is the demo moment that shows the tool does not invent.

---

## 5. How the project is built

**Base loop**: a working CLI chatbot (`src/chat.py`) with streaming, history, system prompt from a file, model chosen by argument or config, clean errors. It earns no points alone but it is the foundation.

**The features, all built** (in the order they were made):
1. `ollama_client.py`: the one place that talks to Ollama (chat, JSON schema, embeddings).
2. `ingestion.py` + `store.py` (R1): PDF to chunks to vectors to a local index, and cosine search.
3. `pipeline.py` (R1 + T5): retrieve, prompt, force the JSON schema, validate, retry.
4. `quote_check.py` and `judge.py` (EV1): two independent checks on every answer, plus `eval_summary.py` for the run summary and the disagreement flag.
5. `writer.py` (M4): update exactly one section of `answers.md`.
6. `cli.py`: wires it all: `python -m src.cli <pdf> <questions.txt>`.

Read next: `USE_CASE.md` (why), `USER_STORIES.md` (what must work), `ARCHITECTURE.md` (how the files fit), `MODEL_SELECTION.md` (which models and why), `RESULTS.md` (what we measured), `KEYNOTE.md` (how we present it).

---

## 6. Questions you should be able to answer at the keynote

Each answer has a short version to say out loud and the reason behind it.

**1. Why can't we give the whole PDF to the model?**
*Say it:* a model reads a limited amount of text at once (its context window); a 40-page PDF does not fit, so we give it only the few passages that matter.
*Behind it:* we set the window to 4096 tokens (about 3,000 words); the demo PDF has about 5,500 words. A bigger window also needs more RAM and is slower, and small models get worse at finding details in long text. So we search first and send only the best 4 chunks: that is RAG.

**2. What is an embedding, and why does it find passages with different words?**
*Say it:* an embedding turns a text into a list of numbers that stands for its meaning; similar meanings give similar numbers, so we find a passage by meaning, not by exact words.
*Behind it:* `nomic-embed-text` gives 768 numbers per text. "How do plants make food?" lands near "photosynthesis turns light into sugar" although they share no word, where a keyword search (Ctrl+F) finds nothing. Chunks and questions are embedded with the same model so they can be compared.

**3. What is cosine similarity?**
*Say it:* a score for how much two vectors point the same way: close to 1 means very similar meaning, close to 0 unrelated.
*Behind it:* two arrows from the same point; a small angle gives a score near 1, a right angle gives 0. With question [1, 0], chunk A [0.9, 0.1] scores about 0.99 and chunk B [0, 1] scores 0, so we pick A. Real vectors have 768 numbers but the idea is the same. We keep the 4 best scores.

**4. Why chunk with overlap? Why store the page number?**
*Say it:* small chunks give sharper matches and fit in the prompt; the overlap keeps a sentence cut at a border whole in one chunk; the page lets the reader check the source.
*Behind it:* a whole page mixes topics, so its embedding is vague. With a 150-character overlap, a sentence split at character 800 still appears whole in the next chunk. The page number is free (we know it when we read the page) and it is the whole point of a sourced answer. Trade-off: too small loses context, too big makes the match vague, so both sizes are settings in `config.json`.

**5. Why force JSON? What happens when the model breaks it?**
*Say it:* our code must use the answer (put it in a file), and free text is hard to parse; so we force a strict shape, validate it, retry twice, and never write a broken result.
*Behind it:* we need three separate fields (`answer`, `page`, `quote`). Ollama's `format` parameter constrains the output to a JSON schema; our code still validates it. After the retries the question is reported as failed, the file is not touched, and the run continues with the next question.

**6. How do you know an answer is not invented? What do your checks prove and not prove?**
*Say it:* the model must give a word-for-word quote; plain code checks that the quote is really in the retrieved text, and a second model call judges the whole answer. The quote check proves the quote exists, not that the answer reads it correctly; the judge reads the whole answer but is a small, lenient model.
*Behind it:* the quote check is deterministic (case, spaces and typography ignored). It cannot tell a misread quote from a right one. The judge can, but it is the same 4B model, so it sometimes misses a wrong refusal. We flag the answers where the two disagree for manual review. We measured this: see `RESULTS.md`.

**7. Why a local model?**
*Say it:* the document stays on the machine, it costs nothing per question, and it works offline.
*Behind it:* course notes, contracts or reports can be confidential, and a cloud API would receive the text. Honest trade-off: a 4B model is weaker than a large cloud model and slow on a laptop CPU (about 40 s per question). We compensate with retrieval, which hands the model exactly the text it needs, and with the two checks, which catch many of its mistakes.
