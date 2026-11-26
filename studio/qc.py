"""Automated quality control. Produces a pass/fail gate + report the orchestrator enforces."""
import re
from pathlib import Path

from .analyze import _ff_stderr, audio_stats
from .core import probe, write_json
from .encode import PRESETS


def _stream_durations(path):
    import json, subprocess
    from .core import FFPROBE
    p = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", path],
                       capture_output=True, text=True)
    d = {s["codec_type"]: float(s["duration"]) for s in json.loads(p.stdout).get("streams", []) if s.get("duration")}
    return d.get("video"), d.get("audio")


def check(path, preset=None, out_dir=None, expect_audio=True, max_black=1.0, max_freeze=2.5, lufs_tol=2.0):
    info = probe(path)
    checks = []

    def add(name, ok, detail, severity="error"):
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "severity": severity})

    v, a = info["video"], info["audio"]
    add("video_stream", v is not None, v and f"{v['codec']} {v['width']}x{v['height']} @{v['fps']}")
    if expect_audio:
        add("audio_stream", a is not None, a and f"{a['codec']} {a['sample_rate']}Hz {a['channels']}ch")
    if preset:
        p = PRESETS[preset]
        add("resolution", v and (v["width"], v["height"]) == (p["w"], p["h"]), f"expected {p['w']}x{p['h']}")
        add("frame_rate", v and abs(v["fps"] - p["fps"]) < 0.05, f"expected {p['fps']}")
        add("codec", v and v["codec"] == {"libx264": "h264", "prores_ks": "prores"}.get(p["vcodec"], p["vcodec"]),
            f"expected {p['vcodec']}")
        if p["vcodec"] != "prores_ks":
            add("pix_fmt", v and v["pix_fmt"] == "yuv420p", "8-bit 4:2:0 required for platforms")
        if p["max_dur"]:
            add("duration_limit", info["duration"] <= p["max_dur"] + 0.1, f"{info['duration']:.1f}s ≤ {p['max_dur']}s")
    if v:
        err = _ff_stderr(["-i", path, "-vf", "blackdetect=d=0.3:pix_th=0.08", "-an"])
        blacks = [(float(s), float(e)) for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
        long_black = [b for b in blacks if b[1] - b[0] > max_black]
        add("black_frames", not long_black, f"{len(blacks)} black segments; long: {long_black}", "warning" if not long_black else "error")
        err = _ff_stderr(["-i", path, "-vf", f"freezedetect=n=0.001:d={max_freeze}", "-an"])
        freezes = re.findall(r"freeze_start: ([\d.]+)", err)
        add("frozen_frames", not freezes, f"frozen segments starting at {freezes}", "warning")
    if a:
        st = audio_stats(path)
        target = PRESETS[preset]["lufs"] if preset and PRESETS[preset]["lufs"] else -14
        lufs = st["integrated_lufs"]
        add("loudness", lufs is not None and abs(lufs - target) <= lufs_tol, f"{lufs} LUFS (target {target}±{lufs_tol})")
        add("true_peak", st["true_peak_db"] is not None and st["true_peak_db"] <= -0.9, f"{st['true_peak_db']} dBTP ≤ -1")
        vd, ad = _stream_durations(path)
        add("av_sync", vd is None or ad is None or abs(vd - ad) < 0.25, f"video {vd}s / audio {ad}s")
    passed = all(c["ok"] for c in checks if c["severity"] == "error")
    summary = f"{sum(c['ok'] for c in checks)}/{len(checks)} checks ok — {'PASS' if passed else 'FAIL'}"
    rep = {"file": Path(path).name, "preset": preset, "passed": passed, "summary": summary, "checks": checks,
           "duration": info["duration"]}
    out = None
    if out_dir:
        out = str(Path(out_dir) / "qc_report.json")
        write_json(out, rep)
        md = [f"# QC — {Path(path).name}", f"**{summary}**", "", "| الفحص | النتيجة | التفاصيل |", "|---|---|---|"]
        md += [f"| {c['check']} | {'✅' if c['ok'] else ('⚠️' if c['severity'] != 'error' else '❌')} | {c['detail']} |" for c in checks]
        (Path(out_dir) / "qc_report.md").write_text("\n".join(md), encoding="utf-8")
    return {"output": out or "", "qc_pass": passed, "summary": summary, "report": rep}


def check_many(files, out_dir, presets=None):
    files = files if isinstance(files, (list, tuple)) else [files]
    presets = presets or [None] * len(files)
    reps = [check(f, p)["report"] for f, p in zip(files, presets)]
    ok = all(r["passed"] for r in reps)
    out = str(Path(out_dir) / "qc_report.json")
    write_json(out, {"passed": ok, "files": reps})
    md = ["# تقرير مراقبة الجودة", ""]
    for r in reps:
        md += [f"## {r['file']} ({r['preset']}) — {'✅ PASS' if r['passed'] else '❌ FAIL'}", "| الفحص | النتيجة | التفاصيل |", "|---|---|---|"]
        md += [f"| {c['check']} | {'✅' if c['ok'] else ('⚠️' if c['severity'] != 'error' else '❌')} | {c['detail']} |" for c in r["checks"]]
        md.append("")
    (Path(out_dir) / "qc_report.md").write_text("\n".join(md), encoding="utf-8")
    return {"output": out, "qc_pass": ok, "summary": f"{sum(r['passed'] for r in reps)}/{len(reps)} files pass"}
