---
name: studio-preproduction
description: Scripts, TTS-ready voice-over text, shot lists and storyboards/animatics for AI Studio productions.
---

# studio-preproduction

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Scripts, TTS-ready voice-over text, shot lists and storyboards/animatics for AI Studio productions.

## الموظفون المخوّلون
- `film-director` — المخرج السينمائي
- `screenwriter` — كاتب السيناريو
- `storyboard-artist` — مصمم الستوري بورد

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `script.prepare_vo` | `{"script_path":"raw/script.md","out_dir":"work"}` | نص TTS نظيف + فحص |
| `script.check` | `{"text":"..."}` | فحص الطول والخطاف |
| `script.scaffold` | `{"structure":"ad_30","out_dir":"work"}` | قالب مؤقّت: ad_30, ad_15, explainer, documentary, tutorial, short |
| `storyboard.style_guide` | `{"out_dir":"work","name":"Brand"}` | دليل أسلوب |
| `storyboard.write_shotlist` | `{"shots":[{"size":"WS","action":"...","dur":3}],"out_dir":"work"}` | قائمة لقطات (ECU/CU/MS/WS/EWS/OTS/POV/INSERT/SCREEN/GFX) |
| `storyboard.sheet` | `{"shotlist_json":"shotlist.json","out_dir":"work"}` | لوحة ستوري بورد PNG |
| `storyboard.animatic` | `{"shotlist_json":"shotlist.json","out_dir":"work"}` | أنيماتيك |
