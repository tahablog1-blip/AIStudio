"""Shared helpers: running ffmpeg/ffprobe, media probing, logging, paths."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"


class StudioError(RuntimeError):
    pass


def log(msg, role=None):
    tag = f"[{role}] " if role else ""
    print(f"{time.strftime('%H:%M:%S')} {tag}{msg}", flush=True)


def run(cmd, quiet=True, check=True, capture=False):
    """Run a command list. Raises StudioError with the tail of stderr on failure."""
    cmd = [str(c) for c in cmd]
    if cmd[0] == "ffmpeg":
        cmd[0] = FFMPEG
        if quiet and "-loglevel" not in cmd:
            cmd[1:1] = ["-hide_banner", "-loglevel", "error", "-y"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise StudioError(f"command failed ({p.returncode}): {' '.join(cmd[:6])}...\n{p.stderr[-1500:]}")
    return p if capture or not check else p


def ffmpeg(*args):
    return run(["ffmpeg", *args])


def probe(path):
    """Return a compact description of a media file."""
    p = run([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", path], capture=True)
    d = json.loads(p.stdout)
    out = {"path": str(path), "duration": float(d["format"].get("duration", 0) or 0),
           "size_bytes": int(d["format"].get("size", 0) or 0), "format": d["format"].get("format_name"),
           "video": None, "audio": None}
    for s in d.get("streams", []):
        if s["codec_type"] == "video" and out["video"] is None and s.get("disposition", {}).get("attached_pic", 0) == 0:
            num, den = (s.get("avg_frame_rate") or "0/1").split("/")
            fps = float(num) / float(den) if float(den or 0) else 0
            out["video"] = {"codec": s.get("codec_name"), "width": s.get("width"), "height": s.get("height"),
                            "fps": round(fps, 3), "pix_fmt": s.get("pix_fmt"),
                            "bitrate": int(s.get("bit_rate", 0) or 0), "field_order": s.get("field_order", "progressive")}
        elif s["codec_type"] == "audio" and out["audio"] is None:
            out["audio"] = {"codec": s.get("codec_name"), "sample_rate": int(s.get("sample_rate", 0) or 0),
                            "channels": s.get("channels"), "bitrate": int(s.get("bit_rate", 0) or 0)}
    return out


def duration(path):
    return probe(path)["duration"]


def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)
    return Path(p)


def write_json(path, data):
    path = Path(path)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def chromium_render(html_path, out_png, width=1920, height=1080, selector=None, transparent=False):
    """Render an HTML file to PNG with the pre-installed Playwright Chromium (via node)."""
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch({{ args: ['--allow-file-access-from-files'] }});
  const p = await b.newPage({{ viewport: {{ width: {width}, height: {height} }} }});
  await p.goto('file://{Path(html_path).resolve()}');
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  const target = {json.dumps(selector)} ? p.locator({json.dumps(selector)}) : p;
  await target.screenshot({{ path: {json.dumps(str(out_png))}, omitBackground: {str(transparent).lower()} }});
  await b.close();
}})();"""
    run(["node", "-e", js])
    return out_png
