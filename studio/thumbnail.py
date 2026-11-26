"""Thumbnails & covers: best-frame selection (sharpness × exposure × colourfulness) + designed layouts."""
import html
from pathlib import Path

import cv2
import numpy as np

from .core import ROOT, chromium_render, probe

SIZES = {"youtube": (1280, 720), "shorts": (1080, 1920), "instagram": (1080, 1350), "square": (1080, 1080)}


def best_frames(video, out_dir, n=3, samples=40):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    scored = []
    for k in range(samples):
        idx = int((k + 0.5) * total / samples)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, f = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        expo = 1 - abs(g.mean() - 128) / 128
        b, gg, r = [f[:, :, i].astype(float) for i in range(3)]
        rg, yb = r - gg, 0.5 * (r + gg) - b
        colorful = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
        scored.append((np.log1p(sharp) * expo * (1 + colorful / 60), idx, f))
    scored.sort(key=lambda x: -x[0])
    outs = []
    for i, (s, idx, f) in enumerate(scored[:n]):
        p = str(Path(out_dir) / f"frame_{i + 1}.jpg")
        cv2.imwrite(p, f)
        outs.append(p)
    return {"output": outs[0] if outs else "", "frames": outs}


def design(out_dir, title, highlight="", badge="", image=None, size="youtube", layout="split", colors=None, name=None):
    """layout: 'split' (image left, text right) or 'full' (image background + big text)."""
    W, H = SIZES[size]
    c = {"bg": "#0b1020", "primary": "#a3e635", "accent": "#22d3ee", "text": "#ffffff"}
    c.update(colors or {})
    img = f"file://{Path(image).resolve()}" if image else ""
    e = html.escape
    big = int(min(W, H) * 0.16)
    if layout == "full" and image:
        body = f"""<div style="position:absolute;inset:0;background:url('{img}') center/cover"></div>
        <div style="position:absolute;inset:0;background:linear-gradient(90deg,#000d 0%,#0009 45%,#0000 75%)"></div>
        <div style="position:absolute;right:5%;top:8%;width:62%;font-size:{big}px;font-weight:900;line-height:1.1;color:{c['text']};text-shadow:0 6px 30px #000">{e(title)}</div>"""
    else:
        body = f"""<div style="position:absolute;left:4%;top:12%;width:46%;height:76%;border-radius:28px;border:8px solid {c['accent']};
             box-shadow:0 0 60px {c['accent']}88;background:#111 {('url(' + repr(img) + ') center/cover') if img else ''}"></div>
        <div style="position:absolute;right:4%;top:8%;width:44%;font-size:{int(big*0.8)}px;font-weight:900;line-height:1.15;color:{c['text']}">{e(title)}</div>"""
    if highlight:
        body += f"""<div style="position:absolute;right:4%;bottom:9%;font-size:{int(big*0.7)}px;font-weight:900;background:{c['primary']};color:{c['bg']};
             padding:0 32px 14px;border-radius:24px;transform:rotate(-3deg);box-shadow:0 14px 40px #000a">{e(highlight)}</div>"""
    if badge:
        body += f"""<div style="position:absolute;left:4%;top:4%;font-size:{int(big*0.35)}px;font-weight:900;background:{c['accent']};color:{c['bg']};padding:0 20px 8px;border-radius:14px">{e(badge)}</div>"""
    doc = f"""<!doctype html><html dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Cairo;font-weight:900;src:url("{(ROOT / 'assets/fonts/Cairo-Black.ttf').as_uri()}")}}
*{{margin:0;box-sizing:border-box}}body{{font-family:Cairo}}
#t{{width:{W}px;height:{H}px;position:relative;overflow:hidden;background:radial-gradient(ellipse at 85% 15%,#1e3a8a 0,transparent 60%),radial-gradient(ellipse at 5% 100%,#3f6212 0,transparent 55%),{c['bg']}}}
</style></head><body><div id="t">{body}</div></body></html>"""
    hp = Path(out_dir) / "_thumb.html"
    hp.write_text(doc, encoding="utf-8")
    out = str(Path(out_dir) / (name or f"thumb_{layout}.png"))
    chromium_render(hp, out, W, H, selector="#t")
    return {"output": out}


def ab_set(video, out_dir, title, highlight="", badge=""):
    fr = best_frames(video, out_dir, n=2)["frames"]
    a = design(out_dir, title, highlight, badge, fr[0] if fr else None, layout="split", name="thumb_A.png")["output"]
    b = design(out_dir, title, highlight, badge, fr[-1] if fr else None, layout="full", name="thumb_B.png")["output"]
    return {"output": a, "variants": [a, b]}
