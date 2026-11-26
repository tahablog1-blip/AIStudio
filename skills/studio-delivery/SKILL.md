---
name: studio-delivery
description: Platform-correct encoding (YouTube, Shorts, TikTok, Instagram, Facebook, X, broadcast ProRes master).
---

# studio-delivery

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Platform-correct encoding (YouTube, Shorts, TikTok, Instagram, Facebook, X, broadcast ProRes master).

## الموظفون المخوّلون
- `encoding-engineer` — خبير الضغط والتصدير

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `encode.export` | `{"src":"final.mp4","out_dir":"deliver","preset":"youtube_1080p"}` | presets: youtube_1080p, youtube_4k, youtube_shorts, tiktok, instagram_reel, instagram_feed, facebook_square, x_twitter, broadcast_master, web_small |
| `encode.export_many` | `{"src":"final.mp4","out_dir":"deliver","presets":["youtube_1080p","tiktok"]}` | عدة منصات |
