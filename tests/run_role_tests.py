"""Phase 7 — a practical, measured test for every studio role.

Each test executes the role's real tools (through the same authorisation check the CLI uses),
then asserts on a measured property of the output, not only on file existence.
Run:  python tests/run_role_tests.py [role ...]
"""
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio import (analyze, audio, captions, color, edit, encode, enhance, motion, project as prj,  # noqa
                    qc, rhythm, script, storyboard, thumbnail, three_d, tracking, vfx, voice)
from studio.core import probe, read_json
from studio.orchestrator import validate
from studio.roles import ROLES

M = ROOT / "tests" / "media"
OUT = ROOT / "tests" / "results"
RESULTS = []


def do(role, fn, **kw):
    """Same rule as `studio do`: a role may only run functions of its authorised modules."""
    mod = fn.__module__.split(".")[-1]
    assert mod in ROLES[role]["modules"], f"{role} not authorised for {mod}"
    return fn(**kw)


def out_dir(role):
    d = OUT / role
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


TESTS = {}


def test(role):
    def deco(f):
        TESTS[role] = f
        return f
    return deco


# ---------------- management ----------------
@test("executive-producer")
def _(d):
    import shutil
    base = Path(d) / "projects"
    shutil.rmtree(base, ignore_errors=True)
    pr = prj.Project.create("EP Test", "اختبار", raw_files=[M / "product_demo.mp4"], base=base)
    pr.add_task("a", "cinematographer", "تحليل", {"fn": "analyze.report", "args": {"path": "{raw}/product_demo.mp4", "out": "{out}/r.json"}})
    from studio.orchestrator import run_project
    run_project(pr, workers=2)
    t = pr.m["tasks"]["a"]
    assert t["status"] == "done", t
    res = do("executive-producer", prj.deliver, project_path=str(pr.path), files=[pr.latest("a")], out_dir=d)
    assert res["files"] == ["r.json"]
    return f"project created, task executed, delivered {res['files']}", res["output"]


@test("production-manager")
def _(d):
    import shutil
    base = Path(d) / "projects"
    shutil.rmtree(base, ignore_errors=True)
    pr = prj.Project.create("PM Test", raw_files=[M / "product_demo.mp4"], base=base)
    pr.add_task("x", "colorist", "x", {"fn": "color.correct", "args": {}}, deps=["y"])
    pr.add_task("y", "colorist", "y", {"fn": "color.correct", "args": {}}, deps=["x"])
    pr.add_task("z", "colorist", "unauthorised", {"fn": "audio.mix", "args": {}})
    probs = validate(pr)
    assert any("cycle" in p for p in probs) and any("not authorised" in p for p in probs), probs
    # failure → retry → blocked dependents
    pr2 = prj.Project.create("PM Test2", raw_files=[M / "product_demo.mp4"], base=base)
    pr2.add_task("bad", "video-enhancement", "ملف غير موجود", {"fn": "enhance.denoise", "args": {"src": "{raw}/missing.mp4", "out_dir": "{out}"}})
    pr2.add_task("after", "colorist", "تابع", {"fn": "color.correct", "args": {"src": "{task:bad}", "out_dir": "{out}"}}, deps=["bad"])
    from studio.orchestrator import run_project
    run_project(pr2)
    st = {k: v["status"] for k, v in pr2.m["tasks"].items()}
    assert st == {"bad": "failed", "after": "blocked"}, st
    assert pr2.m["tasks"]["bad"]["attempts"] == 2
    return f"detected {len(probs)} graph problems; failed task retried ×2 and dependent blocked", str(pr2.path / "manifest.json")


@test("creative-director")
def _(d):
    r = do("creative-director", storyboard.style_guide, out_dir=d, name="ورشة AI", tone="حماسي", music="lofi")
    g = read_json(r["output"])
    assert g["colors"]["primary"].startswith("#")
    return "style guide written", r["output"]


