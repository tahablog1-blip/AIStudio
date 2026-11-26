"""Generate the 31 agent files (Claude Code sub-agents) and the installable skills from studio/roles.py.

Outputs (both layouts, so the studio works as a project folder AND as a Claude Code plugin):
  .claude/agents/<role>.md, .claude/skills/<skill>/SKILL.md      (project-level)
  agents/<role>.md, skills/<skill>/SKILL.md, .claude-plugin/plugin.json  (plugin)
  docs/roles/<role>.md  (human-readable employee file)
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio.roles import DEPTS, EXTERNAL, ROLES  # noqa

FN_DOCS = {
    "analyze": [("analyze.report", '{"path":"raw/clip.mp4","out":"work/camera_report.json"}', "تقرير تقني + ملاحظات موجهة للأقسام"),
                ("analyze.analyze_folder", '{"folder":"raw","out":"work/camera_report.json"}', "تقرير لكل ملفات المجلد"),
                ("analyze.scenes", '{"path":"raw/clip.mp4","threshold":0.3}', "أزمنة القطعات/تغير المشاهد")],
    "edit": [("edit.render", '{"timeline":"work/timeline.json","out_dir":"work/edit"}', "رندر timeline (قص، انتقالات xfade، سرعة، Ken Burns، طبقات، صوت، LUT، letterbox، ترجمة)"),
             ("edit.auto_assemble", '{"body_clips":["a.mp4","b.mp4"],"target_duration":25,"out_dir":"work","intro":"intro.mp4","outro":"outro.mp4"}', "يبني timeline يغطي مدة التعليق"),
             ("edit.cut_silence", '{"src":"raw/talk.mp4","out_dir":"work"}', "قص الصمت"),
             ("edit.reframe", '{"src":"edit.mp4","out_dir":"work","track":"track.json"}', "أفقي → عمودي: fit_blur (افتراضي، يحافظ على النصوص) أو crop أو يتبع عنصراً"),
             ("edit.zoom_region", '{"src":"screen.mp4","out_dir":"work","x":600,"y":120,"w":640,"h":360,"start":2,"end":6}', "تكبير منطقة في الشرح"),
             ("edit.clip", '{"src":"long.mp4","out_dir":"work","start":30,"end":75}', "قص مقطع"),
             ("edit.finish", '{"video":"edit.mp4","out_dir":"work","audio":"mix.wav","subtitles":"captions.ass"}', "دمج الصورة والمكس والترجمة"),
             ("edit.export_project", '{"timeline":"work/timeline.json","out_dir":"work","name":"ad"}', "مشروع FCP7 XML + EDL + OTIO يفتح في Premiere/Resolve")],
    "rhythm": [("rhythm.beats", '{"audio":"music.wav","out_dir":"work"}', "BPM وشبكة النبض"),
               ("rhythm.beat_cut_timeline", '{"beats_json":"beats.json","sources":["a.mp4","b.mp4"],"out_dir":"work","every":2}', "timeline بقطع على الإيقاع")],
    "captions": [("captions.transcribe", '{"media":"talk.mp4","out_dir":"work"}', "تفريغ بالتوقيت (Whisper)"),
                 ("captions.render_overlay", '{"timeline_json":"timeline.json","out_dir":"work","width":1920,"height":1080}', "ترجمة كاريوكي كطبقة شفافة (ترتيب عربي صحيح دائماً) — الافتراضي للحرق"),
                 ("captions.to_ass", '{"timeline_json":"timeline.json","out_dir":"work","width":1920,"height":1080,"style":"karaoke"}', "ترجمة كاريوكي ASS بخط Cairo"),
                 ("captions.to_srt", '{"timeline_json":"timeline.json","out_dir":"work"}', "ملف SRT"),
                 ("captions.burn", '{"video":"v.mp4","subs":"captions.ass","out_dir":"work"}', "حرق الترجمة")],
    "motion": [("motion.render", '{"spec":"spec.json","out_dir":"work"}', "مشاهد متحركة: title/lower_third/kinetic/bullets/stat/compare/cta/logo_reveal/end_screen/html"),
               ("motion.title_card", '{"out_dir":"work","title":"العنوان","subtitle":"","highlight":"مجاني"}', "عنوان متحرك"),
               ("motion.lower_third", '{"out_dir":"work","name":"الاسم","role":"الوظيفة"}', "Lower third بشفافية (ProRes 4444)"),
               ("motion.intro", '{"out_dir":"work","name":"القناة","tagline":"","logo":"raw/logo.png"}', "مقدمة بالشعار"),
               ("motion.outro", '{"out_dir":"work","duration":20}', "شاشة نهاية يوتيوب")],
    "three_d": [("three_d.text_3d", '{"text":"BRAND","out_dir":"work","duration":3}', "نص/شعار 3D بـ Blender Cycles (لاتيني)")],
    "color": [("color.correct", '{"src":"clip.mp4","out_dir":"work"}', "تصحيح مقاس بتكرار حتى الهدف (يكتشف تسجيلات الشاشة/الجرافيك ولا يعيد تعريضها)"),
              ("color.match", '{"src":"b.mp4","reference":"a.mp4","out_dir":"work"}', "مطابقة لقطة على مرجع"),
              ("color.grade", '{"src":"clip.mp4","out_dir":"work","look":"teal_orange","intensity":0.85}', "Look سينمائي"),
              ("color.make_lut", '{"look":"film","out_dir":"work"}', "ملف LUT ‎.cube (teal_orange, film, noir, warm, cool, vivid, bleach_bypass)")],
    "vfx": [("vfx.key", '{"fg":"green.mp4","bg":"bg.mp4","out_dir":"work"}', "كروما + despill"),
            ("vfx.composite", '{"base":"a.mp4","layer":"logo.png","out_dir":"work","x":"W-w-40","y":"40"}', "تركيب طبقة"),
            ("vfx.effect", '{"src":"a.mp4","out_dir":"work","fx":"glow"}', "glow/grain/vignette/glitch/dreamy/old_film/light_leak/sharpen"),
            ("vfx.stack_effects", '{"src":"a.mp4","out_dir":"work","fxs":["vignette","grain"]}', "سلسلة مؤثرات"),
            ("vfx.letterbox", '{"src":"a.mp4","out_dir":"work","ratio":2.39}', "شريط سينمائي")],
    "tracking": [("tracking.track", '{"src":"a.mp4","out_dir":"work","box":[x,y,w,h]}', "تتبع عنصر (box اختياري)"),
                 ("tracking.attach", '{"src":"a.mp4","track_json":"track.json","overlay_png":"label.png","out_dir":"work"}', "تثبيت عنصر على المتتبَّع"),
                 ("tracking.remove_bg", '{"src":"a.mp4","out_dir":"work","bg":"new_bg.jpg"}', "إزالة الخلفية بالذكاء الاصطناعي")],
    "audio": [("audio.cleanup", '{"src":"voice.wav","out_dir":"work"}', "تنظيف حوار"),
              ("audio.mix", '{"voice":"vo.wav","out_dir":"work","music":"music.wav","events":[[1.2,"whoosh"]]}', "مكس مع ducking وتطبيع ‎-14 LUFS"),
              ("audio.sfx_library", '{"out_dir":"work"}', "مكتبة مؤثرات مخلّقة"),
              ("audio.music_bed", '{"duration":60,"out_dir":"work"}', "موسيقى خلفية بلا حقوق"),
              ("audio.mux", '{"video":"v.mp4","audio":"mix.wav","out_dir":"work"}', "دمج")],
    "voice": [("voice.tts", '{"text":"النص","out_dir":"work"}', "تعليق Piper محلي (عربي/إنجليزي)"),
              ("voice.align", '{"audio":"vo.mp3","script_text":"النص","out_dir":"work"}', "توقيت كل كلمة لأي تعليق (ElevenLabs/بشري)")],
    "enhance": [("enhance.stabilize", '{"src":"shaky.mp4","out_dir":"work"}', "تثبيت vidstab"),
                ("enhance.denoise", '{"src":"a.mp4","out_dir":"work","strength":"medium"}', "إزالة ضوضاء"),
                ("enhance.upscale", '{"src":"a.mp4","out_dir":"work","height":2160}', "رفع دقة"),
                ("enhance.deinterlace", '{"src":"a.mp4","out_dir":"work"}', "إزالة التداخل"),
                ("enhance.interpolate", '{"src":"a.mp4","out_dir":"work","fps":60}', "مضاعفة الفريمات"),
                ("enhance.restore", '{"src":"old.mp4","out_dir":"work"}', "سلسلة ترميم كاملة")],
    "thumbnail": [("thumbnail.best_frames", '{"video":"v.mp4","out_dir":"work","n":3}', "أفضل فريمات"),
                  ("thumbnail.design", '{"out_dir":"work","title":"العنوان","highlight":"ببلاش","image":"frame.jpg","size":"youtube"}', "تصميم صورة مصغّرة"),
                  ("thumbnail.ab_set", '{"video":"v.mp4","out_dir":"work","title":"العنوان"}', "نسختين A/B")],
    "encode": [("encode.export", '{"src":"final.mp4","out_dir":"deliver","preset":"youtube_1080p"}', "presets: youtube_1080p, youtube_4k, youtube_shorts, tiktok, instagram_reel, instagram_feed, facebook_square, x_twitter, broadcast_master, web_small"),
               ("encode.export_many", '{"src":"final.mp4","out_dir":"deliver","presets":["youtube_1080p","tiktok"]}', "عدة منصات")],
    "qc": [("qc.check", '{"path":"final.mp4","preset":"youtube_1080p","out_dir":"work"}', "تقرير QC + بوابة نجاح/فشل"),
           ("qc.check_many", '{"files":["a.mp4","b.mp4"],"presets":["youtube_1080p","youtube_shorts"],"out_dir":"work"}', "QC لعدة ملفات")],
    "storyboard": [("storyboard.style_guide", '{"out_dir":"work","name":"Brand"}', "دليل أسلوب"),
                   ("storyboard.write_shotlist", '{"shots":[{"size":"WS","action":"...","dur":3}],"out_dir":"work"}', "قائمة لقطات (ECU/CU/MS/WS/EWS/OTS/POV/INSERT/SCREEN/GFX)"),
                   ("storyboard.sheet", '{"shotlist_json":"shotlist.json","out_dir":"work"}', "لوحة ستوري بورد PNG"),
                   ("storyboard.animatic", '{"shotlist_json":"shotlist.json","out_dir":"work"}', "أنيماتيك")],
    "script": [("script.prepare_vo", '{"script_path":"raw/script.md","out_dir":"work"}', "نص TTS نظيف + فحص"),
               ("script.check", '{"text":"..."}', "فحص الطول والخطاف"),
               ("script.scaffold", '{"structure":"ad_30","out_dir":"work"}', "قالب مؤقّت: ad_30, ad_15, explainer, documentary, tutorial, short")],
    "project": [("project.deliver", '{"project_path":"projects/x","files":["..."],"out_dir":"work"}', "الاعتماد والتسليم")],
    "pipelines": [],
}

SKILLS = {
    "studio-orchestration": ("Run AI Studio productions: create projects, plan task graphs from templates, run them in parallel with retries, review gates, versioning and the inter-agent message board. Use for any video production request handled by the studio team.",
                             ["project", "pipelines"]),
    "studio-creative-direction": ("Creative direction for AI Studio: brief, style guide (colours, font, tone, pacing), and structured review notes.", ["storyboard"]),
    "studio-preproduction": ("Scripts, TTS-ready voice-over text, shot lists and storyboards/animatics for AI Studio productions.", ["script", "storyboard"]),
    "studio-media-analysis": ("Technical analysis of raw footage/audio (exposure, colour cast, noise, resolution, interlacing, loudness, silences, scene cuts).", ["analyze"]),
    "studio-editing": ("Executable video editing: timeline render with transitions/speed/Ken Burns/overlays, auto-assembly, silence cutting, reframing to vertical, beat-sync cutting, captions, and Premiere/Resolve XML/EDL export.", ["edit", "rhythm", "captions"]),
    "studio-vfx": ("VFX and compositing: chroma key, layer compositing, glow/grain/glitch/light-leak effects, letterbox, motion tracking and AI background removal.", ["vfx", "tracking"]),
    "studio-motion": ("Motion graphics, kinetic typography, lower thirds (alpha), intros/outros and animated explainer scenes rendered frame-accurately.", ["motion"]),
    "studio-3d": ("3D text/logo animation with headless Blender 4.0 (Cycles).", ["three_d"]),
    "studio-thumbnail": ("Thumbnail and cover design with automatic best-frame selection and A/B variants.", ["thumbnail"]),
    "studio-color": ("Measured colour correction, shot matching, cinematic grading and .cube LUT generation.", ["color"]),
    "studio-audio": ("Dialogue cleanup, voice-over (Piper TTS / alignment of ElevenLabs or human VO), SFX design, music beds and loudness-correct mixing with ducking.", ["audio", "voice"]),
    "studio-enhance": ("Video enhancement: stabilisation, denoise, upscale, deinterlace, frame interpolation, restoration.", ["enhance"]),
    "studio-delivery": ("Platform-correct encoding (YouTube, Shorts, TikTok, Instagram, Facebook, X, broadcast ProRes master).", ["encode"]),
    "studio-qc": ("Automated broadcast/platform QC with pass/fail gate and report.", ["qc"]),
}

HEADER = """> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.
"""


def fn_table(mods):
    rows = ["| الأداة | مثال args | الوظيفة |", "|---|---|---|"]
    for m in mods:
        for fn, ex, desc in FN_DOCS.get(m, []):
            rows.append(f"| `{fn}` | `{ex}` | {desc} |")
    return "\n".join(rows)


def agent_md(r):
    collab = ", ".join(f"`{c}`" for c in r["collaborates"])
    ext = "\n".join(f"- {EXTERNAL[e]}" for e in r["external"] if e in EXTERNAL) or "- لا يوجد"
    desc = (f"{r['en']} ({r['ar']}) of the AI Studio. Use for: " + "; ".join(r["tasks"][:3]) +
            ". Executes real work with the studio toolkit, not advice.")
    return f"""---
