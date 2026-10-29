# Sensai – Abandoned Features & Design Trade-offs

This document formalizes the architectural trade-offs, engineering scope decisions, and discarded features from the project catalogue. Explaining *what was deliberately ruled out* and *why* is a key requirement of the Epitech AI project defense and ensures clear traceability with [USER_STORIES.md](file:///home/rescue/Repositories/Tek%203/Semestre%205/Sensai/G-AIA-500-COT-5-1-sensai-37/docs/USER_STORIES.md).

---

## 1. Executive Summary of Feature Scoping

When selecting our 4 stars of catalogue features, our team prioritized:
1. **100% Offline Local Privacy**: No data, queries, or embeddings should ever leave the user's workstation.
2. **Deterministic Reliability**: Low latency, verifiable citations, and zero fragile cloud dependencies.
3. **High Return on Investment**: Features that directly empower students and researchers analyzing academic/technical PDFs.

As a result, we selected:
- **`[X2] Branching — Resume & Interrupt` (2 ⭐)**: Editing past messages, tree-based history branching, and state preservation.
- **`[M3] External Structured Memory / Second Brain` (2 ⭐)**: Cross-session conversation recall and persistent vector indexing.
- **`General Fallback & Basic Calculation Routing` (`D6`)**: Trivial calculation handling without inappropriate document refusal.

Below are the features evaluated, tested, and deliberately abandoned or discarded.

---

## 2. Discarded Features Analysis

### Feature 1: Web Search Integration (T3 – 2 ⭐)

#### Description
Enabling the agent to query external search engines (e.g., DuckDuckGo, SearXNG, Bing API) when a question cannot be resolved using the ingested PDF document.

#### Reasons for Abandonment
1. **Direct Violation of the 100% Local Guarantee**:
   The primary value proposition of Sensai is total data sovereignty for confidential research papers, legal contracts, and non-public university exam materials. Triggering external web queries risks leaking query contents and proprietary document topics to third-party search providers.
2. **Network Dependency & Latency Explosion**:
   Sensai is engineered to operate seamlessly in offline environments (air-gapped labs, airplanes, campus basements). External web requests introduce latency spikes, rate-limiting, CAPTCHA blocks, and HTTP timeout failures.
3. **Hallucination Risk & Grounding Contamination**:
   Uncurated web search snippets introduce conflicting, unverified information that dilutes the strict page citation guarantees enforced by our quote verification engine.

#### Impacted User Stories
- **Refocused**: Instead of looking up general topics on the internet, we implemented `D6` (General Fallback & Basic Calculations) which routes arithmetic and general conversational pleasantries locally within the LLM's frozen weights without reaching out to external networks.

---

### Feature 2: Code Execution Sandbox (T2 – 3 ⭐)

#### Description
Executing generated Python or Bash snippets in a secure containerized environment (e.g. Docker, gVisor, or WASM) to verify numerical calculations or generate plots.

#### Reasons for Abandonment
1. **Host Security & System Vulnerabilities**:
   Running arbitrary LLM-generated code locally introduces severe security attack vectors (such as directory traversal, socket binding, or resource exhaustion attacks).
2. **Heavyweight Infrastructure Requirements**:
   A true secure sandbox requires running a Docker daemon or complex Linux namespaces, which contradicts our core design principle of zero-dependency native execution (standard library + lightweight numpy).
3. **Disproportionate Complexity / Value Ratio**:
   The primary task of our target users (students and researchers) is document comprehension and semantic Q&A, not automated scripting.

#### Impacted User Stories
- **Refocused**: Safe mathematical evaluation is achieved via our AST-safe arithmetic engine in `src/routing.py`, which parses expressions using Python's abstract syntax tree without calling `eval()` or spawning sub-processes.

---

### Feature 3: Model Context Protocol (MCP) Integration (T1 – 2 ⭐)

#### Description
Exposing Sensai tools and vector stores over Anthropic's Model Context Protocol (MCP) JSON-RPC specification.

#### Reasons for Abandonment
1. **Specification Volatility**:
   The MCP specification has evolved rapidly over recent months, introducing breaking client/server schema changes.
2. **Redundancy with Web UI & CLI**:
   Sensai already provides a robust dual-interface model: a fast terminal CLI (`src/cli.py`, `src/chat.py`) and a ChatGPT-quality native Web UI (`WEB-UI/server.py`). Adding an RPC transport layer added architectural overhead without direct end-user benefit.

#### Impacted User Stories
- **Refocused**: Direct RESTful endpoints (`/api/run`, `/api/chat`, `/api/memory/search`) are integrated into the built-in HTTP server with zero protocol translation layers.

---

### Feature 4: Audio Transcription / Whisper Ingestion (A1 – 2 ⭐)

#### Description
Allowing users to upload MP3/WAV lecture recordings alongside PDFs and transcribing them using local Whisper models.

#### Reasons for Abandonment
1. **Hardware & VRAM Exhaustion**:
   Running Whisper alongside an Ollama LLM (`qwen3:4b` or `qwen2.5:7b`) simultaneously exceeds the 8 GB / 16 GB unified memory limit of standard student laptops, triggering swap thrashing and process crashes.
2. **Scope Alignment**:
   The project mandate focuses on document question-answering with exact page and quote verification. Audio files lack verifiable page boundaries.

---

## 3. Summary Matrix of Design Arbitrations

| Discarded Feature | Catalogue Code | Star Value | Primary Technical Constraint | Alternative Selected |
|---|---|---|---|---|
| **Web Search** | T3 | 2 ⭐ | Privacy leakage, offline violation | Native general calculation routing (`D6`) |
| **Code Sandbox** | T2 | 3 ⭐ | Security risk, Docker dependency | AST-safe math evaluator (`src/routing.py`) |
| **MCP Integration** | T1 | 2 ⭐ | Redundant transport overhead | Native SSE REST API (`WEB-UI/`) |
| **Audio Whisper** | A1 | 2 ⭐ | VRAM / RAM exhaustion on laptops | Focused PDF page-level citation engine |

All decisions were peer-reviewed and verified to maximize system reliability and user privacy.
