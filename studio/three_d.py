"""3D animation with headless Blender 4.0 (Cycles CPU): extruded 3D text / logo turntables."""
import json
from pathlib import Path

from .core import ffmpeg, run

BLENDER_SCRIPT = r"""
import bpy, json, sys, math
cfg = json.loads(sys.argv[sys.argv.index('--') + 1])
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = cfg['samples']; sc.cycles.use_denoising = False
sc.render.resolution_x, sc.render.resolution_y = cfg['width'], cfg['height']
sc.render.fps = cfg['fps']; sc.frame_start = 1; sc.frame_end = int(cfg['duration'] * cfg['fps'])
sc.render.film_transparent = cfg['transparent']
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = cfg['frames'] + '/f_'
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (*cfg['bg'], 1); world.node_tree.nodes['Background'].inputs[1].default_value = 0.6
if cfg.get('font'):
    fnt = bpy.data.fonts.load(cfg['font'])
bpy.ops.object.text_add(location=(0, 0, 0)); t = bpy.context.object
t.data.body = cfg['text']; t.data.extrude = 0.18; t.data.bevel_depth = 0.02; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
if cfg.get('font'): t.data.font = fnt
t.rotation_euler = (math.radians(90), 0, 0)
m = bpy.data.materials.new('m'); m.use_nodes = True
bsdf = m.node_tree.nodes['Principled BSDF']; bsdf.inputs['Base Color'].default_value = (*cfg['color'], 1)
bsdf.inputs['Metallic'].default_value = 0.6; bsdf.inputs['Roughness'].default_value = 0.25
t.data.materials.append(m)
bpy.ops.object.camera_add(location=(0, -9, 0.4), rotation=(math.radians(88), 0, 0)); sc.camera = bpy.context.object
bpy.ops.object.light_add(type='AREA', location=(3, -5, 4)); bpy.context.object.data.energy = 1200; bpy.context.object.data.size = 4
bpy.ops.object.light_add(type='AREA', location=(-4, -3, -1)); bpy.context.object.data.energy = 500; bpy.context.object.data.color = cfg['rim']
n = sc.frame_end
t.rotation_euler[2] = math.radians(-cfg['spin']); t.keyframe_insert('rotation_euler', frame=1)
t.scale = (0.2, 0.2, 0.2); t.keyframe_insert('scale', frame=1)
t.scale = (1, 1, 1); t.keyframe_insert('scale', frame=max(2, int(n * 0.35)))
t.rotation_euler[2] = math.radians(0); t.keyframe_insert('rotation_euler', frame=max(2, int(n * 0.6)))
t.rotation_euler[2] = math.radians(cfg['spin'] * 0.15); t.keyframe_insert('rotation_euler', frame=n)
bpy.ops.render.render(animation=True)
"""


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def text_3d(text, out_dir, duration=3, width=1280, height=720, fps=24, color="#a3e635", bg="#0b1020",
            rim="#22d3ee", spin=120, samples=12, transparent=False, font=None, name="text3d.mp4"):
    """Note: Blender's text object has no Arabic shaping; use Latin text here, Arabic via motion.py."""
    out_dir = Path(out_dir)
    frames = out_dir / "_frames3d"
    frames.mkdir(exist_ok=True)
    cfg = dict(text=text, duration=duration, width=width, height=height, fps=fps, color=_rgb(color), bg=_rgb(bg),
               rim=_rgb(rim), spin=spin, samples=samples, transparent=transparent, frames=str(frames), font=font)
    script = out_dir / "_scene3d.py"
    script.write_text(BLENDER_SCRIPT)
    run(["blender", "-b", "-noaudio", "-P", str(script), "--", json.dumps(cfg)])
    if transparent:
        out = str(out_dir / name.replace(".mp4", ".mov"))
        ffmpeg("-framerate", str(fps), "-i", str(frames / "f_%04d.png"), "-c:v", "prores_ks", "-profile:v", "4444",
               "-pix_fmt", "yuva444p10le", out)
    else:
        out = str(out_dir / name)
        ffmpeg("-framerate", str(fps), "-i", str(frames / "f_%04d.png"), "-c:v", "libx264", "-crf", "18",
               "-pix_fmt", "yuv420p", out)
    return {"output": out}
