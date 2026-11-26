"""Motion tracking (OpenCV CSRT), tracked overlays, and AI background removal (rembg)."""
from pathlib import Path

import cv2
import numpy as np

from .core import ffmpeg, probe, read_json, write_json


def track(src, out_dir, box=None, name="track.json"):
    """Track a box [x,y,w,h] through the clip. If box is None, auto-pick the most salient moving region."""
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("cannot read video")
    if box is None:
        ok2, nxt = cap.read()
        diff = cv2.absdiff(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.cvtColor(nxt if ok2 else frame, cv2.COLOR_BGR2GRAY))
        _, th = cv2.threshold(cv2.GaussianBlur(diff, (21, 21), 0), 8, 255, cv2.THRESH_BINARY)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = frame.shape[:2]
        box = list(cv2.boundingRect(max(cnts, key=cv2.contourArea))) if cnts else [w // 3, h // 3, w // 3, h // 3]
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = cap.read()
    if hasattr(cv2, "TrackerCSRT_create"):
        tr = cv2.TrackerCSRT_create()
    elif hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        tr = cv2.legacy.TrackerCSRT_create()
    else:
        tr = cv2.TrackerMIL_create()  # available in the core OpenCV build
    tr.init(frame, tuple(int(v) for v in box))
    boxes = [list(map(int, box))]
    lost = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        good, b = tr.update(frame)
        if good:
            boxes.append([int(v) for v in b])
        else:
            boxes.append(boxes[-1])
            lost += 1
    out = str(Path(out_dir) / name)
    write_json(out, {"fps": fps, "boxes": boxes, "lost_frames": lost, "init": box})
    return {"output": out, "frames": len(boxes), "lost_frames": lost}


def attach(src, track_json, overlay_png, out_dir, offset=(0, -80), name="tracked.mp4"):
    """Pin an image (label/logo) to a tracked object, frame-accurately."""
    data = read_json(track_json)
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ov = cv2.imread(overlay_png, cv2.IMREAD_UNCHANGED)
    if ov.shape[2] == 3:
        ov = np.dstack([ov, np.full(ov.shape[:2], 255, np.uint8)])
    tmp = str(Path(out_dir) / "_tracked_noaudio.mp4")
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        b = data["boxes"][min(i, len(data["boxes"]) - 1)]
        x = int(b[0] + b[2] / 2 - ov.shape[1] / 2 + offset[0])
        y = int(b[1] + offset[1] - ov.shape[0] / 2)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + ov.shape[1]), min(H, y + ov.shape[0])
        if x1 > x0 and y1 > y0:
            o = ov[y0 - y:y1 - y, x0 - x:x1 - x]
            a = o[:, :, 3:4] / 255.0
            f[y0:y1, x0:x1] = (f[y0:y1, x0:x1] * (1 - a) + o[:, :, :3] * a).astype(np.uint8)
        vw.write(f)
        i += 1
    vw.release()
    out = str(Path(out_dir) / name)
    ffmpeg("-i", tmp, "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "copy", out)
    return {"output": out}


def remove_bg(src, out_dir, bg=None, model="u2netp", max_frames=None, name=None):
    """AI matting per frame. Output: ProRes 4444 with alpha (.mov), or composited over `bg` if given."""
    from rembg import new_session, remove
    from PIL import Image
    sess = new_session(model)
    is_img = Path(src).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    if is_img:
        out = str(Path(out_dir) / (name or (Path(src).stem + "_cutout.png")))
        remove(Image.open(src), session=sess).save(out)
        return {"output": out}
    frames = Path(out_dir) / "_matte"
    frames.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    i = 0
    while True:
        ok, f = cap.read()
        if not ok or (max_frames and i >= max_frames):
            break
        im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        remove(im, session=sess).save(frames / f"{i:05d}.png")
        i += 1
    if bg:
        out = str(Path(out_dir) / (name or "bg_replaced.mp4"))
        W, H = probe(src)["video"]["width"], probe(src)["video"]["height"]
        bg_in = ["-loop", "1", "-i", bg] if Path(bg).suffix.lower() in (".png", ".jpg", ".jpeg") else ["-stream_loop", "-1", "-i", bg]
        ffmpeg(*bg_in, "-framerate", str(fps), "-i", str(frames / "%05d.png"), "-filter_complex",
               f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[b];[b][1:v]overlay=shortest=1,format=yuv420p[v]",
               "-map", "[v]", "-c:v", "libx264", "-crf", "18", out)
    else:
        out = str(Path(out_dir) / (name or "cutout_alpha.mov"))
        ffmpeg("-framerate", str(fps), "-i", str(frames / "%05d.png"), "-c:v", "prores_ks", "-profile:v", "4444",
               "-pix_fmt", "yuva444p10le", out)
    return {"output": out, "frames": i}
