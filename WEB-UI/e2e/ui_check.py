#!/usr/bin/env python3
"""Optional end-to-end check of the web UI in a real browser (Chromium through Playwright).

    pip install playwright && playwright install chromium        # once, not in requirements.txt
    python WEB-UI/server.py &                                    # the server under test
    python WEB-UI/e2e/ui_check.py [--base http://127.0.0.1:8000] [--quick] [--shots DIR]

--quick skips the checks that need Ollama and the models (the PDF run and the chat).
Exit code 0 when every check passes. Screenshots of the main states are saved when --shots is given.
"""
import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from pdf_factory import make_blank_pdf, make_text_pdf  # noqa: E402

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    sys.exit("Playwright is not installed: pip install playwright && playwright install chromium")

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def wait_idle(page, seconds=300):
    """Poll /api/status until the server's single job slot is free (a stopped run ends when its next write fails)."""
    for _ in range(seconds):
        if not page.evaluate("fetch('/api/status').then(r => r.json()).then(s => s.busy)"):
            return
        page.wait_for_timeout(1000)
    raise TimeoutError("the server stayed busy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--shots")
    args = parser.parse_args()
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    make_blank_pdf(tmp / "scan.pdf")
    make_text_pdf(tmp / "good.pdf", ["Networks connect computers so they can share data across a building. " * 3,
                                      "The OSI model has seven layers from the physical layer to the application layer. " * 3])
    (tmp / "fake.pdf").write_bytes(b"this is not a pdf at all")
    errors = []

    def watch(page):
        page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page.on("console", lambda m: errors.append("console.error: " + m.text) if m.type == "error" and "status of 400" not in m.text else None)

    def shot(page, name):
        if shots:
            page.screenshot(path=str(shots / (name + ".png")), full_page=False)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================= desktop =================
        ctx = browser.new_context(viewport={"width": 1280, "height": 860})
        page = ctx.new_page()
        watch(page)
        page.goto(args.base, wait_until="load")
        page.wait_for_selector("#status-pill.pill-ok", timeout=15000)
        page.wait_for_timeout(1200)
        shot(page, "01_home")
        check("boot: no console or script errors", not errors, "; ".join(errors[:2]))
        check("boot: the status pill shows Ollama ready", "Ollama ready" in page.inner_text("#status-pill"))
        check("boot: the demo document is selected with its page count", "24 pages" in page.inner_text("#doc-info"))
        check("boot: the empty state invites a one-click demo", page.is_visible("#try-demo") and page.is_visible("#empty"))
        check("boot: the 3 quick example questions are pre-filled", page.input_value("#questions").count("\n") == 2)
        check("layout: the setup column sits left of the results", page.locator(".setup").bounding_box()["x"] < page.locator(".results").bounding_box()["x"])

        # tabs and the sliding indicator
        x0 = page.locator("#tab-indicator").bounding_box()["x"]
        page.click('[data-tab="chat"]')
        page.wait_for_timeout(700)
        ind, btn = page.locator("#tab-indicator").bounding_box(), page.locator('[data-tab="chat"]').bounding_box()
        check("tabs: the indicator slides under the selected tab", ind["x"] > x0 + 20 and abs(ind["x"] - btn["x"]) < 3 and abs(ind["width"] - btn["width"]) < 3)
        check("tabs: only the selected panel is visible", page.is_visible("#tab-chat") and not page.is_visible("#tab-qa"))
        check("tabs: aria-selected follows", page.get_attribute('[data-tab="chat"]', "aria-selected") == "true")
        shot(page, "02_chat_empty")
        page.click('[data-tab="settings"]')
        page.wait_for_timeout(600)
        check("settings: 8 labelled fields in 3 groups, none for the host", page.locator("#settings-form input").count() == 8 and page.locator("#settings-form .group").count() == 3)
        check("settings: human-readable labels", "Passages per question" in page.inner_text("#settings-form"))
        page.fill("#set-top_k", "99")
        page.click("#settings-apply")
        page.wait_for_selector("#settings-msg:not([hidden])")
        check("settings: an out-of-range value shows the server's message", "between 1 and 20" in page.inner_text("#settings-msg"))
        page.fill("#set-top_k", "3")
        page.click("#settings-apply")
        page.wait_for_function("document.querySelector('#settings-msg').textContent.includes('Applied')")
        page.click("#settings-reset")
        page.wait_for_function("document.querySelector('#settings-msg').textContent.includes('Back to')")
        check("settings: apply then reset round-trips", page.input_value("#set-top_k") == "4")
        shot(page, "03_settings")
        page.click('[data-tab="qa"]')

        # theme
        before = page.evaluate("getComputedStyle(document.body).backgroundColor")
        page.click("#theme")
        page.wait_for_timeout(500)
        after = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("theme: the toggle switches the palette", before != after, f"{before} -> {after}")
        shot(page, "04_dark")
        page.reload(wait_until="load")
        page.wait_for_timeout(500)
        check("theme: the choice survives a reload", page.get_attribute("html", "data-theme") in ("dark", "light"))
        page.click("#theme")
        page.wait_for_timeout(300)

        # questions and documents
        page.fill("#questions", "One?\nTwo?")
        check("questions: the counter follows the text", "2 questions" in page.inner_text("#q-count"))
        page.click("#load-all")
        check("questions: 'Load all' fills the 9 example questions", "9 questions" in page.inner_text("#q-count"))
        page.fill("#questions", "")
        page.click("#run")
        page.wait_for_selector("#notice:not([hidden])")
        check("run: no questions gives a clear message", "at least one question" in page.inner_text("#notice"))
        with page.expect_file_chooser() as chooser:
            page.click("#dropzone")
        check("upload: the drop zone opens the file chooser", chooser.value is not None)
        page.focus("#dropzone")
        check("a11y: the drop zone is reachable by keyboard", page.evaluate("document.activeElement.id") == "dropzone")
        page.set_input_files("#upload", str(tmp / "scan.pdf"))
        page.wait_for_function("document.querySelector('#notice').textContent.includes('no extractable text')")
        check("upload: a scanned PDF is refused with the clear message", True)
        page.set_input_files("#upload", str(tmp / "fake.pdf"))
        page.wait_for_function("document.querySelector('#notice').textContent.includes('not a PDF')")
        check("upload: a file that is not a PDF is refused", True)
        page.set_input_files("#upload", str(tmp / "good.pdf"))
        page.wait_for_function("document.querySelector('#doc-select').value === 'upload/good.pdf'")
        check("upload: a valid PDF is accepted and selected", "2 pages" in page.inner_text("#doc-info"))
        page.select_option("#doc-select", "builtin/demo.pdf")

        # accessibility basics
        unnamed = page.evaluate("""() => [...document.querySelectorAll('button, a[href]')].filter(b => !b.hidden && !(b.innerText.trim() || b.getAttribute('aria-label') || b.getAttribute('title'))).map(b => b.id || b.className)""")
        check("a11y: every button and link has an accessible name", not unnamed, ", ".join(unnamed))
        unlabelled = page.evaluate("""() => [...document.querySelectorAll('input, select, textarea')].filter(i => i.type !== 'file' && i.type !== 'hidden' && !(i.getAttribute('aria-label') || (i.id && document.querySelector('label[for="'+i.id+'"]')) || i.closest('label'))).map(i => i.id)""")
        check("a11y: every form field is labelled", not unlabelled, ", ".join(unlabelled))
        check("a11y: page language, one h1, a skip link", page.get_attribute("html", "lang") == "en" and page.locator("h1").count() >= 1 and page.locator(".skip").count() == 1)
        page.focus("#questions")
        page.keyboard.press("Tab")
        outline = page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
        check("a11y: keyboard focus is visible", outline != "none", outline)
        ctx.close()

        # ================= reduced motion =================
        ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
        rm = ctx.new_page()
        rm.goto(args.base, wait_until="load")
        rm.wait_for_timeout(500)
        dur = rm.evaluate("parseFloat(getComputedStyle(document.querySelector('.rise')).animationDuration)")
        check("motion: animations are switched off for prefers-reduced-motion", dur < 0.01, f"{dur}s")
        ctx.close()

        # ================= phone =================
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        ph = ctx.new_page()
        watch(ph)
        ph.goto(args.base, wait_until="load")
        ph.wait_for_selector("#status-pill.pill-ok", timeout=15000)
        ph.wait_for_timeout(1200)
        tabs = ph.locator("#tabs").bounding_box()
        check("phone: the tab bar is a bottom navigation", tabs["y"] > 844 - 130 and tabs["y"] + tabs["height"] <= 844, f"y={tabs['y']:.0f}")
        header = ph.locator("#top").bounding_box()
        check("phone: the header stays compact", header["height"] < 90, f"{header['height']:.0f}px")
        check("phone: the main action comes first", ph.locator("#try-demo").bounding_box()["y"] < ph.locator("#questions").bounding_box()["y"])
        check("phone: nothing overflows horizontally", ph.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
        small = ph.evaluate("""() => [...document.querySelectorAll('button, select, input[type=text], input[type=number], .small-btn')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 40).map(b => b.id || b.className)""")
        check("phone: touch targets are at least 40px tall", not small, ", ".join(small[:4]))
        shot(ph, "05_phone")
        ph.click('[data-tab="chat"]')
        ph.wait_for_timeout(700)
        shot(ph, "06_phone_chat")
        ctx.close()

        # ================= opened from disk =================
        ctx = browser.new_context(viewport={"width": 900, "height": 600})
        fp = ctx.new_page()
        fp.goto((ROOT / "WEB-UI" / "index.html").as_uri(), wait_until="load")
        fp.wait_for_timeout(600)
        check("file://: the page is styled and explains that it needs its server", fp.is_visible("#needs-server") and "python WEB-UI/server.py" in fp.inner_text("#needs-server")
              and fp.evaluate("getComputedStyle(document.body).fontFamily").lower().find("times") < 0)
        shot(fp, "07_opened_from_disk")
        ctx.close()

        # ================= with the models =================
        if not args.quick:
            ctx = browser.new_context(viewport={"width": 1280, "height": 860})
            page = ctx.new_page()
            watch(page)
            page.goto(args.base, wait_until="load")
            page.wait_for_selector("#status-pill.pill-ok", timeout=15000)
            page.click("#try-demo")
            page.wait_for_selector("#progress:not([hidden])")
            page.wait_for_timeout(3000)
            check("run: the progress header, the stop button and one card per question appear at once",
                  page.is_visible("#stop") and page.locator(".qcard").count() == 3 and page.is_disabled("#run"))
            shot(page, "08_running")
            page.wait_for_selector("#summary-panel:not([hidden])", timeout=420000)
            page.wait_for_function("document.querySelector('#progress').classList.contains('done')", timeout=60000)
            page.wait_for_timeout(1500)
            shot(page, "09_results")
            check("run: the bar ends at 100 and Stop disappears", page.get_attribute("#progress .bar", "aria-valuenow") == "100" and not page.is_visible("#stop"))
            check("run: a single 'Done in' message, no duplicated clock", "Done in" in page.inner_text("#progress-text") and page.inner_text("#elapsed") == "")
            card1 = page.inner_text("#card-1")
            check("run: card 1 shows the answer, the quote and both checks", "128" in card1 and "quote check: supported" in card1 and "judge:" in card1, card1[:60].replace("\n", " "))
            check("run: the summary tiles are shown", page.locator("#tiles .tile").count() == 4 and "3 / 3" in page.inner_text("#tiles"))
            card3 = page.inner_text("#card-3")
            if "faithful" in card3 and "unfaithful" not in card3:
                check("run: a correct refusal is shown calmly, without a review alarm", "not in the document" in card3 and "Review needed" not in card3)
            # PDF drawer
            page.click("#card-1 a.page-link")
            page.wait_for_selector("#drawer:not([hidden])")
            page.wait_for_timeout(700)
            src = page.get_attribute("#drawer-frame", "src")
            check("drawer: the page link opens the PDF viewer at that page", "#page=13" in src, src)
            check("drawer: it has a way to open the PDF in a new tab and focus moves into it", page.get_attribute("#drawer-open", "href").endswith("#page=13") and page.evaluate("document.activeElement.id") == "drawer-close")
            shot(page, "10_drawer")
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            check("drawer: Escape closes it and focus returns to the link", not page.is_visible("#drawer") and "page-link" in page.evaluate("document.activeElement.className"))
            # edit and re-run
            before_md = page.inner_text("#answers-md") if page.is_visible("#answers-md") else ""
            page.click("#file-preview summary")
            before_md = page.inner_text("#answers-md")
            card1_before = page.inner_text("#card-1")
            page.click("#card-2 .edit")
            page.fill("#card-2 textarea", "What is the largest payload an Ethernet frame can carry?")
            page.click("#card-2 .rerun")
            page.wait_for_function("document.querySelector('#answers-md').textContent.includes('Q2. What is the largest payload')", timeout=240000)
            page.wait_for_function("!document.querySelector('#run').disabled", timeout=60000)
            check("re-run: only card 2 changed", page.inner_text("#card-1") == card1_before and "largest payload" in page.inner_text("#card-2"))
            sec = lambda md, n: md.split(f"<!-- sensai:section {n} -->")[1].split(f"<!-- /sensai:section {n} -->")[0]
            after_md = page.inner_text("#answers-md")
            check("re-run: only section 2 of the answers file changed", sec(before_md, 1) == sec(after_md, 1) and sec(before_md, 3) == sec(after_md, 3) and sec(before_md, 2) != sec(after_md, 2))
            # filter tile (only when something needs review)
            tile = page.locator("#tiles button.tile")
            if tile.is_enabled():
                tile.click()
                page.wait_for_timeout(300)
                visible = page.locator(".qcard:visible").count()
                check("filter: clicking 'Needs review' hides the other cards", 0 < visible < 3, f"{visible} visible")
                tile.click()
            # stop in the middle of a run
            page.click("#load-all")
            page.click("#run")
            page.wait_for_function("document.querySelector('#progress-text').textContent.includes('Answering question 1')", timeout=120000)
            page.click("#stop")
            page.wait_for_function("!document.querySelector('#run').disabled", timeout=60000)
            check("stop: the UI says so and the run button works again", "Stopped" in page.inner_text("#progress-text") and not page.is_visible("#stop"))
            wait_idle(page)
            # chat with markdown
            page.click('[data-tab="chat"]')
            wait_idle(page)
            page.click("#chips button >> nth=1")
            try:
                page.wait_for_selector("#meter-text:has-text('/ 4,096')", timeout=300000)
            except Exception:
                shot(page, "chat_timeout")
                print("chat state:", page.inner_text("#meter-text"), "|", page.inner_text("#messages")[:300].replace("\n", " "))
                raise
            page.wait_for_timeout(800)
            shot(page, "11_chat_reply")
            bubble = page.locator("#messages .msg.bot .bubble").first
            text = bubble.inner_text()
            check("chat: the reply is rendered as formatted text, not raw Markdown", "**" not in text and bubble.locator("strong, table, ul, ol, p").count() > 0, text[:60].replace("\n", " "))
            check("chat: the context meter shows the tokens used", "/ 4,096 tokens" in page.inner_text("#meter-text"))
            check("chat: the composer stays inside the panel (the page does not scroll)", page.evaluate("document.documentElement.scrollHeight <= window.innerHeight + 2"))
            check("chat: the Send button is back after the reply", page.is_visible("#send") and not page.is_visible("#chat-stop"))
            ctx.close()
        browser.close()

    failed = results.count(False)
    print(f"\nUI CHECK: {len(results) - failed}/{len(results)} checks passed" + (f"; console errors: {errors[:3]}" if errors else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
