#!/usr/bin/env python3
"""Drive the real web UI and save the screenshots the demo video is cut from.

Starts the stub model and the web server, walks through the product in Chromium (dark theme,
1440x900 at 2x), and writes OUT/shots/*.png plus OUT/manifest.json: for every shot, its file,
its time inside its burst, and the boxes (CSS px) of the elements the video points at.

    python scripts/demo_video/capture.py OUT_DIR
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STUB_PORT, WEB_PORT = 11555, 8123
QUESTIONS = ["How many bits long is an IPv6 address?",
             "What are the four steps of the DHCP process?",
             "Which port does SSH use?",
             "Who invented the World Wide Web?"]
RERUN = "What does the TTL field do in an IP packet?"
CHAT = "Compare TCP and UDP in a short table"

out = Path(sys.argv[1]).resolve()
shots = out / "shots"
shutil.rmtree(shots, ignore_errors=True)
shots.mkdir(parents=True)
manifest = {}


def start_servers():
    config = json.loads((ROOT / "config.json").read_text())
    config["host"] = f"http://127.0.0.1:{STUB_PORT}"
    (out / "config.json").write_text(json.dumps(config, indent=1))
    ws = out / "workspace"
    shutil.rmtree(ws, ignore_errors=True)
    procs = [subprocess.Popen([sys.executable, str(HERE / "stub_ollama.py"), "--port", str(STUB_PORT)]),
             subprocess.Popen([sys.executable, str(ROOT / "WEB-UI" / "server.py"), "--port", str(WEB_PORT),
                               "--config", str(out / "config.json")], cwd=ROOT)]
    # the server keeps its uploads and answers files in WEB-UI/workspace (git-ignored)
    time.sleep(2)
    return procs


def pdf_viewer(ctx):
    """Headless Chromium has no PDF viewer, so the side panel would stay blank on film. Serve the
    panel a look-alike viewer that shows the real page, rendered from data/demo.pdf by pdftoppm."""
    pages = out / "pdf_pages"
    pages.mkdir(exist_ok=True)
    subprocess.run(["pdftoppm", "-png", "-r", "144", str(ROOT / "data" / "demo.pdf"), str(pages / "p")], check=True)
    viewer = ("<!doctype html><html><body style='margin:0;background:#525659;display:flex;justify-content:center'>"
              "<img id=p style='width:88%;margin:22px 0;box-shadow:0 2px 10px rgba(0,0,0,.5);background:#fff'>"
              "<script>var n=(location.hash.match(/page=(\\d+)/)||[0,1])[1];"
              "document.getElementById('p').src='/__pdf_page/'+n;</script></body></html>")

    def page_png(route):
        n = int(route.request.url.rsplit("/", 1)[1])
        found = sorted(pages.glob(f"p-*{n}.png"), key=lambda f: len(f.name))
        exact = [f for f in found if int(f.stem.split("-")[1]) == n]
        route.fulfill(path=str(exact[0]), content_type="image/png")

    ctx.route("**/files/**/*.pdf", lambda route: route.fulfill(body=viewer, content_type="text/html"))
    ctx.route("**/__pdf_page/*", page_png)


def boxes(page, targets):
    found = {}
    for key, sel in targets.items():
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            b = loc.bounding_box()
            found[key] = [round(b["x"], 1), round(b["y"], 1), round(b["width"], 1), round(b["height"], 1)]
    return found


def snap(page, name, targets=None, group=None, t=0.0):
    page.screenshot(path=str(shots / f"{name}.png"))
    entry = {"file": f"shots/{name}.png", "t": round(t, 3), "boxes": boxes(page, targets or {})}
    if group:
        manifest.setdefault(group, []).append(entry)
    else:
        manifest[name] = entry
    print("shot", name, flush=True)


def burst(page, group, done_js, targets, every=0.25, limit=90):
    """Screenshots until done_js is true; each is stamped with its time since the burst began."""
    t0, i = time.time(), 0
    while True:
        finished = page.evaluate(done_js)
        snap(page, f"{group}_{i:03d}", targets, group, time.time() - t0)
        i += 1
        if finished or time.time() - t0 > limit:
            return
        time.sleep(every)


def type_burst(page, group, selector, text, step=4):
    """Type text a few characters at a time, one screenshot per step (timing is set by the video)."""
    field = page.locator(selector)
    for n in list(range(step, len(text), step)) + [len(text)]:
        field.fill(text[:n])
        snap(page, f"{group}_{len(manifest.get(group, [])):03d}",
             {"input": selector, "send": "#send", "composer": "#composer"}, group)


QA = {"run": ".run-status", "q1": ".qa >> nth=0", "q2": ".qa >> nth=1", "q3": ".qa >> nth=2", "q4": ".qa >> nth=3",
      "link1": ".qa >> nth=0 >> .page-link", "quote1": ".qa >> nth=0 >> blockquote",
      "checks1": ".qa >> nth=0 >> .checks", "checks4": ".qa >> nth=3 >> .checks", "ans4": ".qa >> nth=3 >> .ans",
      "summary": ".summary", "tiles": ".tiles", "meter": "#meter", "stop": "#chat-stop"}


def main():
    procs = start_servers()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2,
                                      color_scheme="dark")
            pdf_viewer(ctx)
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{WEB_PORT}", wait_until="load")
            page.wait_for_selector("#status-pill.pill-ok", timeout=15000)
            page.wait_for_timeout(1200)
            snap(page, "home", {"composer": "#composer", "chips": "#chips", "pill": "#status-pill",
                                "sidebar": "#sidebar", "plus": "#plus", "greeting": "#chat-empty"})

            page.click("#plus")
            page.wait_for_timeout(400)
            snap(page, "menu", {"plus": "#plus", "menu": "#plus-menu", "demo": "#menu-docs button", "upload": "#menu-upload"})
            page.click("#menu-docs button")
            page.wait_for_timeout(500)
            snap(page, "attached", {"chip": "#attached", "input": "#chat-input", "composer": "#composer"})

            type_burst(page, "typing", "#chat-input", "\n".join(QUESTIONS))
            page.click("#send")
            burst(page, "run", "!!document.querySelector('.run-status.done')", QA, every=0.2)
            page.wait_for_timeout(1500)
            page.evaluate("document.querySelector('.qa').scrollIntoView({block: 'start'})")
            page.wait_for_timeout(400)
            snap(page, "results_top", QA)
            page.locator(".summary").scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            snap(page, "results_bottom", dict(QA, download="text=Download answers.md", view="text=View answers.md",
                                              review_tile="button.tile"))

            page.evaluate("document.querySelector('.qa').scrollIntoView({block: 'start'})")
            page.wait_for_timeout(300)
            snap(page, "before_panel", QA)
            page.click(".qa >> nth=0 >> .page-link")
            page.wait_for_selector("#drawer:not([hidden])")
            page.wait_for_timeout(2500)
            snap(page, "panel", {"drawer": "#drawer", "frame": "#drawer-frame", "title": "#drawer-title"})
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)

            page.locator(".summary").scroll_into_view_if_needed()
            page.click("text=View answers.md")
            page.wait_for_selector("#drawer-text:not([hidden])")
            page.wait_for_timeout(800)
            snap(page, "answers_md", {"drawer": "#drawer", "text": "#drawer-text"})
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)

            q4 = page.locator(".qa").nth(3)
            q4.scroll_into_view_if_needed()
            page.evaluate("document.querySelectorAll('.qa')[3].scrollIntoView({block: 'center'})")
            page.wait_for_timeout(300)
            snap(page, "edit_before", dict(QA, edit4=".qa >> nth=3 >> .q-edit"))
            q4.locator(".q-edit").click()
            q4.locator("textarea").fill(RERUN)
            page.wait_for_timeout(300)
            snap(page, "edit_open", dict(QA, area4=".qa >> nth=3 >> textarea", rerun4=".qa >> nth=3 >> .rerun"))
            q4.locator(".rerun").click()
            burst(page, "rerun", "!!document.querySelector('.run-status.done') && !document.querySelector('#chat-stop:not([hidden])')"
                  " && document.querySelectorAll('.qa')[3].textContent.includes('TTL')", QA, every=0.25)
            page.wait_for_timeout(1200)
            page.evaluate("document.querySelectorAll('.qa')[3].scrollIntoView({block: 'center'})")
            page.wait_for_timeout(300)
            snap(page, "rerun_done", dict(QA, newchat="#new-chat"))
            page.click("text=View answers.md")
            page.wait_for_selector("#drawer-text:not([hidden])")
            page.wait_for_timeout(600)
            page.evaluate("var t=document.querySelector('#drawer-text'); t.scrollTop = t.scrollHeight")
            page.wait_for_timeout(300)
            snap(page, "answers_md_after", {"drawer": "#drawer", "text": "#drawer-text"})
            page.keyboard.press("Escape")

            page.click("#new-chat")
            page.wait_for_timeout(600)
            type_burst(page, "chat_typing", "#chat-input", CHAT, step=3)
            page.click("#send")
            burst(page, "chat", "document.querySelector('#meter-text').textContent.includes('/ 4,096') && "
                  "!document.querySelector('#chat-stop:not([hidden])')",
                  {"meter": "#meter", "reply": ".turn.bot >> nth=-1", "user": ".turn.user >> nth=-1"}, every=0.15)
            page.wait_for_timeout(800)
            snap(page, "chat_done", {"meter": "#meter", "reply": ".turn.bot >> nth=-1", "history": "#history",
                                   "settingsbtn": "#open-settings"})

            page.click("#open-settings")
            page.wait_for_timeout(600)
            snap(page, "settings", {"modal": "#settings-modal .modal, #settings-modal > *", "form": "#settings-form"})
            browser.close()
    finally:
        for proc in procs:
            proc.terminate()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("manifest:", out / "manifest.json")


if __name__ == "__main__":
    main()
