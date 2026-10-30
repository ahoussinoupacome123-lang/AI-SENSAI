# Sensai Visual Scenarios & Screenshots Gallery

This document catalogs the verified visual test runs and operational scenarios of **Sensai Q&A**, including nominal CLI pipeline operations, legitimate refusal guardrails, interactive conversational branching, cross-session memory recall, general knowledge fallback, full unit test suite execution, and the Web UI control dashboard.

All visual captures shown below are real live screenshots captured directly from the execution environment and stored under [`docs/assets/screenshots/`](assets/screenshots/).

---

## 1. Nominal CLI RAG Pipeline Execution

**Image**: [`docs/assets/screenshots/01_cli_rag_nominal.png`](assets/screenshots/01_cli_rag_nominal.png)  
**Task / Feature**: `R1` (Basic RAG), `T5` (Structured Output), `EV1` (Quote Verification & Judge)

Demonstrates the primary Sensai batch processing pipeline reading a target PDF (`data/demo.pdf`), retrieving top cosine-similarity context chunks, generating JSON-structured answers with page citations and exact quotes, and passing deterministic quote verification and LLM judge checks (the same `qwen3:4b`).

<p align="center">
  <img src="assets/screenshots/01_cli_rag_nominal.png" alt="Sensai CLI RAG Nominal Execution" width="850">
</p>

- **Command executed**: `python3 -m src.cli data/demo.pdf data/questions_demo.txt --only 1` followed by inspection of `answers.md`.
- **Observed behavior**: Chunks retrieved with cosine score ~0.842; Question 1 (*"How many bits long is an IPv6 address?"*) answered with `128 bits long`, page 13, exact quote verified in document text (`quote check: valid`), and Judge status marked `faithful (1.00)`.

---

## 2. Legitimate Refusal / Zero Hallucination (Guardrails)

**Image**: [`docs/assets/screenshots/02_cli_refusal_uncovered.png`](assets/screenshots/02_cli_refusal_uncovered.png)  
**Task / Feature**: `R1` (RAG Guardrails) & `EV1` (Quote & Judge Disagreement Flag)

Demonstrates Sensai's anti-hallucination behavior when posed with a question that is **not** covered in the course notes (`data/demo.pdf`). Rather than inventing false information, Sensai strictly refuses to fabricate an answer and flags the discrepancy for manual review.

<p align="center">
  <img src="assets/screenshots/02_cli_refusal_uncovered.png" alt="Sensai Legitimate Refusal Guardrail" width="850">
</p>

- **Command executed**: `python3 -m src.cli data/demo.pdf data/questions_demo.txt --only 3` followed by `grep -A 11 '## Q3' data/answers.md`.
- **Observed behavior**: Question 3 (*"Who invented the World Wide Web?"*) is correctly refused with `answer: The document does not cover this.` and empty quote. The deterministic quote check flags `not supported`, the judge marks `faithful`, and a manual review warning `[not supported / faithful]` is raised.

---

## 3. Interactive Conversational Branching (Resume & Interrupt)

**Image**: [`docs/assets/screenshots/02_cli_branching_edit.png`](assets/screenshots/02_cli_branching_edit.png)  
**Task / Feature**: `[X2] Branching — Resume & Interrupt` (Catalogue 2-star feature)

Demonstrates editing a prior user message after the AI has already replied. Sensai preserves the parent branch in history and forks the conversation into an active alternate branch (`[Branch 2/2]`), regenerating responses down the new path without corrupting historical context.

<p align="center">
  <img src="assets/screenshots/02_cli_branching_edit.png" alt="Sensai CLI Interactive Branching" width="850">
</p>

- **Commands demonstrated**:
  1. `you> What is an IP address in one sentence?` -> Bot answers with definition.
  2. `/history` -> Shows turn `[1]`.
  3. `/edit 1 What is an IPv6 address in one sentence?` -> Displays `[Branch created: editing turn 1]` and regenerates the response for IPv6 (128 bits).
  4. `/branches` -> Confirms `[Branch 1] 3 messages` is preserved intact.

---

## 4. Cross-Session Memory & Recall ("Second Brain")

**Image**: [`docs/assets/screenshots/03_cross_session_memory.png`](assets/screenshots/03_cross_session_memory.png)  
**Task / Feature**: `[M3] External Structured Memory` (Catalogue 2-star feature)

Demonstrates the assistant recalling critical details across separate conversation sessions. Even when starting a fresh session with no active conversation history, Sensai queries `.sensai/sessions/` using vector semantic search and injects past insights into its working context.

<p align="center">
  <img src="assets/screenshots/03_cross_session_memory.png" alt="Sensai Cross-Session Memory Recall" width="850">
</p>

- **Commands demonstrated**:
  1. `/memory` -> Lists persisted historical sessions from `.sensai/sessions/`.
  2. `you> What did we say about the Ethernet frame payload in our earlier chat?` (or `/recall Ethernet`).
- **Observed behavior**: Sensai identifies the prior discussion on network frames and confirms: *"In our earlier chat, we specifically stated that the maximum payload size for a standard Ethernet frame (IEEE 802.3) is 1500 bytes..."*.

---

## 5. General Knowledge Fallback & Math Routing

**Image**: [`docs/assets/screenshots/06_cli_fallback_math.png`](assets/screenshots/06_cli_fallback_math.png)  
**Task / Feature**: `D6` — General Knowledge Fallback

Demonstrates handling everyday conversational queries and basic arithmetic without artificially triggering the document refusal mechanism.

<p align="center">
  <img src="assets/screenshots/06_cli_fallback_math.png" alt="Sensai General Fallback Math" width="850">
</p>

- **Commands demonstrated**:
  1. `you> How much is 19 - 5 ?` -> Bot replies directly: `19 - 5 = 14`.
  2. `you> Hello, what is your role?` -> Bot responds politely with its AI assistant identity.

---

## 6. Web UI Control Dashboard & Visual Studio

**Image**: [`docs/assets/screenshots/05_web_ui_dashboard.png`](assets/screenshots/05_web_ui_dashboard.png)  
**Task / Feature**: `[X1] Web UI` & `P9` Feature Flags System

Showcases the Sensai Web UI dashboard interface with document ingestion statistics, live streaming Q&A monitor, real-time memory session browser, feature flag toggle switches (`RAG`, `Judge`, `Quote Check`, `Cache`), and inline user message editing.

<p align="center">
  <img src="assets/screenshots/05_web_ui_dashboard.png" alt="Sensai Web UI Dashboard" width="850">
</p>

- **Interface modules**: One-click demo PDF attachment (`Try the demo PDF`), active Q&A streaming with page citation badges, branch indicator `< 1 / 2 >`, and Settings modal with active Feature Flags (RAG, Judge, Quote Check, Memory).

---

## 7. Comprehensive Pytest Test Suite (100% Green)

**Image**: [`docs/assets/screenshots/04_pytest_test_suite_all_green.png`](assets/screenshots/04_pytest_test_suite_all_green.png)  
**Task / Feature**: Quality Assurance & Regression Testing

Shows execution of the complete Sensai automated test suite (380 unit and integration tests covering RAG ingestion, chunking, retrieval, prompt formatting, LLM judge, branching, dynamic context windowing, memory, routing fallback, and feature flags).

<p align="center">
  <img src="assets/screenshots/04_pytest_test_suite_all_green.png" alt="Sensai Pytest Test Suite All Green" width="850">
</p>

- **Command executed**: `PYTHONPATH=. .venv/bin/pytest -v`
- **Result**: `380 passed in 3.56s (100% pass rate)`. Zero failures, zero warnings.
