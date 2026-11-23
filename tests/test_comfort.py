# Fase 8 (comodidad de uso): the safety nets around sewing.
#
#   blender -b --python tests/test_comfort.py
#
# On the built-in woman: Quick Sew, a sewn garment not rebuilt by live
# updates, the sewn shape kept in the mesh, Unsew, Change Garment, Delete
# Garment, the arms lowered again after T-Pose, Finalize All and exporting
# only the selected garment.
import bpy, os, sys, time, tempfile

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import build, export, fitpose, avatar, sim

FAIL = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        FAIL.append(what)


def coords(ob):
    return [v.co.copy() for v in ob.data.vertices]


def evaluated(ob):
    with sim.sim_cage_only(ob):
        bpy.context.view_layer.update()
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        out = [(ev.matrix_world.inverted() @ (ev.matrix_world @ v.co)) for v in me.vertices]
        ev.to_mesh_clear()
    return out


def max_diff(a, b):
    if len(a) != len(b):
        return float("inf")
    return max(((p - q).length for p, q in zip(a, b)), default=0.0)


scn = bpy.context.scene
bpy.ops.cd.import_character(figure='WOMAN')
bpy.context.view_layer.objects.active = None
bpy.ops.cd.set_avatar()
rig = avatar.find_armature(scn.cd.avatar)

bpy.ops.cd.add_garment(preset='TSHIRT', fit=0.08)
g = build.garment_object(bpy.context, create=False)
check(g is not None and g.cd.preset == 'TSHIRT', "Add Garment keeps what it was made from (%s)" % (g.cd.preset if g else None))
flat = coords(g)

t0 = time.time()
bpy.ops.cd.sew(draft=True)
t_quick = time.time() - t0
check(g.cd.sewn and g.cd.draft, "Quick Sew marks the garment sewn and quick (%.0f s)" % t_quick)
sewn = coords(g)
check(max_diff(flat, sewn) > 0.01, "the sewn shape is in the mesh, not only in the cloth cache")

# live updates leave a sewn garment alone
g.cd.size = 1.1
piece = next(o for o in scn.objects if o.cd.is_pattern and o.cd.garment == g.cd.garment)
piece.cd.height = piece.cd.height + 0.05
check(max_diff(sewn, coords(g)) < 1e-6, "Size and a piece slider don't rebuild the sewn garment")
check(scn.cd.locked_note == g.cd.garment, "the panel is told why (%r)" % scn.cd.locked_note)
g.cd.size = 1.0
piece.cd.height = piece.cd.height - 0.05

# the sewn shape survives the timeline
scn.frame_set(scn.frame_start)
check(max_diff(sewn, evaluated(g)) < 1e-4, "back at the first frame the garment is still sewn")
scn.frame_set(scn.frame_current + 30)

bpy.ops.cd.unsew()
check(not g.cd.sewn and max_diff(sewn, coords(g)) > 0.01, "Unsew opens it again and live updates work")

# Change Garment
n_seams = len(scn.cd.seams)
name = g.cd.garment
bpy.ops.cd.change_garment(preset='TSHIRT', fit=0.08, length='SHORT', sleeves='ELBOW')
g = build.garment_object(bpy.context, create=False)
check(g is not None and g.cd.garment == name and g.cd.opt_length == 'SHORT' and g.cd.opt_sleeves == 'ELBOW',
      "Change Garment redrafts it under the same name with the new options")
check(len([o for o in scn.objects if o.cd.is_garment]) == 1, "and leaves no copy of the old one")
check(len(scn.cd.seams) == n_seams, "its seams are replaced, not added (%d)" % len(scn.cd.seams))

# Delete Garment
bpy.ops.cd.add_garment(preset='SKIRT', fit=0.08)
sk = scn.cd.garment_name
bpy.ops.cd.remove_garment()
check(not any(o.cd.garment == sk for o in scn.objects if o.cd.is_pattern or o.cd.is_garment),
      "Delete Garment removes the pieces and the 3D garment")
check(not any(s.obj_a and s.obj_a.cd.garment == sk for s in scn.cd.seams), "and its seams")

# arms lowered again after T-Pose
if fitpose.is_active(rig):
    bpy.ops.cd.rest_pose()
    check(not fitpose.is_active(rig), "T-Pose raises the arms")
    bpy.ops.cd.add_garment(preset='SKIRT', fit=0.08)
    check(fitpose.is_active(rig), "the next Add Garment lowers them again")
else:
    print("  --   the woman needs no lowered arms: pose check skipped")
    bpy.ops.cd.add_garment(preset='SKIRT', fit=0.08)
skirt = scn.cd.garment_name

# Finalize All, then export only the selected garment
bpy.ops.cd.sew(all_garments=True, draft=True)
bpy.ops.cd.finalize(all_garments=True)
done = export.finished_garments(bpy.context)
check(len(done) == 2, "Finalize All finishes both garments (%d)" % len(done))
for i, o in enumerate(bpy.data.objects):
    if o.cd.is_garment and o.cd.garment == name:
        scn.cd.active_garment = i
out = os.path.join(tempfile.mkdtemp(), "only.fbx")
bpy.ops.cd.export_vrchat(filepath=out, only_active=True)
check(os.path.exists(out), "Export Selected writes the FBX")
info = export.export_outfit(bpy.context, out, garments=[build.garment_object(bpy.context, create=False)])
check(info["garments"] == [name], "with only the selected garment in it (%s)" % info["garments"])

print("%d failure(s)" % len(FAIL))