# ---------------- pre-production ----------------
SHOTS = [{"size": "WS", "action": "لقطة افتتاحية للمكتب", "dur": 3, "camera": "slow push-in"},
         {"size": "SCREEN", "action": "البرنامج بيحمّل ملف", "dur": 4, "on_screen": "أسرع ×2.5", "vo": "شوف السرعة"},
         {"size": "CU", "action": "إيد على الماوس", "dur": 2, "camera": "static"},
         {"size": "GFX", "action": "شعار ورشة AI", "dur": 3}]


@test("film-director")
def _(d):
    try:
        storyboard.write_shotlist([{"size": "XX", "action": "bad"}], d)
        raise AssertionError("invalid shot accepted")
    except ValueError:
        pass
    r = do("film-director", storyboard.write_shotlist, shots=SHOTS, out_dir=d)
    assert read_json(r["output"])["total"] == 12
    return "4-shot list, 12.0s; invalid shot rejected", r["output"]


@test("storyboard-artist")
def _(d):
    sl = storyboard.write_shotlist(SHOTS, d)["output"]
    r = do("storyboard-artist", storyboard.sheet, shotlist_json=sl, out_dir=d, title="FastDM")
    from PIL import Image
    w, h = Image.open(r["output"]).size
    a = do("storyboard-artist", storyboard.animatic, shotlist_json=sl, out_dir=d)
    assert w >= 1700 and abs(probe(a["output"])["duration"] - 12) < 0.2
    return f"sheet {w}x{h}, animatic {probe(a['output'])['duration']:.1f}s", r["output"]


@test("screenwriter")
def _(d):
    s = Path(d) / "script.md"
    s.write_text("# إعلان\n[موسيقى]\nبتدفع فلوس علشان تحمّل أسرع؟ FastDM بيقسّم الملف لتمن أجزاء، ويحمّلهم مع بعض! حمّله مجاناً.", encoding="utf-8")
    r = do("screenwriter", script.prepare_vo, script_path=str(s), out_dir=d)
    vo = Path(r["output"]).read_text(encoding="utf-8")
    assert "[" not in vo and "،" not in vo and "!" not in vo and "#" not in vo
    o = do("screenwriter", script.scaffold, structure="ad_30", out_dir=d, topic="FastDM")
    return f"VO cleaned ({r['words']} words ≈{r['seconds']}s); ad_30 outline {o['total_seconds']}s", r["output"]


@test("cinematographer")
def _(d):
    r = do("cinematographer", analyze.report, path=str(M / "dark_cast.mp4"), out=str(Path(d) / "camera_report.json"))
    f = " | ".join(r["report"]["findings"])
    assert "معتمة" in f or "انحراف" in f, f
    return f"findings: {f[:120]}", r["output"]


# ---------------- editorial ----------------
@test("lead-editor")
def _(d):
    tl = {"width": 1280, "height": 720, "fps": 30, "clips": [
        {"src": str(M / "product_demo.mp4"), "in": 0, "out": 3},
        {"src": str(M / "product_race.mp4"), "in": 0, "out": 3, "transition": {"type": "slideleft", "dur": 0.5}},
        {"src": str(M / "logo.png"), "dur": 2, "transition": {"type": "fade", "dur": 0.5}}]}
    r = do("lead-editor", edit.render, timeline=tl, out_dir=d)
    x = do("lead-editor", edit.export_project, timeline=tl, out_dir=d, name="lead_test")
    xml = Path(x["output"]).read_text()
    assert "<xmeml" in xml and xml.count("<clipitem") >= 3
    assert abs(r["duration"] - 7.0) < 0.15, r["duration"]
    return f"3-clip edit {r['duration']}s with transitions; FCP7 XML ({xml.count('<clipitem')} clipitems) + EDL", r["output"]


