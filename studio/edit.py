"""Editorial engine: timeline JSON → rendered video, plus editor tools and NLE project export.

Timeline schema (all times in seconds):
{
  "width": 1920, "height": 1080, "fps": 30,
  "clips": [ {"src": "a.mp4", "in": 0, "out": 4.5, "speed": 1.0, "fit": "crop|pad",
              "kenburns": 0.06, "volume": 1.0, "transition": {"type": "fade|wipeleft|slideleft|circleopen|dissolve|...", "dur": 0.5}} ],
  "overlays": [ {"src": "title.mov|logo.png", "start": 1.0, "end": 4.0, "x": "(W-w)/2", "y": "H*0.1", "scale": 1.0} ],
  "audio":    [ {"src": "music.wav", "start": 0, "volume": 0.3} ],
  "keep_clip_audio": true, "letterbox": 2.39, "lut": "look.cube", "subtitles": "captions.ass"
}
"""
import re
from pathlib import Path

from .core import ASSETS, StudioError, ffmpeg, probe, read_json, write_json

XFADES = {"fade", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown", "slideleft", "slideright", "slideup",
          "slidedown", "circleopen", "circleclose", "radial", "smoothleft", "smoothright", "zoomin", "fadeblack",
          "fadewhite", "pixelize", "hblur", "distance", "squeezeh", "squeezev"}


