---
name: studio-audio
description: Dialogue cleanup, voice-over (Piper TTS / alignment of ElevenLabs or human VO), SFX design, music beds and loudness-correct mixing with ducking.
---

# studio-audio

> نفّذ الأوامر من مجلد الاستوديو: `cd "${AISTUDIO_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
> كل أداة تتشغّل بـ: `python -m studio do <module.function> --role <دورك> --args '<JSON>'` — المنسّق بيرفض أي أداة خارج صلاحياتك.

## متى تُستخدم
Dialogue cleanup, voice-over (Piper TTS / alignment of ElevenLabs or human VO), SFX design, music beds and loudness-correct mixing with ducking.

## الموظفون المخوّلون
- `sound-engineer` — مهندس الصوت
- `sound-designer` — مصمم المؤثرات الصوتية
- `voice-over` — متخصص التعليق الصوتي

## الأدوات
| الأداة | مثال args | الوظيفة |
|---|---|---|
| `audio.cleanup` | `{"src":"voice.wav","out_dir":"work"}` | تنظيف حوار |
| `audio.mix` | `{"voice":"vo.wav","out_dir":"work","music":"music.wav","events":[[1.2,"whoosh"]]}` | مكس مع ducking وتطبيع ‎-14 LUFS |
| `audio.sfx_library` | `{"out_dir":"work"}` | مكتبة مؤثرات مخلّقة |
| `audio.music_bed` | `{"duration":60,"out_dir":"work"}` | موسيقى خلفية بلا حقوق |
| `audio.mux` | `{"video":"v.mp4","audio":"mix.wav","out_dir":"work"}` | دمج |
| `voice.tts` | `{"text":"النص","out_dir":"work"}` | تعليق Piper محلي (عربي/إنجليزي) |
| `voice.align` | `{"audio":"vo.mp3","script_text":"النص","out_dir":"work"}` | توقيت كل كلمة لأي تعليق (ElevenLabs/بشري) |
