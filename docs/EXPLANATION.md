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
   7. writer updates ONLY this question's section in answers.md
end: print "7/8 answers supported, 1 failed"
```

If the PDF does not contain the answer, the system prompt tells the model to say "The document does not cover this" with an empty quote. That is the demo moment that shows the tool does not invent.

---

## 5. How the project is built

**Base loop (done)**: a working CLI chatbot (`src/chat.py`) with streaming, history, system prompt from a file, model chosen by argument or config, clean errors. It earns no points alone but it is the foundation: its Ollama-calling code becomes `ollama_client.py`.

**Features (next)**: add the pieces on top, in this order:
1. `ollama_client.py`: the one place that talks to Ollama (chat, JSON schema, embeddings).
2. `ingestion.py` + `store.py` (R1).
3. `pipeline.py` (retrieve, prompt, JSON, retry) (R1 + T5).
4. `writer.py` and the quote check (M4).

Read next: `USE_CASE.md` (why), `USER_STORIES.md` (what must work), `ARCHITECTURE.md` (how the files fit), `MODEL_SELECTION.md` (which models and why).

---

## 6. Questions you should be able to answer at the keynote

- Why can't we give the whole PDF to the model? (context window)
- What is an embedding, and why does it find passages with different words? (meaning as numbers)
- What is cosine similarity? (angle between vectors)
- Why chunk with overlap? Why store the page number?
- Why force JSON? What happens when the model breaks it? (validate, retry, never write on failure)
- How do you know an answer is not invented? What does your check prove and not prove?
- Why a local model? (privacy, no cost, works offline)
