#!/usr/bin/env bash
# AI Studio — one-time setup for a fresh machine/session. Safe to re-run (idempotent).
#   bash bootstrap.sh            # core (editing, colour, audio, motion, QC, captions, TTS)
#   bash bootstrap.sh --with-3d  # + Blender for 3D
set -euo pipefail
cd "$(dirname "$0")"
say(){ printf '\033[1;32m[AI Studio]\033[0m %s\n' "$*"; }

command -v ffmpeg >/dev/null || { say "installing ffmpeg"; (apt-get install -y -q ffmpeg || (apt-get update -q && apt-get install -y -q ffmpeg)) >/dev/null; }
if [[ "${1:-}" == "--with-3d" ]] && ! command -v blender >/dev/null; then
  say "installing Blender (3D)"; (apt-get install -y -q blender || (apt-get update -q && apt-get install -y -q blender)) >/dev/null || say "Blender install failed — 3D tasks disabled"
fi
say "python packages"
python3 -m pip install -q -r requirements.txt 2>&1 | grep -vi "warning\|notice" || true
say "fonts (Cairo)"
mkdir -p ~/.fonts && cp -n assets/fonts/*.ttf ~/.fonts/ 2>/dev/null || true
command -v fc-cache >/dev/null && fc-cache -f >/dev/null || true
if ! node -e "require('playwright')" 2>/dev/null; then
  say "playwright (motion graphics / thumbnails renderer)"
  npm install -g playwright >/dev/null 2>&1 && npx playwright install --with-deps chromium >/dev/null 2>&1 || say "playwright missing — motion/thumbnail tasks need it"
fi
say "installing Claude skills (studio + specialist pack) into ~/.claude/skills"
SK="$HOME/.claude/skills"; mkdir -p "$SK"
for d in skills/*/ skills-pack/*/; do
  n=$(basename "$d"); [ "$n" = "_shared-reference" ] && continue
  [ -f "$d/SKILL.md" ] && rm -rf "$SK/$n" && cp -r "$d" "$SK/$n"
done
mkdir -p "$SK/production-studio-orchestrator/reference" && cp skills-pack/_shared-reference/*.md "$SK/production-studio-orchestrator/reference/" 2>/dev/null || true
say "self-check"
python3 -m studio roles >/dev/null && python3 - <<'PY'
import shutil, subprocess
ok = lambda c: "✅" if c else "❌"
node = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode == 0
print(f"  ffmpeg {ok(shutil.which('ffmpeg'))}  playwright {ok(node)}  blender {ok(shutil.which('blender'))}")
for m in ("cv2", "rembg", "faster_whisper", "opentimelineio", "scipy"):
    try:
        __import__(m); print(f"  {m} ✅")
    except Exception:
        print(f"  {m} ❌")
PY
say "ready — try:  python -m studio roles"
