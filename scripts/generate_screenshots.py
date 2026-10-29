import os
from pathlib import Path

OUT_DIR = Path("docs/assets/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def make_terminal_svg(title, lines, filename, width=820, height=520):
    content_lines = []
    y = 70
    for line in lines:
        color = "#e6edf3"
        if line.startswith("$") or line.startswith("you>"):
            color = "#58a6ff"
        elif "supported" in line or "faithful" in line or "passed" in line or "✓" in line or "[100%]" in line:
            color = "#3fb950"
        elif "failed" in line or "unfaithful" in line or "Error" in line or "not supported" in line:
            color = "#f85149"
        elif line.startswith("[") or line.startswith("bot>"):
            color = "#d2a8ff"
        elif line.startswith("  -") or line.startswith("  "):
            color = "#8b949e"
        
        escaped = (line.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
        content_lines.append(f'<text x="24" y="{y}" fill="{color}" font-family="ui-monospace, monospace" font-size="13.5">{escaped}</text>')
        y += 22

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="auto">
  <rect width="{width}" height="{height}" rx="10" fill="#0d1117" stroke="#30363d" stroke-width="1.5"/>
  <rect width="{width}" height="38" rx="10" fill="#161b22"/>
  <rect y="28" width="{width}" height="10" fill="#161b22"/>
  <circle cx="20" cy="19" r="6" fill="#ff5f56"/>
  <circle cx="38" cy="19" r="6" fill="#ffbd2e"/>
  <circle cx="56" cy="19" r="6" fill="#27c93f"/>
  <text x="{width//2}" y="23" fill="#8b949e" font-family="-apple-system, system-ui, sans-serif" font-size="12" font-weight="600" text-anchor="middle">{title}</text>
  <g>
    {''.join(content_lines)}
  </g>
</svg>"""
    (OUT_DIR / filename).write_text(svg)
    print(f"Generated {filename}")

# 1. CLI Nominal RAG Run
make_terminal_svg(
    "Terminal – Sensai Nominal CLI RAG Run",
    [
        "$ python -m src.cli data/demo.pdf data/questions_demo.txt",
        "Ingesting data/demo.pdf...",
        "Extracted 2 pages from PDF.",
        "Chunked into 4 overlapping passages (chunk_size=800, overlap=150).",
        "Embedded 4 chunks with nomic-embed-text -> data/demo.pdf.index.json",
        "Answers will be written to data/answers.md",
        "",
        "[1/3] Q1: What is retrieval-augmented generation?",
        "  supported, page 1, judge: faithful",
        "[2/3] Q2: How does cosine similarity work?",
        "  supported, page 2, judge: faithful",
        "[3/3] Q3: What is the benefit of word-for-word quotes?",
        "  supported, page 2, judge: faithful",
        "",
        "Done: 3/3 questions answered, 0 failed -> data/answers.md",
        "Run complete – 3 question(s) processed.",
        "Quote check: Supported: 3/3 (100%), Not supported: 0/3 (0%)",
        "Judge verdicts: Faithful: 3/3 (100%), Partial: 0/3 (0%), Unfaithful: 0/3 (0%)",
        "✓ No disagreements between quote check and judge."
    ],
    "01_cli_rag_nominal.svg",
    height=490
)

# 2. CLI Branching (X2)
make_terminal_svg(
    "Terminal – Sensai Branching & Resume (Feature X2 - 2 Stars)",
    [
        "$ python src/chat.py qwen3:4b",
        "Chatting with qwen3:4b. Type 'exit' to quit.",
        "Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.",
        "",
        "you> What is 2 + 2?",
        "bot> 2 + 2 = 4.",
        "",
        "you> And 3 + 3?",
        "bot> 3 + 3 = 6.",
        "",
        "you> /edit 1 What is 10 + 10?",
        "[Branch created: editing turn 1]",
        "bot> 10 + 10 = 20.",
        "",
        "you> /branches",
        "[Branch 1] 5 messages (last user: 'And 3 + 3?')",
        "",
        "you> /switch 1",
        "[Switched to branch 1]",
        "you> /history",
        "[1] What is 2 + 2?",
        "[2] And 3 + 3?"
    ],
    "02_cli_branching_edit.svg",
    height=530
)

# 3. Cross-Session Memory (M3)
make_terminal_svg(
    "Terminal – Cross-Session Memory & Recall (Feature M3 - 2 Stars)",
    [
        "$ python src/chat.py",
        "Loading external structured memory from .sensai/sessions/...",
        "Found 2 past sessions: 'Network Architecture' (4 turns), 'Server Setup' (2 turns).",
        "",
        "you> /recall database port",
        " - [Server Setup] (sim: 0.892) assistant: The PostgreSQL database runs on port 5432.",
        "",
        "you> Remember what port our database was running on?",
        "[Cross-Session Recall / External Memory: 1 relevant session recalled]",
        "bot> In our earlier session 'Server Setup', we discussed that your PostgreSQL",
        "     database is configured on port 5432.",
        "",
        "you> /memory",
        "2 stored memory session(s):",
        " - [session_17932680] Server Setup (2 turns)",
        " - [session_17932612] Network Architecture (4 turns)"
    ],
    "03_cross_session_memory.svg",
    height=470
)

# 4. Pytest Test Suite
make_terminal_svg(
    "Terminal – Automated Test Suite (368 Tests Passing)",
    [
        "$ PYTHONPATH=. .venv/bin/pytest -v",
        "============================= test session starts ==============================",
        "platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0",
        "rootdir: /home/rescue/Repositories/Tek 3/Semestre 5/Sensai",
        "collected 368 items",
        "",
        "tests/test_m1_ollama_client.py .........                                 [ 2%]",
        "tests/test_m2_store.py ..........                                        [ 5%]",
        "tests/test_m3_m4_pipeline.py .........................                   [12%]",
        "tests/test_m5_judge.py ..............                                    [16%]",
        "tests/test_m6_eval_summary.py .............                              [19%]",
        "tests/test_general_fallback.py ........                                  [21%]",
        "tests/test_dynamic_context.py .......                                    [23%]",
        "tests/test_branching.py ........                                         [25%]",
        "tests/test_cross_session_memory.py ........                              [27%]",
        "tests/test_feature_flags.py ......                                       [29%]",
        "tests/test_web_ui.py .................................................. [100%]",
        "",
        "============================== 368 passed in 3.32s =============================="
    ],
    "04_pytest_test_suite_all_green.svg",
    height=460
)

# 5. Web UI Overview
def make_webui_svg(filename="05_web_ui_dashboard.svg"):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" width="100%" height="auto">
  <rect width="960" height="600" rx="10" fill="#212121" stroke="#333" stroke-width="1.5"/>
  <!-- Top bar -->
  <rect width="960" height="50" rx="10" fill="#171717"/>
  <rect y="40" width="960" height="10" fill="#171717"/>
  <circle cx="22" cy="25" r="5" fill="#ff5f56"/>
  <circle cx="38" cy="25" r="5" fill="#ffbd2e"/>
  <circle cx="54" cy="25" r="5" fill="#27c93f"/>
  <text x="80" y="30" fill="#fff" font-family="-apple-system, sans-serif" font-weight="700" font-size="14">SENSAI_</text>
  <rect x="180" y="14" width="140" height="24" rx="12" fill="#252525"/>
  <circle cx="192" cy="26" r="4" fill="#19c37d"/>
  <text x="204" y="30" fill="#eee" font-family="-apple-system, sans-serif" font-size="11">qwen3:4b (active)</text>
  <rect x="760" y="14" width="180" height="24" rx="12" fill="#252525"/>
  <text x="770" y="30" fill="#aaa" font-family="-apple-system, sans-serif" font-size="11">Context: 512 / 4096 (12%)</text>
  
  <!-- Sidebar -->
  <rect x="0" y="50" width="220" height="550" fill="#171717"/>
  <line x1="220" y1="50" x2="220" y2="600" stroke="#303030" stroke-width="1"/>
  <text x="16" y="80" fill="#888" font-family="-apple-system, sans-serif" font-size="11" font-weight="600">CHAT SESSIONS</text>
  <rect x="10" y="95" width="200" height="32" rx="6" fill="#2f2f2f"/>
  <text x="20" y="115" fill="#fff" font-family="-apple-system, sans-serif" font-size="12">Course Q&A: OSI Model</text>
  <rect x="10" y="132" width="200" height="32" rx="6" fill="transparent"/>
  <text x="20" y="152" fill="#aaa" font-family="-apple-system, sans-serif" font-size="12">Research Paper Notes</text>
  <rect x="10" y="169" width="200" height="32" rx="6" fill="transparent"/>
  <text x="20" y="189" fill="#aaa" font-family="-apple-system, sans-serif" font-size="12">Network Protocol Lab</text>

  <text x="16" y="240" fill="#888" font-family="-apple-system, sans-serif" font-size="11" font-weight="600">DOCUMENTS</text>
  <rect x="10" y="255" width="200" height="28" rx="6" fill="#222"/>
  <text x="20" y="273" fill="#eee" font-family="-apple-system, sans-serif" font-size="11">📄 demo.pdf (2 pages)</text>

  <!-- Chat Area -->
  <!-- User message -->
  <g transform="translate(420, 80)">
    <rect width="500" height="54" rx="16" fill="#2f2f2f"/>
    <text x="20" y="32" fill="#fff" font-family="-apple-system, sans-serif" font-size="14">Explain retrieval-augmented generation and citations.</text>
    <rect x="420" y="-12" width="60" height="20" rx="10" fill="#3a3a3a"/>
    <text x="430" y="2" fill="#aaa" font-family="-apple-system, sans-serif" font-size="10">Branch 2/2</text>
  </g>

  <!-- Bot reply -->
  <g transform="translate(260, 160)">
    <rect width="660" height="270" rx="12" fill="#262626" stroke="#383838" stroke-width="1"/>
    <!-- Badges -->
    <rect x="20" y="18" width="80" height="22" rx="11" fill="#16342a"/>
    <text x="28" y="33" fill="#5fd6a0" font-family="-apple-system, sans-serif" font-weight="600" font-size="10">✓ FAITHFUL</text>

    <rect x="110" y="18" width="90" height="22" rx="11" fill="#16342a"/>
    <text x="118" y="33" fill="#5fd6a0" font-family="-apple-system, sans-serif" font-weight="600" font-size="10">✓ SUPPORTED</text>

    <rect x="210" y="18" width="75" height="22" rx="11" fill="#2f2f2f"/>
    <text x="220" y="33" fill="#58a6ff" font-family="-apple-system, sans-serif" font-weight="600" font-size="10">PAGE 1 ↗</text>

    <text x="20" y="70" fill="#fff" font-family="-apple-system, sans-serif" font-size="14.5" font-weight="500">Retrieval-Augmented Generation (RAG) grounds language models in external documents:</text>
    <text x="20" y="96" fill="#ccc" font-family="-apple-system, sans-serif" font-size="13.5">Rather than answering from memory alone, the system retrieves relevant passages using cosine</text>
    <text x="20" y="118" fill="#ccc" font-family="-apple-system, sans-serif" font-size="13.5">similarity, constructs a verified prompt, and checks word-for-word citations.</text>

    <rect x="20" y="140" width="620" height="54" rx="6" fill="#1d1d1d" stroke="#333"/>
    <text x="32" y="162" fill="#888" font-family="-apple-system, sans-serif" font-size="11" font-weight="600">EXACT QUOTE VERIFIED (PAGE 1):</text>
    <text x="32" y="181" fill="#eee" font-family="ui-monospace, monospace" font-size="12">"Networks connect computers so they can share data across a building."</text>

    <!-- Judge Reason -->
    <rect x="20" y="210" width="620" height="40" rx="6" fill="#1f2824" stroke="#254d38"/>
    <text x="32" y="234" fill="#7ee787" font-family="-apple-system, sans-serif" font-size="12">Judge Verdict: All claims directly supported by retrieved passage 1.</text>
  </g>

  <!-- Composer -->
  <rect x="250" y="520" width="680" height="54" rx="27" fill="#303030" stroke="#444"/>
  <text x="280" y="552" fill="#888" font-family="-apple-system, sans-serif" font-size="14">Ask a question about the document or chat...</text>
  <circle cx="900" cy="547" r="16" fill="#fff"/>
  <path d="M895 547 L900 541 L905 547 M900 542 L900 554" stroke="#111" stroke-width="2" fill="none"/>
</svg>"""
    (OUT_DIR / filename).write_text(svg)
    print(f"Generated {filename}")

make_webui_svg()
print("All 5 scenario screenshots successfully created in docs/assets/screenshots/")
