"""VFX & compositing: keying, layered comps, glow, grain, vignette, light leaks, glitch, letterbox."""
from pathlib import Path

from .core import ffmpeg, probe

ENC = ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p"]


def _out(out_dir, name):
    return str(Path(out_dir) / name)


def key(fg, bg, out_dir, color="0x00FF00", similarity=0.32, blend=0.08, despill=True, name="comp.mp4"):
    """Chroma key fg over bg (video or image), with spill suppression and edge blur."""
    W, H = probe(fg)["video"]["width"], probe(fg)["video"]["height"]
    bg_is_img = Path(bg).suffix.lower() in (".png", ".jpg", ".jpeg")
    inputs = ["-i", fg] + (["-loop", "1", "-i", bg] if bg_is_img else ["-stream_loop", "-1", "-i", bg])
    ds = ",despill=type=green" if despill and color.lower() in ("0x00ff00", "green") else ""
    flt = (f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[bg];"
           f"[0:v]chromakey={color}:{similarity}:{blend}{ds}[fgk];[bg][fgk]overlay=shortest=1,format=yuv420p[v]")
    out = _out(out_dir, name)
    a = ["-map", "0:a?"]
    ffmpeg(*inputs, "-filter_complex", flt, "-map", "[v]", *a, *ENC, "-c:a", "copy", out)
    return {"output": out}


def composite(base, layer, out_dir, x="(W-w)/2", y="(H-h)/2", start=0, end=None, opacity=1.0, mode="normal", scale=1.0,
              name="composited.mp4"):
    end = end or probe(base)["duration"]
    is_img = Path(layer).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    inputs = ["-i", base] + (["-loop", "1", "-i", layer] if is_img else ["-i", layer])
    if mode == "normal":
        flt = (f"[1:v]format=rgba,scale=iw*{scale}:ih*{scale},colorchannelmixer=aa={opacity}[l];"
               f"[0:v][l]overlay=x={x}:y={y}:enable='between(t,{start},{end})':shortest=0:eof_action=pass,format=yuv420p[v]")
    else:
        flt = (f"[1:v]scale={probe(base)['video']['width']}:{probe(base)['video']['height']}[l];"
               f"[0:v][l]blend=all_mode={mode}:all_opacity={opacity}:enable='between(t,{start},{end})',format=yuv420p[v]")
    out = _out(out_dir, name)
    ffmpeg(*inputs, "-filter_complex", flt, "-map", "[v]", "-map", "0:a?", "-t", str(probe(base)["duration"]), *ENC, "-c:a", "copy", out)
    return {"output": out}


EFFECTS = {
    "glow": "split[a][b];[b]gblur=sigma=18,eq=brightness=0.05[g];[a][g]blend=all_mode=screen:all_opacity=0.55",
    "grain": "noise=alls=14:allf=t+u",
    "vignette": "vignette=PI/4.5",
    "glitch": "split[a][b];[b]rgbashift=rh=14:bh=-14:edge=wrap,noise=alls=30:allf=t[g];[a][g]blend=all_mode=lighten:all_opacity=1:enable='lt(mod(t\\,1.3)\\,0.14)'",
    "dreamy": "split[a][b];[b]gblur=sigma=10[g];[a][g]blend=all_mode=softlight:all_opacity=0.7",
    "sharpen": "unsharp=5:5:1.0",
    "old_film": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,noise=alls=22:allf=t,vignette=PI/4",
    "light_leak": "split[a][b];[b]geq=r='255*exp(-((X-W*(0.2+0.6*sin(T*0.6)))^2)/(2*(W*0.18)^2))':g='140*exp(-((X-W*(0.2+0.6*sin(T*0.6)))^2)/(2*(W*0.2)^2))':b='40',format=rgb24[l];[a]format=rgb24[a2];[a2][l]blend=all_mode=screen:all_opacity=0.45",
}


def effect(src, out_dir, fx="glow", name=None):
    chain = EFFECTS[fx]
    out = _out(out_dir, name or f"fx_{fx}.mp4")
    if "[" in chain:
        ffmpeg("-i", src, "-filter_complex", f"[0:v]{chain},format=yuv420p[v]", "-map", "[v]", "-map", "0:a?", *ENC, "-c:a", "copy", out)
    else:
        ffmpeg("-i", src, "-vf", chain + ",format=yuv420p", *ENC, "-c:a", "copy", out)
    return {"output": out}


def stack_effects(src, out_dir, fxs=("vignette", "grain"), name="fx_stack.mp4"):
    cur = src
    for i, f in enumerate(fxs):
        cur = effect(cur, out_dir, f, name=f"_fx{i}_{f}.mp4")["output"]
    final = _out(out_dir, name)
    Path(cur).rename(final)
    return {"output": final}


def letterbox(src, out_dir, ratio=2.39, name="letterbox.mp4"):
    out = _out(out_dir, name)
    ffmpeg("-i", src, "-vf", f"drawbox=x=0:y=0:w=iw:h=(ih-iw/{ratio})/2:color=black:t=fill,"
           f"drawbox=x=0:y=ih-(ih-iw/{ratio})/2:w=iw:h=(ih-iw/{ratio})/2:color=black:t=fill", *ENC, "-c:a", "copy", out)
    return {"output": out}
