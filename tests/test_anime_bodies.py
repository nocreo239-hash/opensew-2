# Does the drafting hold up on anime proportions?
#
#   CD_AVATARS="/path/Hanka.fbx;/path/mao.fbx" blender -b --python tests/test_anime_bodies.py [-- --quick]
#
# The companion of tests/test_bodies.py for avatars made for VRChat and the
# like: slim necks and wrists against large heads and hands, narrow waists,
# long legs, and a T-pose rest. Like test_bodies.py everything is checked
# against the body's own landmarks, and like test_fit.py every block is sewn
# and its hem, top edge and sleeve must land where that block belongs.
#
# The avatars are paid assets, so the paths come from CD_AVATARS (separated by
# ';' or the OS path separator). --quick measures and drafts without sewing.
import bpy, os, sys, math, time
from mathutils import Vector

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, build, sim, library, patterns, fitpose

QUICK = "--quick" in sys.argv
paths = [p for p in os.environ.get("CD_AVATARS", "").replace(os.pathsep, ";").split(";") if p.strip()]
fails = []

# the avatar's own outfit sits between the body and a new garment
OWN_CLOTHES = {"coat", "jacket", "tops", "pants", "belt", "shirt", "skinny", "inner", "tanktop",
               "tsyatu", "outer", "hat", "arm cover", "gloves", "necklace", "underwear",
               "m_tshirt", "m_chestarmor", "m_pants", "m_gauntlets", "m_glove", "m_farmant",
               "m_hiparmor"}


def check(cond, msg):
    print(("    ok   " if cond else "    FAIL ") + msg)
    if not cond:
        fails.append(msg)


