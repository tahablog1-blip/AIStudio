"""Audio department: dialogue cleanup, loudness, ducking mix, SFX library, music bed, spotting."""
import json
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

from .core import ffmpeg, probe, write_json

SR = 44100


def to_wav(src, out, sr=SR, mono=True):
    ffmpeg("-i", src, "-vn", "-ar", str(sr), "-ac", "1" if mono else "2", str(out))
    return str(out)


def _read(p):
    sr, x = wavfile.read(p)
    x = x.astype(np.float32) / (32768 if x.dtype == np.int16 else 1)
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = signal.resample_poly(x, SR, sr)
    return x


def _write(p, x):
    wavfile.write(p, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    return str(p)


def cleanup(src, out_dir, denoise=True, deess=True, target_lufs=-16):
    """Dialogue chain: HPF 80Hz → FFT denoise → de-ess → presence EQ → compressor → loudness."""
    chain = ["highpass=f=80", "lowpass=f=15000"]
    if denoise:
        chain.append("afftdn=nr=12:nf=-40")
    if deess:
        chain.append("deesser=i=0.4")
    chain += ["equalizer=f=3000:t=q:w=1.2:g=2", "equalizer=f=250:t=q:w=1:g=-2",
              "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2",
              f"loudnorm=I={target_lufs}:TP=-1.5:LRA=9"]
    out = str(Path(out_dir) / "dialogue_clean.wav")
    ffmpeg("-i", src, "-vn", "-af", ",".join(chain), "-ar", str(SR), "-ac", "1", out)
    return {"output": out}


def sfx_library(out_dir):
    from .synth import SFX
    out = {}
    for k, v in SFX.items():
        out[k] = _write(Path(out_dir) / f"{k}.wav", v)
    return {"output": str(out_dir), "files": out}


def music_bed(duration, out_dir, name="music.wav"):
    from .synth import music
    return {"output": _write(Path(out_dir) / name, music(float(duration)))}


def mix(voice, out_dir, music=None, events=(), sfx_dir=None, music_level=0.22, duck=0.13, target_lufs=-14,
        sfx_levels=None):
    """Voice + ducked music + SFX events [[time, name], ...] → normalised mix."""
    tmp = Path(out_dir)
    v = _read(to_wav(voice, tmp / "_voice.wav")) if voice else np.zeros(SR)
    L = len(v) + SR // 2
    v = np.pad(v, (0, L - len(v)))
    mixd = v.copy()
    if music:
        m = _read(to_wav(music, tmp / "_music.wav"))
        m = np.pad(m, (0, max(0, L - len(m))))[:L]
        env = signal.sosfiltfilt(signal.butter(2, 4, fs=SR, output="sos"), np.abs(v))
        env = np.clip(env / (np.percentile(env, 95) + 1e-6), 0, 1)
        mixd += m * (music_level - duck * env)
    lv = {"whoosh": .45, "whoosh_s": .4, "pop": .5, "pop_hi": .45, "click": .55, "ding": .4, "stamp": .55,
          "riser": .35, "typing": .35, "success": .45}
    lv.update(sfx_levels or {})
    if events:
        if not sfx_dir:
            sfx_dir = tmp / "sfx"
            sfx_dir.mkdir(exist_ok=True)
            sfx_library(sfx_dir)
        for t, name in events:
            s = _read(str(Path(sfx_dir) / f"{name}.wav")) * lv.get(name, .4)
            i = int(max(0, float(t)) * SR)
            j = min(L, i + len(s))
            if i < L:
                mixd[i:j] += s[: j - i]
    pk = np.max(np.abs(mixd))
    if pk > 0.95:
        mixd = mixd / pk * 0.95
    raw = _write(tmp / "_mix_raw.wav", mixd)
    out = str(tmp / "mix.wav")
    ffmpeg("-i", raw, "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11", "-ar", str(SR), out)
    return {"output": out, "events": len(events)}


def spot_from_cuts(cuts, out=None, kind="whoosh_s", offset=-0.15):
    """Place a transition SFX slightly before every cut time."""
    ev = [[round(max(0, c + offset), 3), kind] for c in cuts]
    if out:
        write_json(out, ev)
    return ev


def mux(video, audio, out_dir, name="final.mp4"):
    out = str(Path(out_dir) / name)
    ffmpeg("-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", out)
    return {"output": out}
