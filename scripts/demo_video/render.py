#!/usr/bin/env python3
"""Build the Sensai product demo video: capture the real UI, add callouts, music, encode MP4.

    python scripts/demo_video/render.py BUILD_DIR OUT.mp4            # capture + render
    python scripts/demo_video/render.py BUILD_DIR OUT.mp4 --no-capture
    python scripts/demo_video/render.py BUILD_DIR --stills 12,30,47  # a few PNG frames to check

Needs Playwright with Chromium, ffmpeg (libx264, aac) and pdftoppm. No Ollama: the answers come
from stub_ollama.py, so the video shows the real interface with scripted model output.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FPS = 30

# ---------------------------------------------------------------------------------------------
# The timeline, in seconds. Targets are "shot:box" from manifest.json (boxes in screenshot px);
# a burst is addressed as "name#index" (default: its last frame).
# ---------------------------------------------------------------------------------------------
TIMELINE = {
    "introEnd": 5.4,
    "outro": 77.8,
    "end": 86.0,
    "features": [["R1", "Local RAG"], ["T5", "Structured JSON"], ["EV1", "Quote check + judge"],
                 ["M4", "Living answers.md"], ["X1", "Web UI"], ["B1", "CLI chatbot"]],
    "chapters": [
        {"at": 5.4, "n": "01", "label": "Attach a PDF"},
        {"at": 12.0, "n": "02", "label": "Ask a list of questions"},
        {"at": 18.4, "n": "03", "label": "Watch it answer"},
        {"at": 29.2, "n": "04", "label": "Check every source"},
        {"at": 46.4, "n": "05", "label": "A living answers file"},
        {"at": 63.2, "n": "06", "label": "Chat and settings"},
    ],
    "screens": [
        {"at": 0, "shot": "home"},
        {"at": 9.4, "shot": "menu"},
        {"at": 11.0, "shot": "attached"},
        {"at": 12.4, "burst": "typing", "dur": 5.6},
        {"at": 18.6, "burst": "run", "speed": 0.95},
        {"at": 29.2, "shot": "results_top", "fade": 0.5},
        {"at": 36.8, "shot": "panel"},
        {"at": 41.0, "shot": "results_bottom", "fade": 0.5},
        {"at": 46.8, "shot": "answers_md"},
        {"at": 51.6, "shot": "edit_before", "fade": 0.5},
        {"at": 53.4, "shot": "edit_open"},
        {"at": 55.6, "burst": "rerun", "speed": 0.9},
        {"at": 58.8, "shot": "rerun_done", "fade": 0.4},
        {"at": 63.4, "burst": "chat_typing", "dur": 2.2},
        {"at": 66.0, "burst": "chat", "speed": 0.9},
        {"at": 70.0, "shot": "chat_done", "fade": 0.3},
        {"at": 73.6, "shot": "settings"},
    ],
    "camera": [
        {"at": 5.6, "z": 1.0},
        {"at": 8.6, "z": 1.32, "focus": "home:composer", "dur": 1.4},
        {"at": 12.2, "z": 1.38, "focus": "typing:composer", "dur": 1.0},
        {"at": 18.6, "z": 1.0, "dur": 1.0},
        {"at": 21.0, "z": 1.18, "focus": [830, 360], "dur": 1.6},
        {"at": 29.2, "z": 1.38, "focus": [745, 230], "dur": 1.2},
        {"at": 36.4, "z": 1.0, "dur": 0.9},
        {"at": 41.0, "z": 1.35, "focus": [740, 230], "dur": 1.2},
        {"at": 46.4, "z": 1.0, "dur": 0.8},
        {"at": 47.4, "z": 1.22, "focus": [900, 450], "dur": 1.2},
        {"at": 51.6, "z": 1.38, "focus": [740, 420], "dur": 1.2},
        {"at": 58.8, "z": 1.38, "focus": [740, 400], "dur": 0.8},
        {"at": 62.4, "z": 1.0, "dur": 1.0},
        {"at": 66.2, "z": 1.2, "focus": [830, 400], "dur": 1.2},
        {"at": 73.4, "z": 1.0, "dur": 0.8},
        {"at": 74.4, "z": 1.15, "focus": "settings:modal", "dur": 1.0},
        {"at": 77.4, "z": 0.94, "dur": 0.8},
    ],
    "cursor": [
        {"at": 8.8, "to": [980, 640], "move": 0.6},
        {"at": 9.4, "to": "home:plus", "move": 0.6, "click": True},
        {"at": 11.0, "to": "menu:demo", "move": 0.8, "click": True},
        {"at": 12.4, "to": "typing#-1:send", "move": 1.0},
        {"at": 18.4, "to": "typing#-1:send", "move": 0.2, "click": True},
        {"at": 20.0, "to": [1320, 760], "move": 1.2},
        {"at": 36.6, "to": "results_top:link1", "move": 1.2, "click": True},
        {"at": 40.6, "to": [1300, 700], "move": 0.8},
        {"at": 46.6, "to": "results_bottom:view", "move": 1.2, "click": True},
        {"at": 53.4, "to": "edit_before:edit4", "move": 1.2, "click": True},
        {"at": 55.6, "to": "edit_open:rerun4", "move": 1.0, "click": True},
        {"at": 63.2, "to": "rerun_done:newchat", "move": 1.4, "click": True},
        {"at": 65.8, "to": "chat_typing#-1:send", "move": 1.2, "click": True},
        {"at": 73.4, "to": "chat_done:settingsbtn", "move": 1.4, "click": True},
        {"at": 77.0, "hide": True},
    ],
    "callouts": [
        {"at": 6.0, "dur": 2.7, "target": "home:pill", "side": "right", "dy": 40, "kicker": "100% LOCAL",
         "title": "Runs on your machine", "text": "Ollama + qwen3:4b. Your PDF never leaves your computer."},
        {"at": 9.8, "dur": 2.0, "target": "menu:menu", "side": "right", "kicker": "R1 · INGESTION",
         "title": "Upload any text PDF", "text": "Or pick the 24-page demo course on networks."},
        {"at": 13.0, "dur": 5.0, "target": "typing#-1:input", "side": "bottom", "dy": 30, "h": 150, "kicker": "ONE PER LINE",
         "title": "Ask a whole list", "text": "Sensai answers each question in turn."},
        {"at": 19.6, "dur": 3.8, "target": "run#5:run", "side": "right", "kicker": "R1 · RETRIEVAL",
         "title": "Find the passages first", "text": "Each question is embedded; the 4 closest chunks are retrieved."},
        {"at": 23.8, "dur": 4.6, "target": "run#-1:q1", "side": "right", "kicker": "T5 · STRUCTURED OUTPUT",
         "title": "{ answer, page, quote }", "text": "The model must answer in JSON. Invalid output is retried, never written."},
        {"at": 30.2, "dur": 2.6, "target": "results_top:quote1", "side": "left", "pad": 6, "kicker": "SOURCED",
         "title": "Word-for-word quote", "text": "Copied from the passage, so you can verify it."},
        {"at": 33.0, "dur": 3.2, "target": "results_top:checks1", "side": "left", "pad": 6, "kicker": "EV1 · EVALUATION",
         "title": "Hallucination guard", "text": "A deterministic quote check plus an LLM judge. Disagreements are flagged."},
        {"at": 34.6, "dur": 2.2, "target": "results_top:link1", "side": "top", "pad": 6, "h": 110, "dx": 120, "kicker": "CITATION",
         "title": "Every answer cites its page"},
        {"at": 37.4, "dur": 3.2, "target": "panel:drawer", "side": "left", "pad": 0, "kicker": "ONE CLICK",
         "title": "Opens the PDF at page 13", "text": "Read the source right next to the answer."},
        {"at": 41.8, "dur": 2.4, "target": "results_bottom:ans4", "side": "left", "pad": 8, "kicker": "NO GUESSING",
         "title": "Knows when to say no", "text": "Not in the PDF? It says so instead of inventing an answer."},
        {"at": 44.3, "dur": 2.2, "target": "results_bottom:tiles", "side": "left", "pad": 8, "kicker": "RUN SUMMARY",
         "title": "Trust at a glance", "text": "Answered, sourced, faithful, and what needs review."},
        {"at": 47.8, "dur": 3.4, "target": "answers_md:text", "side": "left", "pad": 0, "kicker": "M4 · ARTIFACT",
         "title": "A sourced answers.md", "text": "One section per question: answer, page, quote and both checks."},
        {"at": 53.8, "dur": 1.8, "target": "edit_open:area4", "side": "left", "pad": 6, "kicker": "EDIT AND RE-RUN",
         "title": "Change one question"},
        {"at": 59.4, "dur": 3.2, "target": "rerun_done:q4", "side": "left", "pad": 8, "kicker": "M4 · LIVING DOCUMENT",
         "title": "Only that section changes", "text": "Every other byte of answers.md stays identical."},
        {"at": 70.4, "dur": 2.8, "target": "chat_done:reply", "side": "right", "pad": 8, "dx": -30, "kicker": "B1 · CHAT",
         "title": "Plain chat, too", "text": "Streaming replies with Markdown, and a live token meter."},
        {"at": 74.6, "dur": 2.8, "target": "settings:modal", "side": "right", "pad": 0, "kicker": "CONFIGURATION",
         "title": "Tune it live", "text": "Models, top-k, chunking and context size, no restart."},
    ],
}


def load_manifest(build):
    manifest = json.loads((build / "manifest.json").read_text())
    for entry in manifest.values():
        for e in entry if isinstance(entry, list) else [entry]:
            e["file"] = (build / e["file"]).as_uri()
    return manifest


def open_compositor(p, build):
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((HERE / "compositor.html").as_uri())
    page.evaluate("([m, t]) => window.setup(m, t)", [load_manifest(build), TIMELINE])
    return browser, page, errors


def render_frame(page, t):
    page.evaluate("t => window.renderAt(t)", t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--no-capture", action="store_true")
    ap.add_argument("--stills", help="comma-separated times; writes BUILD/still_T.png and stops")
    args = ap.parse_args()
    build = Path(args.build).resolve()

    if not args.no_capture and not args.stills:
        subprocess.run([sys.executable, str(HERE / "capture.py"), str(build)], check=True)

    with sync_playwright() as p:
        browser, page, errors = open_compositor(p, build)
        if args.stills:
            for t in [float(x) for x in args.stills.split(",")]:
                render_frame(page, t)
                page.screenshot(path=str(build / f"still_{t:05.1f}.png"))
            browser.close()
            print("errors:", errors or "none")
            return

        music = build / "music.wav"
        subprocess.run([sys.executable, str(HERE / "music.py"), str(music), str(TIMELINE["end"])], check=True)
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(FPS), "-i", "-",
             "-i", str(music), "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(Path(args.out).resolve())],
            stdin=subprocess.PIPE)
        frames = int(TIMELINE["end"] * FPS)
        for i in range(frames):
            render_frame(page, i / FPS)
            ffmpeg.stdin.write(page.screenshot(type="jpeg", quality=93))
            if i % (FPS * 5) == 0:
                print(f"frame {i}/{frames}", flush=True)
        ffmpeg.stdin.close()
        browser.close()
        if ffmpeg.wait() != 0:
            sys.exit("ffmpeg failed")
        if errors:
            sys.exit(f"compositor errors: {errors}")
        print("wrote", args.out)


if __name__ == "__main__":
    main()
