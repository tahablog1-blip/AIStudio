"""Voice-over: offline Piper TTS (Arabic) + forced alignment of any VO (TTS or human) to its script."""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from .core import ASSETS, StudioError, ensure_dir, ffmpeg, write_json

VOICES = {
    "ar": ("ar/ar_JO/kareem/medium", "ar_JO-kareem-medium"),
    "en": ("en/en_US/ryan/medium", "en_US-ryan-medium"),
}


def _model(lang="ar"):
    sub, name = VOICES[lang]
    d = ensure_dir(ASSETS / "voices")
    onnx = d / f"{name}.onnx"
    for f in (f"{name}.onnx", f"{name}.onnx.json"):
        if not (d / f).exists():
            urllib.request.urlretrieve(f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{sub}/{f}", d / f)
    return onnx


def clean_for_tts(text):
    """TTS-safe text: no commas/colons/exclamations, latin brand words spelled for Arabic voices."""
    t = re.sub(r"[،,;؛:!]+", ".", text)
    t = re.sub(r"\s*\.\s*\.+", ".", t)
    return re.sub(r"\s+", " ", t).strip()


def sentences(text):
    return [s.strip() for s in re.findall(r"[^.؟?]+[.؟?]?", text) if s.strip()]


def tts(text, out_dir, lang="ar", speed=0.9, replacements=None):
    """Synthesize sentence by sentence (exact per-sentence timings come for free)."""
    model = _model(lang)
    out_dir = Path(out_dir)
    parts, timeline, t = [], [], 0.0
    reps = {"AI": "إيه آي", "IDM": "آي دي إم"} if lang == "ar" else {}
    reps.update(replacements or {})
    for i, s in enumerate(sentences(clean_for_tts(text))):
        say = s
        for k, v in reps.items():
            say = say.replace(k, v)
        wav = out_dir / f"_s{i:03d}.wav"
        p = subprocess.run([sys.executable, "-m", "piper", "-m", str(model), "--length-scale", str(speed),
                            "-f", str(wav)], input=say.encode(), capture_output=True)
        if p.returncode != 0:
            raise StudioError(p.stderr.decode()[-500:])
        from .core import duration
        d = duration(str(wav)) + 0.25
        timeline.append({"i": i, "text": s, "start": round(t, 3), "dur": round(d, 3)})
        parts.append(wav)
        t += d
    lst = out_dir / "_list.txt"
    lst.write_text("".join(f"file '{p.name}'\nfile '_gap.wav'\n" for p in parts))
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", "0.25", str(out_dir / "_gap.wav"))
    out = str(out_dir / "vo.wav")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "44100", out)
    write_json(out_dir / "sentences.json", timeline)
    return {"output": out, "sentences": str(out_dir / "sentences.json"), "engine": f"piper:{model.stem}"}


def align(audio, script_text, out_dir, lang="ar", model_size="small"):
    """Word-level timings for a VO against its script (works for ElevenLabs or human recordings)."""
    import difflib
    import wave
    import numpy as np
    from faster_whisper import WhisperModel
    out_dir = Path(out_dir)
    w16 = out_dir / "_a16.wav"
    ffmpeg("-i", audio, "-ar", "16000", "-ac", "1", str(w16))
    w = wave.open(str(w16))
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    total = len(a) / 16000
    segs, _ = WhisperModel(model_size, device="cpu", compute_type="int8").transcribe(a, language=lang, word_timestamps=True)
    words = [{"w": x.word.strip(), "s": x.start, "e": x.end} for s in segs for x in s.words]

    def norm(x):
        x = re.sub(r"[ً-ْـ]", "", x)
        x = re.sub("[أإآ]", "ا", x).replace("ة", "ه").replace("ى", "ي")
        return re.sub(r"[^\w]", "", x).lower()
    sents = sentences(script_text)
    sw, own = [], []
    for i, s in enumerate(sents):
        for wd in s.split():
            sw.append(wd)
            own.append(i)
    m = {}
    for a_, b_, n in difflib.SequenceMatcher(None, [norm(x) for x in sw], [norm(x["w"]) for x in words], autojunk=False).get_matching_blocks():
        for k in range(n):
            m[a_ + k] = b_ + k
    times = [words[m[i]]["s"] if i in m else None for i in range(len(sw))]
    # interpolate unmatched words
    known = [(i, t) for i, t in enumerate(times) if t is not None]
    for i in range(len(times)):
        if times[i] is None:
            lo = max([k for k in known if k[0] < i], default=(-1, 0.0))
            hi = min([k for k in known if k[0] > i], default=(len(times), total))
            times[i] = lo[1] + (hi[1] - lo[1]) * (i - lo[0]) / (hi[0] - lo[0])
    for i in range(1, len(times)):
        times[i] = max(times[i], times[i - 1] + 0.05)
    timeline = []
    for si, s in enumerate(sents):
        idx = [i for i in range(len(sw)) if own[i] == si]
        st = 0.0 if si == 0 else times[idx[0]] - 0.08
        timeline.append({"i": si, "text": s, "start": round(st, 3), "words": [[sw[i], round(times[i], 3)] for i in idx]})
    for si in range(len(timeline)):
        nxt = timeline[si + 1]["start"] if si + 1 < len(timeline) else total
        timeline[si]["dur"] = round(nxt - timeline[si]["start"], 3)
    out = out_dir / "timeline.json"
    write_json(out, timeline)
    return {"output": str(out), "matched": f"{len(m)}/{len(sw)}", "duration": round(total, 2)}
