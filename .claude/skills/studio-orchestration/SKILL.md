---
name: studio-orchestration
description: Run AI Studio productions: create projects, plan task graphs from templates, run them in parallel with retries, review gates, versioning and the inter-agent message board. Use for any video production request handled by the studio team.
---

# studio-orchestration

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Run AI Studio productions: create projects, plan task graphs from templates, run them in parallel with retries, review gates, versioning and the inter-agent message board. Use for any video production request handled by the studio team.

## الموظفون المخوّلون
- `executive-producer` — المدير التنفيذي لاستوديو الإنتاج
- `production-manager` — مدير الإنتاج (تنسيق المهام)

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `project.deliver` | `{"project_path":"projects/x","files":["..."],"out_dir":"work"}` | الاعتماد والتسليم |

## دورة المشروع
```bash
python -m studio new "اسم المشروع" --brief "..." --raw raw1.mp4 logo.png script.md
python -m studio plan <slug> promo --params '{"footage":["raw1.mp4"],"script":"script.md","logo":"logo.png","brand":"X","tagline":"..."}'
python -m studio validate <slug>          # حلقات/تعارض مخرجات/صلاحيات
python -m studio run <slug> --workers 4   # تنفيذ متوازي + إعادة محاولة + حجب التوابع عند الفشل
python -m studio status <slug>            # نسبة الإنجاز
python -m studio retry <slug> <task>      # إعادة مهمة وكل اللي بعدها
python -m studio review <slug> <task> --by creative-director --decision approve|reject --note "..."
python -m studio add-task <slug> <id> --role colorist --title "..." --fn color.grade --args '{...}' --deps a b
```
القوالب: `promo` (إعلان/منتج/تسويق من مواد خام)، `short_from_long` (تقطيع شورتس من فيديو طويل).
المراجع داخل args: `{raw}` `{out}` `{project}` `{task:<id>}` `{task:<id>:<file>}` و`@file:` `@dur:` `@shift:<json>:<sec>` `@pad:<audio>:<sec>` `@cuts:<edit>`.

## توزيع المشروع حسب النوع
| النوع | الفريق الأساسي |
|---|---|
| إعلان تجاري | creative-director, screenwriter, film-director, commercial-editor, motion-designer, color-grader, sound-designer, sound-engineer |
| فيلم/مشهد سينمائي | film-director, cinematographer, cinema-editor, colorist, color-grader, vfx-artist, sound-engineer |
| وثائقي/مقابلة/بودكاست | documentary-editor, voice-over (تفريغ), motion-designer (lower thirds), sound-engineer |
| تعليمي/شرح | educational-editor, motion-designer, voice-over, thumbnail-designer |
| سوشيال/شورتس | social-editor, shortlong-editor, rhythmic-editor, encoding-engineer |
| فيديو موسيقي/أعراس | rhythmic-editor, color-grader, vfx-artist |
| 3D/رسوم متحركة | animator, motion-designer, intro-outro |
وكل مشروع ينتهي بـ: lead-editor → encoding-engineer → quality-control → executive-producer.
