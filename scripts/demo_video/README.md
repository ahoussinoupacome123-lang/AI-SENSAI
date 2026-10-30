# Demo video

`docs/assets/demo/sensai_demo.mp4` is an 86-second product demo of the web UI (1920x1080, 30 fps, H.264) with a spoken narration, background music ducked under the voice, and English subtitles you can turn on in the player. It is built by the scripts in this folder, end to end, without Ollama.

**What is real and what is simulated.** The interface is the real one: the video is cut from screenshots of `WEB-UI/server.py` driven in Chromium. Ingestion, retrieval, the JSON validation, the quote check, `answers.md` and the summary run through the real backend code. The model is replaced by `stub_ollama.py`: its answers come from a short table about `data/demo.pdf`, its quotes are copied from the passages Sensai retrieved, and its judge always says "faithful". So the video shows how Sensai looks and behaves, not how good `qwen3:4b` is (for that, see `docs/RESULTS.md`). Headless Chromium has no PDF viewer, so during capture the side panel is served a look-alike viewer that shows page 13 rendered by `pdftoppm`.

## Build it

Needs Python with `playwright` (and its Chromium), `numpy`, `ffmpeg` with libx264 and aac, and `pdftoppm` (poppler). The narration also needs Kokoro, an open-source text-to-speech model that runs offline (Apache-2.0):

```bash
pip install kokoro-onnx soundfile
mkdir -p ~/kokoro && cd ~/kokoro
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Then, from the repository root:

```bash
python scripts/demo_video/render.py /tmp/sensai-video docs/assets/demo/sensai_demo.mp4 --voice ~/kokoro
```

Leave out `--voice` for a music-only video. That runs the steps below in order. It takes a few minutes, mostly for rendering the frames. The build folder gets `shots/` (about 100 screenshots at 2x), `manifest.json`, `music.wav` and a throwaway server workspace.

```bash
python scripts/demo_video/render.py /tmp/sensai-video --stills 15,31,60   # a few PNG frames, to check a change
python scripts/demo_video/render.py /tmp/sensai-video out.mp4 --no-capture   # re-render without re-capturing
python scripts/demo_video/render.py /tmp/sensai-video out.mp4 --audio-only --voice ~/kokoro   # only redo the sound (seconds)
```

## How it works

| File | Role |
|---|---|
| `stub_ollama.py` | an Ollama look-alike (`/api/tags`, `/api/embed`, `/api/chat`, `/api/show`): hashed bag-of-words embeddings, scripted answers and verdicts, a streamed Markdown chat reply |
| `capture.py` | starts the stub and the web server, walks through the UI (attach the demo PDF, ask 4 questions, open a page, view `answers.md`, edit and re-run one question, chat, settings), and saves each screenshot with the boxes of the elements the video points at |
| `music.py` | writes an original background track with numpy (96 BPM, A minor, pad, arpeggio, bass, soft drums, with a fade in and out), so there is no licensing question |
| `voiceover.py` | speaks one line per scene with Kokoro (voice `af_heart`), places each line at its time on the video, and writes the subtitles; it stops with an error if a line would run into the next one |
| `compositor.html` | draws any frame from its time `t`: the browser frame, camera zooms, cursor and clicks, callout cards with connectors and highlight rings, chapter titles, intro and outro in the keynote's colours |
| `render.py` | holds the timeline (screens, camera, cursor, callouts), renders every frame in Chromium into a silent video, then mixes the music (lowered under the voice) with the narration and adds the subtitles |

To change the story, edit `TIMELINE` in `render.py`, and the spoken lines in `SCRIPT` in `voiceover.py` (their times follow the timeline). Callouts and camera moves point at elements by name (`"results_top:quote1"`), so they follow the UI if its layout changes and you capture again.
