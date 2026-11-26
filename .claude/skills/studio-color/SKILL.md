---
name: studio-color
description: Measured colour correction, shot matching, cinematic grading and .cube LUT generation.
---

# studio-color

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Measured colour correction, shot matching, cinematic grading and .cube LUT generation.

## الموظفون المخوّلون
- `colorist` — خبير تصحيح الألوان Color Correction
- `color-grader` — خبير المعالجة السينمائية للألوان Color Grading

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `color.correct` | `{"src":"clip.mp4","out_dir":"work"}` | تصحيح مقاس بتكرار حتى الهدف (يكتشف تسجيلات الشاشة/الجرافيك ولا يعيد تعريضها) |
| `color.match` | `{"src":"b.mp4","reference":"a.mp4","out_dir":"work"}` | مطابقة لقطة على مرجع |
| `color.grade` | `{"src":"clip.mp4","out_dir":"work","look":"teal_orange","intensity":0.85}` | Look سينمائي |
| `color.make_lut` | `{"look":"film","out_dir":"work"}` | ملف LUT ‎.cube (teal_orange, film, noir, warm, cool, vivid, bleach_bypass) |
