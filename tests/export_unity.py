# Coser una prenda en un avatar y exportarla como lo hace el add-on (Sew, Finalize,
# Export Selected: fbx + .opensew.json + máscara del cuerpo), para probarla en Unity.
#
#   blender -b --python tests/export_unity.py -- FBX PRESET OUT.fbx DROP [LENGTH] [SLEEVES]
#
# FBX "WOMAN"/"MAN" = integrados. DROP: nombres de mallas del avatar a quitar,
# separados por comas. OUT.fbx: ruta del FBX (el json y la máscara van al lado,
# con el mismo nombre); el nombre empieza por el avatar (TheBeast_TANK.fbx), que
# es lo que usa la prueba de Unity para elegir el prefab.
import bpy, sys, os, json

a = sys.argv[sys.argv.index("--") + 1:]
fbx, preset, out = a[0], a[1].upper(), os.path.abspath(a[2])
drop = {d.strip().lower() for d in (a[3] if len(a) > 3 else "").split(",") if d.strip()}
length = a[4] if len(a) > 4 else "REGULAR"
sleeves = a[5] if len(a) > 5 else "REGULAR"
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg, flush=True)
    if not cond:
        fails.append(msg)


bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.preferences.addon_enable(module="clothing_design")
import clothing_design
from clothing_design import export, build
print("add-on:", clothing_design.__file__)
if fbx in ("WOMAN", "MAN"):
    bpy.ops.cd.import_character(figure=fbx)
else:
    bpy.ops.import_scene.fbx(filepath=fbx)
    gone = []
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.name.lower() in drop:
            gone.append(o.name)
            bpy.data.objects.remove(o)
    print("quitadas:", gone)
bpy.context.view_layer.objects.active = None
bpy.ops.cd.set_avatar()
ctx = bpy.context
print("avatar:", ctx.scene.cd.avatar.name if ctx.scene.cd.avatar else None)
bpy.ops.cd.add_garment(preset=preset, fit=0.10, length=length, sleeves=sleeves)
r = bpy.ops.cd.sew()
check(r == {'FINISHED'}, "sewn (%s)" % r)
r = bpy.ops.cd.finalize()
check(r == {'FINISHED'}, "finalized (%s)" % r)
g = export.finished_garments(ctx)
check(len(g) == 1, "una prenda terminada (%d)" % len(g))
os.makedirs(os.path.dirname(out), exist_ok=True)
# Export Selected: the garment selected in the list, scene export settings
r = bpy.ops.cd.export_vrchat('EXEC_DEFAULT', filepath=out, only_active=True)
check(r == {'FINISHED'}, "Export Selected (%s)" % r)
meta = out[:-4] + ".opensew.json"
check(os.path.exists(out) and os.path.getsize(out) > 10000, "FBX escrito (%s, %d bytes)"
      % (out, os.path.getsize(out) if os.path.exists(out) else 0))
check(os.path.exists(meta), "json escrito (%s)" % meta)
if os.path.exists(meta):
    m = json.load(open(meta, encoding="utf-8"))
    print("json:", json.dumps(m, ensure_ascii=False))
    for e in m.get("masks", []):
        p = os.path.join(os.path.dirname(out), e["file"])
        check(os.path.exists(p), "máscara %s" % e["file"])
print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
