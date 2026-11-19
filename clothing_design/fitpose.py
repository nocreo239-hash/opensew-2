# Clothing Design - fitting pose for avatars that stand in a T-pose.
#
# Avatars made for VRChat and similar platforms usually rest in a T-pose: arms
# straight out. A bodice is drafted with its armhole on the side of the torso,
# where it sits when the arms hang, so on a T-pose the sleeve cap - wrapped
# round a horizontal arm - is dragged down to that armhole by the stitching
# springs and the sleeve comes off the arm (seen on Hanka, Mao and Minase).
#
# Garment makers sew on a figure with its arms lowered and carry the result
# back to the bind pose afterwards. Here the same happens: the upper arms are
# posed down for measuring, arranging and sewing, and Finalize writes the
# garment back to the rig's rest pose by inverting the skinning, so that when
# the rig returns to its T-pose the sleeves rise with the arms and stay on
# them. The rest pose itself is never edited.
import json, math
import bpy
from mathutils import Matrix, Vector

from . import rig

PROP = "cd_fit_pose"          # on the armature object: the rotations to restore
DEFAULT_ANGLE = 60.0          # arm angle from straight down, as the bundled bodies


def _arm_bones(arm):
    hm = rig.humanoid_map(arm)
    out = []
    for s in (".l", ".r"):
        ua, la = hm.get("upper_arm" + s), hm.get("lower_arm" + s)
        if ua is not None and la is not None:
            out.append((ua, la))
    if len(out) < 2:              # Mixamo and the other legacy names
        from . import avatar
        for key in ("arm_l", "arm_r"):
            ka, kb = avatar.LIMB_CHAINS[key]
            ua, la = avatar._find_bone(arm, ka), avatar._find_bone(arm, kb)
            if ua is not None and la is not None and all(ua.name != o[0].name for o in out):
                out.append((ua, la))
    return out


def arm_angle(arm, ua, la):
    """Angle in degrees between the upper arm and straight down, as posed."""
    mw = arm.matrix_world
    d = (mw @ la.head) - (mw @ ua.head)
    if d.length < 1e-6:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, -d.normalized().z))))


def is_active(arm):
    return arm is not None and PROP in arm


def needed(arm, angle=DEFAULT_ANGLE, margin=10.0):
    """Whether the rig's arms are held out further than the fitting angle."""
    bones = _arm_bones(arm) if arm is not None else []
    return bool(bones) and any(arm_angle(arm, ua, la) > angle + margin for ua, la in bones)


def apply(context, arm, angle=DEFAULT_ANGLE):
    """Lower the upper arms to `angle` from vertical, about the axis that keeps
    each arm in its own plane with the vertical. Returns the angles changed."""
    if arm is None:
        return []
    if is_active(arm):
        clear(context, arm)
    saved, changed = {}, []
    mw = arm.matrix_world
    mw_inv = mw.inverted()
    down = Vector((0.0, 0.0, -1.0))
    for ua, la in _arm_bones(arm):
        before = arm_angle(arm, ua, la)
        if before <= angle + 1.0:
            continue
        saved[ua.name] = {"mode": ua.rotation_mode,
                          "q": list(ua.rotation_quaternion),
                          "e": list(ua.rotation_euler),
                          "aa": list(ua.rotation_axis_angle)}
        d = ((mw @ la.head) - (mw @ ua.head)).normalized()
        axis_w = d.cross(down)
        if axis_w.length < 1e-6:
            continue
        axis_w.normalize()
        rot_w = Matrix.Rotation(math.radians(before - angle), 4, axis_w)
        # the same rotation in armature space, about the bone's head
        rot_a = (mw_inv.to_3x3() @ rot_w.to_3x3() @ mw.to_3x3()).to_4x4()
        head = ua.head.copy()
        ua.matrix = Matrix.Translation(head) @ rot_a @ Matrix.Translation(-head) @ ua.matrix
        context.view_layer.update()
        changed.append((ua.name, round(before, 1), round(arm_angle(arm, ua, la), 1)))
    if saved:
        arm[PROP] = json.dumps(saved)
    return changed


def clear(context, arm):
    """Put the arms back where they were before apply()."""
    if not is_active(arm):
        return False
    try:
        saved = json.loads(arm[PROP])
    except Exception:
        saved = {}
    for name, st in saved.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            continue
        pb.rotation_mode = st["mode"]
        pb.rotation_quaternion = st["q"]
        pb.rotation_euler = st["e"]
        pb.rotation_axis_angle = st["aa"]
    del arm[PROP]
    context.view_layer.update()
    return True


def unpose_garment(ob, arm):
    """Rewrite a skinned garment's mesh into the rig's rest pose.

    The garment was sewn on the posed body, so its vertices are posed. With
    the skin weights it now has, each vertex was carried there by the blend of
    its bones' pose matrices (linear blend skinning, as Blender's Armature
    modifier applies it, weights normalised). Applying the inverse of that
    blend gives the rest position; the Armature modifier then reproduces the
    sewn shape in the fitting pose, and follows the arms when the rig is put
    back in its T-pose. Returns the number of vertices moved.
    """
    mw = arm.matrix_world
    mw_inv = mw.inverted()
    mats = {}
    for pb in arm.pose.bones:
        if not pb.bone.use_deform:
            continue
        mats[pb.name] = mw @ pb.matrix @ pb.bone.matrix_local.inverted() @ mw_inv
    idx = {g.index: mats[g.name] for g in ob.vertex_groups if g.name in mats}
    if not idx:
        return 0
    omw = ob.matrix_world
    omw_inv = omw.inverted()
    moved = 0
    for v in ob.data.vertices:
        ws = [(idx[e.group], e.weight) for e in v.groups if e.group in idx and e.weight > 0.0]
        tot = sum(w for _, w in ws)
        if tot <= 1e-9:
            continue
        M = Matrix.Diagonal((0.0, 0.0, 0.0, 0.0))
        for mat, w in ws:
            M = M + mat * (w / tot)
        if M.is_identity:
            continue
        try:
            Mi = M.inverted()
        except ValueError:
            continue
        v.co = omw_inv @ (Mi @ (omw @ v.co))
        moved += 1
    ob.data.update()
    return moved
