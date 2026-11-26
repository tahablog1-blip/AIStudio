---
name: studio-qc
description: Automated broadcast/platform QC with pass/fail gate and report.
---

# studio-qc

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Automated broadcast/platform QC with pass/fail gate and report.

## الموظفون المخوّلون
- `quality-control` — مراقب الجودة النهائي

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `qc.check` | `{"path":"final.mp4","preset":"youtube_1080p","out_dir":"work"}` | تقرير QC + بوابة نجاح/فشل |
| `qc.check_many` | `{"files":["a.mp4","b.mp4"],"presets":["youtube_1080p","youtube_shorts"],"out_dir":"work"}` | QC لعدة ملفات |

## معايير القبول
- الأبعاد والفريمات والكوديك = preset المنصة · yuv420p للمنصات · المدة ≤ حد المنصة
- الصوت: ‎-14±2 LUFS (‎-23 للبث) · true peak ≤ ‎-1 dBTP · تزامن الصوت والصورة ≤ 0.25s
- لا فريمات سوداء > 1s · لا تجمّد > 2.5s
الفشل يوقف التسليم ويرجع المهمة للقسم المسؤول عبر `studio retry`.
