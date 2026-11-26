"""Delivery presets (encoding-engineer). Each preset is also the spec QC checks against."""
from pathlib import Path

from .core import ffmpeg, probe

PRESETS = {
    "youtube_1080p": dict(w=1920, h=1080, fps=30, vcodec="libx264", crf=18, preset="slow", profile="high",
                          abr="192k", lufs=-14, max_dur=None, container="mp4"),
    "youtube_4k":    dict(w=3840, h=2160, fps=30, vcodec="libx264", crf=18, preset="medium", profile="high",
                          abr="192k", lufs=-14, max_dur=None, container="mp4"),
    "youtube_shorts": dict(w=1080, h=1920, fps=30, vcodec="libx264", crf=19, preset="slow", profile="high",
                           abr="160k", lufs=-14, max_dur=180, container="mp4"),
    "tiktok":        dict(w=1080, h=1920, fps=30, vcodec="libx264", crf=20, preset="slow", profile="high",
                          abr="160k", lufs=-14, max_dur=600, container="mp4"),
    "instagram_reel": dict(w=1080, h=1920, fps=30, vcodec="libx264", crf=20, preset="slow", profile="high",
                           abr="160k", lufs=-14, max_dur=180, container="mp4"),
    "instagram_feed": dict(w=1080, h=1350, fps=30, vcodec="libx264", crf=20, preset="slow", profile="high",
                           abr="160k", lufs=-14, max_dur=60, container="mp4"),
    "facebook_square": dict(w=1080, h=1080, fps=30, vcodec="libx264", crf=20, preset="slow", profile="high",
                            abr="160k", lufs=-14, max_dur=None, container="mp4"),
    "x_twitter":     dict(w=1280, h=720, fps=30, vcodec="libx264", crf=21, preset="slow", profile="high",
                          abr="128k", lufs=-14, max_dur=140, container="mp4"),
    "broadcast_master": dict(w=1920, h=1080, fps=25, vcodec="prores_ks", crf=None, preset=None, profile="3",
                             abr=None, lufs=-23, max_dur=None, container="mov"),
    "web_small":     dict(w=1280, h=720, fps=30, vcodec="libx264", crf=24, preset="slow", profile="main",
                          abr="128k", lufs=-16, max_dur=None, container="mp4"),
}


def export(src, out_dir, preset="youtube_1080p", fit="pad", name=None):
    """fit: 'pad' (letter/pillar-box, keeps everything) or 'crop' (fill frame)."""
    p = PRESETS[preset]
    info = probe(src)
    out = Path(out_dir) / f"{name or Path(src).stem}_{preset}.{p['container']}"
    w, h = p["w"], p["h"]
    if fit == "crop":
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    else:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
    vf += f",fps={p['fps']},setsar=1,format={'yuv422p10le' if p['vcodec']=='prores_ks' else 'yuv420p'}"
    args = ["-i", src]
    if p["max_dur"] and info["duration"] > p["max_dur"]:
        args = ["-t", str(p["max_dur"])] + args
    args += ["-vf", vf, "-c:v", p["vcodec"]]
    if p["vcodec"] == "prores_ks":
        args += ["-profile:v", p["profile"]]
    else:
        args += ["-crf", str(p["crf"]), "-preset", p["preset"], "-profile:v", p["profile"], "-movflags", "+faststart"]
    if info["audio"]:
        af = f"loudnorm=I={p['lufs']}:TP=-1.5:LRA=11,aresample=48000"
        args += ["-af", af, "-ar", "48000"]
        args += ["-c:a", "pcm_s24le"] if p["vcodec"] == "prores_ks" else ["-c:a", "aac", "-b:a", p["abr"]]
    else:
        args += ["-an"]
    ffmpeg(*args, str(out))
    return {"output": str(out), "preset": preset}


def export_many(src, out_dir, presets=("youtube_1080p",), fit="pad", name=None):
    outs = {pr: export(src, out_dir, pr, fit, name)["output"] for pr in presets}
    return {"output": outs[presets[0]], "files": outs}
