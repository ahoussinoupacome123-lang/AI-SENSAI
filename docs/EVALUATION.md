# Sensai – Evaluation Architecture & LLM Framework Analysis

This document addresses two strategic aspects of the Sensai evaluation subsystem:
1. **The LLM Framework Exemption for the Judge** (subject compliance and architectural rationale).
2. **Which model is the judge** (the same `qwen3:4b` by default, and why; `judge_model` can point to another model).

---

## 1. Technical Note: LLM Framework Exemption for the Judge

### 1.1 The Project Rule & Framework Exemption

The Epitech project guidelines establish a strict constraint regarding LLM orchestration frameworks:
> *"No high-level LLM application frameworks (such as LangChain, LlamaIndex, Haystack, AutoGen, or CrewAI) may be used to build the chatbot core or RAG pipeline. All retrieval, prompt assembly, and inference calls must be implemented directly."*

However, the evaluation guideline includes an explicit **exemption for evaluation**:
> *"An external LLM evaluation framework (such as Ragas, DeepEval, or G-Eval) is permitted exclusively for assessing and scoring model outputs in the evaluation / judge phase."*

### 1.2 Our Architectural Choice: Native Direct HTTP vs External Framework

While our team was legally authorized to install an external framework for the Judge component, we conducted an engineering trade-off analysis and made the deliberate design decision to implement our Judge using **native direct HTTP calls to Ollama with constrained JSON schema enforcement**.

Here is why our team chose native direct calls over an external evaluation framework:

| Evaluation Dimension | Native Ollama Judge (`src/judge.py`) | External Framework (e.g. Ragas / DeepEval) |
|---|---|---|
| **Dependency Footprint** | **0 heavy dependencies** (only `requests` + standard library). | **Heavy** (requires PyTorch, HuggingFace transformers, datasets, pydantic v2, or cloud API SDKs: 2.5+ GB disk). |
| **Hardware Compatibility** | Runs smoothly on 8 GB to 16 GB RAM local laptops without GPU. | Frequently triggers CUDA/CPU OOM errors or requires cloud GPU instances. |
| **Offline Privacy** | **100% strictly local and offline**; zero telemetry, zero internet calls. | Many frameworks default to sending telemetry or metrics to external endpoints (e.g., Confident AI). |
| **Calls per Answer** | **One short call** (a verdict and one sentence). | Typically several intermediate calls per metric. |
| **Output Determinism** | Guaranteed valid JSON with `reason` and `verdict` via Ollama's schema mode (`think=false`, `temperature: 0`). | Regex-based parsing of natural language judge outputs, prone to schema breakages and parsing failures. |
| **Auditing & Transparency** | Simple, auditable prompt in `prompts/judge_prompt.txt` visible to jury and users. | Complex multi-stage prompt chains abstracted away behind opaque library classes. |

### 1.3 Key Takeaways for Keynote & Jury Defense
- We did **not** skip frameworks out of ignorance; we deliberately evaluated Ragas and DeepEval, proved the exemption applied, and chose native HTTP direct calls for superior reliability, minimal resource footprint, and zero third-party cloud lock-in.
- Our implementation conforms 100% with the subject spirit: a completely self-contained, reproducible, local AI system.

---

## 2. Which Model Is the Judge

### 2.1 Decision: the same `qwen3:4b`, with a separate setting

By default the judge is the **same model as the chatbot, `qwen3:4b`**, called in schema mode (thinking off, temperature 0). The reasons are in [MODEL_SELECTION.md](MODEL_SELECTION.md): one model is loaded, so there is no extra RAM and no model-swap delay on an 8 GB laptop.

The known cost is that a model judging its own output tends to be lenient and can share its mistakes. We handle it in two ways:
- the quote check stays as an independent, deterministic anchor, and
- answers where the quote check and the judge disagree are flagged for manual review.

The judge has its own setting, so a different model can be tried without touching the code:
```json
{
  "chat_model": "qwen3:4b",
  "judge_model": "qwen3:4b",
  "host": "http://localhost:11434"
}
```
Setting `judge_model` to a larger model (for example `qwen3:8b`) is optional and needs more RAM. **We have not measured a larger judge**, so this project makes no accuracy claim for one.

### 2.2 Operational Resilience & Missing Model Handling

When a user configures a different judge model that has not yet been downloaded to their local Ollama instance:
1. `src/ollama_client.py` catches the HTTP 404 response and raises `ModelNotFoundError`.
2. `src/judge.py` intercepts the error and returns a clean, informative status without crashing the pipeline:
   ```json
   {
     "verdict": "unknown",
     "reason": "Judge model 'qwen3:8b' not found. Pull it with: ollama pull qwen3:8b"
   }
   ```
3. The RAG pipeline and answers file generation continue uninterrupted for all remaining questions.

### 2.3 What was measured

Only the same-model judge was measured, on the demo document (see [RESULTS.md](RESULTS.md)): it caught one of the two wrong refusals and raised one false alarm on a correct refusal. A comparison with a larger judge is an optional future experiment.