name: {r['id']}
description: {desc}
tools: Bash, Read, Write, Edit, Glob, Grep
---

# {r['ar']} — {r['en']}

أنت **{r['ar']}** في «AI Studio»، قسم **{DEPTS[r['dept']]}**{f"، وتتبع `{r['reports_to']}`" if r['reports_to'] else ""}.
وظيفتك **التنفيذ الفعلي** بأدوات الاستوديو وتسليم ملفات، مش الشرح.

{HEADER}
## المسؤوليات
{chr(10).join('- ' + x for x in r['responsibilities'])}

## الخبرات
{chr(10).join('- ' + x for x in r['expertise'])}

## المهارات الفنية
{chr(10).join('- ' + x for x in r['skills'])}

## أدواتك المتاحة فعلاً (صلاحياتك: {', '.join('`'+m+'`' for m in r['modules'])})
{fn_table(r['modules'])}

مهارات Claude المرتبطة: {', '.join('`'+s+'`' for s in r['skill_dirs'])}

## أدوات الصناعة غير المتاحة هنا (قل ذلك بصراحة للعميل)
{ext}

## المهام اللي بتنفّذها
{chr(10).join('- ' + x for x in r['tasks'])}

## المدخلات المطلوبة
{chr(10).join('- ' + x for x in r['inputs'])}

