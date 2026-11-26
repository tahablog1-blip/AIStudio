"""Colour department: measured primary correction, shot matching, LUT design (.cube) and grading."""
from pathlib import Path

import numpy as np

from .analyze import video_stats
from .core import ASSETS, ffmpeg, write_json


def _correction_filter(st, target_luma):
    y = st["luma_avg"] or target_luma
    gamma = float(np.clip(np.log(max(y, 1) / 255) / np.log(target_luma / 255), 0.6, 2.2))
    du = (st["u_avg"] or 128) - 128
    dv = (st["v_avg"] or 128) - 128
    lo, hi = (st["luma_min"] or 16), (st["luma_max"] or 235)
    contrast = float(np.clip(219 / max(hi - lo, 60), 0.95, 1.3))
    return (f"lutyuv=u='clip(val-({du:.2f}),16,240)':v='clip(val-({dv:.2f}),16,240)',"
            f"eq=gamma={gamma:.3f}:contrast={contrast:.3f},format=yuv420p")


def correct(src, out_dir, target_luma=118, tolerance=8, max_passes=3, name="corrected.mp4"):
    """Measure → correct → re-measure (like checking scopes): neutralise the U/V cast exactly,
    move average luma to target with gamma, normalise contrast. Repeats until within tolerance."""
    first = video_stats(src)
    from .analyze import content_type
    kind = content_type(src)
    if kind["type"] == "screen_graphics":
        # UI / graphics: brightness is intentional — only neutralise a real colour cast, never re-expose
        du, dv = (first["u_avg"] or 128) - 128, (first["v_avg"] or 128) - 128
        out = str(Path(out_dir) / name)
        vf = (f"lutyuv=u='clip(val-({du:.2f}),16,240)':v='clip(val-({dv:.2f}),16,240)'" if max(abs(du), abs(dv)) > 6 else "null")
        ffmpeg("-i", src, "-vf", vf + ",format=yuv420p", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-c:a", "copy", out)
        after = video_stats(out)
        write_json(Path(out_dir) / "color_report.json", {"content": kind, "before": first, "after": after, "filter": vf, "passes": 0})
        return {"output": out, "before_luma": first["luma_avg"], "after_luma": after["luma_avg"], "content": kind["type"], "passes": 0}
    chain, st, cur = [], first, src
    out = str(Path(out_dir) / name)
    for i in range(max_passes):
        chain.append(_correction_filter(st, target_luma))
        tmp = str(Path(out_dir) / f"_pass{i}.mp4")
        ffmpeg("-i", src, "-vf", ",".join(chain), "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-c:a", "copy", tmp)
        st = video_stats(tmp)
        cur = tmp
        if abs((st["luma_avg"] or target_luma) - target_luma) <= tolerance and abs(st["u_avg"] - 128) < 3 and abs(st["v_avg"] - 128) < 3:
            break
    Path(cur).replace(out)
    rep = {"before": first, "after": st, "filter": ",".join(chain), "passes": len(chain)}
    write_json(Path(out_dir) / "color_report.json", rep)
    return {"output": out, "before_luma": first["luma_avg"], "after_luma": st["luma_avg"], "passes": len(chain)}


def match(src, reference, out_dir, name="matched.mp4"):
    """Shot matching: align luma mean/contrast and chroma means of src to a reference shot."""
    a, b = video_stats(src), video_stats(reference)
    gain = (b["luma_max"] - b["luma_min"]) / max(a["luma_max"] - a["luma_min"], 1)
    off = (b["luma_avg"] - a["luma_avg"] * gain) / 255
    du, dv = (b["u_avg"] - a["u_avg"]) / 255, (b["v_avg"] - a["v_avg"]) / 255
    vf = (f"lutyuv=y='clip(val*{gain:.3f}+{off*255:.2f},16,235)':u='clip(val+{du*255:.2f},16,240)':v='clip(val+{dv*255:.2f},16,240)'")
    out = str(Path(out_dir) / name)
    ffmpeg("-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "17", "-c:a", "copy", out)
    return {"output": out, "gain": round(gain, 3)}


LOOKS = {
    # name: function(rgb array Nx3 in 0..1) -> rgb
    "teal_orange": lambda c: _split_tone(_contrast(c, 1.12), shadows=(0.0, 0.06, 0.10), highlights=(0.10, 0.04, -0.06), sat=1.1),
    "film": lambda c: _sat(_fade(_contrast(c, 1.08), lift=0.05, gain=0.97), 0.88),
    "noir": lambda c: _contrast(np.repeat(c @ np.array([[0.30], [0.59], [0.11]]), 3, axis=1), 1.3),
    "warm": lambda c: _sat(np.clip(c * np.array([1.06, 1.0, 0.9]), 0, 1), 1.05),
    "cool": lambda c: _sat(np.clip(c * np.array([0.92, 1.0, 1.08]), 0, 1), 0.95),
    "vivid": lambda c: _sat(_contrast(c, 1.1), 1.3),
    "bleach_bypass": lambda c: _sat(_contrast(c, 1.25), 0.55),
}


def _contrast(c, k, pivot=0.45):
    return np.clip((c - pivot) * k + pivot, 0, 1)


def _sat(c, k):
    y = (c @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
    return np.clip(y + (c - y) * k, 0, 1)


def _fade(c, lift=0.04, gain=1.0):
    return np.clip(lift + c * (gain - lift), 0, 1)


def _split_tone(c, shadows, highlights, sat=1.0):
    y = (c @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
    w = np.clip((y - 0.2) / 0.6, 0, 1)
    c = c + (1 - w) * np.array(shadows) + w * np.array(highlights)
    return _sat(np.clip(c, 0, 1), sat)


def make_lut(look, out_dir, size=33):
    g = np.linspace(0, 1, size)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")  # .cube order: R fastest
    rgb = np.stack([r.ravel(), gg.ravel(), b.ravel()], 1)
    res = LOOKS[look](rgb)
    out = Path(out_dir) / f"{look}.cube"
    lines = [f'TITLE "AIStudio {look}"', f"LUT_3D_SIZE {size}", "DOMAIN_MIN 0 0 0", "DOMAIN_MAX 1 1 1"]
    lines += [f"{x:.6f} {y:.6f} {z:.6f}" for x, y, z in res]
    out.write_text("\n".join(lines) + "\n")
    return {"output": str(out)}


def grade(src, out_dir, look="teal_orange", intensity=1.0, name=None, graphics_intensity=0.25):
    """Creative look. Screen recordings / graphics get a much lighter touch so UI colours stay true."""
    from .analyze import content_type
    if content_type(src)["type"] == "screen_graphics":
        intensity = min(intensity, graphics_intensity)
    lut = make_lut(look, out_dir)["output"]
    out = str(Path(out_dir) / (name or f"graded_{look}.mp4"))
    if intensity >= 0.999:
        vf = f"lut3d='{lut}'"
        ffmpeg("-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "17", "-c:a", "copy", out)
    else:
        ffmpeg("-i", src, "-filter_complex", f"[0:v]split[a][b];[b]lut3d='{lut}'[g];[a][g]blend=all_mode=normal:all_opacity={intensity}",
               "-c:v", "libx264", "-crf", "17", "-c:a", "copy", out)
    return {"output": out, "lut": lut}


def build_library():
    d = ASSETS / "luts"
    d.mkdir(exist_ok=True)
    return {k: make_lut(k, d)["output"] for k in LOOKS}
