"""Phase 8 — full-team end-to-end: raw footage + script + logo → finished ad (16:9 + 9:16), QC'd and delivered."""
import json, shutil, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio.cli import main as cli

M = ROOT / "tests" / "media"
proj = ROOT / "projects" / "fastdm-ad"
shutil.rmtree(proj, ignore_errors=True)
t0 = time.time()
cli(["new", "FastDM Ad", "--client", "ورشة AI", "--brief", "إعلان 25-30 ثانية لبرنامج FastDM بنسختين يوتيوب وشورتس",
     "--raw", str(M / "product_demo.mp4"), str(M / "product_race.mp4"), str(M / "dark_cast.mp4"), str(M / "logo.png"),
     str(ROOT / "tests" / "e2e" / "script.md")])
params = {
  "footage": ["product_demo.mp4", "product_race.mp4", "dark_cast.mp4"], "script": "script.md", "logo": "logo.png",
  "brand": "FastDM", "tagline": "حمّل أسرع ببلاش",
  "shots": [{"size": "GFX", "action": "مقدمة الشعار", "dur": 3.5},
            {"size": "SCREEN", "action": "البرنامج والأيقونة العائمة", "dur": 6, "on_screen": "أيقونة عائمة"},
            {"size": "GFX", "action": "أسرع ×2.5 + المميزات", "dur": 8, "vo": "أسرع مرتين ونص"},
            {"size": "SCREEN", "action": "سباق التحميل", "dur": 6},
            {"size": "GFX", "action": "دعوة للتحميل", "dur": 4.5}],
  "gfx": {"duration": 8, "scenes": [
      {"start": 0, "end": 4, "template": "stat", "params": {"label": "أسرع من المتصفح", "value": 2.5, "decimals": 1, "prefix": "×", "caption": "8 اتصالات في نفس الوقت"}},
      {"start": 4, "end": 8, "template": "bullets", "params": {"heading": "ليه FastDM؟", "items": ["تقسيم ذكي للملف", "إيقاف واستكمال", "أيقونة عائمة في كروم"], "gap": 0.5}}]},
  "presets": ["youtube_1080p", "youtube_shorts"], "look": "teal_orange"}
cli(["plan", "fastdm-ad", "promo", "--params", json.dumps(params, ensure_ascii=False)])
cli(["run", "fastdm-ad", "--workers", "4"])
print(f"\nTOTAL {time.time()-t0:.0f}s")