def _norm_clip(c, i, W, H, fps, tmp):
    """Render one clip to a uniform intermediate (same size/fps/format, stereo 48k audio)."""
    src = c["src"]
    info = probe(src)
    a, b = float(c.get("in", 0)), c.get("out")
    is_img = Path(src).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    dur = float(c.get("dur", 4)) if is_img else (float(b) if b is not None else info["duration"]) - a
    speed = float(c.get("speed", 1.0))
    fit = c.get("fit", "crop")
    vf = []
    if fit == "crop":
        vf.append(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
    else:
        vf.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
    kb = c.get("kenburns")
    if is_img:
        z = float(kb or 0.08)
        n = int(dur / speed * fps)
        vf = [f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2}",
              f"zoompan=z='1+{z}*on/{max(n,1)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={fps}"]
    elif kb:
        # video Ken Burns = slow camera pan across a slightly enlarged frame (cheap, no per-frame resample)
        z = float(kb)
        W2, H2 = int(W * (1 + z)) // 2 * 2, int(H * (1 + z)) // 2 * 2
        span = max(dur / speed, 0.1)
        xe = f"(iw-ow)*t/{span:.3f}" if i % 2 == 0 else f"(iw-ow)*(1-t/{span:.3f})"
        vf = [f"scale={W2}:{H2}:force_original_aspect_ratio=increase,crop={W2}:{H2}",
              f"crop={W}:{H}:x='{xe}':y='(ih-oh)/2'"]
    if speed != 1.0:
        vf.append(f"setpts=PTS/{speed}")
    vf += [f"fps={fps}", "setsar=1", "format=yuv420p"]
    out = tmp / f"clip_{i:03d}.mp4"
    args = []
    if is_img:
        args += ["-loop", "1", "-t", f"{dur:.3f}", "-i", src]
    else:
        args += ["-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", src]
    has_a = info["audio"] is not None and not is_img
    if has_a:
        af = []
        sp = speed
        while sp > 2.0:
            af.append("atempo=2.0"); sp /= 2
        while sp < 0.5:
            af.append("atempo=0.5"); sp /= 0.5
        if sp != 1.0:
            af.append(f"atempo={sp:.4f}")
        af.append(f"volume={c.get('volume', 1.0)}")
        af.append("aresample=48000,aformat=channel_layouts=stereo")
        args += ["-af", ",".join(af)]
    else:
        args += ["-f", "lavfi", "-t", f"{dur / speed:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    args += ["-vf", ",".join(vf), "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", str(out)]
    ffmpeg(*args)
    return out, probe(str(out))["duration"]


def render(timeline, out_dir, name="edit.mp4"):
    tl = read_json(timeline) if isinstance(timeline, str) else timeline
    W, H, fps = int(tl.get("width", 1920)), int(tl.get("height", 1080)), int(tl.get("fps", 30))
    tmp = Path(out_dir) / "_render"
    tmp.mkdir(parents=True, exist_ok=True)
    if not tl.get("clips"):
        raise StudioError("timeline has no clips")
    segs = [_norm_clip(c, i, W, H, fps, tmp) for i, c in enumerate(tl["clips"])]
    # chain clips with transitions
    inputs, fv, fa = [], [], []
    for p, _ in segs:
        inputs += ["-i", str(p)]
    lastv, lasta, t = "0:v", "0:a", segs[0][1]
    cuts = []
    for i in range(1, len(segs)):
        tr = tl["clips"][i].get("transition") or {}
        typ, d = tr.get("type", "cut"), float(tr.get("dur", 0.5))
        if typ == "cut" or typ not in XFADES:
            fv.append(f"[{lastv}][{i}:v]concat=n=2:v=1:a=0[v{i}]")
            fa.append(f"[{lasta}][{i}:a]concat=n=2:v=0:a=1[a{i}]")
            cuts.append(round(t, 3))
            t += segs[i][1]
        else:
            d = min(d, segs[i][1] / 2, segs[i - 1][1] / 2)
            off = t - d
            fv.append(f"[{lastv}][{i}:v]xfade=transition={typ}:duration={d:.3f}:offset={off:.3f}[v{i}]")
            fa.append(f"[{lasta}][{i}:a]acrossfade=d={d:.3f}[a{i}]")
            cuts.append(round(off + d / 2, 3))
            t = off + segs[i][1]
        lastv, lasta = f"v{i}", f"a{i}"
    base = tmp / "base.mp4"
    if len(segs) == 1:
        import shutil
        shutil.copy(segs[0][0], base)
    else:
        ffmpeg(*inputs, "-filter_complex", ";".join(fv + fa), "-map", f"[{lastv}]", "-map", f"[{lasta}]",
               "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", str(base))
    # second pass: overlays, audio beds, look, letterbox, subtitles
    inputs = ["-i", str(base)]
    graph, v = [], "0:v"
    k = 1
    for ov in tl.get("overlays", []):
        is_img = Path(ov["src"]).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        inputs += (["-loop", "1", "-i", ov["src"]] if is_img else ["-itsoffset", str(ov.get("start", 0)), "-i", ov["src"]])
        sc = ov.get("scale", 1.0)
        lbl = f"ov{k}"
        graph.append(f"[{k}:v]format=rgba,scale=iw*{sc}:ih*{sc}[{lbl}]")
        st, en = float(ov.get("start", 0)), float(ov.get("end", t))
        graph.append(f"[{v}][{lbl}]overlay=x={ov.get('x', '(W-w)/2')}:y={ov.get('y', '(H-h)/2')}:enable='between(t,{st},{en})':eof_action=pass[o{k}]")
        v = f"o{k}"
        k += 1
    post = []
    if tl.get("lut"):
        post.append(f"lut3d='{tl['lut']}'")
    if tl.get("letterbox"):
        ar = float(tl["letterbox"])
        bar = max(0, int((H - W / ar) / 2))
        post.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")
    if tl.get("subtitles"):
        esc = str(tl["subtitles"]).replace(":", r"\:")
        post.append(f"ass='{esc}':fontsdir='{ASSETS / 'fonts'}'")
    if post:
        graph.append(f"[{v}]{','.join(post)}[vpost]")
        v = "vpost"
    amix_in = [] if not tl.get("keep_clip_audio", True) else ["[0:a]"]
    for au in tl.get("audio", []):
        inputs += ["-i", au["src"]]
        ms = int(float(au.get("start", 0)) * 1000)
        graph.append(f"[{k}:a]adelay={ms}|{ms},volume={au.get('volume', 1.0)},aresample=48000,aformat=channel_layouts=stereo[au{k}]")
        amix_in.append(f"[au{k}]")
        k += 1
    if amix_in:
        graph.append(f"{''.join(amix_in)}amix=inputs={len(amix_in)}:duration=first:normalize=0[aout]")
    out = str(Path(out_dir) / name)
    if graph:
        args = [*inputs, "-filter_complex", ";".join(graph), "-map", f"[{v}]" if v != "0:v" else "0:v"]
        args += ["-map", "[aout]"] if amix_in else ["-an"]
        ffmpeg(*args, "-t", f"{t:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", out)
    else:
        import shutil
        shutil.copy(base, out)
    write_json(Path(out_dir) / "cuts.json", cuts)
    return {"output": out, "duration": round(t, 3), "cuts": cuts}


# ---------------- editor tools ----------------
def cut_silence(src, out_dir, threshold_db=-35, min_silence=0.6, pad=0.12):
    """Remove silent stretches (tutorials/podcasts)."""
    from .analyze import _ff_stderr
    d = probe(src)["duration"]
    err = _ff_stderr(["-i", src, "-vn", "-af", f"silencedetect=n={threshold_db}dB:d={min_silence}"])
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    keep, cur = [], 0.0
    for s, e in zip(st, en + [d] * (len(st) - len(en))):
        if s - cur > 0.05:
            keep.append((max(0, cur - pad), min(d, s + pad)))
        cur = e
    if d - cur > 0.05:
        keep.append((max(0, cur - pad), d))
    clips = [{"src": src, "in": round(a, 3), "out": round(b, 3), "fit": "pad"} for a, b in keep]
    info = probe(src)["video"] or {"width": 1920, "height": 1080, "fps": 30}
    res = render({"width": info["width"], "height": info["height"], "fps": round(info["fps"] or 30),
                  "clips": clips}, out_dir, "no_silence.mp4")
    res["removed_seconds"] = round(d - res["duration"], 2)
    return res


def reframe(src, out_dir, width=1080, height=1920, track=None, mode=None, name="reframed.mp4"):
    """Horizontal → vertical.
    mode 'fit_blur' (default without a track): whole frame scaled to width over a blurred fill — keeps all
                    on-screen text/graphics; 'crop': centre crop; with `track`: crop that follows the subject."""
    info = probe(src)["video"]
    if not track and (mode or "fit_blur") == "fit_blur":
        out = str(Path(out_dir) / name)
        flt = (f"[0:v]split[a][b];[a]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
               f"gblur=sigma=40,eq=brightness=-0.12[bg];[b]scale={width}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-{int(height*0.04)},setsar=1,format=yuv420p[v]")
        ffmpeg("-i", src, "-filter_complex", flt, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
               "-preset", "medium", "-c:a", "copy", out)
        return {"output": out, "mode": "fit_blur"}
    W, H = info["width"], info["height"]
    cw = min(W, int(H * width / height))
    out = str(Path(out_dir) / name)
    if track:
        pts = read_json(track)["boxes"]
        fps = read_json(track)["fps"]
        xs = []
        for i, b in enumerate(pts):
            cx = b[0] + b[2] / 2 if b else (xs[-1] + cw / 2 if xs else W / 2)
            xs.append(min(max(0, cx - cw / 2), W - cw))
        # smooth & write a sendcmd-free expression via piecewise lerp on keyframes every 0.5s
        step = max(1, int(fps / 2))
        keys = [(i / fps, sum(xs[i:i + step]) / len(xs[i:i + step])) for i in range(0, len(xs), step)]
        expr = str(int(keys[-1][1]))
        for (t0, x0), (t1, x1) in reversed(list(zip(keys, keys[1:]))):
            expr = f"if(lt(t,{t1:.3f}),{x0:.1f}+({x1:.1f}-{x0:.1f})*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f},{expr})"
        crop = f"crop={cw}:{H}:x='{expr}':y=0"
    else:
        crop = f"crop={cw}:{H}:(iw-{cw})/2:0"
    ffmpeg("-i", src, "-vf", f"{crop},scale={width}:{height},setsar=1", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
           "-c:a", "copy", out)
    return {"output": out}


def zoom_region(src, out_dir, x, y, w, h, start, end, ramp=0.4, name="zoomed.mp4"):
    """Smooth zoom into a screen region between start..end (tutorial focus)."""
    info = probe(src)["video"]
    W, H = info["width"], info["height"]
    z = f"if(between(t,{start},{end}),min(1,(t-{start})/{ramp})*min(1,({end}-t)/{ramp}),0)"
    cw = f"({W}-({W}-{w})*{z})"
    ch = f"({H}-({H}-{h})*{z})"
    cx = f"({x}*{z})"
    cy = f"({y}*{z})"
    out = str(Path(out_dir) / name)
    ffmpeg("-i", src, "-vf", f"crop=w='{cw}':h='{ch}':x='{cx}':y='{cy}',scale={W}:{H},setsar=1",
           "-c:v", "libx264", "-crf", "18", "-c:a", "copy", out)
    return {"output": out}


def clip(src, out_dir, start, end, name=None):
    out = str(Path(out_dir) / (name or f"clip_{start:.0f}_{end:.0f}.mp4"))
    ffmpeg("-ss", str(start), "-to", str(end), "-i", src, "-c:v", "libx264", "-crf", "18", "-c:a", "aac", out)
    return {"output": out}


# ---------------- NLE interchange ----------------
def export_project(timeline, out_dir, name="project"):
    """Write FCP7 XML (opens in Premiere Pro, DaVinci Resolve, Final Cut 7) + CMX3600 EDL + OTIO."""
    import opentimelineio as otio
    tl = read_json(timeline) if isinstance(timeline, str) else timeline
    fps = int(tl.get("fps", 30))
    t = otio.schema.Timeline(name=name)
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    t.tracks.append(track)
    for i, c in enumerate(tl["clips"]):
        info = probe(c["src"])
        a = float(c.get("in", 0))
        b = float(c["out"]) if c.get("out") is not None else (a + float(c.get("dur", 4)) if not info["video"] or info["duration"] == 0 else info["duration"])
        if i > 0 and (c.get("transition") or {}).get("type", "cut") not in ("cut", None):
            d = float(c["transition"].get("dur", 0.5))
            track.append(otio.schema.Transition(transition_type=otio.schema.TransitionTypes.SMPTE_Dissolve,
                                                in_offset=otio.opentime.RationalTime(d * fps / 2, fps),
                                                out_offset=otio.opentime.RationalTime(d * fps / 2, fps)))
        ref = otio.schema.ExternalReference(target_url=Path(c["src"]).resolve().as_uri(),
                                            available_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps),
                                                                                    otio.opentime.RationalTime(max(info["duration"], b) * fps, fps)))
        track.append(otio.schema.Clip(name=Path(c["src"]).stem, media_reference=ref,
                                      source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(round(a * fps), fps),
                                                                           otio.opentime.RationalTime(round((b - a) * fps), fps))))
    out = Path(out_dir)
    otio.adapters.write_to_file(t, str(out / f"{name}.otio"))
    otio.adapters.write_to_file(t, str(out / f"{name}.xml"), adapter_name="fcp_xml")
    try:
        otio.adapters.write_to_file(t, str(out / f"{name}.edl"), adapter_name="cmx_3600")
    except Exception:  # EDL cannot express some transitions; XML is the primary interchange
        pass
    return {"output": str(out / f"{name}.xml"), "otio": str(out / f"{name}.otio"), "edl": str(out / f"{name}.edl")}


