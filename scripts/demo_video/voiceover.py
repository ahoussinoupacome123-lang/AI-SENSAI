#!/usr/bin/env python3
"""Narrate the demo video: one spoken line per scene, placed on the video's timeline.

Uses Kokoro (open-source neural text-to-speech, Apache-2.0) through the kokoro-onnx package,
fully offline once its two model files are downloaded:

    pip install kokoro-onnx soundfile
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

    python scripts/demo_video/voiceover.py MODELS_DIR OUT.wav [OUT.srt]

Writes a 24 kHz mono track as long as the video, and optional subtitles. Stops with an error if
a line runs into the next one, so the narration always stays in sync with the picture.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

VOICE, SPEED = "af_heart", 1.05
GAP = 0.25          # minimum silence between two lines, in seconds

# (start in seconds, text). The times follow TIMELINE in render.py.
SCRIPT = [
    (0.6, "Meet Sensai. Ask a PDF, and get sourced answers. Locally."),
    (5.8, "It all runs on your machine. Your PDF never leaves it."),
    (9.6, "Attach a PDF, or try the demo."),
    (12.6, "Then ask a whole list of questions, one per line."),
    (19.0, "For each question, Sensai first finds the most relevant passages."),
    (23.9, "The model must answer in strict JSON: the answer, the page, and a quote."),
    (30.0, "Every answer comes with a word-for-word quote."),
    (33.1, "A quote check and an AI judge catch hallucinations."),
    (36.9, "One click opens the PDF at the right page."),
    (41.4, "Not in the PDF? Sensai says so, instead of guessing."),
    (45.0, "The summary shows what you can trust."),
    (47.3, "Everything is saved to a sourced answers file."),
    (52.0, "Want to change one question? Edit it, and re-run just that one."),
    (59.0, "Only its section of the file is rewritten. The rest stays identical."),
    (63.8, "Sensai is also a plain chat assistant, with a live token meter."),
    (73.9, "And you can tune the models and retrieval settings, live."),
    (78.6, "Sensai. Every answer, with its page and a quote. One hundred percent local."),
]
END = 86.0


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    from kokoro_onnx import Kokoro

    models, out = Path(sys.argv[1]), Path(sys.argv[2])
    srt = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    tts = Kokoro(str(models / "kokoro-v1.0.int8.onnx"), str(models / "voices-v1.0.bin"))
    sr = 24000
    track = np.zeros(int(END * sr), dtype=np.float32)
    cues, late = [], []
    for i, (start, text) in enumerate(SCRIPT):
        samples, sr = tts.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        loud = np.flatnonzero(np.abs(samples) > 1e-3)
        samples = samples[loud[0]:loud[-1] + 1]          # trim the leading and trailing silence only
        end = start + len(samples) / sr
        limit = SCRIPT[i + 1][0] - GAP if i + 1 < len(SCRIPT) else END - 1.0
        print(f"{start:5.1f}-{end:5.1f}s  {text}", flush=True)
        if end > limit:
            late.append(f"line at {start}s lasts {end - start:.1f}s and runs past {limit:.1f}s")
        a = int(start * sr)
        track[a:a + len(samples)] += samples
        cues.append((start, end, text))
    if late:
        sys.exit("shorten or move these lines:\n  " + "\n  ".join(late))
    track *= 0.9 / max(1e-6, float(np.abs(track).max()))
    sf.write(out, track, sr)
    if srt:
        srt.write_text("\n".join(f"{n}\n{srt_time(s)} --> {srt_time(e + 0.3)}\n{t}\n"
                                 for n, (s, e, t) in enumerate(cues, 1)))
    print("wrote", out, f"({len(cues)} lines)")


if __name__ == "__main__":
    main()
