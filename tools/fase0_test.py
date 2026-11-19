# Fase 0: prueba headless de OpenSew 2 con un avatar.
#   blender -b --python tools/fase0_test.py -- <ruta.fbx | DEFAULT_WOMAN> <out_dir> [TSHIRT,JACKET]
#   (con el módulo bpy: python tools/fase0_test.py <ruta.fbx> <out_dir>)
#   CD_ZIP=clothing_design.zip lo instala desde el zip, como Install from Disk.
import sys, os, time, json, math, traceback
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
src, out = argv[0], argv[1]
presets = (argv[2] if len(argv) > 2 else "TSHIRT,JACKET").split(",")
os.makedirs(out, exist_ok=True)

# instalar el zip como lo haría Allan
ZIP = os.environ.get("CD_ZIP")
if ZIP:
    bpy.ops.preferences.addon_install(filepath=ZIP, overwrite=True)
bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, build, sim

report = {"src": src, "steps": {}}


def log(k, v):
    print("[fase0]", k, "=>", v, flush=True)
    report["steps"][k] = v


def load_body():
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")
    if src.startswith("DEFAULT_"):
        bpy.ops.cd.import_character(figure=src.split("_")[1])
    else:
        bpy.ops.import_scene.fbx(filepath=src)
    ctx = bpy.context
    meshes = [o for o in ctx.scene.objects if o.type == 'MESH']
    arms = [o for o in ctx.scene.objects if o.type == 'ARMATURE']
    return ctx, meshes, arms


def penetration(ctx, g, tol=0.004):
    bvh = avatar.body_bvh(ctx)
    ev = g.evaluated_get(ctx.evaluated_depsgraph_get())
    inside = 0
    for v in ev.data.vertices:
        p = ev.matrix_world @ v.co
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None and (p - loc).dot(nrm) < -tol:
            inside += 1
    return inside, len(ev.data.vertices)


def set_avatar(ctx, meshes):
    # Set Avatar sin selección: usa auto_avatar, como el botón
    for o in ctx.view_layer.objects:
        o.select_set(False)
    ctx.view_layer.objects.active = None
    r = bpy.ops.cd.set_avatar()
    body = ctx.scene.cd.avatar
    return r, body


# ---------------------------------------------------------------- avatar
ctx, meshes, arms = load_body()
log("objects", {"meshes": [(o.name, len(o.data.vertices), len(o.vertex_groups)) for o in meshes],
                "armatures": [(a.name, len(a.data.bones)) for a in arms]})
if arms:
    log("bones", [b.name for b in arms[0].data.bones])
    log("armature_scale", [list(arms[0].scale), list(arms[0].rotation_euler)])

r, body = set_avatar(ctx, meshes)
log("set_avatar", {"result": list(r), "body": body.name if body else None,
                   "facing": ctx.scene.cd.facing})
m = avatar.measure(ctx, body, force=True)
arm = avatar.find_armature(body)
found = {}
for name, cands in avatar.BONE_TABLE.items():
    b = avatar._find_bone(arm, cands) if arm else None
    found[name] = b.name if b else None
limbs = {}
for name, (ka, kb) in avatar.LIMB_CHAINS.items():
    ba = avatar._find_bone(arm, ka) if arm else None
    bb = avatar._find_bone(arm, kb) if arm else None
    limbs[name] = [ba.name if ba else None, bb.name if bb else None]
ex = sum(1 for g in body.vertex_groups if any(k in g.name.lower() for k in avatar.EXCLUDE_TORSO))
meas = {
    "height_cm": round(m["height"] * 100, 1),
    "chest_cm": round(avatar.girth_at(m, avatar.z_of(m, "chest")) * 100, 1),
    "waist_cm": round(avatar.girth_at(m, avatar.z_of(m, "waist")) * 100, 1),
    "hip_cm": round(avatar.girth_at(m, avatar.z_of(m, "hip")) * 100, 1),
    "neck_cm": round(avatar.neck_girth(m) * 100, 1),
    "figure_auto": m["figure_auto"], "figure_score": round(avatar.figure_score(m), 2),
    "landmarks_from_bones": sorted(m["landmarks"].keys()),
    "landmark_z_pct": {k: round((v - m["zmin"]) / m["height"] * 100, 1) for k, v in m["landmarks"].items()},
    "limbs_measured": sorted(m["limbs"].keys()),
    "bone_table_match": found, "limb_chain_match": limbs,
    "vgroups_masked_from_torso": ex, "vgroups_total": len(body.vertex_groups),
}
log("measure", meas)

# ---------------------------------------------------------------- garments
for preset in presets:
    t0 = time.time()
    res = {}
    try:
        ctx, meshes, arms = load_body()
        set_avatar(ctx, meshes)
        scn = ctx.scene
        bpy.ops.cd.add_garment(preset=preset, fit=0.10)
        g = build.garment_object(ctx, create=False)
        res["pieces"] = len([o for o in scn.objects if o.cd.is_pattern and o.cd.garment == scn.cd.garment_name])
        res["seams"] = len([s for s in scn.cd.seams if s.obj_a and s.obj_a.cd.garment == scn.cd.garment_name])
        res["verts"] = len(g.data.vertices)
        t1 = time.time()
        res["sew"] = list(bpy.ops.cd.sew())
        res["sew_s"] = round(time.time() - t1)
        merged, left = sim.close_seams(ctx, g)
        res["late_welds"] = merged
        ins, n = penetration(ctx, g)
        res["inside_body_pct"] = round(100.0 * ins / max(1, n), 1)
        bb = [g.evaluated_get(ctx.evaluated_depsgraph_get()).matrix_world @ v.co
              for v in g.evaluated_get(ctx.evaluated_depsgraph_get()).data.vertices]
        zs = [p.z for p in bb]
        res["garment_z_pct"] = [round((min(zs) - m["zmin"]) / m["height"] * 100, 1),
                                round((max(zs) - m["zmin"]) / m["height"] * 100, 1)]
        res["finalize"] = list(bpy.ops.cd.finalize())
        res["modifiers"] = [(md.type, getattr(md, "object", None) and md.object.name) for md in g.modifiers]
        res["vgroups_after"] = len(g.vertex_groups)
        res["parent"] = g.parent.name if g.parent else None
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "%s.blend" % preset.lower()))
    except Exception as e:
        res["error"] = repr(e)
        res["trace"] = traceback.format_exc()[-1500:]
    res["total_s"] = round(time.time() - t0)
    log(preset, res)

json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1, default=str)
print("[fase0] done")