## المخرجات المتوقعة
{chr(10).join('- ' + x for x in r['outputs'])}

## الصلاحيات
- **مسموح:** {'، '.join(r['can'])}
- **ممنوع:** {'، '.join(r['cannot'])}
- ممنوع تشغيل أدوات خارج: {', '.join(r['modules'])}

## التعاون
بتشتغل مع: {collab}

## بروتوكول العمل
1. اقرأ مهمتك من `projects/<p>/manifest.json` ورسائلك: `python -m studio inbox <p> --role {r['id']}`.
2. **حلّل المدخلات قبل التنفيذ** (`analyze.report` لو عندك صلاحية، أو `ffprobe`).
3. نفّذ بأدواتك، والمخرج دايماً في `{{out}}` = `work/<task>/vNNN` — **ممنوع الكتابة فوق إصدار سابق**.
4. **افحص مخرجك بنفسك** (مدة، أبعاد، قياس) قبل التسليم؛ لو فيه عيب صلّحه أو أعد المحاولة.
5. سلّم برسالة: `python -m studio post <p> --from {r['id']} --to <المستلم> "<ملخص + مسار الملف>"`.
6. لو المهمة محتاجة أداة مش متاحة: ابعت للمدير التنفيذي بالبديل المقترح، ومتدّعيش إنك نفذت.
"""


def human_md(r):
    return agent_md(r).split("---\n", 2)[2]


def skill_md(name, desc, mods):
    roles = [r for r in ROLES.values() if name in r["skill_dirs"]]
    body = f"""---
