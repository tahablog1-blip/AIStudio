"""Production templates: turn a project type into a task graph assigned to the right roles.

Each task = (id, role, title, action{fn,args}, deps). Templates reference earlier outputs with
{task:<id>} / {task:<id>:<file>}, {raw}, {out}, {project}. The executive producer (or the Claude
agent playing that role) can add/remove tasks before `studio run`.
"""
from pathlib import Path

from .core import StudioError, write_json
from .project import Project


def _t(pr, tid, role, title, fn, args, deps=(), review_by=None, max_attempts=2):
    pr.add_task(tid, role, title, action={"fn": fn, "args": args}, deps=deps, review_by=review_by,
                max_attempts=max_attempts)


def promo(pr: Project, footage, script="script.md", logo=None, brand="", tagline="", shots=None, gfx=None,
          presets=("youtube_1080p", "youtube_shorts"), look="teal_orange", width=1920, height=1080):
    """Commercial / product / marketing video from raw footage + script (+ logo)."""
    raw = "{raw}"
    footage = [f"{raw}/{f}" for f in footage]
    _t(pr, "camera-report", "cinematographer", "تحليل تقني للمواد الخام", "analyze.analyze_folder",
       {"folder": raw, "out": "{out}/camera_report.json"})
    _t(pr, "style", "creative-director", "دليل الأسلوب", "storyboard.style_guide",
       {"out_dir": "{out}", "name": brand, "tone": "حماسي وواضح", "music": "lofi"})
    _t(pr, "script", "screenwriter", "تجهيز نص التعليق الصوتي", "script.prepare_vo",
       {"script_path": f"{raw}/{script}", "out_dir": "{out}"})
    if shots:
        _t(pr, "shotlist", "film-director", "قائمة اللقطات", "storyboard.write_shotlist", {"shots": shots, "out_dir": "{out}"})
        _t(pr, "storyboard", "storyboard-artist", "لوحة الستوري بورد", "storyboard.sheet",
           {"shotlist_json": "{task:shotlist}", "out_dir": "{out}", "title": brand}, deps=["shotlist"], review_by="creative-director")
    _t(pr, "vo", "voice-over", "تعليق صوتي", "voice.tts", {"text": "@file:{task:script}", "out_dir": "{out}"}, deps=["script"])
    _t(pr, "vo-align", "voice-over", "توقيت كل كلمة", "voice.align",
       {"audio": "{task:vo}", "script_text": "@file:{task:script}", "out_dir": "{out}"}, deps=["vo"])
    enh_ids = []
    for i, f in enumerate(footage):
        tid = f"enhance-{i+1}"
        _t(pr, tid, "video-enhancement", f"تحسين {Path(f).name}", "enhance.restore", {"src": f, "out_dir": "{out}"}, deps=["camera-report"])
        _t(pr, f"correct-{i+1}", "colorist", f"تصحيح ألوان {Path(f).name}", "color.correct", {"src": f"{{task:{tid}}}", "out_dir": "{out}"}, deps=[tid])
        _t(pr, f"grade-{i+1}", "color-grader", f"معالجة سينمائية {Path(f).name}", "color.grade",
           {"src": f"{{task:correct-{i+1}}}", "out_dir": "{out}", "look": look, "intensity": 0.85}, deps=[f"correct-{i+1}"])
        enh_ids.append(f"grade-{i+1}")
    _t(pr, "intro", "intro-outro", "مقدمة الشعار", "motion.intro",
       {"out_dir": "{out}", "name": brand, "tagline": tagline, "logo": f"{raw}/{logo}" if logo else None,
        "duration": 3.5, "width": width, "height": height}, deps=["style"])
    _t(pr, "outro", "intro-outro", "خاتمة واشتراك", "motion.render",
       {"spec": {"width": width, "height": height, "duration": 4.5,
                 "scenes": [{"start": 0, "end": 4.5, "template": "cta", "params": {"text": tagline or brand, "button": "⬇ حمّل مجاناً"}}]},
        "out_dir": "{out}", "name": "outro.mp4"}, deps=["style"])
    if gfx:
        _t(pr, "gfx", "motion-designer", "مشاهد الموشن جرافيك", "motion.render",
           {"spec": {"width": width, "height": height, **gfx}, "out_dir": "{out}", "name": "gfx.mp4"}, deps=["style"],
           review_by="creative-director")
    _t(pr, "logo3d", "animator", "شعار ثلاثي الأبعاد", "three_d.text_3d",
       {"text": brand, "out_dir": "{out}", "duration": 2.5, "width": 1280, "height": 720, "samples": 8}, deps=["style"])
    _t(pr, "music", "sound-designer", "موسيقى خلفية", "audio.music_bed", {"duration": 120, "out_dir": "{out}"})
    _t(pr, "sfx-lib", "sound-designer", "مكتبة مؤثرات", "audio.sfx_library", {"out_dir": "{out}"})
    _t(pr, "assemble", "commercial-editor", "تجميع الإعلان على طول التعليق", "edit.auto_assemble",
       {"body_clips": [f"{{task:{x}}}" for x in enh_ids] + ["{task:logo3d}"], "target_duration": "@dur:{task:vo}",
        "out_dir": "{out}", "intro": "{task:intro}", "outro": "{task:outro}", "gfx": "{task:gfx}" if gfx else None,
        "width": width, "height": height},
       deps=enh_ids + ["intro", "outro", "logo3d", "vo"] + (["gfx"] if gfx else []))
    _t(pr, "edit", "lead-editor", "رندر المونتاج", "edit.render", {"timeline": "{task:assemble}", "out_dir": "{out}"},
       deps=["assemble"])
    _t(pr, "nle-export", "lead-editor", "مشروع قابل للتعديل (Premiere/Resolve XML + EDL)", "edit.export_project",
       {"timeline": "{task:assemble}", "out_dir": "{out}", "name": brand or "project"}, deps=["assemble"])
    _t(pr, "captions", "lead-editor", "ترجمة كاريوكي (طبقة شفافة RTL)", "captions.render_overlay",
       {"timeline_json": "@shift:{task:vo-align}:3.5", "out_dir": "{out}", "width": width, "height": height}, deps=["vo-align"])
    _t(pr, "mix", "sound-engineer", "المكس النهائي", "audio.mix",
       {"voice": "@pad:{task:vo}:3.5", "out_dir": "{out}", "music": "{task:music}", "events": "@cuts:{task:edit}",
        "sfx_dir": "{task:sfx-lib}"}, deps=["vo", "music", "sfx-lib", "edit"])
    _t(pr, "conform", "lead-editor", "النسخة النهائية (صورة+صوت+ترجمة)", "edit.finish",
       {"video": "{task:edit}", "out_dir": "{out}", "audio": "{task:mix}", "subtitles": "{task:captions}"},
       deps=["edit", "mix", "captions"], review_by="creative-director")
    _t(pr, "export-main", "encoding-engineer", "تصدير المنصات الأفقية", "encode.export_many",
       {"src": "{task:conform}", "out_dir": "{out}", "presets": [p for p in presets if p not in ("youtube_shorts", "tiktok", "instagram_reel")] or ["youtube_1080p"],
        "name": "final"}, deps=["conform"])
    vertical = [p for p in presets if p in ("youtube_shorts", "tiktok", "instagram_reel")]
    deliver_files = ["{task:export-main}"]
    qc_files, qc_presets = ["{task:export-main}"], [next(p for p in presets if p not in vertical)]
    if vertical:
        _t(pr, "vertical", "social-editor", "نسخة عمودية 9:16 (من المونتاج النظيف)", "edit.reframe",
           {"src": "{task:edit}", "out_dir": "{out}"}, deps=["edit"])
        _t(pr, "captions-vertical", "social-editor", "ترجمة مقاس العمودي", "captions.render_overlay",
           {"timeline_json": "@shift:{task:vo-align}:3.5", "out_dir": "{out}", "width": 1080, "height": 1920, "max_words": 4},
           deps=["vo-align"])
        _t(pr, "conform-vertical", "social-editor", "العمودي النهائي", "edit.finish",
           {"video": "{task:vertical}", "out_dir": "{out}", "audio": "{task:mix}", "subtitles": "{task:captions-vertical}"},
           deps=["vertical", "mix", "captions-vertical"])
        _t(pr, "export-vertical", "encoding-engineer", "تصدير العمودي", "encode.export",
           {"src": "{task:conform-vertical}", "out_dir": "{out}", "preset": vertical[0], "name": "final"}, deps=["conform-vertical"])
        deliver_files.append("{task:export-vertical}")
        qc_files.append("{task:export-vertical}")
        qc_presets.append(vertical[0])
    _t(pr, "thumbnail", "thumbnail-designer", "صورتين مصغّرتين A/B", "thumbnail.ab_set",
       {"video": "{task:conform}", "out_dir": "{out}", "title": brand, "highlight": tagline[:18] if tagline else ""}, deps=["conform"])
    _t(pr, "qc", "quality-control", "فحص الجودة النهائي", "qc.check_many",
       {"files": qc_files, "out_dir": "{out}", "presets": qc_presets},
       deps=["export-main"] + (["export-vertical"] if vertical else []))
    _t(pr, "deliver", "executive-producer", "الاعتماد والتسليم", "project.deliver",
       {"project_path": "{project}", "files": deliver_files + ["{task:thumbnail}", "{task:nle-export}", "{task:qc}"],
        "out_dir": "{out}", "notes": f"تسليم {brand}"}, deps=["qc", "thumbnail", "nle-export"])
    return pr


