"""Screenwriting tools: structure templates, timing estimates, TTS-safe VO text, shot-list scaffolds."""
import re
from pathlib import Path

from .core import write_json
from .voice import clean_for_tts, sentences

WPM = {"ar": 140, "en": 155}

STRUCTURES = {
    "ad_30": [("hook", 3), ("problem", 6), ("solution", 10), ("proof", 6), ("cta", 5)],
    "ad_15": [("hook", 3), ("solution", 7), ("cta", 5)],
    "explainer": [("hook", 8), ("problem", 20), ("how_it_works", 60), ("example", 30), ("cta", 12)],
    "documentary": [("cold_open", 30), ("context", 90), ("conflict", 120), ("resolution", 90), ("closing", 30)],
    "tutorial": [("result_preview", 10), ("steps", 180), ("recap", 20), ("cta", 10)],
    "short": [("hook", 2), ("payoff", 20), ("loop_or_cta", 3)],
}


def estimate(text, lang="ar"):
    words = len(re.findall(r"\S+", text))
    return {"words": words, "seconds": round(words / WPM[lang] * 60, 1)}


def check(text, lang="ar", max_seconds=None):
    issues = []
    sents = sentences(text)
    long = [s for s in sents if len(s.split()) > 28]
    if long:
        issues.append(f"{len(long)} جملة طويلة جداً (أكثر من 28 كلمة) — صعبة في التعليق")
    if re.search(r"[،,;؛:!]", text):
        issues.append("فيه فواصل/علامات تعجب — هتتشال في نسخة TTS")
    est = estimate(text, lang)
    if max_seconds and est["seconds"] > max_seconds * 1.1:
        issues.append(f"المدة المتوقعة {est['seconds']}ث أطول من المطلوب {max_seconds}ث")
    hook = sents[0] if sents else ""
    if hook and len(hook.split()) > 14:
        issues.append("الخطاف (أول جملة) أطول من 14 كلمة — المشاهد ممكن يمشي")
    return {"ok": not issues, "issues": issues, **est, "sentences": len(sents)}


def prepare_vo(script_path, out_dir, lang="ar"):
    text = Path(script_path).read_text(encoding="utf-8")
    text = re.sub(r"^#.*$", "", text, flags=re.M)          # drop markdown headings
    text = re.sub(r"\[[^\]]*\]", "", text)                  # drop [stage directions]
    vo = clean_for_tts(" ".join(text.split()))
    out = Path(out_dir) / "vo_text.txt"
    out.write_text(vo, encoding="utf-8")
    rep = check(vo, lang)
    write_json(Path(out_dir) / "script_check.json", rep)
    return {"output": str(out), **rep}


def scaffold(structure, out_dir, topic=""):
    """Timed outline the screenwriter fills in (keeps the writer on the target duration)."""
    lines = [f"# {topic or 'سيناريو'} — قالب {structure}", ""]
    t = 0
    for sec, d in STRUCTURES[structure]:
        lines += [f"## {sec} ({t}s → {t + d}s, ≈{int(d * WPM['ar'] / 60)} كلمة)", "", ""]
        t += d
    out = Path(out_dir) / "script_outline.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return {"output": str(out), "total_seconds": t}