name: {name}
description: {desc}
---

# {name}

{HEADER}
## متى تُستخدم
{desc}

## الموظفون المخوّلون
{chr(10).join(f"- `{r['id']}` — {r['ar']}" for r in roles)}

## الأدوات
{fn_table(mods)}
"""
    extra = {
        "studio-orchestration": """
## دورة المشروع
```bash
python -m studio new "اسم المشروع" --brief "..." --raw raw1.mp4 logo.png script.md
python -m studio plan <slug> promo --params '{"footage":["raw1.mp4"],"script":"script.md","logo":"logo.png","brand":"X","tagline":"..."}'
python -m studio validate <slug>          # حلقات/تعارض مخرجات/صلاحيات
python -m studio run <slug> --workers 4   # تنفيذ متوازي + إعادة محاولة + حجب التوابع عند الفشل
python -m studio status <slug>            # نسبة الإنجاز
python -m studio retry <slug> <task>      # إعادة مهمة وكل اللي بعدها
python -m studio review <slug> <task> --by creative-director --decision approve|reject --note "..."
python -m studio add-task <slug> <id> --role colorist --title "..." --fn color.grade --args '{...}' --deps a b
```
القوالب: `promo` (إعلان/منتج/تسويق من مواد خام)، `short_from_long` (تقطيع شورتس من فيديو طويل).
المراجع داخل args: `{raw}` `{out}` `{project}` `{task:<id>}` `{task:<id>:<file>}` و`@file:` `@dur:` `@shift:<json>:<sec>` `@pad:<audio>:<sec>` `@cuts:<edit>`.

