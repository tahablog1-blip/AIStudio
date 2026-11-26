"""Raw-media analysis (cinematographer / QC / enhancement): technical report per file."""
import re
from pathlib import Path

from .core import FFMPEG, probe, run, write_json


def _ff_stderr(args):
    p = run([FFMPEG, "-hide_banner", "-nostats", *args, "-f", "null", "-"], check=False, capture=True)
    return p.stderr


def scenes(path, threshold=0.3):
    err = _ff_stderr(["-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo", "-an"])
    return [round(float(x), 3) for x in re.findall(r"pts_time:([\d.]+)", err)]


def video_stats(path, samples=60):
    """Average luma / saturation / noise proxy from signalstats over sampled frames."""
    d = probe(path)["duration"] or 1
    step = max(d / samples, 0.04)
    err = _ff_stderr(["-i", path, "-vf", f"fps=1/{step:.3f},signalstats,metadata=print", "-an"])
    def avg(key):
        v = [float(x) for x in re.findall(rf"lavfi\.signalstats\.{key}=([\d.]+)", err)]
        return round(sum(v) / len(v), 2) if v else None
    ymin, ymax = avg("YMIN"), avg("YMAX")
    return {"luma_avg": avg("YAVG"), "luma_min": ymin, "luma_max": ymax, "sat_avg": avg("SATAVG"),
            "u_avg": avg("UAVG"), "v_avg": avg("VAVG"), "noise_proxy": avg("YDIF")}


def audio_stats(path):
    err = _ff_stderr(["-i", path, "-vn", "-af", "ebur128=peak=true"])
    def g(pat):
        m = re.findall(pat, err)
        return float(m[-1]) if m else None
    sil = _ff_stderr(["-i", path, "-vn", "-af", "silencedetect=n=-45dB:d=1.5"])
    silences = [(float(a), float(b)) for a, b in re.findall(r"silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+)", sil)]
    return {"integrated_lufs": g(r"I:\s+(-?[\d.]+) LUFS"), "true_peak_db": g(r"Peak:\s+(-?[\d.]+) dBFS"),
            "lra": g(r"LRA:\s+([\d.]+) LU"), "long_silences": silences}


def report(path, out=None):
    """Full technical report with plain-language findings."""
    info = probe(path)
    rep = {"file": Path(path).name, "probe": info, "findings": []}
    if info["video"]:
        vs = video_stats(path)
        rep["video_stats"] = vs
        rep["scene_cuts"] = scenes(path)
        v = info["video"]
        if vs["luma_avg"] is not None:
            if vs["luma_avg"] < 60:
                rep["findings"].append("الصورة معتمة (under-exposed) → colorist: رفع التعريض")
            if vs["luma_avg"] > 190:
                rep["findings"].append("الصورة محروقة (over-exposed) → colorist: خفض التعريض")
            if vs["u_avg"] and vs["v_avg"] and (abs(vs["u_avg"] - 128) > 8 or abs(vs["v_avg"] - 128) > 8):
                rep["findings"].append("انحراف لوني في توازن الأبيض → colorist: correct")
            if (vs["luma_max"] or 0) - (vs["luma_min"] or 0) < 120:
                rep["findings"].append("تباين ضعيف → colorist: contrast")
        if v["height"] and v["height"] < 1080:
            rep["findings"].append(f"الدقة {v['width']}x{v['height']} أقل من 1080p → video-enhancement: upscale")
        if v.get("field_order") not in (None, "progressive", "unknown"):
            rep["findings"].append("فيديو interlaced → video-enhancement: deinterlace")
        if v["fps"] and v["fps"] < 23:
            rep["findings"].append(f"معدل فريمات منخفض {v['fps']} → video-enhancement: interpolate")
    if info["audio"]:
        a = audio_stats(path)
        rep["audio_stats"] = a
        if a["integrated_lufs"] is not None and (a["integrated_lufs"] < -20 or a["integrated_lufs"] > -10):
            rep["findings"].append(f"مستوى الصوت {a['integrated_lufs']} LUFS بعيد عن ‎-14 → sound-engineer: loudnorm")
        if a["long_silences"]:
            rep["findings"].append(f"{len(a['long_silences'])} فترة صمت طويلة → editor: cut_silence")
    else:
        rep["findings"].append("لا يوجد مسار صوت")
    if not rep["findings"]:
        rep["findings"].append("المادة سليمة تقنياً")
    if out:
        write_json(out, rep)
    return {"output": out or "", "report": rep}


def analyze_folder(folder, out):
    reps = {}
    for f in sorted(Path(folder).iterdir()):
        if f.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".wav", ".mp3", ".m4a"):
            reps[f.name] = report(str(f))["report"]
    write_json(out, reps)
    return {"output": out, "files": len(reps)}


def content_type(path, samples=8):
    """'screen_graphics' (UI/recordings/motion graphics: large flat regions) vs 'camera' (textured footage).
    Colour & exposure decisions differ: graphics are intentionally bright/dark and must not be 'normalised'."""
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    flats = []
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((k + 0.5) * n / samples))
        ok, f = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(cv2.resize(f, (480, 270)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
        flats.append(float((np.hypot(gx, gy) < 6).mean()))
    flat = float(np.mean(flats)) if flats else 0.0
    return {"type": "screen_graphics" if flat > 0.55 else "camera", "flat_fraction": round(flat, 3)}