def short_from_long(pr: Project, source, starts_ends, preset="youtube_shorts"):
    """Clip several shorts from a long video, caption them and export vertical."""
    _t(pr, "transcript", "voice-over", "تفريغ الفيديو الطويل", "captions.transcribe", {"media": f"{{raw}}/{source}", "out_dir": "{out}"})
    for i, (a, b) in enumerate(starts_ends, 1):
        _t(pr, f"clip-{i}", "shortlong-editor", f"قص المقطع {i}", "edit.clip", {"src": f"{{raw}}/{source}", "out_dir": "{out}", "start": a, "end": b})
        _t(pr, f"vert-{i}", "social-editor", f"عمودي {i}", "edit.reframe", {"src": f"{{task:clip-{i}}}", "out_dir": "{out}"}, deps=[f"clip-{i}"])
        _t(pr, f"exp-{i}", "encoding-engineer", f"تصدير {i}", "encode.export", {"src": f"{{task:vert-{i}}}", "out_dir": "{out}", "preset": preset}, deps=[f"vert-{i}"])
        _t(pr, f"qc-{i}", "quality-control", f"QC {i}", "qc.check", {"path": f"{{task:exp-{i}}}", "preset": preset, "out_dir": "{out}"}, deps=[f"exp-{i}"])
    return pr


TEMPLATES = {"promo": promo, "short_from_long": short_from_long}