## توزيع المشروع حسب النوع
| النوع | الفريق الأساسي |
|---|---|
| إعلان تجاري | creative-director, screenwriter, film-director, commercial-editor, motion-designer, color-grader, sound-designer, sound-engineer |
| فيلم/مشهد سينمائي | film-director, cinematographer, cinema-editor, colorist, color-grader, vfx-artist, sound-engineer |
| وثائقي/مقابلة/بودكاست | documentary-editor, voice-over (تفريغ), motion-designer (lower thirds), sound-engineer |
| تعليمي/شرح | educational-editor, motion-designer, voice-over, thumbnail-designer |
| سوشيال/شورتس | social-editor, shortlong-editor, rhythmic-editor, encoding-engineer |
| فيديو موسيقي/أعراس | rhythmic-editor, color-grader, vfx-artist |
| 3D/رسوم متحركة | animator, motion-designer, intro-outro |
وكل مشروع ينتهي بـ: lead-editor → encoding-engineer → quality-control → executive-producer.
""",
        "studio-motion": """
## مواصفة المشاهد (spec)
```json
{"width":1920,"height":1080,"fps":30,"duration":9,"transparent":false,
 "style":{"colors":{"bg":"#0b1020","primary":"#a3e635","accent":"#22d3ee"},"dir":"rtl"},
 "scenes":[{"start":0,"end":3,"template":"kinetic","params":{"words":["أسرع","من","المتصفح"]}},
           {"start":3,"end":6,"template":"stat","params":{"label":"السرعة","value":2.5,"decimals":1,"prefix":"×"}},
           {"start":6,"end":9,"template":"bullets","params":{"heading":"المميزات","items":["أ","ب","ج"]}}],
 "captions": null}
```
- `transparent:true` ⇒ ProRes 4444 بقناة ألفا للتركيب فوق الفيديو.
- القالب `html` يقبل HTML حر بعناصر `data-a="pop|stamp|up|down|left|right|fade|spin|count" data-at="ثواني"`.
- المخرج يشمل `sfx_events.json` (توقيتات المؤثرات) لمصمم الصوت.
""",
        "studio-editing": """
