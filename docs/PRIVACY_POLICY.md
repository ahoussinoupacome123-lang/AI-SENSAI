# Sensai – Privacy Policy & Local Data Sovereignty Charter

**Effective Date:** October 2026  
**Core Guarantee:** **100% Local Execution. Zero Documents, Queries, or Embeddings Leave Your Machine.**

---

## 1. Fundamental Privacy Commitment

Sensai was built from the ground up on the principle of **radical data sovereignty**. Unlike commercial AI assistants (e.g., ChatGPT, Claude, Microsoft Copilot) which transmit user documents, confidential questions, and personal data to remote corporate cloud servers, Sensai operates **entirely offline on your local computer**.

> ### The Zero-Egress Promise
> - **Zero External Telemetry**: Sensai contains no tracking scripts, analytics beacons, or remote crash reporters.
> - **Zero Cloud LLM Calls**: Every neural network computation (embedding generation, answer synthesis, and judge evaluation) executes via local Ollama instances running on `127.0.0.1`.
> - **Zero Data Resale or AI Training**: Your personal PDFs, questions, and research notes are never stored in third-party databases, and are never used to train any public or private AI models.

---

## 2. What Data Is Processed and Where It Lives

All data processed by Sensai remains strictly confined to your local file system:

| Data Type | Purpose | Local Storage Location | Retention Lifecycle |
|---|---|---|---|
| **PDF Documents** | Source material analyzed for question answering | Stored in your chosen project directory or `WEB-UI/workspace/uploads/` | Remains on disk until manually deleted by the user. |
| **Vector Search Indices** | Numerical representations of text chunks for fast retrieval | Saved locally as `<filename>.index.json` | Generated on demand; deleted when the corresponding `.index.json` file is removed. |
| **Generated Answers** | Output Markdown report containing answers, citations, and judge verdicts | Saved locally as `answers.md` next to your PDF | Overwritten or updated only upon user command; fully under user control. |
| **Chat & Memory History** | In-session turns and cross-session conversational recall (M3) | Stored in `.sensai/sessions/` and browser `localStorage` | Purely client-side; instantly purged via `/clear`, browser cache reset, or deleting `.sensai/`. |

---

## 3. Network Architecture & Security Verification

### 3.1 Network Isolation Verification
You can independently verify that Sensai never opens outbound internet sockets during execution:

```bash
# 1. Inspect active network listeners while Sensai is running
ss -tulpn | grep -E "(11434|8000)"

# Expected Output:
# tcp LISTEN 0 128 127.0.0.1:11434 (Ollama local daemon)
# tcp LISTEN 0 128 127.0.0.1:8000  (Sensai local Web UI)

# 2. Run with network interface severed (airplane mode or air-gapped test)
# All ingestion, retrieval, chat, and judge evaluation continue to function with zero degradation.
```

### 3.2 Host Header & Cross-Origin Protection
In the Web UI (`WEB-UI/server.py`):
- The server binds strictly to loopback interfaces (`127.0.0.1` and `localhost`).
- Incoming requests from foreign origins or DNS rebinding attempts are rejected with `HTTP 403 Forbidden`.
- Content Security Policy (CSP) headers forbid loading scripts, styles, or fonts from external CDNs.

---

## 4. User Rights & Data Deletion (GDPR / CCPA Compliance)

In accordance with international privacy standards (GDPR Regulation (EU) 2016/679 and California Consumer Privacy Act):

1. **Right to Complete Erasure**:
   To erase all data, embeddings, and conversation histories created by Sensai, simply delete the local directories:
   ```bash
   rm -rf .sensai/ answers.md *.index.json WEB-UI/workspace/
   ```
2. **Right to Access & Portability**:
   All outputs (`answers.md`, `index.json`, session files) are stored in open, human-readable formats (plain text, JSON, and standard Markdown) with zero proprietary encryption or vendor lock-in.

---

## 5. Contact & Institutional Deployment

For compliance inquiries, university data protection audits, or air-gapped lab certifications:
- **Project Repository**: [Sensai GitHub Relay](file:///home/rescue/Repositories/Tek%203/Semestre%205/Sensai/G-AIA-500-COT-5-1-sensai-37)
- **Maintainer**: `murchid.aboudoumamatarouwere@epitech.eu`