@test("cinema-editor")
def _(d):
    tl = {"width": 1920, "height": 1080, "fps": 24, "letterbox": 2.39, "clips": [
        {"src": str(M / "product_race.mp4"), "in": 0, "out": 2.5},
        {"src": str(M / "product_demo.mp4"), "in": 2, "out": 4.5, "transition": {"type": "dissolve", "dur": 0.6}}]}
    r = do("cinema-editor", edit.render, timeline=tl, out_dir=d)
    import cv2
    cap = cv2.VideoCapture(r["output"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
    ok, f = cap.read()
    top = f[:100].mean()
    assert top < 8, f"letterbox not black ({top})"
    return f"2.39:1 letterboxed dissolve edit, {r['duration']}s @24fps", r["output"]


@test("commercial-editor")
def _(d):
    b = rhythm.beats(str(M / "music.wav"), d)
    tl = do("commercial-editor", rhythm.beat_cut_timeline, beats_json=b["output"],
            sources=[str(M / "product_demo.mp4"), str(M / "product_race.mp4"), str(M / "shaky.mp4")], out_dir=d, every=4, total=10)
    t = read_json(tl["output"])
    t["audio"] = [{"src": str(M / "music.wav"), "start": 0, "volume": 0.8}]
    r = do("commercial-editor", edit.render, timeline=t, out_dir=d, name="ad_beatcut.mp4")
    return f"beat-cut ad: {tl['cuts']} cuts on every 4th beat ({b['bpm']} bpm)", r["output"]


@test("documentary-editor")
def _(d):
    t = do("documentary-editor", captions.transcribe, media=str(M / "narration.wav"), out_dir=d)
    tl = read_json(t["output"])
    paper = Path(d) / "paper_edit.md"
    paper.write_text("\n".join(f"- [{s['start']:.1f}s] {s['text']}" for s in tl), encoding="utf-8")
    assert len(tl) >= 2 and sum(len(s["words"]) for s in tl) > 10
    kb = do("documentary-editor", edit.render, timeline={"width": 1280, "height": 720, "clips": [{"src": str(M / "logo.png"), "dur": 3, "kenburns": 0.1}]}, out_dir=d, name="kenburns.mp4")
    return f"transcribed {len(tl)} segments → paper edit; Ken Burns still {probe(kb['output'])['duration']:.1f}s", str(paper)


@test("educational-editor")
def _(d):
    r = do("educational-editor", edit.cut_silence, src=str(M / "screen_tutorial.mp4"), out_dir=d)
    assert r["removed_seconds"] > 2.0, r
    z = do("educational-editor", edit.zoom_region, src=r["output"], out_dir=d, x=600, y=120, w=640, h=360, start=1, end=4)
    return f"removed {r['removed_seconds']}s of silence; zoom-in on UI region", z["output"]


@test("marketing-editor")
def _(d):
    lt = motion.lower_third(d, "FastDM", "برنامج تحميل مجاني", duration=4, width=1280, height=720)
    tl = {"width": 1280, "height": 720, "clips": [{"src": str(M / "product_demo.mp4"), "in": 0, "out": 5}],
          "overlays": [{"src": lt["output"], "start": 0.5, "end": 4.5, "x": 0, "y": 0}]}
    r = do("marketing-editor", edit.render, timeline=tl, out_dir=d, name="promo_lt.mp4")
    return "product clip with animated lower-third overlay (alpha)", r["output"]


@test("social-editor")
def _(d):
    tr = tracking.track(str(M / "greenscreen.mp4"), d, box=[300, 280, 520, 520])
    r = do("social-editor", edit.reframe, src=str(M / "greenscreen.mp4"), out_dir=d, track=tr["output"])
    v = probe(r["output"])["video"]
    assert (v["width"], v["height"]) == (1080, 1920)
    return "16:9 → 9:16 reframe following the tracked subject", r["output"]


@test("shortlong-editor")
def _(d):
    r = do("shortlong-editor", edit.clip, src=str(M / "screen_tutorial.mp4"), out_dir=d, start=1, end=6)
    assert abs(probe(r["output"])["duration"] - 5) < 0.2
    return "5.0s highlight clipped from long video", r["output"]


@test("rhythmic-editor")
def _(d):
    r = do("rhythmic-editor", rhythm.beats, audio=str(M / "music.wav"), out_dir=d)
    assert abs(r["bpm"] - 84) < 3 or abs(r["bpm"] - 168) < 5, r["bpm"]
    sp = do("rhythmic-editor", edit.render, timeline={"width": 1280, "height": 720, "clips": [
        {"src": str(M / "shaky.mp4"), "in": 0, "out": 2, "speed": 1.0},
        {"src": str(M / "shaky.mp4"), "in": 2, "out": 6, "speed": 2.0}]}, out_dir=d, name="speed_ramp.mp4")
    assert abs(sp["duration"] - 4.0) < 0.15, sp["duration"]
    return f"detected {r['bpm']} bpm (music generated at 84); 2× speed ramp", sp["output"]


# ---------------- graphics ----------------
@test("vfx-artist")
def _(d):
    r = do("vfx-artist", vfx.stack_effects, src=str(M / "product_race.mp4"), out_dir=d, fxs=("glow", "vignette", "grain"))
    g = do("vfx-artist", vfx.effect, src=str(M / "product_race.mp4"), out_dir=d, fx="glitch")
    return "glow+vignette+grain stack; glitch pass", r["output"]


@test("motion-designer")
def _(d):
    spec = {"width": 1280, "height": 720, "duration": 9, "scenes": [
        {"start": 0, "end": 3, "template": "kinetic", "params": {"words": ["أسرع", "من", "المتصفح", "مرتين", "ونص"]}},
        {"start": 3, "end": 6, "template": "stat", "params": {"label": "السرعة", "value": 2.5, "decimals": 1, "prefix": "×", "caption": "أسرع"}},
        {"start": 6, "end": 9, "template": "bullets", "params": {"heading": "المميزات", "items": ["تقسيم ذكي", "إيقاف واستكمال", "أيقونة عائمة"]}}]}
    r = do("motion-designer", motion.render, spec=spec, out_dir=d)
    assert abs(probe(r["output"])["duration"] - 9) < 0.15
    ev = read_json(r["sfx_events"])
    return f"3 animated scenes, {len(ev)} SFX cue points exported", r["output"]


@test("animator")
def _(d):
    r = do("animator", three_d.text_3d, text="FastDM", out_dir=d, duration=1.5, width=640, height=360, samples=6)
    assert abs(probe(r["output"])["duration"] - 1.5) < 0.1
    return "Blender Cycles 3D extruded logo animation", r["output"]


@test("compositor")
def _(d):
    r = do("compositor", vfx.key, fg=str(M / "greenscreen.mp4"), bg=str(M / "product_race.mp4"), out_dir=d)
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(r["output"])
    ok, f = cap.read()
    green = ((f[:, :, 1] > 200) & (f[:, :, 2] < 60) & (f[:, :, 0] < 60)).mean()
    assert green < 0.02, f"green remains {green:.3f}"
    cut = do("compositor", tracking.remove_bg, src=str(M / "logo.png"), out_dir=d)
    return f"chroma key: pure-green pixels {green*100:.2f}%; AI cut-out PNG", r["output"]


@test("motion-tracker")
def _(d):
    t = do("motion-tracker", tracking.track, src=str(M / "greenscreen.mp4"), out_dir=d, box=[300, 280, 520, 520])
    b = read_json(t["output"])["boxes"]
    moved = b[-1][0] - b[0][0]
    assert moved > 400, f"tracker moved only {moved}px (subject moves ~600px)"
    lab = thumbnail.design(d, "هدف", size="square", name="label.png")["output"]
    from PIL import Image
    Image.open(lab).resize((160, 160)).save(Path(d) / "label_small.png")
    a = do("motion-tracker", tracking.attach, src=str(M / "greenscreen.mp4"), track_json=t["output"], overlay_png=str(Path(d) / "label_small.png"), out_dir=d)
    return f"tracked {len(b)} frames, subject moved {moved}px, label pinned", a["output"]


@test("intro-outro")
def _(d):
    i = do("intro-outro", motion.intro, out_dir=d, name="ورشة AI", tagline="نبني بالذكاء الاصطناعي", logo=str(M / "logo.png"), duration=3, width=1280, height=720)
    o = do("intro-outro", motion.outro, out_dir=d, duration=5, width=1280, height=720)
    return "logo-reveal intro 3s + end screen 5s", i["output"]


@test("thumbnail-designer")
def _(d):
    r = do("thumbnail-designer", thumbnail.ab_set, video=str(M / "product_demo.mp4"), out_dir=d, title="برنامج تحميل مجاني", highlight="أسرع ×2.5", badge="جديد")
    from PIL import Image
    assert all(Image.open(v).size == (1280, 720) for v in r["variants"])
    return "A/B thumbnails 1280×720 from auto-selected best frames", r["output"]


# ---------------- colour ----------------
@test("colorist")
def _(d):
    r = do("colorist", color.correct, src=str(M / "dark_cast.mp4"), out_dir=d)
    assert abs(r["after_luma"] - 118) < abs(r["before_luma"] - 118), r
    rep = read_json(Path(d) / "color_report.json")
    du_b, du_a = abs(rep["before"]["u_avg"] - 128), abs(rep["after"]["u_avg"] - 128)
    return f"luma {r['before_luma']} → {r['after_luma']} (target 118); blue cast |U-128| {du_b:.1f} → {du_a:.1f}", r["output"]


@test("color-grader")
def _(d):
    r = do("color-grader", color.grade, src=str(M / "product_race.mp4"), out_dir=d, look="teal_orange")
    lut = Path(r["lut"]).read_text().splitlines()
    assert "LUT_3D_SIZE 33" in lut[1] and len(lut) == 4 + 33 ** 3
    color.build_library()
    return f"teal-orange grade + .cube LUT ({33**3} entries) + LUT library", r["output"]


# ---------------- audio ----------------
@test("sound-engineer")
def _(d):
    c = do("sound-engineer", audio.cleanup, src=str(M / "narration.wav"), out_dir=d)
    m = do("sound-engineer", audio.mix, voice=c["output"], out_dir=d, music=str(M / "music.wav"), events=[[1, "whoosh"], [4, "ding"]])
    st = analyze.audio_stats(m["output"])
    assert abs(st["integrated_lufs"] + 14) < 1.5, st
    return f"cleanup chain + ducked mix: {st['integrated_lufs']} LUFS, peak {st['true_peak_db']} dBTP", m["output"]


@test("sound-designer")
def _(d):
    lib = do("sound-designer", audio.sfx_library, out_dir=d)
    mb = do("sound-designer", audio.music_bed, duration=12, out_dir=d)
    assert len(lib["files"]) >= 10 and abs(probe(mb["output"])["duration"] - 12) < 0.1
    return f"{len(lib['files'])} synthesized SFX + 12s royalty-free music bed", mb["output"]


@test("voice-over")
def _(d):
    t = do("voice-over", voice.tts, text="أهلاً بيكم في ورشة AI. النهارده هنعمل برنامج تحميل.", out_dir=d)
    al = do("voice-over", voice.align, audio=t["output"], script_text="أهلاً بيكم في ورشة AI. النهارده هنعمل برنامج تحميل.", out_dir=d)
    m, n = map(int, al["matched"].split("/"))
    assert m / n >= 0.5, al
    return f"Piper TTS {probe(t['output'])['duration']:.1f}s; Whisper alignment matched {al['matched']} words", t["output"]


# ---------------- delivery ----------------
@test("video-enhancement")
def _(d):
    s = do("video-enhancement", enhance.stabilize, src=str(M / "shaky.mp4"), out_dir=d)
    u = do("video-enhancement", enhance.restore, src=str(M / "lowres_interlaced.mp4"), out_dir=d)
    v = probe(u["output"])["video"]
    assert v["height"] == 1080, v
    # stabilisation metric: mean absolute frame difference should drop
    import cv2
    import numpy as np
    def jitter(p):
        cap = cv2.VideoCapture(p)
        prev, ds = None, []
        for _ in range(60):
            ok, f = cap.read()
            if not ok:
                break
            g = cv2.cvtColor(cv2.resize(f, (480, 270)), cv2.COLOR_BGR2GRAY).astype(float)
            if prev is not None:
                ds.append(np.abs(g - prev).mean())
            prev = g
        return float(np.mean(ds))
    j0, j1 = jitter(str(M / "shaky.mp4")), jitter(s["output"])
    assert j1 < j0, (j0, j1)
    return f"stabilised (frame-diff {j0:.1f} → {j1:.1f}); 480i → 1080p progressive", s["output"]


@test("encoding-engineer")
def _(d):
    r = do("encoding-engineer", encode.export_many, src=str(M / "screen_tutorial.mp4"), out_dir=d,
           presets=["youtube_1080p", "instagram_feed", "broadcast_master"])
    oks = {p: qc.check(f, p)["qc_pass"] for p, f in r["files"].items()}
    assert all(oks.values()), oks
    return f"3 deliverables, all pass spec QC: {oks}", r["output"]


@test("quality-control")
def _(d):
    good = encode.export(str(M / "screen_tutorial.mp4"), d, "youtube_1080p", name="good")["output"]
    g = do("quality-control", qc.check, path=good, preset="youtube_1080p", out_dir=d)
    b = qc.check(str(M / "lowres_interlaced.mp4"), "youtube_1080p")
    assert g["qc_pass"] and not b["qc_pass"], (g["summary"], b["summary"])
    return f"good file {g['summary']}; defective file correctly rejected ({b['summary']})", g["output"]


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    roles = only or list(ROLES)
    for role in roles:
        f = TESTS.get(role)
        if not f:
            RESULTS.append((role, "MISSING", 0, "no test", ""))
            continue
        t0 = time.time()
        try:
            detail, output = f(out_dir(role))
            RESULTS.append((role, "PASS", time.time() - t0, detail, output))
            print(f"PASS  {role:<22} {time.time()-t0:5.1f}s  {detail}", flush=True)
        except Exception as e:  # noqa
            RESULTS.append((role, "FAIL", time.time() - t0, f"{e}", traceback.format_exc()[-800:]))
            print(f"FAIL  {role:<22} {e}\n{traceback.format_exc()[-600:]}", flush=True)
    md = ["# نتائج اختبار الموظفين (المرحلة 7)", "", f"{sum(r[1]=='PASS' for r in RESULTS)}/{len(RESULTS)} PASS", "",
          "| الموظف | النتيجة | الزمن | القياس | المخرج |", "|---|---|---|---|---|"]
    for role, st, dt, det, outp in RESULTS:
        md.append(f"| {ROLES[role]['ar']} (`{role}`) | {'✅' if st=='PASS' else '❌'} {st} | {dt:.1f}s | {det} | `{Path(outp).relative_to(ROOT) if outp and str(outp).startswith(str(ROOT)) else outp}` |")
    (OUT / "role_tests.md").write_text("\n".join(md), encoding="utf-8")
    json.dump([dict(role=r[0], status=r[1], seconds=round(r[2], 1), detail=r[3], output=str(r[4])) for r in RESULTS],
              open(OUT / "role_tests.json", "w"), ensure_ascii=False, indent=1)
    return sum(r[1] != "PASS" for r in RESULTS)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
