---
name: studio-thumbnail
description: Thumbnail and cover design with automatic best-frame selection and A/B variants.
---

# studio-thumbnail

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Thumbnail and cover design with automatic best-frame selection and A/B variants.

## الموظفون المخوّلون
- `thumbnail-designer` — مصمم الأغلفة والصور المصغرة

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `thumbnail.best_frames` | `{"video":"v.mp4","out_dir":"work","n":3}` | أفضل فريمات |
| `thumbnail.design` | `{"out_dir":"work","title":"العنوان","highlight":"ببلاش","image":"frame.jpg","size":"youtube"}` | تصميم صورة مصغّرة |
| `thumbnail.ab_set` | `{"video":"v.mp4","out_dir":"work","title":"العنوان"}` | نسختين A/B |
