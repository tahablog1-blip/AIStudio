"""Motion graphics / animation / intros: deterministic frame-by-frame HTML animation renderer.

spec = {"width":1920,"height":1080,"fps":30,"duration":8,"transparent":false,
        "style":{"colors":{...},"dir":"rtl","font":"Cairo"},
        "scenes":[{"start":0,"end":3,"template":"title","params":{...},"transition":"slide|fade|none","exit":true}],
        "captions": timeline (list) or null}
templates: title, lower_third, kinetic, bullets, stat, compare, cta, logo_reveal, end_screen, html
"""
import json
from pathlib import Path

from .core import ROOT, run, write_json

ENGINE = ROOT / "studio" / "motion_engine.html"

NODE = r"""
const { chromium } = require('playwright'); const fs = require('fs'); const { spawn } = require('child_process');
const [specPath, out, sfxOut] = process.argv.slice(2); const spec = JSON.parse(fs.readFileSync(specPath));
(async () => {
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: spec.width, height: spec.height } });
  p.on('pageerror', e => { console.error('pageerror', e.message); process.exit(3); });
  await p.goto('file://' + spec.engine); await p.evaluate(() => document.fonts.ready);
  const sfx = await p.evaluate(s => build(s), spec); fs.writeFileSync(sfxOut, JSON.stringify(sfx));
  const n = Math.ceil(spec.duration * spec.fps);
  const args = spec.transparent
    ? ['-y','-loglevel','error','-f','image2pipe','-c:v','png','-framerate',String(spec.fps),'-i','-','-c:v','prores_ks','-profile:v','4444','-pix_fmt','yuva444p10le',out]
    : ['-y','-loglevel','error','-f','image2pipe','-c:v','mjpeg','-framerate',String(spec.fps),'-i','-','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p',out];
  const ff = spawn('ffmpeg', args); ff.stderr.on('data', d => process.stderr.write(d));
  for (let i = 0; i < n; i++) {
    await p.evaluate(t => setT(t), i / spec.fps);
    const buf = spec.transparent ? await p.screenshot({ type: 'png', omitBackground: true }) : await p.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await b.close();
})();
"""


def render(spec, out_dir, name=None):
    spec = json.loads(Path(spec).read_text()) if isinstance(spec, str) else dict(spec)
    spec.setdefault("width", 1920)
    spec.setdefault("height", 1080)
    spec.setdefault("fps", 30)
    spec.setdefault("duration", max(s["end"] for s in spec["scenes"]))
    spec["engine"] = str(ENGINE)
    if isinstance(spec.get("captions"), str):
        spec["captions"] = json.loads(Path(spec["captions"]).read_text())
    out_dir = Path(out_dir)
    sp = out_dir / "_motion_spec.json"
    write_json(sp, spec)
    js = out_dir / "_motion.js"
    js.write_text(NODE)
    out = out_dir / (name or ("motion.mov" if spec.get("transparent") else "motion.mp4"))
    sfx = out_dir / "sfx_events.json"
    run(["node", str(js), str(sp), str(out), str(sfx)])
    return {"output": str(out), "sfx_events": str(sfx), "frames": int(spec["duration"] * spec["fps"])}


# -------- convenience builders (used by roles) --------
def title_card(out_dir, title, subtitle="", kicker="", highlight="", duration=4, width=1920, height=1080, style=None):
    return render({"width": width, "height": height, "duration": duration, "style": style or {},
                   "scenes": [{"start": 0, "end": duration, "template": "title", "exit": True,
                               "params": {"title": title, "subtitle": subtitle, "kicker": kicker, "highlight": highlight}}]},
                  out_dir, "title.mp4")


def lower_third(out_dir, name, role, duration=5, width=1920, height=1080, style=None):
    return render({"width": width, "height": height, "duration": duration, "transparent": True, "style": style or {},
                   "scenes": [{"start": 0, "end": duration, "template": "lower_third", "exit": True,
                               "params": {"name": name, "role": role}}]}, out_dir, "lower_third.mov")


def intro(out_dir, name, tagline="", logo=None, duration=4, width=1920, height=1080, style=None):
    return render({"width": width, "height": height, "duration": duration, "style": style or {},
                   "scenes": [{"start": 0, "end": duration, "template": "logo_reveal", "exit": True,
                               "params": {"name": name, "tagline": tagline, "logo": Path(logo).resolve().as_uri() if logo else None}}]},
                  out_dir, "intro.mp4")


def outro(out_dir, title="شكراً للمشاهدة", subscribe="🔔 اشترك", duration=20, width=1920, height=1080, style=None):
    """YouTube end screen (20 s with placeholders for end-screen elements)."""
    return render({"width": width, "height": height, "duration": duration, "style": style or {},
                   "scenes": [{"start": 0, "end": duration, "template": "end_screen",
                               "params": {"title": title, "subscribe": subscribe}}]}, out_dir, "outro.mp4")
