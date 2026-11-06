#!/usr/bin/env python3
"""Synthesise the demo video's background track (original, royalty-free, numpy only).

A calm 96 BPM electronic loop in A minor (Am - F - C - G): a soft pad, a plucked arpeggio,
a sub bass, a gentle kick and hats, with an intro, a build and a fade out.

    python scripts/demo_video/music.py OUT.wav SECONDS
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
# chord roots (MIDI) and minor/major thirds: Am, F, C, G
CHORDS = [(57, [0, 3, 7, 12]), (53, [0, 4, 7, 12]), (48, [0, 4, 7, 12]), (55, [0, 4, 7, 12])]
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    """One-pole low-pass filter, run as a recursive filter on the signal."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    e[:a] = np.linspace(0, 1, a) if a else 1
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def pad(root, intervals, seconds):
    t = np.arange(int(seconds * SR)) / SR
    x = np.zeros_like(t)
    for iv in intervals[:3]:
        for detune in (-0.12, 0.0, 0.11):
            x += saw(hz(root + iv + 12 + detune), t + rng.random())
    x = lowpass(x / 9, 1400)
    return x * env(len(t), 0.6, 0.8) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t))


def pluck(f, seconds=0.5):
    t = np.arange(int(seconds * SR)) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return tone * np.exp(-t * 7) * env(len(t), 0.004, 0.05)


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 42 + 90 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat():
    t = np.arange(int(0.06 * SR)) / SR
    n = rng.standard_normal(len(t))
    return (n - lowpass(n, 6000)) * np.exp(-t * 70)


def bass(f, seconds):
    t = np.arange(int(seconds * SR)) / SR
    return np.tanh(1.6 * np.sin(2 * np.pi * f * t)) * env(len(t), 0.01, 0.12)


def add(track, sig, at, gain, pan=0.0):
    i = int(at * SR)
    if i >= len(track):
        return
    sig = sig[: len(track) - i]
    track[i:i + len(sig), 0] += sig * gain * (1 - pan) / 2 * 2
    track[i:i + len(sig), 1] += sig * gain * (1 + pan) / 2 * 2


def song(seconds):
    total = int(seconds * SR)
    track = np.zeros((total + SR, 2))
    bars = int(np.ceil(seconds / BAR))
    k, h = kick(), hat()
    for b in range(bars):
        root, ivs = CHORDS[b % 4]
        t0 = b * BAR
        add(track, pad(root, ivs, BAR + 0.8), t0, 0.26)
        drums = 2 <= b < bars - 1
        arp = b >= 1
        if b >= 2:
            for beat in range(4):
                add(track, bass(hz(root - 12), BEAT * 0.9), t0 + beat * BEAT, 0.16)
        for step in range(8):
            at = t0 + step * BEAT / 2
            if arp:
                note = root + 12 + ivs[[0, 1, 2, 3, 2, 1, 2, 3][step]]
                add(track, pluck(hz(note)), at, 0.11, pan=-0.35 if step % 2 else 0.35)
            if drums:
                if step in (0, 4):
                    add(track, k, at, 0.26)
                if step % 2 == 1:
                    add(track, h, at, 0.07, pan=0.2)
    # simple stereo echo on everything for space
    d = int(BEAT * 0.75 * SR)
    echo = np.zeros_like(track)
    echo[d:, 0] = track[:-d, 1] * 0.22
    echo[d:, 1] = track[:-d, 0] * 0.22
    track = (track + echo)[:total]
    fade_in, fade_out = int(1.5 * SR), int(4 * SR)
    track[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    track[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    return track / (np.abs(track).max() + 1e-9) * 0.8


def main():
    out, seconds = sys.argv[1], float(sys.argv[2])
    data = (song(seconds) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"wrote {out} ({seconds:.1f} s)")


if __name__ == "__main__":
    main()
