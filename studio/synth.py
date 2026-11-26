"""Synthesize sound effects and a lo-fi background track (44.1 kHz mono float)."""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.005, r=None, curve=4.0):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    if r is not None:
        e *= np.exp(-curve * np.arange(n) / n)
    return e


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lowpass(x, f, order=2):
    sos = signal.butter(order, f, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def whoosh(d=0.55, up=True):
    n = int(SR * d)
    noise = rng.standard_normal(n)
    # sweep a band-pass filter across the noise in short blocks
    out = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        p = i / n
        c = 300 + (4000 if up else 2500) * (p if up else 1 - p)
        seg = bandpass(noise[i:i + blk * 2], c * 0.6, min(c * 1.6, 18000))[:blk]
        out[i:i + len(seg)] = seg
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return norm(out * shape, 0.55)


def pop(f0=900, f1=380, d=0.09):
    t = t_(d)
    f = np.geomspace(f0, f1, len(t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(np.sin(ph) * np.exp(-t * 38), 0.5)


def click(d=0.03):
    t = t_(d)
    x = np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 260) + 0.4 * rng.standard_normal(len(t)) * np.exp(-t * 500)
    return norm(x, 0.45)


def ding(f=1318.5, d=1.1):
    t = t_(d)
    x = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3.01 * f * t))
    return norm(x * np.exp(-t * 4.5) * env(len(t)), 0.5)


def stamp(d=0.35):
    t = t_(d)
    thump = np.sin(2 * np.pi * np.geomspace(140, 45, len(t)) * t) * np.exp(-t * 14)
    crack = lowpass(rng.standard_normal(len(t)), 3000) * np.exp(-t * 40)
    return norm(thump + 0.5 * crack, 0.75)


def riser(d=1.2):
    t = t_(d)
    f = np.geomspace(200, 1600, len(t))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    noise = bandpass(rng.standard_normal(len(t)), 800, 8000) * 0.5
    return norm((tone + noise) * np.linspace(0, 1, len(t)) ** 2, 0.4)


def typing(d=0.9):
    out = np.zeros(int(SR * d))
    c = click(0.025) * 0.6
    pos = 0
    while pos + len(c) < len(out):
        out[pos:pos + len(c)] += c * rng.uniform(0.5, 1.0)
        pos += int(SR * rng.uniform(0.06, 0.11))
    return out


SFX = {"whoosh": whoosh(), "whoosh_s": whoosh(0.35), "pop": pop(), "pop_hi": pop(1300, 600, 0.07),
       "click": click(), "ding": ding(), "stamp": stamp(), "riser": riser(), "typing": typing(),
       "success": None}
SFX["success"] = norm(np.concatenate([ding(1046.5, 0.18)[: int(SR * 0.12)], ding(1568, 0.9)]), 0.5)


# ---------------- music: lo-fi chord loop ----------------
def epiano(freq, d, vel=1.0):
    t = t_(d)
    x = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 3)
         + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 6))
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    return x * np.exp(-t * 1.3) * env(len(t), 0.01) * trem * vel


def note(n):  # midi -> Hz
    return 440 * 2 ** ((n - 69) / 12)


def music(total):
    bpm = 84
    beat = 60 / bpm
    bar = beat * 4
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 64]]  # Am7 Fmaj7 Cmaj7 G6
    bass = [45, 41, 36, 43]
    out = np.zeros(int(SR * (total + 3)))

    def put(x, at):
        i = int(at * SR)
        j = min(len(out), i + len(x))
        if i < len(out):
            out[i:j] += x[: j - i]

    kick = np.sin(2 * np.pi * np.geomspace(110, 40, int(SR * 0.3)) * t_(0.3)) * np.exp(-t_(0.3) * 12)
    hat = bandpass(rng.standard_normal(int(SR * 0.05)), 6000, 14000) * np.exp(-t_(0.05) * 90)
    snare = (bandpass(rng.standard_normal(int(SR * 0.18)), 1200, 6000) * np.exp(-t_(0.18) * 25))
    tb = 0
    k = 0
    while tb < total + bar:
        ch = chords[k % 4]
        for m in ch:
            put(epiano(note(m), bar * 1.05, 0.22), tb + 0.012 * ch.index(m))
        put(np.sin(2 * np.pi * note(bass[k % 4]) * t_(bar)) * np.exp(-t_(bar) * 0.8) * 0.35, tb)
        for b in range(4):
            at = tb + b * beat
            if b in (0, 2):
                put(kick * 0.55, at)
            if b in (1, 3):
                put(snare * 0.18, at)
            put(hat * 0.12, at + beat / 2 + 0.02)
            put(hat * 0.06, at)
        tb += bar
        k += 1
    out = lowpass(out, 5500)
    out = out[: int(SR * total)]
    fade = int(SR * 2.5)
    out[:int(SR * 1.5)] *= np.linspace(0, 1, int(SR * 1.5))
    out[-fade:] *= np.linspace(1, 0, fade)
    return norm(out, 0.8)


def _cli():
    import os, sys
    d = sys.argv[1]
    os.makedirs(d, exist_ok=True)
    for k, v in SFX.items():
        wavfile.write(f"{d}/{k}.wav", SR, (v * 32767).astype(np.int16))
    m = music(float(sys.argv[2]))
    wavfile.write(f"{d}/music.wav", SR, (m * 32767).astype(np.int16))
    print("ok", list(SFX), len(m) / SR)
