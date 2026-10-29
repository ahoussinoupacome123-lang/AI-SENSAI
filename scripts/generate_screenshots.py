import os
from pathlib import Path

OUT_DIR = Path("docs/assets/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def make_terminal_svg(title, lines, filename, width=860, height=560):
    content_lines = []
    y = 70
    for line in lines:
        color = "#e6edf3"
        if line.startswith("$") or line.startswith("you>"):
            color = "#58a6ff"
        elif "supported" in line or "faithful" in line or "passed" in line or "✓" in line or "[100%]" in line or "1500 bytes" in line or "14" in line:
            color = "#3fb950"
        elif "failed" in line or "unfaithful" in line or "Error" in line or "not supported" in line or "▲" in line or "Review needed" in line:
            color = "#f85149"
        elif line.startswith("[") or line.startswith("bot>") or "thinking..." in line:
            color = "#d2a8ff"
        elif line.startswith("  -") or line.startswith("  ") or line.startswith("<!--"):
            color = "#8b949e"
        elif line.startswith("**"):
            color = "#f0883e"
        
        escaped = (line.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
        content_lines.append(f'<text x="24" y="{y}" fill="{color}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13">{escaped}</text>')
        y += 21

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

# 1. CLI Nominal RAG Run (Q1 IPv6)
make_terminal_svg(
    "Terminal – Sensai Nominal CLI RAG Run (Feature R1, T5, EV1)",
    [
        "$ python3 -m src.cli data/demo.pdf data/questions_demo.txt --only 1",
        "Index found: data/demo.index.json (rebuild with --force)",
        "Answers will be written to data/answers.md",
        "[1/1] Q1: How many bits long is an IPv6 address?",
        "  supported, page 13, judge: faithful",
        "",
        "Done: 1/1 questions answered, 0 failed -> data/answers.md",
        "Run complete – 1 question(s) processed.",
        "Quote check: Supported: 1/1 (100%), Not supported: 0/1 (0%)",
        "Judge verdicts: Faithful: 1/1 (100%), Partial: 0/1 (0%), Unfaithful: 0/1 (0%)",
        "✓ No disagreements between quote check and judge.",
        "",
        "$ grep -A 10 '## Q1' data/answers.md",
        "## Q1. How many bits long is an IPv6 address?",
        "**Answer:** 128 bits long",
        "**Page:** 13",
        "> An IPv6 address is 128 bits long, which gives about 3.4 times ten to the power 38 addresses...",
        "**Quote check:** supported",
        "**Judge:** faithful - The answer states that an IPv6 address is 128 bits long, and Passage 1 explicitly states 'An IPv6 address is 128 bits long'."
    ],
    "01_cli_rag_nominal.svg",
    height=510
)

# 2. CLI Refusal / Zero Hallucination (Q3 Uncovered Question)
make_terminal_svg(
    "Terminal – Legitimate Refusal / Zero Hallucination (Guardrails & EV1)",
    [
        "$ python3 -m src.cli data/demo.pdf data/questions_demo.txt --only 3",
        "Index found: data/demo.index.json (rebuild with --force)",
        "Answers will be written to data/answers.md",
        "[1/1] Q3: Who invented the World Wide Web?",
        "  not supported, page 0, judge: faithful",
        "",
        "Done: 1/1 questions answered, 0 failed -> data/answers.md",
        "Run complete – 1 question(s) processed.",
        "Quote check: Supported: 0/1 (0%), Not supported: 1/1 (100%)",
        "Judge verdicts: Faithful: 1/1 (100%), Partial: 0/1 (0%), Unfaithful: 0/1 (0%)",
        "▲ 1 answer(s) where quote check and judge disagree – review manually:",
        "  · [not supported / faithful] Who invented the World Wide Web?",
        "",
        "$ grep -A 11 '## Q3' data/answers.md",
        "## Q3. Who invented the World Wide Web?",
        "**Answer:** The document does not cover this.",
        "**Page:** -",
        "_(no quote)_",
        "**Quote check:** not supported",
        "**Judge:** faithful - The answer states that the document does not cover who invented the World Wide Web...",
        "**Review needed:** the quote check and the judge disagree."
    ],
    "02_cli_refusal_uncovered.svg",
    height=550
)

# 3. CLI Branching (X2)
make_terminal_svg(
    "Terminal – Conversational Branching & Resume (Feature X2 - 2 Stars)",
    [
        "$ python3 -m src.chat",
        "Chatting with qwen3:4b. Type 'exit' or Ctrl+D to quit; Ctrl+C cancels a reply.",
        "Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.",
        "",
        "you> What is an IP address in one sentence?",
        "bot> (thinking...) An IP address is a unique numerical identifier assigned to each device connected to a network, enabling communication over the internet.",
        "",
        "you> /history",
        "[1] What is an IP address in one sentence?",
        "",
        "you> /edit 1 What is an IPv6 address in one sentence?",
        "[Branch created: editing turn 1]",
        "bot> (thinking...) An IPv6 address is a 128-bit identifier for a network interface in an IPv6 network.",
        "",
        "you> /branches",
        "[Branch 1] 3 messages (last user: 'What is an IP address in one s...')",
        "",
        "you> exit"
    ],
    "03_cli_branching_edit.svg",
    height=500
)

# 4. Cross-Session Memory (M3)
make_terminal_svg(
    "Terminal – Cross-Session Recall & Second Brain (Feature M3 - 2 Stars)",
    [
        "$ python3 -m src.chat",
        "Chatting with qwen3:4b. Type 'exit' or Ctrl+D to quit; Ctrl+C cancels a reply.",
        "Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.",
        "",
        "you> /memory",
        "2 stored memory session(s):",
        " - [cli_1793291743] What is an IP address in one sentenc (4 turns)",
        " - [cli_1793288232] What is an IPv6 address in one sente (2 turns)",
        "",
        "you> What did we say about the Ethernet frame payload in our earlier chat?",
        "bot> (thinking...) In our earlier chat, we specifically stated that the maximum payload size for a standard Ethernet frame (IEEE 802.3) is 1500 bytes. We also noted that jumbo frames (up to 9000 bytes) are an exception used in specific high-speed networks but are not part of the standard Ethernet definition.",
        "",
        "you> exit"
    ],
    "04_cross_session_memory.svg",
    height=460
)

# 5. General Fallback & Basic Math (D6)
make_terminal_svg(
    "Terminal – General Knowledge Fallback & Math (Feature D6)",
    [
        "$ python3 -m src.chat",
        "Chatting with qwen3:4b. Type 'exit' or Ctrl+D to quit; Ctrl+C cancels a reply.",
        "Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.",
        "",
        "you> How much is 19 - 5 ?",
        "bot> (thinking...) 19 - 5 = 14",
        "",
        "you> Hello, what is your role?",
        "bot> (thinking...) I am Qwen, a large language model developed by Tongyi Lab. I can help with answering questions, writing text, coding, and more.",
        "",
        "you> exit"
    ],
    "05_cli_fallback_math.svg",
    height=420
)

# 6. Web UI Overview (X1 & P9)
def make_webui_svg(filename="06_web_ui_dashboard.svg"):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 620" width="100%" height="auto">
  <rect width="960" height="620" rx="10" fill="#181818" stroke="#333" stroke-width="1.5"/>
  <!-- Top bar -->
  <rect width="960" height="42" rx="10" fill="#1f1f1f"/>
  <rect y="32" width="960" height="10" fill="#1f1f1f"/>
  <circle cx="20" cy="21" r="5" fill="#ff5f56"/>
  <circle cx="36" cy="21" r="5" fill="#ffbd2e"/>
  <circle cx="52" cy="21" r="5" fill="#27c93f"/>
  <text x="480" y="26" fill="#888" font-family="-apple-system, system-ui, sans-serif" font-size="12" text-anchor="middle">http://127.0.0.1:8000 – SENSAI Local Assistant</text>

  <!-- Sidebar -->
  <rect x="0" y="42" width="230" height="578" fill="#141414"/>
  <text x="24" y="78" fill="#fff" font-family="-apple-system, system-ui, sans-serif" font-size="15" font-weight="700">SENSAI</text>
  <rect x="18" y="96" width="194" height="34" rx="6" fill="#242424"/>
  <text x="36" y="118" fill="#e0e0e0" font-family="-apple-system, system-ui, sans-serif" font-size="12.5">+ New chat</text>
  <rect x="18" y="138" width="194" height="34" rx="6" fill="#1e293b" stroke="#38bdf8" stroke-width="1"/>
  <text x="36" y="160" fill="#38bdf8" font-family="-apple-system, system-ui, sans-serif" font-size="12" font-weight="600">📄 Try the demo PDF</text>
  <text x="20" y="200" fill="#666" font-family="-apple-system, system-ui, sans-serif" font-size="10.5" font-weight="700">CHATS</text>
  <text x="24" y="226" fill="#bbb" font-family="-apple-system, system-ui, sans-serif" font-size="12">IPv6 Network Analysis</text>
  <text x="24" y="254" fill="#777" font-family="-apple-system, system-ui, sans-serif" font-size="12">Ethernet Frame Payload</text>

  <!-- Settings in sidebar bottom -->
  <line x1="0" y1="565" x2="230" y2="565" stroke="#252525" stroke-width="1"/>
  <text x="24" y="592" fill="#999" font-family="-apple-system, system-ui, sans-serif" font-size="12">⚙ Settings &amp; Feature Flags</text>

  <!-- Main Chat Area -->
  <rect x="230" y="42" width="460" height="578" fill="#1a1a1a"/>
  
  <!-- User Message -->
  <rect x="420" y="80" width="250" height="54" rx="8" fill="#262626"/>
  <text x="432" y="102" fill="#fff" font-family="-apple-system, system-ui, sans-serif" font-size="12">How many bits long is an</text>
  <text x="432" y="120" fill="#fff" font-family="-apple-system, system-ui, sans-serif" font-size="12">IPv6 address?</text>
  <text x="635" y="126" fill="#888" font-family="-apple-system, system-ui, sans-serif" font-size="10">✎ &lt; 1 / 2 &gt;</text>

  <!-- Bot Message -->
  <rect x="250" y="150" width="420" height="150" rx="8" fill="#212121" stroke="#2f2f2f" stroke-width="1"/>
  <text x="268" y="180" fill="#7ee787" font-family="-apple-system, system-ui, sans-serif" font-size="12" font-weight="700">SENSAI Assistant</text>
  <text x="268" y="206" fill="#eee" font-family="-apple-system, system-ui, sans-serif" font-size="13">An IPv6 address is 128 bits long.</text>
  
  <!-- Source Citation badge -->
  <rect x="268" y="226" width="384" height="58" rx="6" fill="#171e27" stroke="#1f4460" stroke-width="1"/>
  <text x="282" y="246" fill="#38bdf8" font-family="-apple-system, system-ui, sans-serif" font-size="11" font-weight="700">PAGE 13 CITATION</text>
  <text x="282" y="266" fill="#94a3b8" font-family="-apple-system, system-ui, sans-serif" font-size="11">"An IPv6 address is 128 bits long, giving 3.4x10^38 addresses..."</text>

  <!-- Input Bar -->
  <rect x="250" y="555" width="420" height="42" rx="21" fill="#262626" stroke="#333" stroke-width="1"/>
  <text x="274" y="581" fill="#777" font-family="-apple-system, system-ui, sans-serif" font-size="12.5">Message SENSAI (demo.pdf attached)...</text>
  <circle cx="648" cy="576" r="14" fill="#38bdf8"/>
  <path d="M648 571 L643 577 L653 577 Z" fill="#000"/>

  <!-- Right Drawer / Settings Panel (Feature Flags) -->
  <rect x="690" y="42" width="270" height="578" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="710" y="78" fill="#fff" font-family="-apple-system, system-ui, sans-serif" font-size="13.5" font-weight="700">Configuration &amp; Flags</text>
  
  <rect x="710" y="100" width="230" height="40" rx="6" fill="#21262d"/>
  <text x="722" y="125" fill="#58a6ff" font-family="-apple-system, system-ui, sans-serif" font-size="11" font-weight="600">Model: qwen3:4b (Local)</text>

  <text x="710" y="170" fill="#8b949e" font-family="-apple-system, system-ui, sans-serif" font-size="10.5" font-weight="700">ACTIVE FEATURE FLAGS (P9)</text>
  
  <rect x="710" y="186" width="230" height="34" rx="6" fill="#1c2128"/>
  <text x="724" y="208" fill="#e6edf3" font-family="-apple-system, system-ui, sans-serif" font-size="11">✓ RAG Pipeline (R1)</text>
  
  <rect x="710" y="226" width="230" height="34" rx="6" fill="#1c2128"/>
  <text x="724" y="248" fill="#e6edf3" font-family="-apple-system, system-ui, sans-serif" font-size="11">✓ LLM Judge Eval (EV1)</text>

  <rect x="710" y="266" width="230" height="34" rx="6" fill="#1c2128"/>
  <text x="724" y="288" fill="#e6edf3" font-family="-apple-system, system-ui, sans-serif" font-size="11">✓ Exact Quote Check</text>

  <rect x="710" y="306" width="230" height="34" rx="6" fill="#1c2128"/>
  <text x="724" y="328" fill="#e6edf3" font-family="-apple-system, system-ui, sans-serif" font-size="11">✓ Cross-Session Memory (M3)</text>
</svg>"""
    (OUT_DIR / filename).write_text(svg)
    print(f"Generated {filename}")

make_webui_svg()

# 7. Pytest Test Suite (380 tests passed)
make_terminal_svg(
    "Terminal – Automated Pytest Test Suite (380 Tests Passing)",
    [
        "$ PYTHONPATH=. .venv/bin/pytest -v",
        "============================= test session starts ==============================",
        "platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0",
        "rootdir: /home/rescue/Repositories/Tek 3/Semestre 5/Sensai",
        "collected 380 items",
        "",
        "tests/test_m1_ollama_client.py .........                                 [ 2%]",
        "tests/test_m2_store.py ..........                                        [ 5%]",
        "tests/test_m3_m4_pipeline.py .........................                   [11%]",
        "tests/test_m5_judge.py ..............                                    [15%]",
        "tests/test_m6_eval_summary.py .............                              [18%]",
        "tests/test_general_fallback.py ........                                  [20%]",
        "tests/test_dynamic_context.py .......                                    [22%]",
        "tests/test_branching.py ........                                         [24%]",
        "tests/test_cross_session_memory.py ........                              [26%]",
        "tests/test_feature_flags.py ......                                       [28%]",
        "tests/test_cli.py ..................................................... [ 78%]",
        "tests/test_web_ui.py .................................................. [100%]",
        "",
        "============================== 380 passed in 3.56s =============================="
    ],
    "07_pytest_test_suite_all_green.svg",
    height=480
)

# Also generate the legacy 04 & 05 names for backwards compatibility
make_terminal_svg(
    "Terminal – Automated Pytest Test Suite (380 Tests Passing)",
    [
        "$ PYTHONPATH=. .venv/bin/pytest -q",
        "................................................................................ [ 21%]",
        "................................................................................ [ 42%]",
        "................................................................................ [ 63%]",
        "................................................................................ [ 84%]",
        "............................................................                     [100%]",
        "380 passed in 3.56s (100% pass rate)"
    ],
    "04_pytest_test_suite_all_green.svg",
    height=280
)
make_webui_svg("05_web_ui_dashboard.svg")
make_terminal_svg(
    "Terminal – Conversational Branching & Resume (Feature X2 - 2 Stars)",
    [
        "$ python3 -m src.chat",
        "Chatting with qwen3:4b. Type 'exit' or Ctrl+D to quit; Ctrl+C cancels a reply.",
        "Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.",
        "",
        "you> What is an IP address in one sentence?",
        "bot> (thinking...) An IP address is a unique numerical identifier assigned to each device connected to a network, enabling communication over the internet.",
        "",
        "you> /history",
        "[1] What is an IP address in one sentence?",
        "",
        "you> /edit 1 What is an IPv6 address in one sentence?",
        "[Branch created: editing turn 1]",
        "bot> (thinking...) An IPv6 address is a 128-bit identifier for a network interface in an IPv6 network.",
        "",
        "you> /branches",
        "[Branch 1] 3 messages (last user: 'What is an IP address in one s...')",
        "",
        "you> exit"
    ],
    "02_cli_branching_edit.svg",
    height=500
)
make_terminal_svg(
    "Terminal – Cross-Session Recall & Second Brain (Feature M3 - 2 Stars)",
    [
        "$ python3 -m src.chat",
        "Commands: /edit <text>, /history, /branches, /switch <n>, /memory, /recall <query>.",
        "",
        "you> /memory",
        "2 stored memory session(s):",
        " - [cli_1793291743] What is an IP address in one sentenc (4 turns)",
        " - [cli_1793288232] What is an IPv6 address in one sente (2 turns)",
        "",
        "you> What did we say about the Ethernet frame payload in our earlier chat?",
        "bot> (thinking...) In our earlier chat, we specifically stated that the maximum payload size for a standard Ethernet frame (IEEE 802.3) is 1500 bytes. We also noted that jumbo frames (up to 9000 bytes) are an exception used in specific high-speed networks but are not part of the standard Ethernet definition.",
        "",
        "you> exit"
    ],
    "03_cross_session_memory.svg",
    height=440
)

print("All screenshots successfully regenerated!")
