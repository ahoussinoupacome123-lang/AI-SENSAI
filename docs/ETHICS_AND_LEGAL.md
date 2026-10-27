# Sensai – Legal Boundaries & Ethical Considerations Analysis

This document sets forth the comprehensive legal framework, copyright compliance, and ethical boundaries governing the design, deployment, and academic usage of **Sensai**.

---

## 1. Legal Boundaries & Copyright Compliance

Sensai ingests, chunks, embeds, and retrieves excerpts from user-provided PDF documents. Operating legally in academic and research environments requires compliance with international copyright statutes, European intellectual property directives, and national fair use exceptions.

### 1.1 Copyright Exceptions for Document Ingestion

| Legal Jurisdiction | Applicable Statute / Exception | Practical Application to Sensai |
|---|---|---|
| **European Union (EU)** | **Directive (EU) 2019/790** (Copyright in the Digital Single Market), Articles 3 & 4 | **Text and Data Mining (TDM) Exception**: Authorizes copying and extraction of lawfully accessible works for scientific research by research organizations and cultural heritage institutions. |
| **France (CPI)** | **Code de la Propriété Intellectuelle**, Art. L. 122-5 (Exception pédagogique & recherche) | Authorizes reproduction and representation of extracts of works exclusively for educational illustration and research purposes. |
| **United States** | **17 U.S. Code § 107** (Fair Use Doctrine) | Multi-factor fair use analysis: Transformative purpose (search indexation and Q&A synthesis), non-commercial academic use, limited excerpt extraction rather than full publication. |
| **General Private Copy** | Private Copy Exception (e.g. CPI Art. L. 122-5 2°) | Reproductions strictly reserved for private, individual student study on local personal machines are protected. |

### 1.2 Preservation of Attribution and Intellectual Paternity
Sensai actively enforces intellectual property attribution:
- Every synthesized answer explicitly maps to the exact source **page number** (`page: N`).
- Every answer includes a verbatim **word-for-word quote** (`quote: "..."`) verified by automated substring matching.
- Sensai **never** redistributes, syndicates, or exposes the ingested PDF file externally; all indices (`*.index.json`) remain strictly localized on the user's hard drive.

---

## 2. Regulatory Compliance: GDPR & EU AI Act

### 2.1 General Data Protection Regulation (GDPR / RGPD)
Under Regulation (EU) 2016/679:
- **Zero Third-Party Data Transfer (Art. 44)**: Because all inference runs on local Ollama processes via `127.0.0.1`, zero personal data, research queries, or student information cross international borders or cloud servers.
- **Data Minimization (Art. 5(1)(c))**: Only vectors and text passages directly necessary for Q&A are indexed.
- **Right to Erasure (Art. 17)**: Deleting the target directory or running standard file removal instantly eliminates all embeddings, session logs, and answers without lingering cloud backups.

### 2.2 EU AI Act Classification
Under the European Union Artificial Intelligence Act (Regulation (EU) 2024/1689):
- Sensai operates as a **Minimal / Low-Risk AI System**: It is a tool for document reading assistance and educational study.
- It does **not** engage in biometric identification, social scoring, critical infrastructure management, or autonomous high-stakes admissions decisions.
- **Transparency Obligation (Art. 50)**: Sensai informs users that responses are AI-generated, provides citations for human verification, and visibly flags potential discrepancies between quote matching and judge evaluation.

---

## 3. Ethical Considerations & Responsible AI Usage

### 3.1 Academic Integrity & The Exam Dilemma
When students utilize generative AI tools for exam preparation:
1. **The Over-Reliance Trap**: Uncritical acceptance of model outputs can lead to compounding conceptual misunderstandings.
2. **Plagiarism & Authorship**: Using AI outputs directly in submitted graded papers without attribution violates institutional honor codes.
3. **Sensai's Mitigation**: Sensai is intentionally architected not as a ghost-writer, but as an **auditable study assistant**. It insists on page citations and extracts direct quotes so students learn *from the source material itself*.

### 3.2 Hallucination Risks in High-Stakes Contexts
In medical, legal, or engineering studies, factual hallucinations pose genuine risks.
Sensai addresses this through a **dual-safeguard verification system**:
1. **Mechanical Quote Check**: Fast string verification ensuring cited quotes exist verbatim in the source text.
2. **Automated LLM Judge**: A second, independent LLM evaluates semantic faithfulness.
3. **Review Flags**: Whenever the quote check and judge disagree, Sensai highlights the answer with a prominent warning badge: `"Check this answer against the PDF before trusting it."`

---

## 4. User Disclaimer & Operational Recommendations

Every user deploying Sensai receives the following explicit disclaimer:

> [!IMPORTANT]
> **User Disclaimer & Academic Responsibility**
> Sensai is an automated reading and study assistance tool. While equipped with multi-stage quote verification and hallucination detection, large language models may occasionally produce partial, imprecise, or contextually incomplete interpretations.
> 
> **Users must:**
> - Systematically verify critical formulas, definitions, and citations against the linked source PDF page.
> - Comply with their academic institution's intellectual integrity and plagiarism guidelines.
> - Ensure they possess lawful access rights (private copy, institutional subscription, or open-access license) for any uploaded document.
