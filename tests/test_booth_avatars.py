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
# sewn and must still be on the body afterwards; the T-shirt is finalized and
# must follow the rig when the upper arm is posed.
import bpy, sys, os, json, time
from mathutils import Vector

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, build, sim, rig, fitpose

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


def finalize_and_pose(ctx, g):
    """Finalize binds the garment to the avatar's rig: an Armature modifier on
    that rig and weights on its humanoid bones. Raising the upper arm must
    then carry the sleeve with it."""
    body = ctx.scene.cd.avatar
    arm = avatar.find_armature(body)
    bpy.ops.cd.finalize()
    mods = [m for m in g.modifiers if m.type == 'ARMATURE']
    check(mods and mods[0].object == arm, "finalize: Armature modifier on %s" % arm.name)
    hm = rig.humanoid_map(arm)
    ua = hm.get("upper_arm.l")
    if ua is None:
        check(False, "finalize: no upper arm to pose")
        return
    # every group that rig.group_label calls the left upper arm: the bone
    # itself and its twist segments (Vlau splits the arm over three)
    arm_groups = {gr.index for gr in g.vertex_groups if rig.group_label(gr.name) == "upper_arm.l"}
    torso_groups = {gr.index for gr in g.vertex_groups
                    if rig.group_label(gr.name) in ("spine", "hips")}
    # only bone groups: the garment also keeps one group per pattern piece,
    # always at weight 1, which would win every comparison
    bone_names = {b.name for b in arm.data.bones}
    bone_idx = {gr.index for gr in g.vertex_groups if gr.name in bone_names}
    weighted, torso = [], []
    for v in g.data.vertices:
        bg = [e for e in v.groups if e.group in bone_idx]
        if not bg:
            continue
        top = max(bg, key=lambda e: e.weight)
        if top.group in arm_groups and top.weight > 0.5:
            weighted.append(v.index)
        elif top.group in torso_groups and top.weight > 0.5:
            torso.append(v.index)
    check(len(weighted) > 20, "finalize: %d verts weighted to the upper arm (%s)"
          % (len(weighted), ua.name))
    if not weighted:
        return

    def co(idx):
        ev = g.evaluated_get(ctx.evaluated_depsgraph_get())
        return [ev.matrix_world @ ev.data.vertices[i].co for i in idx]

    # the cloth cache would replay the drape on top of the pose
    for m in list(g.modifiers):
        if m.type == 'CLOTH':
            g.modifiers.remove(m)
    def median_move(b, a):
        d = sorted((x - y).length for x, y in zip(a, b))
        return d[len(d) // 2] if d else 0.0

    b_arm, b_torso = co(weighted), co(torso)
    ua.rotation_mode = 'XYZ'
    ua.rotation_euler = (0.0, 0.0, 0.8)
    ctx.view_layer.update()
    m_arm, m_torso = median_move(b_arm, co(weighted)), median_move(b_torso, co(torso))
    ua.rotation_euler = (0.0, 0.0, 0.0)
    ctx.view_layer.update()
    check(m_arm > 0.02 and m_arm > 4 * m_torso,
          "posing %s moves the sleeve %.0f mm and the torso %.0f mm (median)"
          % (ua.name, m_arm * 1000, m_torso * 1000))

    # back in the rig's own rest pose (a T-pose for these avatars) the sleeve
    # must sit round the arm, not hang under it
    if fitpose.is_active(arm):
        bpy.ops.cd.rest_pose()
    la = avatar.find_part(arm, "lower_arm.l", avatar.LIMB_CHAINS["arm_l"][1])
    mw = arm.matrix_world
    p0, p1 = mw @ ua.head, mw @ la.head
    ax = (p1 - p0).normalized()
    L = (p1 - p0).length
    gap = []
    for p in co(weighted):
        t = (p - p0).dot(ax)
        if 0.25 * L < t < 0.9 * L:
            gap.append(((p - p0) - ax * t).length)
    gap.sort()
    if gap:
        med = gap[len(gap) // 2]
        check(med < 0.075, "rest pose: sleeve sits round the upper arm (median %.0f mm from its axis)"
              % (med * 1000))
    else:
        check(False, "rest pose: no sleeve vertex along the upper arm")


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
            if key == "TSHIRT":
                finalize_and_pose(ctx, g)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
