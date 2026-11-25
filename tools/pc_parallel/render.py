# Coser una prenda en un avatar y guardar frente, lado y espalda.
#   -- FBX PRESET OUT_PREFIX DROP [LENGTH] [SLEEVES]   (FBX "WOMAN"/"MAN" = integrados)
import bpy, sys, math
a = sys.argv[sys.argv.index("--") + 1:]
fbx, preset, out, drop = a[0], a[1], a[2], {d.strip().lower() for d in a[3].split(",")}
length = a[4] if len(a) > 4 else "REGULAR"; sleeves = a[5] if len(a) > 5 else "REGULAR"
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import build
if fbx in ("WOMAN", "MAN"):
    bpy.ops.cd.import_character(figure=fbx)
else:
    bpy.ops.import_scene.fbx(filepath=fbx)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.name.lower() in drop:
            bpy.data.objects.remove(o)
    bpy.context.view_layer.objects.active = None
    bpy.ops.cd.set_avatar()
bpy.ops.cd.add_garment(preset=preset, fit=0.10, length=length, sleeves=sleeves)
bpy.ops.cd.sew()
scn = bpy.context.scene
g = build.garment_object(bpy.context, create=False)
av = scn.cd.avatar
zs = [(av.matrix_world @ v.co).z for v in av.data.vertices]
H = max(zs) - min(zs)
for o in scn.objects:
    if o.type == 'MESH':
        o.hide_render = bool(o.cd.is_pattern) or (o.name.startswith("CD_") and o is not g and o is not av)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam)
cam.data.type = 'ORTHO'; cam.data.ortho_scale = H * 1.12
scn.render.engine = 'BLENDER_WORKBENCH'
scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'OBJECT'
av.color = (0.62, 0.52, 0.48, 1)
if g: g.color = (0.15, 0.3, 0.65, 1)
scn.render.resolution_x = 420; scn.render.resolution_y = 520
for name, ang in (("front", 0), ("side", 90), ("back", 180)):
    r = math.radians(ang)
    cam.location = (H * 3 * math.sin(r), -H * 3 * math.cos(r), min(zs) + H * 0.52)
    cam.rotation_euler = (math.pi / 2, 0, r)
    scn.camera = cam
    scn.render.filepath = "%s_%s.png" % (out, name)
    bpy.ops.render.render(write_still=True)
print("[done]", preset)