def finish(video, out_dir, audio=None, subtitles=None, name="final.mp4"):
    """Conform: burn subtitles and lay the final mix under the picture."""
    out = str(Path(out_dir) / name)
    args = ["-i", video] + (["-i", audio] if audio else [])
    amap = ["-map", "1:a"] if audio else ["-map", "0:a?"]
    if subtitles and str(subtitles).endswith((".mov", ".webm", ".mkv")):
        # alpha caption track (captions.render_overlay) — correct RTL rendering
        args += ["-i", subtitles, "-filter_complex", f"[0:v][{2 if audio else 1}:v]overlay=0:0:eof_action=pass,format=yuv420p[v]",
                 "-map", "[v]"] + amap
    else:
        vf = f"ass='{str(subtitles).replace(':', chr(92)+':')}':fontsdir='{ASSETS / 'fonts'}'" if subtitles else "null"
        args += ["-vf", vf, "-map", "0:v"] + amap
    ffmpeg(*args, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", out)
    return {"output": out}


def auto_assemble(body_clips, target_duration, out_dir, intro=None, outro=None, gfx=None, width=1920, height=1080,
                  fps=30, transition="fade", lead_in=0.0):
    """Cover `target_duration` with the body clips (cycling, never repeating a span), interleaving the gfx
    segment(s) in the middle; intro/outro bookend. Writes timeline.json for render/export."""
    gfx = [g for g in ([gfx] if isinstance(gfx, str) else (gfx or [])) if g]
    gfx_total = sum(probe(g)["duration"] for g in gfx)
    remaining = max(1.0, target_duration - gfx_total)
    per = max(1.5, remaining / max(1, len(body_clips) * 2))
    clips, used, t = [], {c: 0.0 for c in body_clips}, 0.0
    if intro:
        clips.append({"src": intro, "fit": "crop"})
    body = []
    i = 0
    durs = {c: probe(c)["duration"] for c in body_clips}
    k = 0
    while t < remaining - 0.05 and i < 200:
        d = min(per, remaining - t)
        # next source that still has an unused span; reuse from the start only if all are exhausted
        cands = [body_clips[(k + j) % len(body_clips)] for j in range(len(body_clips))]
        fresh = [c for c in cands if used[c] + d <= durs[c]]
        src = fresh[0] if fresh else max(body_clips, key=lambda c: durs[c])
        k = body_clips.index(src) + 1
        a = used[src] if fresh else 0.0
        body.append({"src": src, "in": round(a, 3), "out": round(a + d, 3), "fit": "crop", "kenburns": 0.05,
                     "transition": {"type": transition, "dur": 0.4}})
        used[src] = a + d if fresh else d
        t += d
        i += 1
    mid = len(body) // 2
    for g in gfx:
        body.insert(mid, {"src": g, "fit": "crop", "transition": {"type": "slideleft", "dur": 0.4}})
        mid += 1
    clips += body
    if outro:
        clips.append({"src": outro, "fit": "crop", "transition": {"type": "fadeblack", "dur": 0.5}})
    tl = {"width": width, "height": height, "fps": fps, "clips": clips, "keep_clip_audio": False}
    out = str(Path(out_dir) / "timeline.json")
    write_json(out, tl)
    return {"output": out, "clips": len(clips)}
