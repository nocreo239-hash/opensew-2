# Headless check of avatars sold on Booth (VRChat humanoid rigs).
#
#   CD_AVATARS="/path/Hanka.fbx;/path/mao.fbx" blender -b --python tests/test_booth_avatars.py [-- --drape]
#
# The avatars are paid assets and can't live in this repository, so the paths
# come from the CD_AVATARS environment variable (separated by ';' or the OS
# path separator). Optional expectations per file name, as JSON in
# CD_AVATARS_EXPECT, e.g. {"Hanka.fbx": {"height": [165, 180], "companions": 1}}.
#
# For each avatar: Set Avatar picks the body mesh, every humanoid part and all
# eight limb chains are found, a separate head mesh is measured with the body,
# the walk test finds its bones, and with --drape a T-shirt and a jacket are
# sewn and must still be on the body afterwards.
import bpy, sys, os, json, time
from mathutils import Vector

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, build, sim, rig

DRAPE = "--drape" in sys.argv
paths = [p for p in os.environ.get("CD_AVATARS", "").replace(os.pathsep, ";").split(";") if p.strip()]
expect = json.loads(os.environ.get("CD_AVATARS_EXPECT", "{}") or "{}")
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def load(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")
    bpy.ops.import_scene.fbx(filepath=path)
    ctx = bpy.context
    # the avatar's own outfit would sit between the body and a new garment
    for o in list(ctx.scene.objects):
        if o.type == 'MESH' and o.name.lower() in ("coat", "jacket", "tops", "pants", "shirt",
                                                   "skinny", "tanktop", "tsyatu", "outer", "inner"):
            bpy.data.objects.remove(o)
    ctx.view_layer.objects.active = None
    bpy.ops.cd.set_avatar()
    return ctx


def on_body(ctx, g, m):
    """Fraction of the garment between the crotch and the top of the head, and
    the fraction inside the body."""
    dg = ctx.evaluated_depsgraph_get()
    ev = g.evaluated_get(dg)
    bvh = avatar.body_bvh(ctx)
    lo, hi = avatar.z_of(m, "crotch") - 0.25, m["zmax"]
    n = inb = inside = 0
    for v in ev.data.vertices:
        p = ev.matrix_world @ v.co
        n += 1
        inb += lo <= p.z <= hi
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None and (p - loc).dot(nrm) < -0.004:
            inside += 1
    return inb / max(1, n), inside / max(1, n)


if not paths:
    print("CD_AVATARS is empty: nothing to test")

for path in paths:
    name = os.path.basename(path)
    exp = expect.get(name, {})
    print("== %s" % name)
    if not os.path.exists(path):
        check(False, "%s not found" % path)
        continue
    ctx = load(path)
    scn = ctx.scene
    body = scn.cd.avatar
    check(body is not None, "Set Avatar picked %s" % (body.name if body else None))
    if body is None:
        continue
    if "body" in exp:
        check(body.name == exp["body"], "body mesh is %s (expected %s)" % (body.name, exp["body"]))
    m = avatar.measure(ctx, body, force=True)
    r = m.get("rig", {})
    print("  height %.1f  chest %.1f waist %.1f hip %.1f neck %.1f cm  figure %s  with %s"
          % (m["height"] * 100,
             *(avatar.girth_at(m, avatar.z_of(m, k)) * 100 for k in ("chest", "waist", "hip")),
             avatar.neck_girth(m) * 100, m["figure_auto"], m.get("companions")))
    check(r.get("found") == r.get("of"), "humanoid parts %s/%s %s"
          % (r.get("found"), r.get("of"), r.get("missing") or ""))
    check(len(m["limbs"]) == 8, "limb chains %d/8" % len(m["limbs"]))
    lm = m["landmarks"]
    for k in ("shoulder", "crotch", "knee"):
        check(k in lm, "%s landmark read from the rig" % k)
    arm = avatar.find_armature(body)
    head = avatar.find_part(arm, "head", ["head"])
    if head is not None:
        hz = (arm.matrix_world @ head.head).z
        check(m["zmax"] > hz + 0.08, "measured surface reaches past the head bone (%.2f > %.2f)"
              % (m["zmax"], hz))
    if "height" in exp:
        lo, hi = exp["height"]
        check(lo <= m["height"] * 100 <= hi, "height %.1f in [%s, %s]" % (m["height"] * 100, lo, hi))
    if "companions" in exp:
        check(len(m.get("companions", [])) == exp["companions"],
              "%d separate head mesh(es) measured" % len(m.get("companions", [])))
    act, msg = sim.walk_cycle(ctx, body)
    check(act is not None, "walk test: %s" % msg)
    if act is not None:
        sim.clear_walk(arm)

    if DRAPE:
        for key in ("TSHIRT", "JACKET"):
            ctx = load(path)
            scn = ctx.scene
            if scn.cd.figure == 'AUTO' and exp.get("figure"):
                scn.cd.figure = exp["figure"]
            m = avatar.measure(ctx, force=True)
            t = time.time()
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
            g = build.garment_object(ctx, create=False)
            bpy.ops.cd.sew()
            share, inside = on_body(ctx, g, m)
            print("  drape %-7s %3.0fs" % (key.lower(), time.time() - t))
            check(share > 0.95, "%s still on the body (%.0f%% of verts)" % (key.lower(), share * 100))
            check(inside < 0.02, "%s %.1f%% of verts inside the body" % (key.lower(), inside * 100))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
