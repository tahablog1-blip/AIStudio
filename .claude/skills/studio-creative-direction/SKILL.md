---
name: studio-creative-direction
description: Creative direction for AI Studio: brief, style guide (colours, font, tone, pacing), and structured review notes.
---

# studio-creative-direction

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Creative direction for AI Studio: brief, style guide (colours, font, tone, pacing), and structured review notes.

## الموظفون المخوّلون
- `creative-director` — المخرج الإبداعي

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `storyboard.style_guide` | `{"out_dir":"work","name":"Brand"}` | دليل أسلوب |
| `storyboard.write_shotlist` | `{"shots":[{"size":"WS","action":"...","dur":3}],"out_dir":"work"}` | قائمة لقطات (ECU/CU/MS/WS/EWS/OTS/POV/INSERT/SCREEN/GFX) |
| `storyboard.sheet` | `{"shotlist_json":"shotlist.json","out_dir":"work"}` | لوحة ستوري بورد PNG |
| `storyboard.animatic` | `{"shotlist_json":"shotlist.json","out_dir":"work"}` | أنيماتيك |
