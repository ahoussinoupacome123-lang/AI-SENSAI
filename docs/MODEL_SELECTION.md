# Sensai – Models & Hardware

Based on the project subject and this machine (checked 2026-10-11). Speeds are estimates until measured with `ollama run <model> --verbose`.

## 1. The machine
- CPU: Intel Core 7 240H, 10 cores / 16 threads. **No usable GPU** for Ollama, so everything runs on CPU.
- RAM: under WSL the machine shows 7.6 GiB total and about 3.9 GiB available (checked 2026-10-14; WSL gets half of the 15 GiB unless `.wslconfig` raises it). **RAM is the bottleneck**: model plus working memory must fit or the system swaps and becomes very slow.
- Ollama 0.40.4 installed. Rule of thumb for Q4 models: about 0.6 GB per billion parameters plus 0.5-1.5 GB of working memory.

## 2. The two models we use (and nothing else)

| Stage | Model | Size | Why |
|---|---|---|---|
| Chatbot, answers and EV1 judge | `qwen3:4b` | ~2.5 GB | Handles JSON schemas and instructions well for its size; this tag is a thinking model: keep thinking on (tested: `think=false` makes it leak its reasoning into the answer); the reasoning arrives in a separate field that we ignore, and costs about 10 s per call |
| Embeddings | `nomic-embed-text` | ~0.3 GB | Separate model that turns text into vectors; used through `/api/embed` |

If memory is too tight: fall back to `qwen3:1.7b` for chat (1B-class models are weaker at JSON).

```bash
ollama pull qwen3:4b
ollama pull nomic-embed-text
curl http://localhost:11434        # -> "Ollama is running"
```

Check names with `ollama list`; tags and sizes come from general knowledge and may differ slightly.

## 3. The EV1 judge model
The judge reuses `qwen3:4b` with its default thinking and a very short output (a verdict and one sentence). Reasons:
- Only one chat model is loaded, so no extra RAM and no model-swap delay during the demo.
- The task is easy for a small model: compare an answer with the passages and pick one of three labels.
- Known limit: a model judging its own output tends to be lenient. We keep the quote check as an independent anchor and report disagreements honestly.
- Optional experiment, not required: judge a few answers with a bigger model (for example `qwen3:8b`, about 5 GB) offline to measure how often the 4b judge agrees.
- With 8 GB of RAM in total, `qwen3:4b` plus `nomic-embed-text` (about 3 GB together) fits next to the OS. An 8b judge would not fit comfortably or run fast without a GPU.

## 4. Why not bigger
A 7-8B model answers better but with ~5 GB free and no GPU it swaps and runs at a few tokens per second. A slow or crashing live demo is a bigger risk than a slightly weaker answer.

## 5. Practical advice
1. Close browsers and apps before working; aim for 6 GB or more available (`free -h`).
2. Keep `num_ctx` at 4096 (a bigger context uses more RAM).
3. Keep one chat model loaded at a time (`OLLAMA_MAX_LOADED_MODELS=1`).
4. Make model, host and prompt path configurable in `config.json`.
5. Before the demo pre-warm the model (`ollama run qwen3:4b ""`) and record a fallback video.