## صيغة timeline
```json
{"width":1920,"height":1080,"fps":30,
 "clips":[{"src":"a.mp4","in":0,"out":4,"speed":1.0,"fit":"crop","kenburns":0.05},
          {"src":"b.mp4","in":2,"out":5,"transition":{"type":"slideleft","dur":0.4}}],
 "overlays":[{"src":"lower_third.mov","start":1,"end":5,"x":0,"y":0}],
 "audio":[{"src":"music.wav","start":0,"volume":0.3}],
 "keep_clip_audio":true,"letterbox":2.39,"lut":"look.cube","subtitles":"captions.ass"}
```
الانتقالات: fade, dissolve, wipeleft/right/up/down, slideleft/right/up/down, circleopen/close, radial, smoothleft/right, zoomin, fadeblack, fadewhite, pixelize, hblur, distance, squeezeh/v.
""",
        "studio-qc": """
## معايير القبول
- الأبعاد والفريمات والكوديك = preset المنصة · yuv420p للمنصات · المدة ≤ حد المنصة
- الصوت: ‎-14±2 LUFS (‎-23 للبث) · true peak ≤ ‎-1 dBTP · تزامن الصوت والصورة ≤ 0.25s
- لا فريمات سوداء > 1s · لا تجمّد > 2.5s
الفشل يوقف التسليم ويرجع المهمة للقسم المسؤول عبر `studio retry`.
""",
    }
    return body + extra.get(name, "")


def main():
    for base in (ROOT / ".claude", ROOT):
        ad = base / "agents"
        shutil.rmtree(ad, ignore_errors=True)
        ad.mkdir(parents=True)
        for r in ROLES.values():
            (ad / f"{r['id']}.md").write_text(agent_md(r), encoding="utf-8")
        sd = base / "skills"
        shutil.rmtree(sd, ignore_errors=True)
        for name, (desc, mods) in SKILLS.items():
            (sd / name).mkdir(parents=True)
            (sd / name / "SKILL.md").write_text(skill_md(name, desc, mods), encoding="utf-8")
    hd = ROOT / "docs" / "roles"
    shutil.rmtree(hd, ignore_errors=True)
    hd.mkdir(parents=True)
    for r in ROLES.values():
        (hd / f"{r['id']}.md").write_text(human_md(r), encoding="utf-8")
    (ROOT / ".claude-plugin").mkdir(exist_ok=True)
    json.dump({"name": "ai-studio", "version": "1.0.0",
               "description": "AI video production studio: 31 specialised agents + executable editing/VFX/motion/colour/audio/QC skills",
               "author": {"name": "ورشة AI"}}, open(ROOT / ".claude-plugin" / "plugin.json", "w"), ensure_ascii=False, indent=2)
    print(f"{len(ROLES)} agents, {len(SKILLS)} skills generated")


if __name__ == "__main__":
    main()
