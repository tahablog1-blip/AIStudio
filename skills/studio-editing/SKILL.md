---
name: studio-editing
description: Executable video editing: timeline render with transitions/speed/Ken Burns/overlays, auto-assembly, silence cutting, reframing to vertical, beat-sync cutting, captions, and Premiere/Resolve XML/EDL export.
---

# studio-editing

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Executable video editing: timeline render with transitions/speed/Ken Burns/overlays, auto-assembly, silence cutting, reframing to vertical, beat-sync cutting, captions, and Premiere/Resolve XML/EDL export.

## الموظفون المخوّلون
- `lead-editor` — المونتير الرئيسي
- `cinema-editor` — مونتير الأفلام السينمائية
- `commercial-editor` — مونتير الإعلانات التجارية
- `documentary-editor` — مونتير الفيديوهات الوثائقية
- `educational-editor` — مونتير الفيديوهات التعليمية
- `marketing-editor` — مونتير المحتوى التسويقي
- `social-editor` — مونتير منصات التواصل
- `shortlong-editor` — مونتير الفيديوهات القصيرة والطويلة
- `rhythmic-editor` — متخصص المونتاج السريع والإيقاعي

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `edit.render` | `{"timeline":"work/timeline.json","out_dir":"work/edit"}` | رندر timeline (قص، انتقالات xfade، سرعة، Ken Burns، طبقات، صوت، LUT، letterbox، ترجمة) |
| `edit.auto_assemble` | `{"body_clips":["a.mp4","b.mp4"],"target_duration":25,"out_dir":"work","intro":"intro.mp4","outro":"outro.mp4"}` | يبني timeline يغطي مدة التعليق |
| `edit.cut_silence` | `{"src":"raw/talk.mp4","out_dir":"work"}` | قص الصمت |
| `edit.reframe` | `{"src":"edit.mp4","out_dir":"work","track":"track.json"}` | أفقي → عمودي: fit_blur (افتراضي، يحافظ على النصوص) أو crop أو يتبع عنصراً |
| `edit.zoom_region` | `{"src":"screen.mp4","out_dir":"work","x":600,"y":120,"w":640,"h":360,"start":2,"end":6}` | تكبير منطقة في الشرح |
| `edit.clip` | `{"src":"long.mp4","out_dir":"work","start":30,"end":75}` | قص مقطع |
| `edit.finish` | `{"video":"edit.mp4","out_dir":"work","audio":"mix.wav","subtitles":"captions.ass"}` | دمج الصورة والمكس والترجمة |
| `edit.export_project` | `{"timeline":"work/timeline.json","out_dir":"work","name":"ad"}` | مشروع FCP7 XML + EDL + OTIO يفتح في Premiere/Resolve |
| `rhythm.beats` | `{"audio":"music.wav","out_dir":"work"}` | BPM وشبكة النبض |
| `rhythm.beat_cut_timeline` | `{"beats_json":"beats.json","sources":["a.mp4","b.mp4"],"out_dir":"work","every":2}` | timeline بقطع على الإيقاع |
| `captions.transcribe` | `{"media":"talk.mp4","out_dir":"work"}` | تفريغ بالتوقيت (Whisper) |
| `captions.render_overlay` | `{"timeline_json":"timeline.json","out_dir":"work","width":1920,"height":1080}` | ترجمة كاريوكي كطبقة شفافة (ترتيب عربي صحيح دائماً) — الافتراضي للحرق |
| `captions.to_ass` | `{"timeline_json":"timeline.json","out_dir":"work","width":1920,"height":1080,"style":"karaoke"}` | ترجمة كاريوكي ASS بخط Cairo |
| `captions.to_srt` | `{"timeline_json":"timeline.json","out_dir":"work"}` | ملف SRT |
| `captions.burn` | `{"video":"v.mp4","subs":"captions.ass","out_dir":"work"}` | حرق الترجمة |

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
