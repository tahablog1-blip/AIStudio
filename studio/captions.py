"""Captions: transcription, SRT, styled/karaoke ASS (Arabic-safe via libass) and burn-in."""
from pathlib import Path

from .core import ASSETS, ffmpeg, read_json, write_json


def transcribe(media, out_dir, lang="ar", model_size="small"):
    """Speech → timeline.json (sentences with word timings) for editors with no script."""
    import wave
    import numpy as np
    from faster_whisper import WhisperModel
    w16 = Path(out_dir) / "_a16.wav"
    ffmpeg("-i", media, "-vn", "-ar", "16000", "-ac", "1", str(w16))
    w = wave.open(str(w16))
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    segs, _ = WhisperModel(model_size, device="cpu", compute_type="int8").transcribe(a, language=lang, word_timestamps=True)
    tl = []
    for i, s in enumerate(segs):
        tl.append({"i": i, "text": s.text.strip(), "start": round(s.start, 3), "dur": round(s.end - s.start, 3),
                   "words": [[x.word.strip(), round(x.start, 3)] for x in s.words]})
    out = str(Path(out_dir) / "timeline.json")
    write_json(out, tl)
    return {"output": out, "segments": len(tl)}


def _ts_srt(t):
    h, r = divmod(max(0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def _ts_ass(t):
    h, r = divmod(max(0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _chunks(timeline, max_words=7):
    """Split long sentences into ≤2-line chunks keeping word timings."""
    for s in timeline:
        words = s.get("words") or [[w, s["start"]] for w in s["text"].split()]
        end = s["start"] + s["dur"]
        for k in range(0, len(words), max_words):
            part = words[k:k + max_words]
            nxt = words[k + max_words][1] if k + max_words < len(words) else end
            yield part, part[0][1], nxt


def to_srt(timeline_json, out_dir, max_words=7):
    tl = read_json(timeline_json)
    lines = []
    for n, (part, a, b) in enumerate(_chunks(tl, max_words), 1):
        lines += [str(n), f"{_ts_srt(a)} --> {_ts_srt(b)}", " ".join(w for w, _ in part), ""]
    out = str(Path(out_dir) / "captions.srt")
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    return {"output": out}


def to_ass(timeline_json, out_dir, width=1920, height=1080, style="karaoke", font="Cairo", size=None,
           primary="&H00FFFFFF", highlight="&H0035E6A3", outline=6, margin_v=None, max_words=7):
    """style: 'karaoke' (active word turns lime) or 'plain'. Colours are ASS &HAABBGGRR."""
    tl = read_json(timeline_json)
    size = size or int(height * (0.058 if width >= height else 0.042))
    margin_v = margin_v or int(height * (0.06 if width >= height else 0.22))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{primary},{primary},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},2,2,80,80,{margin_v},1
Style: Hi,{font},{size},{highlight},{highlight},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},2,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for part, a, b in _chunks(tl, max_words):
        if style == "karaoke":
            for i, (w, t) in enumerate(part):
                t2 = part[i + 1][1] if i + 1 < len(part) else b
                words = []
                for j, (w2, _) in enumerate(part):
                    words.append(r"{\c" + highlight.replace("&H00", "&H") + r"&\fscx108\fscy108}" + w2 + r"{\r}" if j == i else w2)
                ev.append(f"Dialogue: 0,{_ts_ass(t)},{_ts_ass(t2)},Cap,,0,0,0,,{' '.join(words)}")
        else:
            ev.append(f"Dialogue: 0,{_ts_ass(a)},{_ts_ass(b)},Cap,,0,0,0,,{' '.join(w for w, _ in part)}")
    out = str(Path(out_dir) / "captions.ass")
    Path(out).write_text(head + "\n".join(ev) + "\n", encoding="utf-8")
    return {"output": out, "events": len(ev)}


def burn(video, subs, out_dir, name="captioned.mp4"):
    out = str(Path(out_dir) / name)
    fontsdir = str(ASSETS / "fonts")
    esc = str(subs).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    flt = f"subtitles='{esc}':fontsdir='{fontsdir}'" if str(subs).endswith(".srt") else f"ass='{esc}':fontsdir='{fontsdir}'"
    ffmpeg("-i", video, "-vf", flt, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", out)
    return {"output": out}


_CAP_NODE = r"""
const { chromium } = require('playwright'); const fs = require('fs');
const [jobPath] = process.argv.slice(2); const job = JSON.parse(fs.readFileSync(jobPath));
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: job.width, height: job.height } });
  await p.setContent(`<html dir="rtl"><head><style>
   @font-face{font-family:Cairo;font-weight:900;src:url("${job.font}")}
   html,body{margin:0;background:transparent;width:${job.width}px;height:${job.height}px;overflow:hidden}
   #c{position:fixed;left:0;right:0;bottom:${job.bottom}px;display:flex;justify-content:center}
   #c p{margin:0;max-width:${Math.round(job.width*0.88)}px;text-align:center;font-family:Cairo;font-weight:900;font-size:${job.size}px;line-height:1.45;
        color:#fff;-webkit-text-stroke:${Math.round(job.size*0.16)}px #000;paint-order:stroke fill;text-shadow:0 4px 14px #000a}
   #c span{display:inline-block;margin:0 .12em} #c .on{color:${job.highlight};transform:scale(1.1)}
  </style></head><body><div id="c"><p id="t"></p></div></body></html>`);
  await p.evaluate(() => document.fonts.ready);
  for (const s of job.states) {
    await p.evaluate(s => { document.getElementById('t').innerHTML = s.words.map((w, i) => `<span class="${i === s.on ? 'on' : ''}">${w.replace(/</g,'&lt;')}</span>`).join(' '); }, s);
    await p.screenshot({ path: s.png, omitBackground: true });
  }
  await b.close();
})();
"""


def render_overlay(timeline_json, out_dir, width=1920, height=1080, max_words=7, highlight="#a3e635", size=None, bottom=None):
    """Karaoke captions rendered by Chromium (correct Arabic shaping AND word order) into a transparent
    ProRes 4444 track, one still per word state — fast, and safe for RTL unlike per-word ASS tags."""
    import json
    from .core import run
    tl = read_json(timeline_json)
    out_dir = Path(out_dir)
    frames = out_dir / "_capframes"
    frames.mkdir(exist_ok=True)
    size = size or int(min(width, height) * (0.058 if width >= height else 0.062))
    bottom = bottom if bottom is not None else int(height * (0.05 if width >= height else 0.2))
    states, timeline = [], []
    blank = str(frames / "blank.png")
    states.append({"words": [], "on": -1, "png": blank})
    t = 0.0
    n = 0
    for part, a, b in _chunks(tl, max_words):
        words = [w for w, _ in part]
        if a > t + 0.01:
            timeline.append((blank, a - t))
        for i, (w, ts) in enumerate(part):
            te = part[i + 1][1] if i + 1 < len(part) else b
            png = str(frames / f"s{n:04d}.png")
            n += 1
            states.append({"words": words, "on": i, "png": png})
            timeline.append((png, max(0.04, te - max(ts, a if i == 0 else ts))))
        t = b
    job = out_dir / "_capjob.json"
    job.write_text(json.dumps({"width": width, "height": height, "size": size, "bottom": bottom, "highlight": highlight,
                               "font": (ASSETS / "fonts" / "Cairo-Black.ttf").as_uri(), "states": states}, ensure_ascii=False))
    js = out_dir / "_cap.js"
    js.write_text(_CAP_NODE)
    run(["node", str(js), str(job)])
    lst = out_dir / "_caplist.txt"
    lines = []
    for png, d in timeline:
        lines += [f"file '{png}'", f"duration {d:.3f}"]
    lines.append(f"file '{timeline[-1][0]}'")
    lst.write_text("\n".join(lines))
    out = str(out_dir / "captions_alpha.mov")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-vf", "fps=30,format=yuva444p10le", "-c:v", "prores_ks",
           "-profile:v", "4444", out)
    return {"output": out, "states": n}
