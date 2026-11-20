# Headless check of the VRChat FBX export (Fase 3).
#
#   blender -b --python tests/test_export.py [-- PRESET]
#   CD_AVATARS="/path/Hanka.fbx;/path/mao.fbx" blender -b --python tests/test_export.py
#
# For each avatar (the built-in woman when CD_AVATARS is empty): sew a garment
# (TSHIRT unless given), Finalize, export, then read the FBX back into an
# empty scene and check what Unity and Modular Avatar will see:
#   * one armature whose root is the hip bone, every bone carrying the suffix;
#   * every bone where the avatar's bone of the same name is (Setup Outfit
#     needs the positions to match);
#   * the garment skinned to that armature: every vertex weighted, 1-4
#     influences, summing to 1, only to bones of the armature;
#   * the garment where it was in Blender, in the rest pose;
#   * posing the upper arm moves the sleeve.
import bpy, sys, os, tempfile
from mathutils import Vector, Matrix, kdtree

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, build, export, fitpose, rig

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PRESET = (args[0] if args else "TSHIRT").upper()
SUFFIX = export.DEFAULT_SUFFIX
paths = [p for p in os.environ.get("CD_AVATARS", "").replace(os.pathsep, ";").split(";") if p.strip()]
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def load(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")
    if path:
        bpy.ops.import_scene.fbx(filepath=path)
        for o in list(bpy.context.scene.objects):
            if o.type == 'MESH' and o.name.lower() in ("coat", "jacket", "tops", "pants", "shirt",
                                                       "skinny", "tanktop", "tsyatu", "outer", "inner"):
                bpy.data.objects.remove(o)
    else:
        bpy.ops.cd.import_character(figure='WOMAN')
    ctx = bpy.context
    ctx.view_layer.objects.active = None
    bpy.ops.cd.set_avatar()
    return ctx


def rest_bones(arm):
    return {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}


def world_verts(ob):
    """Vertex positions of ob with its armature disabled (the rest shape)."""
    mods = [(m, m.show_viewport) for m in ob.modifiers if m.type == 'ARMATURE']
    for m, _ in mods:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = ob.evaluated_get(dg)
    pts = [ev.matrix_world @ v.co for v in ev.data.vertices]
    for m, vis in mods:
        m.show_viewport = vis
    return pts


def run(path):
    label = os.path.basename(path) if path else "built-in woman"
    print("== %s, %s" % (label, PRESET))
    ctx = load(path)
    scn = ctx.scene
    arm = avatar.find_armature(scn.cd.avatar)
    bpy.ops.cd.add_garment(preset=PRESET, fit=0.10)
    r = bpy.ops.cd.sew()
    check(r == {'FINISHED'}, "sewn")
    r = bpy.ops.cd.finalize()
    check(r == {'FINISHED'}, "finalized")
    if fitpose.is_active(arm):
        fitpose.clear(ctx, arm)          # compare against the rest pose
    g = export.finished_garments(ctx)
    check(len(g) == 1, "one finished garment (%d)" % len(g))
    if not g:
        return
    g = g[0]
    src_bones = rest_bones(arm)
    src_pts = world_verts(g)

    out = os.path.join(tempfile.gettempdir(), "cd_export_%s_%s.fbx" % (label.replace(" ", "_"), PRESET))
    n_before = len(bpy.data.objects)
    info = export.export_outfit(ctx, out, suffix=SUFFIX)
    check(os.path.exists(out) and os.path.getsize(out) > 10000, "FBX written (%s)" % out)
    check(len(bpy.data.objects) == n_before, "scene left as it was (%d objects)" % len(bpy.data.objects))
    print("    %s" % {k: v for k, v in info.items() if k != "path"})

    # read it back on its own
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=out)
    arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    check(len(arms) == 1, "one armature (%d)" % len(arms))
    check(len(meshes) == 1, "one mesh (%d)" % len(meshes))
    if len(arms) != 1 or not meshes:
        return
    a, me = arms[0], meshes[0]
    roots = [b.name for b in a.data.bones if b.parent is None]
    check(len(roots) == 1 and "hips" in roots[0].lower(), "root bone is the hips (%s)" % roots)
    check(all(b.name.endswith(SUFFIX) for b in a.data.bones), "every bone ends in %s" % SUFFIX)

    got = rest_bones(a)
    worst, wname = 0.0, ""
    for name, p in got.items():
        q = src_bones.get(name[:-len(SUFFIX)])
        if q is None:
            worst, wname = 1e9, name + " (not on the avatar)"
            break
        d = (p - q).length
        if d > worst:
            worst, wname = d, name
    check(worst < 0.001, "bones where the avatar's are (worst %.2f mm, %s)" % (worst * 1000, wname))

    mod = next((m for m in me.modifiers if m.type == 'ARMATURE'), None)
    check(mod is not None and mod.object == a, "mesh skinned to the armature")
    bone_names = {b.name for b in a.data.bones}
    gname = {vg.index: vg.name for vg in me.vertex_groups}
    check(all(n in bone_names for n in gname.values()), "weights only to bones of the armature")
    zero = many = off = 0
    for v in me.data.vertices:
        ws = [g.weight for g in v.groups if g.weight > 1e-5]
        if not ws:
            zero += 1
        elif len(ws) > 4:
            many += 1
        elif abs(sum(ws) - 1.0) > 0.01:
            off += 1
    check(zero == 0, "every vertex weighted (%d unweighted)" % zero)
    check(many == 0, "at most 4 influences (%d over)" % many)
    check(off == 0, "weights sum to 1 (%d off)" % off)
    weighted = {gname[g.group] for v in me.data.vertices for g in v.groups if g.weight > 1e-5}
    needed = set()
    for n in weighted:
        b = a.data.bones.get(n)
        while b is not None:
            needed.add(b.name); b = b.parent
    extra = [b.name for b in a.data.bones if b.name not in needed]
    check(not extra, "only weighted bones and their parents (%d bones, %d extra)"
          % (len(a.data.bones), len(extra)))

    pts = world_verts(me)
    kd = kdtree.KDTree(len(src_pts))
    for i, p in enumerate(src_pts):
        kd.insert(p, i)
    kd.balance()
    dev = sorted(kd.find(p)[2] for p in pts)
    p95 = dev[int(0.95 * (len(dev) - 1))] if dev else 1.0
    check(len(pts) == len(src_pts), "same vertex count (%d vs %d)" % (len(pts), len(src_pts)))
    check(p95 < 0.001, "garment where it was in Blender (95%% within %.2f mm)" % (p95 * 1000))

    # pose the left upper arm: the sleeve has to move with it
    ua = next((b for b in a.pose.bones
               if rig.parse(b.name[:-len(SUFFIX)]) in (("upper_arm", ".l"), ("_arm", ".l"))), None)
    check(ua is not None, "left upper arm in the export (%s)" % (ua.name if ua else None))
    if ua is not None:
        dg = bpy.context.evaluated_depsgraph_get()
        before = [me.evaluated_get(dg).matrix_world @ v.co for v in me.evaluated_get(dg).data.vertices]
        ua.rotation_mode = 'XYZ'
        ua.rotation_euler = (0.0, 0.0, 0.8)
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        ev = me.evaluated_get(dg)
        moved = sum(1 for v, b in zip(ev.data.vertices, before) if (ev.matrix_world @ v.co - b).length > 0.01)
        check(moved > 50, "posing the upper arm moves the sleeve (%d verts)" % moved)


for p in (paths or [None]):
    run(p)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
