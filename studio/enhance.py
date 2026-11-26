"""Video enhancement: denoise, stabilise, upscale, deinterlace, frame interpolation, sharpen."""
from pathlib import Path

from .core import ffmpeg, probe

ENC = ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p"]


def denoise(src, out_dir, strength="medium", name="denoised.mp4"):
    f = {"light": "hqdn3d=2:1.5:3:3", "medium": "hqdn3d=4:3:6:4.5", "strong": "nlmeans=s=4:p=7:r=15"}[strength]
    out = str(Path(out_dir) / name)
    ffmpeg("-i", src, "-vf", f, *ENC, "-c:a", "copy", out)
    return {"output": out}


def stabilize(src, out_dir, smoothing=20, name="stabilized.mp4"):
    trf = str(Path(out_dir) / "transforms.trf")
    ffmpeg("-i", src, "-vf", f"vidstabdetect=shakiness=6:accuracy=12:result='{trf}'", "-f", "null", "-")
    out = str(Path(out_dir) / name)
    ffmpeg("-i", src, "-vf", f"vidstabtransform=input='{trf}':smoothing={smoothing}:zoom=3,unsharp=5:5:0.6",
           *ENC, "-c:a", "copy", out)
    return {"output": out}


def upscale(src, out_dir, height=2160, name=None):
    """Lanczos upscale + adaptive sharpening (no ML weights available offline; see docs/capabilities.md)."""
    v = probe(src)["video"]
    w = int(round(v["width"] * height / v["height"] / 2) * 2)
    out = str(Path(out_dir) / (name or f"upscaled_{height}p.mp4"))
    ffmpeg("-i", src, "-vf", f"scale={w}:{height}:flags=lanczos,unsharp=7:7:0.8:5:5:0.0,cas=0.4", *ENC, "-c:a", "copy", out)
    return {"output": out, "size": f"{w}x{height}"}


def deinterlace(src, out_dir, name="progressive.mp4"):
    out = str(Path(out_dir) / name)
    ffmpeg("-i", src, "-vf", "bwdif=mode=send_frame:parity=auto", *ENC, "-c:a", "copy", out)
    return {"output": out}


def interpolate(src, out_dir, fps=60, name=None):
    out = str(Path(out_dir) / (name or f"interp_{fps}fps.mp4"))
    ffmpeg("-i", src, "-vf", f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1", *ENC, "-c:a", "copy", out)
    return {"output": out}


def restore(src, out_dir, name="restored.mp4"):
    """One-shot chain for old/low-quality footage: deinterlace → denoise → mild sharpen → 1080p."""
    v = probe(src)["video"]
    chain = ["bwdif=mode=send_frame:parity=auto"] if v.get("field_order") not in (None, "progressive", "unknown") else []
    chain += ["hqdn3d=3:2:5:4", "unsharp=5:5:0.7"]
    if v["height"] < 1080:
        chain.append("scale=-2:1080:flags=lanczos")
    out = str(Path(out_dir) / name)
    ffmpeg("-i", src, "-vf", ",".join(chain), *ENC, "-c:a", "copy", out)
    return {"output": out}
