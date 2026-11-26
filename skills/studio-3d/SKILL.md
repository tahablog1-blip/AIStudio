---
name: studio-3d
description: 3D text/logo animation with headless Blender 4.0 (Cycles).
---

# studio-3d

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
3D text/logo animation with headless Blender 4.0 (Cycles).

## الموظفون المخوّلون
- `animator` — مصمم الرسوم المتحركة

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `three_d.text_3d` | `{"text":"BRAND","out_dir":"work","duration":3}` | نص/شعار 3D بـ Blender Cycles (لاتيني) |
