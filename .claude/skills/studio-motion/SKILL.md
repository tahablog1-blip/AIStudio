---
name: studio-motion
description: Motion graphics, kinetic typography, lower thirds (alpha), intros/outros and animated explainer scenes rendered frame-accurately.
---

# studio-motion

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Motion graphics, kinetic typography, lower thirds (alpha), intros/outros and animated explainer scenes rendered frame-accurately.

## الموظفون المخوّلون
- `motion-designer` — مصمم الموشن جرافيك
- `animator` — مصمم الرسوم المتحركة
- `intro-outro` — متخصص المقدمات والخواتيم

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `motion.render` | `{"spec":"spec.json","out_dir":"work"}` | مشاهد متحركة: title/lower_third/kinetic/bullets/stat/compare/cta/logo_reveal/end_screen/html |
| `motion.title_card` | `{"out_dir":"work","title":"العنوان","subtitle":"","highlight":"مجاني"}` | عنوان متحرك |
| `motion.lower_third` | `{"out_dir":"work","name":"الاسم","role":"الوظيفة"}` | Lower third بشفافية (ProRes 4444) |
| `motion.intro` | `{"out_dir":"work","name":"القناة","tagline":"","logo":"raw/logo.png"}` | مقدمة بالشعار |
| `motion.outro` | `{"out_dir":"work","duration":20}` | شاشة نهاية يوتيوب |

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
