# Sensai – Project Risk Matrix & Deployment Requirements

This document details the engineering risk assessment, failure mode mitigations, and precise hardware/software requirements for deploying **Sensai**. It is prepared for the technical evaluation and aligns directly with the *Honest Assessment* slide of the keynote presentation.

---

## 1. Project Risk Matrix & Failure Mode Mitigations

Building a local RAG assistant on consumer hardware introduces physical and algorithmic constraints. Below is the systematic risk matrix mapping identified failure modes to architectural defenses implemented in Sensai.

| Risk ID | Risk Description | Probability | Severity | Architectural Mitigation Strategy | Status |
|---|---|---|---|---|---|
| **RSK-01** | **Residual Model Hallucination**<br>The LLM asserts ungrounded claims or mixes outside knowledge into academic citations. | Medium | **High** | **Dual verification**: Mechanical substring quote check (`src/pipeline.py`) + decoupled Judge evaluation (`src/judge.py`). In cases of conflict, the answer is flagged with a visual review alert. | **Mitigated** |
| **RSK-02** | **RAM / Swap Thrashing (OOM)**<br>Ingesting large PDFs or running heavy context exceeds unified memory on 8 GB systems. | Medium | **High** | **Dynamic context budgeting**: Removed hardcoded context sizes (`M8`). Prompt passages are dynamically bounded to $\le 85\%$ of `num_ctx`. Generator default is lightweight 4B model (`qwen3:4b`). | **Mitigated** |
| **RSK-03** | **Ollama Process Crash / Hang**<br>Ollama daemon becomes unresponsive or models fail to return valid JSON within timeout. | Low | Medium | **Defensive HTTP client**: Timeout configurations (`(5, 300)`), schema enforcement with `think=false`, and graceful 2-attempt retry loops before returning a non-crashing `unknown` verdict. | **Mitigated** |
| **RSK-04** | **Scanned / Image-Only PDFs**<br>User uploads a PDF containing scanned images without embedded text layers. | High | Low | **Fail-fast ingestion check**: `src/ingestion.py` extracts text per page and immediately raises a clean `IngestionError("...has no extractable text")` before initiating vector embedding calls. | **Mitigated** |
| **RSK-05** | **Context Window Overflow**<br>User questions with extensive conversational history or huge chunk counts exceed the token window. | Medium | Medium | **Automated chunk trimming & history truncation**: Token budget calculator in `src/pipeline.py` trims lower-scoring passages dynamically when context thresholds are approached. | **Mitigated** |
| **RSK-06** | **Trivial Query Refusal Over-Blocking**<br>Model refuses basic arithmetic or greetings because they do not appear in the uploaded PDF. | High | Low | **Intent routing fallback (`D6`)**: Math expressions and conversational greetings are recognized by `src/routing.py` and answered directly without document refusal. | **Mitigated** |

---

## 2. Deployment Requirements Specification

Sensai is designed to run locally on Linux, macOS, and Windows (via WSL2).

### 2.1 Hardware Requirements Table

| Component | Minimum Specification (Verified) | Recommended Specification (Optimal) |
|---|---|---|
| **CPU Architecture** | x86_64 (Intel Core i5 8th Gen+ / AMD Ryzen 3000+) or Apple Silicon (M1+) | 8-core CPU or Apple Silicon (M2/M3/M4) |
| **System Memory (RAM)** | **8 GB RAM** (Runs `qwen3:4b` + `nomic-embed-text`) | **16 GB RAM** (Enables running 7B judge model and larger context windows) |
| **GPU / Acceleration** | Optional. CPU-only execution fully supported out of the box. | Metal (Apple Silicon), NVIDIA CUDA (Compute 7.0+), or AMD ROCm |
| **Disk Space** | **6 GB free space** (Ollama engine + base models) | **15 GB free space** (Allows multi-model setups: 4B generator + 7B judge) |
| **Network Interface** | Local loopback (`127.0.0.1`). **No internet connection required.** | Local loopback. |

### 2.2 Software & Environment Requirements

| Requirement | Supported Versions | Verification Command |
|---|---|---|
| **Operating System** | Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+), macOS (12.0+), Windows 10/11 (WSL2) | `uname -s` or `wsl --status` |
| **Python Runtime** | Python **3.10**, **3.11**, or **3.12** | `python3 --version` |
| **Ollama Daemon** | Ollama **0.3.0+** or newer | `ollama --version` |
| **Required Ollama Models** | `qwen3:4b` (chat/judge) and `nomic-embed-text` (embeddings) | `ollama list` |
| **Python Dependencies** | `requests>=2.28`, `numpy>=1.24`, `pypdf>=3.0`, `pytest>=7.0` | `pip list` or `pytest --version` |

---

## 3. Deployment Checklist for Evaluators & Juries

Before starting the evaluation run or live keynote demonstration:

1. **Verify Ollama is running**:
   ```bash
   curl -s http://localhost:11434/api/tags | grep -q "qwen3:4b" && echo "✓ Ollama Ready" || echo "✗ Run: ollama serve"
   ```
2. **Execute Full Test Suite**:
   ```bash
   PYTHONPATH=. .venv/bin/pytest -q
   # Expected: 380 passed
   ```
3. **Launch Web Interface**:
   ```bash
   python3 WEB-UI/server.py
   # Access via browser at http://localhost:8000
   ```
