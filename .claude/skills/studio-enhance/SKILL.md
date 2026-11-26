---
name: studio-enhance
description: Video enhancement: stabilisation, denoise, upscale, deinterlace, frame interpolation, restoration.
---

# studio-enhance

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Video enhancement: stabilisation, denoise, upscale, deinterlace, frame interpolation, restoration.

## الموظفون المخوّلون
- `video-enhancement` — خبير تحسين الجودة ورفع الدقة

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `enhance.stabilize` | `{"src":"shaky.mp4","out_dir":"work"}` | تثبيت vidstab |
| `enhance.denoise` | `{"src":"a.mp4","out_dir":"work","strength":"medium"}` | إزالة ضوضاء |
| `enhance.upscale` | `{"src":"a.mp4","out_dir":"work","height":2160}` | رفع دقة |
| `enhance.deinterlace` | `{"src":"a.mp4","out_dir":"work"}` | إزالة التداخل |
| `enhance.interpolate` | `{"src":"a.mp4","out_dir":"work","fps":60}` | مضاعفة الفريمات |
| `enhance.restore` | `{"src":"old.mp4","out_dir":"work"}` | سلسلة ترميم كاملة |
