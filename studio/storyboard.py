"""Pre-production: shot lists → storyboard sheets and timed animatics; style guide files."""
import html
from pathlib import Path

from .core import ROOT, chromium_render, ffmpeg, read_json, write_json

SHOT_SIZES = {"ECU": "لقطة قريبة جداً", "CU": "لقطة قريبة", "MS": "لقطة متوسطة", "WS": "لقطة واسعة", "EWS": "لقطة واسعة جداً",
              "OTS": "من فوق الكتف", "POV": "وجهة نظر", "INSERT": "لقطة إدراجية", "SCREEN": "تسجيل شاشة", "GFX": "جرافيك"}

ICONS = {"ECU": "👁", "CU": "🙂", "MS": "🧍", "WS": "🏙", "EWS": "🏔", "OTS": "👥", "POV": "🎥", "INSERT": "🔍", "SCREEN": "🖥", "GFX": "✨"}


def style_guide(out_dir, name, colors=None, font="Cairo", tone="", music="", pacing="medium", dir="rtl"):
    g = {"name": name, "colors": colors or {"bg": "#0b1020", "primary": "#a3e635", "accent": "#22d3ee", "text": "#ffffff"},
         "font": font, "tone": tone, "music": music, "pacing": pacing, "dir": dir}
    out = str(Path(out_dir) / "style.json")
    write_json(out, g)
    return {"output": out}


def validate_shotlist(shots):
    problems = []
    for i, s in enumerate(shots, 1):
        for k in ("size", "action", "dur"):
            if k not in s:
                problems.append(f"shot {i}: missing {k}")
        if s.get("size") and s["size"] not in SHOT_SIZES:
            problems.append(f"shot {i}: unknown size {s['size']}")
    return problems


def sheet(shotlist_json, out_dir, cols=3, title="Storyboard"):
    data = read_json(shotlist_json)
    shots = data["shots"] if isinstance(data, dict) else data
    probs = validate_shotlist(shots)
    if probs:
        raise ValueError("; ".join(probs))
    e = html.escape
    t = 0.0
    cards = []
    for i, s in enumerate(shots, 1):
        cards.append(f"""<div class="p"><div class="f"><span class="i">{ICONS.get(s['size'],'🎬')}</span>
          <span class="tag">{e(s['size'])} · {e(SHOT_SIZES.get(s['size'],''))}</span><span class="cam">{e(s.get('camera',''))}</span>
          {f'<span class="ost">{e(s["on_screen"])}</span>' if s.get('on_screen') else ''}</div>
          <div class="meta"><b>#{i}</b> · {t:.1f}s → {t + float(s['dur']):.1f}s</div>
          <div class="a">{e(s['action'])}</div>{f'<div class="vo">🎙 {e(s["vo"])}</div>' if s.get('vo') else ''}</div>""")
        t += float(s["dur"])
    rows = (len(shots) + cols - 1) // cols
    W, H = 1800, 140 + rows * 560
    doc = f"""<!doctype html><html dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Cairo;font-weight:700;src:url("{(ROOT/'assets/fonts/Cairo-Bold.ttf').as_uri()}")}}
*{{margin:0;box-sizing:border-box}}body{{font-family:Cairo;background:#f4f6fb}}
#s{{width:{W}px;padding:36px;}} h1{{font-size:44px;margin-bottom:20px;color:#111827}}
.g{{display:grid;grid-template-columns:repeat({cols},1fr);gap:26px}}
.p{{background:#fff;border:2px solid #e5e7eb;border-radius:18px;overflow:hidden}}
.f{{aspect-ratio:16/9;background:#1f2937;position:relative;display:grid;place-items:center;color:#fff}}
.i{{font-size:110px}} .tag{{position:absolute;top:12px;right:12px;background:#a3e635;color:#0b1020;font-weight:700;padding:2px 12px;border-radius:8px;font-size:20px}}
.cam{{position:absolute;bottom:10px;left:12px;color:#93c5fd;font-size:20px;direction:ltr}}
.ost{{position:absolute;bottom:10px;right:12px;background:#000a;padding:2px 10px;border-radius:6px;font-size:20px}}
.meta{{padding:10px 16px 0;color:#6b7280;font-size:20px}} .a{{padding:4px 16px;font-size:24px;font-weight:700;color:#111827}}
.vo{{padding:0 16px 14px;font-size:20px;color:#2563eb}}
</style></head><body><div id="s"><h1>{e(title)} — {len(shots)} لقطة · {t:.1f} ثانية</h1><div class="g">{''.join(cards)}</div></div></body></html>"""
    hp = Path(out_dir) / "_storyboard.html"
    hp.write_text(doc, encoding="utf-8")
    out = str(Path(out_dir) / "storyboard.png")
    chromium_render(hp, out, W, H, selector="#s")
    return {"output": out, "shots": len(shots), "duration": round(t, 2)}


def animatic(shotlist_json, out_dir, width=1280, height=720):
    """Timed slideshow of the storyboard panels (one panel per shot for its duration)."""
    from .motion import render
    data = read_json(shotlist_json)
    shots = data["shots"] if isinstance(data, dict) else data
    scenes, t = [], 0.0
    for i, s in enumerate(shots, 1):
        d = float(s["dur"])
        scenes.append({"start": t, "end": t + d, "template": "title", "transition": "fade",
                       "params": {"kicker": f"#{i} · {s['size']} · {SHOT_SIZES.get(s['size'],'')}", "title": s["action"],
                                  "subtitle": s.get("vo", "")}})
        t += d
    return render({"width": width, "height": height, "duration": t, "scenes": scenes}, out_dir, "animatic.mp4")


def write_shotlist(shots, out_dir, notes=""):
    probs = validate_shotlist(shots)
    if probs:
        raise ValueError("; ".join(probs))
    out = str(Path(out_dir) / "shotlist.json")
    write_json(out, {"shots": shots, "notes": notes, "total": round(sum(float(s["dur"]) for s in shots), 2)})
    return {"output": out, "shots": len(shots)}
