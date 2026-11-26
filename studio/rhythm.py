"""Rhythm editing: onset/beat detection and beat-synced cut lists."""
from pathlib import Path

import numpy as np
from scipy import signal

from .audio import SR, _read, to_wav
from .core import write_json


def beats(audio, out_dir, min_bpm=70, max_bpm=170):
    """Onset envelope → tempo by autocorrelation → beat grid aligned to strongest onsets."""
    x = _read(to_wav(audio, Path(out_dir) / "_beats.wav"))
    hop = 512
    frames = np.lib.stride_tricks.sliding_window_view(x, 2048)[::hop]
    spec = np.abs(np.fft.rfft(frames * np.hanning(2048), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fr = SR / hop
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    lo, hi = int(fr * 60 / max_bpm), int(fr * 60 / min_bpm)
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60 * fr / lag
    # phase: choose offset maximising onset energy on the grid
    best = max(range(lag), key=lambda o: flux[o::lag].sum())
    grid = [round((best + k * lag) / fr, 3) for k in range(int((len(flux) - best) / lag) + 1)]
    peaks, _ = signal.find_peaks(flux, height=1.0, distance=int(fr * 0.1))
    onsets = [round(p / fr, 3) for p in peaks]
    out = str(Path(out_dir) / "beats.json")
    write_json(out, {"bpm": round(bpm, 1), "beats": grid, "onsets": onsets})
    return {"output": out, "bpm": round(bpm, 1), "beats": len(grid)}


def beat_cut_timeline(beats_json, sources, out_dir, every=2, width=1920, height=1080, fps=30, total=None,
                      transition=None):
    """Build a timeline that cuts to the next source on every Nth beat (music videos, sports, ads)."""
    from .core import probe, read_json
    b = read_json(beats_json)["beats"][::every]
    if total:
        b = [x for x in b if x <= total]
    clips, pos = [], {s: 0.0 for s in sources}
    for i in range(len(b) - 1):
        src = sources[i % len(sources)]
        d = b[i + 1] - b[i]
        dur = probe(src)["duration"]
        a = pos[src] if pos[src] + d <= dur else 0.0
        c = {"src": src, "in": round(a, 3), "out": round(a + d, 3), "fit": "crop"}
        if transition and i:
            c["transition"] = {"type": transition, "dur": min(0.2, d / 3)}
        clips.append(c)
        pos[src] = a + d
    tl = {"width": width, "height": height, "fps": fps, "clips": clips, "keep_clip_audio": False}
    out = str(Path(out_dir) / "beat_timeline.json")
    write_json(out, tl)
    return {"output": out, "cuts": len(clips), "start_offset": b[0] if b else 0}
