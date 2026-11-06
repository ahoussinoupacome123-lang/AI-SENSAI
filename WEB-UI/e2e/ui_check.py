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
    from playwright.sync_api import sync_playwright
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
        page.on("console", lambda m: errors.append("console.error: " + m.text) if m.type == "error" and "status of 4" not in m.text else None)

    def shot(page, name):
        if shots:
            page.screenshot(path=str(shots / (name + ".png")))

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================= desktop =================
        ctx = browser.new_context(viewport={"width": 1280, "height": 820})
        page = ctx.new_page()
        watch(page)
        page.goto(args.base, wait_until="load")
        page.wait_for_selector("#status-pill.pill-ok", timeout=15000)
        page.wait_for_timeout(900)
        shot(page, "01_home")
        check("boot: no console or script errors", not errors, "; ".join(errors[:2]))
        check("boot: the model button shows Ollama ready and the model", "Ollama ready" in page.inner_text("#status-pill") and "qwen3" in page.inner_text("#status-pill"))
        check("layout: a 260px sidebar with New chat, history and Settings",
              abs(page.locator("#sidebar").bounding_box()["width"] - 260) < 2 and page.is_visible("#new-chat") and page.is_visible("#history") and page.is_visible("#open-settings"))
        check("layout: the empty screen is a centred greeting", "What can I help with?" in page.inner_text("#chat-empty"))
        box = page.locator("#composer").bounding_box()
        check("layout: the composer sits mid-screen on an empty chat", 250 < box["y"] < 520, f"y={box['y']:.0f}")
        check("layout: the conversation column is at most 768px wide", box["width"] <= 770 and box["width"] > 600, f"{box['width']:.0f}px")
        radius = page.evaluate("parseFloat(getComputedStyle(document.getElementById('composer')).borderTopLeftRadius)")
        check("style: the composer is a rounded pill", radius >= 24, f"{radius}px")
        check("style: text is 16px, not oversized", page.evaluate("getComputedStyle(document.body).fontSize") == "16px")
        check("composer: Send is disabled while the box is empty", page.is_disabled("#send"))
        page.fill("#chat-input", "hello")
        check("composer: Send enables when there is text", page.is_enabled("#send"))
        page.fill("#chat-input", "")
        check("empty screen: suggestion pills are under the composer", page.locator("#chips button").count() >= 3 and page.locator("#chips").bounding_box()["y"] > box["y"])

        # attach menu
        page.click("#plus")
        page.wait_for_timeout(250)
        check("attach: the + menu offers upload and the demo document", page.is_visible("#menu-upload") and "demo.pdf" in page.inner_text("#menu-docs"))
        shot(page, "02_menu")
        page.click("#menu-docs button")
        check("attach: choosing a document shows a chip with its page count", "demo.pdf" in page.inner_text("#attached") and "24 pages" in page.inner_text("#attached"))
        check("attach: the placeholder asks about the document", "demo.pdf" in page.get_attribute("#chat-input", "placeholder"))
        page.click("#detach")
        check("attach: the chip can be removed", not page.is_visible("#attached"))
        page.click("#plus")
        page.keyboard.press("Escape")
        check("attach: Escape closes the menu", not page.is_visible("#plus-menu"))

        # uploads
        with page.expect_file_chooser() as chooser:
            page.click("#plus")
            page.click("#menu-upload")
        check("upload: the menu opens the file chooser", chooser.value is not None)
        page.set_input_files("#upload", str(tmp / "scan.pdf"))
        page.wait_for_function("document.querySelector('#notice').textContent.includes('no extractable text')")
        check("upload: a scanned PDF is refused with the clear message", True)
        page.set_input_files("#upload", str(tmp / "fake.pdf"))
        page.wait_for_function("document.querySelector('#notice').textContent.includes('not a PDF')")
        check("upload: a file that is not a PDF is refused", True)
        page.set_input_files("#upload", str(tmp / "good.pdf"))
        page.wait_for_function("document.querySelector('#attached-name').textContent === 'good.pdf'")
        check("upload: a valid PDF is accepted and attached", "2 pages" in page.inner_text("#attached"))
        page.click("#detach")

        # settings dialog
        page.click("#open-settings")
        page.wait_for_selector("#settings-modal:not([hidden])")
        page.wait_for_timeout(300)
        shot(page, "03_settings")
        check("settings: 8 value fields and 3 feature switches in 4 groups, none for the host",
              page.locator("#settings-form input:not([type=checkbox])").count() == 8 and page.locator("#settings-form input[type=checkbox]").count() == 3
              and page.locator("#settings-form .group").count() == 4)
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
        page.uncheck("#flag-judge")
        page.click("#settings-apply")
        page.wait_for_function("document.querySelector('#settings-msg').textContent.includes('Applied')")
        flags_off = page.evaluate("fetch('/api/status').then(r => r.json()).then(s => s.config.feature_flags)")
        check("settings: the judge switch turns the judge off on the server", flags_off.get("judge") is False and flags_off.get("rag") is True)
        page.click("#settings-reset")
        page.wait_for_function("document.querySelector('#settings-msg').textContent.includes('Back to')")
        check("settings: reset switches the judge back on", page.is_checked("#flag-judge"))
        page.keyboard.press("Escape")
        check("settings: Escape closes the dialog and focus returns", not page.is_visible("#settings-modal") and page.evaluate("document.activeElement.id") == "open-settings")

        # theme and sidebar
        before = page.evaluate("getComputedStyle(document.body).backgroundColor")
        page.click("#theme")
        page.wait_for_timeout(400)
        after = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("theme: the toggle switches to a dark palette", before != after, f"{before} -> {after}")
        shot(page, "04_dark")
        page.reload(wait_until="load")
        page.wait_for_timeout(400)
        check("theme: the choice survives a reload", page.get_attribute("html", "data-theme") == "dark")
        page.click("#theme")
        page.click("#side-close")
        page.wait_for_timeout(450)
        check("sidebar: it can be collapsed and reopened", not page.locator("#sidebar").is_visible() or page.locator("#sidebar").bounding_box()["x"] < -200)
        page.click("#side-open")
        page.wait_for_timeout(450)
        check("sidebar: reopening brings it back", page.locator("#sidebar").bounding_box()["x"] >= -1)

        # accessibility basics
        unnamed = page.evaluate("""() => [...document.querySelectorAll('button, a[href]')].filter(b => !b.hidden && b.offsetParent && !(b.innerText.trim() || b.getAttribute('aria-label') || b.getAttribute('title'))).map(b => b.id || b.className)""")
        check("a11y: every button and link has an accessible name", not unnamed, ", ".join(unnamed))
        unlabelled = page.evaluate("""() => [...document.querySelectorAll('input, select, textarea')].filter(i => i.type !== 'file' && i.type !== 'hidden' && !(i.getAttribute('aria-label') || (i.id && document.querySelector('label[for="'+i.id+'"]')) || i.closest('label'))).map(i => i.id)""")
        check("a11y: every form field is labelled", not unlabelled, ", ".join(unlabelled))
        check("a11y: page language, a main landmark, a skip link", page.get_attribute("html", "lang") == "en" and page.locator("main").count() == 1 and page.locator(".skip").count() == 1)
        page.focus("#chat-input")
        page.keyboard.press("Tab")
        outline = page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
        check("a11y: keyboard focus is visible", outline != "none", outline)
        ctx.close()

        # ================= reduced motion =================
        ctx = browser.new_context(viewport={"width": 1280, "height": 820}, reduced_motion="reduce")
        rm = ctx.new_page()
        rm.goto(args.base, wait_until="load")
        rm.wait_for_timeout(400)
        dur = rm.evaluate("parseFloat(getComputedStyle(document.querySelector('.empty')).animationDuration)")
        check("motion: animations are switched off for prefers-reduced-motion", dur < 0.01, f"{dur}s")
        ctx.close()

        # ================= phone =================
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        ph = ctx.new_page()
        watch(ph)
        ph.goto(args.base, wait_until="load")
        ph.wait_for_selector("#status-pill.pill-ok", timeout=15000)
        ph.wait_for_timeout(900)
        shot(ph, "05_phone")
        check("phone: the sidebar is hidden until opened", ph.locator("#sidebar").bounding_box()["x"] < -100)
        check("phone: the composer fits the screen", ph.locator("#composer").bounding_box()["x"] >= 0 and ph.locator("#composer").bounding_box()["x"] + ph.locator("#composer").bounding_box()["width"] <= 391)
        check("phone: nothing overflows horizontally", ph.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
        ph.click("#side-open")
        ph.wait_for_timeout(450)
        shot(ph, "06_phone_sidebar")
        check("phone: the hamburger opens the sidebar over a dimmed page", ph.locator("#sidebar").bounding_box()["x"] >= -1 and ph.is_visible("#scrim"))
        ph.click("#scrim", position={"x": 370, "y": 400})
        ph.wait_for_timeout(450)
        check("phone: tapping the dimmed page closes it", ph.locator("#sidebar").bounding_box()["x"] < -100)
        small = ph.evaluate("""() => [...document.querySelectorAll('button')].filter(b => b.offsetParent && b.getBoundingClientRect().height < 36 && !b.closest('#history')).map(b => b.id || b.className)""")
        check("phone: touch targets are at least 36px tall", not small, ", ".join(small[:4]))
        ctx.close()

        # ================= opened from disk =================
        ctx = browser.new_context(viewport={"width": 900, "height": 600})
        fp = ctx.new_page()
        fp.goto((ROOT / "WEB-UI" / "index.html").as_uri(), wait_until="load")
        fp.wait_for_timeout(500)
        check("file://: the page is styled and explains that it needs its server",
              fp.is_visible("#needs-server") and "python WEB-UI/server.py" in fp.inner_text("#needs-server")
              and fp.evaluate("getComputedStyle(document.body).fontFamily").lower().find("times") < 0)
        ctx.close()

        # ================= with the models =================
        if not args.quick:
            ctx = browser.new_context(viewport={"width": 1280, "height": 820})
            page = ctx.new_page()
            watch(page)
            page.goto(args.base, wait_until="load")
            page.wait_for_selector("#status-pill.pill-ok", timeout=15000)
            wait_idle(page)
            page.click("#try-demo")
            page.wait_for_selector(".run-status", state="visible")
            page.wait_for_timeout(2500)
            check("run: the user message, a live status, the Stop button and one block per question appear at once",
                  page.is_visible("#chat-stop") and page.locator(".qa").count() == 3 and "demo.pdf" in page.inner_text(".user-doc"))
            check("run: the conversation is saved in the sidebar", page.locator(".hist-row").count() == 1 and "demo.pdf" in page.inner_text("#history"))
            shot(page, "07_running")
            page.wait_for_selector(".summary", timeout=420000)
            page.wait_for_function("document.querySelector('.run-status').classList.contains('done')", timeout=60000)
            page.wait_for_timeout(1200)
            shot(page, "08_results")
            check("run: 'Done in' is shown once and Send is back", "Done in" in page.inner_text(".run-status") and page.is_visible("#send") and not page.is_visible("#chat-stop"))
            q1 = page.locator(".qa").nth(0).inner_text()
            check("run: block 1 shows the answer, the quote and both checks", "128" in q1 and "quote check: supported" in q1 and "judge:" in q1, q1[:50].replace("\n", " "))
            check("run: the summary tiles and file buttons are shown", page.locator(".tiles .tile").count() == 4 and "3 / 3" in page.inner_text(".tiles") and "Download answers.md" in page.inner_text(".summary"))
            q3 = page.locator(".qa").nth(2).inner_text()
            if "judge: faithful" in q3:
                check("run: a correct refusal is shown calmly, without a review alarm", "not in the document" in q3 and "Review needed" not in q3)
            # PDF side panel
            page.click("a.page-link >> nth=0")
            page.wait_for_selector("#drawer:not([hidden])")
            page.wait_for_timeout(600)
            src = page.get_attribute("#drawer-frame", "src")
            check("panel: the page link opens the PDF at that page in a side panel", "#page=13" in src, src)
            check("panel: focus moves into it and Escape closes it, returning focus", page.evaluate("document.activeElement.id") == "drawer-close")
            shot(page, "09_panel")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            check("panel: closed again with focus back on the link", not page.is_visible("#drawer") and "page-link" in page.evaluate("document.activeElement.className"))
            # answers file view
            page.click("text=View answers.md")
            page.wait_for_selector("#drawer-text:not([hidden])")
            before_md = page.inner_text("#drawer-text")
            check("file: the answers file opens in the panel", "<!-- sensai:section 1 -->" in before_md)
            page.keyboard.press("Escape")
            # edit and re-run
            q1_before = page.locator(".qa").nth(0).inner_text()
            page.locator(".qa").nth(1).locator(".q-edit").click()
            page.locator(".qa").nth(1).locator("textarea").fill("What is the largest payload an Ethernet frame can carry?")
            page.locator(".qa").nth(1).locator(".rerun").click()
            page.wait_for_function("document.querySelectorAll('.qa')[1].textContent.includes('largest payload') && document.querySelector('.summary') && !document.querySelector('#chat-stop:not([hidden])')", timeout=300000)
            page.wait_for_timeout(800)
            check("re-run: only block 2 changed", page.locator(".qa").nth(0).inner_text() == q1_before)
            page.click("text=View answers.md")
            page.wait_for_selector("#drawer-text:not([hidden])")
            after_md = page.inner_text("#drawer-text")
            sec = lambda md, n: md.split(f"<!-- sensai:section {n} -->")[1].split(f"<!-- /sensai:section {n} -->")[0]
            check("re-run: only section 2 of the answers file changed", sec(before_md, 1) == sec(after_md, 1) and sec(before_md, 3) == sec(after_md, 3) and sec(before_md, 2) != sec(after_md, 2))
            page.keyboard.press("Escape")
            tile = page.locator("button.tile")
            if tile.is_enabled():
                tile.click()
                page.wait_for_timeout(250)
                visible = page.locator(".qa:visible").count()
                check("filter: clicking 'Needs review' hides the other blocks", 0 < visible < 3, f"{visible} visible")
                tile.click()
            # stop in the middle of a run
            page.click("#new-chat")
            page.click("#chips button >> nth=1")
            page.wait_for_function("document.querySelector('.stext') && document.querySelector('.stext').textContent.includes('Answering question 1')", timeout=180000)
            page.click("#chat-stop")
            page.wait_for_function("document.querySelector('.run-status').classList.contains('stopped')", timeout=60000)
            check("stop: the UI says so and Send is back at once", "Stopped" in page.inner_text(".run-status") and page.is_visible("#send") and not page.is_visible("#chat-stop"))
            wait_idle(page)
            # chat with Markdown, then history
            page.click("#new-chat")
            page.click("#chips button >> nth=3")
            page.wait_for_function("document.querySelector('#meter-text').textContent.includes('/ 4,096')", timeout=300000)
            page.wait_for_timeout(600)
            shot(page, "10_chat")
            bot = page.locator(".turn.bot .md").last
            text = bot.inner_text()
            check("chat: the reply is rendered as formatted text, not raw Markdown", "**" not in text and len(text) > 40, text[:50].replace("\n", " "))
            check("chat: the context meter shows the tokens used", "/ 4,096 tokens" in page.inner_text("#meter-text"))
            check("chat: the page itself does not scroll", page.evaluate("document.documentElement.scrollHeight <= window.innerHeight + 2"))
            check("chat: there is no avatar clutter beside the reply", not page.locator(".avatar").first.is_visible())
            n = page.locator(".hist-row").count()
            page.reload(wait_until="load")
            page.wait_for_selector("#status-pill.pill-ok", timeout=15000)
            check("history: chats survive a reload", page.locator(".hist-row").count() == n and n >= 3, f"{n} chats")
            page.locator(".hist-open").nth(n - 1).click()
            page.wait_for_timeout(500)
            check("history: opening an old PDF chat restores its answers", page.locator(".qa").count() == 3 and "128" in page.inner_text(".qa >> nth=0"))
            page.locator(".hist-row").nth(0).hover()
            page.locator(".hist-del").nth(0).click()
            page.wait_for_timeout(300)
            check("history: a chat can be deleted", page.locator(".hist-row").count() == n - 1)
            ctx.close()
        browser.close()

    failed = results.count(False)
    print(f"\nUI CHECK: {len(results) - failed}/{len(results)} checks passed" + (f"; console errors: {errors[:3]}" if errors else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