def load(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")
    bpy.ops.import_scene.fbx(filepath=path)
    ctx = bpy.context
    for o in list(ctx.scene.objects):
        if o.type == 'MESH' and o.name.lower() in OWN_CLOTHES:
            bpy.data.objects.remove(o)
    ctx.view_layer.objects.active = None
    bpy.ops.cd.set_avatar()
    return ctx


def garment_verts(ctx, g):
    ev = g.evaluated_get(ctx.evaluated_depsgraph_get())
    return [ev.matrix_world @ v.co for v in ev.data.vertices]


def penetration(ctx, g, tol=0.004):
    bvh = avatar.body_bvh(ctx)
    inside = 0
    vs = garment_verts(ctx, g)
    for p in vs:
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None and (p - loc).dot(nrm) < -tol:
            inside += 1
    return inside, len(vs)


def sleeve_reach(m, verts):
    """0 at the shoulder joint, 1 at the wrist; verts within 9 cm of the arm."""
    arm, farm = m["limbs"].get("arm_l"), m["limbs"].get("farm_l")
    if not arm or not farm:
        return None
    p0, p1 = Vector(arm["p0"]), Vector(farm["p1"])
    axis = p1 - p0
    L = axis.length
    u = axis / L
    ts = sorted((v - p0).dot(u) / L for v in verts
                if -0.2 < (v - p0).dot(u) / L < 1.6
                and ((v - p0) - u * (v - p0).dot(u)).length < 0.09)
    return ts[int(0.98 * (len(ts) - 1))] if len(ts) > 10 else None


def expectations(m):
    """test_fit.py's expectations, the same offsets from the same landmarks."""
    hip, waist, knee, ankle = (avatar.z_of(m, k) for k in ("hip", "waist", "knee", "ankle"))
    return {
        'TSHIRT':   dict(hem=(hip - 0.15, hip + 0.10), sleeve=(0.25, 0.80)),
        'TANK':     dict(hem=(hip - 0.15, hip + 0.12), sleeve=None),
        'SKIRT':    dict(hem=(knee - 0.08, waist - 0.10), top=(waist - 0.08, waist + 0.06)),
        'TROUSERS': dict(hem=(ankle - 0.04, ankle + 0.16), top=(hip - 0.05, waist + 0.06)),
        'JUMPSUIT': dict(hem=(ankle - 0.04, ankle + 0.18), sleeve=(0.20, 0.85)),
        'DRESS':    dict(hem=(knee - 0.18, knee + 0.18), sleeve=(0.10, 0.85)),
        'JACKET':   dict(hem=(hip - 0.16, hip + 0.12), sleeve=(0.80, 1.18)),
        'HOODIE':   dict(hem=(hip - 0.18, hip + 0.12), sleeve=(0.80, 1.18)),
    }


def piece_extent(segs):
    xs = [p[0] for _, pts in segs for p in pts]
    ys = [p[1] for _, pts in segs for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


if not paths:
    print("CD_AVATARS is empty: nothing to test")

for path in paths:
    name = os.path.splitext(os.path.basename(path))[0]
    if not os.path.exists(path):
        check(False, "%s not found" % path)
        continue
    ctx = load(path)
    m = avatar.measure(ctx, force=True)
    arm = avatar.find_armature(ctx.scene.cd.avatar)
    z = {k: avatar.z_of(m, k) for k in ("neck", "shoulder", "chest", "waist", "hip",
                                        "crotch", "knee", "ankle")}
    g = {k: avatar.girth_at(m, z[k]) for k in ("chest", "waist", "hip")}
    h = m["height"]
    print("== %-10s %.0f cm  chest %.0f waist %.0f hip %.0f neck %.0f  palm %.0f  head %.0f  figure %s"
          % (name, h * 100, g["chest"] * 100, g["waist"] * 100, g["hip"] * 100,
             avatar.neck_girth(m) * 100, (m.get("palm_girth") or 0) * 100,
             (m.get("head") or {}).get("len", 0) * 100, m["figure_auto"]))

    # landmarks: anatomical order, sane spacing - test_bodies.py's checks
    check(z["neck"] > z["shoulder"] > z["chest"] > z["waist"] > z["hip"] > z["knee"] > z["ankle"],
          "landmarks in order")
    check(z["shoulder"] - z["chest"] > 0.015, "chest below the shoulder joint (%.0f mm)"
          % ((z["shoulder"] - z["chest"]) * 1000))
    check(g["waist"] < g["chest"] and g["waist"] < g["hip"], "waist narrower than chest and hip")
    check(0.40 < (z["crotch"] - m["zmin"]) / h < 0.62, "crotch at %.0f%% of height"
          % ((z["crotch"] - m["zmin"]) / h * 100))
    # the arms are posed down to sew when the rig rests in a T-pose
    if arm is not None:
        angles = [fitpose.arm_angle(arm, ua, la) for ua, la in fitpose._arm_bones(arm)]
        check(angles and max(angles) < 70, "arms at %s deg while sewing"
              % [round(a) for a in angles])

    # anime proportions the drafting now accounts for
    check(m.get("palm_girth") and m.get("head"), "palm and head measured")
    d = library._draft_top(m, 0.10)
    for key in ("HOODIE", "JACKET"):
        res = library.PRESETS[key][1](m)
        pieces = res[0] if isinstance(res, tuple) else res
        sl = next(p for p in pieces if p["name"] == "Sleeve_L")
        hem = next(pts for n, pts in sl["segs"] if n == "hem")
        hem_w = abs(hem[-1][0] - hem[0][0])
        if m.get("palm_girth"):
            check(hem_w >= m["palm_girth"] * 1.25, "%s cuff %.1f cm clears the palm %.1f cm"
                  % (key.lower(), hem_w * 100, m["palm_girth"] * 100))
        if key == "HOODIE" and m.get("head"):
            hood = next(p for p in pieces if p["name"] == "Hood_R")
            span, hgt = piece_extent(hood["segs"])
            check(span >= m["head"]["depth"] * 0.95 and hgt >= m["head"]["len"] * 1.0,
                  "hood %.0fx%.0f cm covers a head %.0f deep, %.0f long"
                  % (span * 100, hgt * 100, m["head"]["depth"] * 100, m["head"]["len"] * 100))
    if QUICK:
        continue

    for key, want in expectations(m).items():
        ctx = load(path)
        m = avatar.measure(ctx, force=True)
        t0 = time.time()
        try:
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
            bpy.ops.cd.sew()
        except Exception as e:
            check(False, "%s raised %s" % (key, e))
            continue
        gob = build.garment_object(ctx, create=False)
        vs = garment_verts(ctx, gob)
        zmin, zmax = min(p.z for p in vs), max(p.z for p in vs)
        label = "%-9s" % key.lower()
        print("    %s sewn in %.0fs" % (label, time.time() - t0))
        if want.get("hem"):
            lo, hi = want["hem"]
            check(lo <= zmin <= hi, "%s hem at %.2f m (want %.2f..%.2f)" % (label, zmin, lo, hi))
        if want.get("top"):
            lo, hi = want["top"]
            check(lo <= zmax <= hi, "%s top edge at %.2f m (want %.2f..%.2f)" % (label, zmax, lo, hi))
        if want.get("sleeve"):
            lo, hi = want["sleeve"]
            t = sleeve_reach(m, vs)
            check(t is not None and lo <= t <= hi, "%s sleeve reaches %.2f of the arm (want %.2f..%.2f)"
                  % (label, -1 if t is None else t, lo, hi))
        if key not in ('TROUSERS', 'JUMPSUIT'):
            check(zmin > 0.15 * h / 1.7, "%s clear of the floor (zmin %.2f)" % (label, zmin))
        inside, n = penetration(ctx, gob)
        check(inside < n * 0.02, "%s %d/%d verts inside the body" % (label, inside, n))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
