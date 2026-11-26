---
name: studio-vfx
description: VFX and compositing: chroma key, layer compositing, glow/grain/glitch/light-leak effects, letterbox, motion tracking and AI background removal.
---

# studio-vfx

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
VFX and compositing: chroma key, layer compositing, glow/grain/glitch/light-leak effects, letterbox, motion tracking and AI background removal.

## الموظفون المخوّلون
- `vfx-artist` — خبير المؤثرات البصرية VFX
- `compositor` — خبير التركيب البصري Compositing
- `motion-tracker` — متخصص تتبع العناصر وإزالة الخلفيات

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `vfx.key` | `{"fg":"green.mp4","bg":"bg.mp4","out_dir":"work"}` | كروما + despill |
| `vfx.composite` | `{"base":"a.mp4","layer":"logo.png","out_dir":"work","x":"W-w-40","y":"40"}` | تركيب طبقة |
| `vfx.effect` | `{"src":"a.mp4","out_dir":"work","fx":"glow"}` | glow/grain/vignette/glitch/dreamy/old_film/light_leak/sharpen |
| `vfx.stack_effects` | `{"src":"a.mp4","out_dir":"work","fxs":["vignette","grain"]}` | سلسلة مؤثرات |
| `vfx.letterbox` | `{"src":"a.mp4","out_dir":"work","ratio":2.39}` | شريط سينمائي |
| `tracking.track` | `{"src":"a.mp4","out_dir":"work","box":[x,y,w,h]}` | تتبع عنصر (box اختياري) |
| `tracking.attach` | `{"src":"a.mp4","track_json":"track.json","overlay_png":"label.png","out_dir":"work"}` | تثبيت عنصر على المتتبَّع |
| `tracking.remove_bg` | `{"src":"a.mp4","out_dir":"work","bg":"new_bg.jpg"}` | إزالة الخلفية بالذكاء الاصطناعي |
