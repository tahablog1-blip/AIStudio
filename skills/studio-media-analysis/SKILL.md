---
name: studio-media-analysis
description: Technical analysis of raw footage/audio (exposure, colour cast, noise, resolution, interlacing, loudness, silences, scene cuts).
---

# studio-media-analysis

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Technical analysis of raw footage/audio (exposure, colour cast, noise, resolution, interlacing, loudness, silences, scene cuts).

## الموظفون المخوّلون
- `cinematographer` — مدير التصوير والإضاءة

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `analyze.report` | `{"path":"raw/clip.mp4","out":"work/camera_report.json"}` | تقرير تقني + ملاحظات موجهة للأقسام |
| `analyze.analyze_folder` | `{"folder":"raw","out":"work/camera_report.json"}` | تقرير لكل ملفات المجلد |
| `analyze.scenes` | `{"path":"raw/clip.mp4","threshold":0.3}` | أزمنة القطعات/تغير المشاهد |
