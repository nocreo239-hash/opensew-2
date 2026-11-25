# Clothing Design - avatar measuring: body cross-sections, landmarks, limb axes.
#
# The body is described by a stack of horizontal cross-sections. Each section
# stores a centre and a radius per angular sector, so the torso reads as the
# ellipse it really is instead of a circle. Arms and head are masked out using
# the rig's own skin weights, otherwise a relaxed pose puts the arms inside the
# chest measurement and every garment comes out several sizes too big.
import bpy, json, math
from . import rig
from mathutils import Vector
from mathutils.bvhtree import BVHTree

NBINS = 96      # vertical cross-sections
NSEC = 16       # angular sectors per cross-section
SPACING = 0.007 # target spacing of surface samples (m)

MEASURE_VERSION = 3     # bump when a change alters what measure() returns
SIZE_REF = 1.50         # shoulder height (m) the default Resolution was tuned up to


def size_factor(m):
    """How much coarser to mesh a garment for this avatar: 1 up to SIZE_REF at
    the shoulder (every avatar the defaults were tuned on, the 1.86 m man
    included), and in proportion above it. Never finer: smaller avatars keep
    the tested resolution. The shoulder, not the stature, which counts horns,
    ears and hats (The Beast is 2.36 m with horns, 1.83 m at the shoulder)."""
    if not m:
        return 1.0
    try:
        sh = z_of(m, "shoulder") - m["zmin"]
    except Exception:
        return 1.0
    return max(1.0, sh / SIZE_REF)

PROPORTIONS = {
    "ankle": 0.039, "knee": 0.285, "crotch": 0.485, "hip": 0.530,
    "waist": 0.620, "chest": 0.720, "shoulder": 0.818, "neck": 0.870,
}

# Bone name candidates (lowercased substrings, first match wins).
BONE_TABLE = {
    "neck":   ["cc_base_necktwist01", "mixamorig:neck", "neck", "spine.004"],
    "chest":  ["cc_base_spine02", "mixamorig:spine2", "spine.003", "chest", "spine02"],
    "waist":  ["cc_base_waist", "mixamorig:spine", "spine.001", "waist", "spine01"],
    "hip":    ["cc_base_pelvis", "mixamorig:hips", "pelvis", "hips", "spine"],
}
# The same landmarks and limbs as humanoid parts (rig.py). These are tried
# first; the name lists above and below stay as the fallback for rigs whose
# words are ambiguous out of context (Mixamo's LeftArm/LeftLeg, Rigify's spine.00N).
HUMANOID_LANDMARKS = {"neck": "neck", "chest": "chest", "waist": "spine", "hip": "hips"}
HUMANOID_CHAINS = {
    "arm_l": ("upper_arm.l", "lower_arm.l"), "arm_r": ("upper_arm.r", "lower_arm.r"),
    "farm_l": ("lower_arm.l", "hand.l"),     "farm_r": ("lower_arm.r", "hand.r"),
    "thigh_l": ("upper_leg.l", "lower_leg.l"), "thigh_r": ("upper_leg.r", "lower_leg.r"),
    "calf_l": ("lower_leg.l", "foot.l"),     "calf_r": ("lower_leg.r", "foot.r"),
}
# Limb chains: (start bone, end bone). The axis runs start.head -> end.head,
# because CC4 bone tails stop at twist bones and badly understate limb length.
LIMB_CHAINS = {
    "arm_l":   (["cc_base_l_upperarm", "mixamorig:leftarm", "upper_arm.l"],
                ["cc_base_l_forearm", "mixamorig:leftforearm", "forearm.l"]),
    "arm_r":   (["cc_base_r_upperarm", "mixamorig:rightarm", "upper_arm.r"],
                ["cc_base_r_forearm", "mixamorig:rightforearm", "forearm.r"]),
    "farm_l":  (["cc_base_l_forearm", "mixamorig:leftforearm", "forearm.l"],
                ["cc_base_l_hand", "mixamorig:lefthand", "hand.l"]),
    "farm_r":  (["cc_base_r_forearm", "mixamorig:rightforearm", "forearm.r"],
                ["cc_base_r_hand", "mixamorig:righthand", "hand.r"]),
    "thigh_l": (["cc_base_l_thigh", "mixamorig:leftupleg", "thigh.l"],
                ["cc_base_l_calf", "mixamorig:leftleg", "shin.l"]),
    "thigh_r": (["cc_base_r_thigh", "mixamorig:rightupleg", "thigh.r"],
                ["cc_base_r_calf", "mixamorig:rightleg", "shin.r"]),
    "calf_l":  (["cc_base_l_calf", "mixamorig:leftleg", "shin.l"],
                ["cc_base_l_foot", "mixamorig:leftfoot", "foot.l"]),
    "calf_r":  (["cc_base_r_calf", "mixamorig:rightleg", "shin.r"],
                ["cc_base_r_foot", "mixamorig:rightfoot", "foot.r"]),
}
# Vertex groups whose verts must not contribute to the torso cross-sections.
# Finger bones are named Index1/Mid1/Ring1/Pinky1 in CC4, not "indexfinger" -
# missing them puts the hands inside the torso cross-section, which reads as a
# 164 cm waist on a figure standing in an A-pose.
EXCLUDE_TORSO = ("upperarm", "forearm", "elbow", "wrist", "hand", "palm", "thumb",
                 "index", "mid", "ring", "pinky", "head", "eye", "teeth", "tongue",
                 "jaw", "facial", "brow", "nose", "lip", "cheek", "ear",
                 "leftarm", "rightarm",   # Mixamo upper arms have no "upperarm" in the name
                 "upper_arm")             # what rig.group_label calls them, as Rigify does
# Keywords identifying the verts belonging to each limb.
LIMB_GROUPS = {
    "arm_l":   ("l_upperarm", "leftarm", "upper_arm.l"),
    "arm_r":   ("r_upperarm", "rightarm", "upper_arm.r"),
    "farm_l":  ("l_forearm", "leftforearm", "forearm.l"),
    "farm_r":  ("r_forearm", "rightforearm", "forearm.r"),
    "thigh_l": ("l_thigh", "leftupleg", "thigh.l"),
    "thigh_r": ("r_thigh", "rightupleg", "thigh.r"),
    "calf_l":  ("l_calf", "leftleg", "shin.l"),
    "calf_r":  ("r_calf", "rightleg", "shin.r"),
}


# ---------------------------------------------------------------- basics

def basis(facing):
    """(forward, side). side = forward rotated +90 deg CCW about Z (character's left)."""
    fwd = {'-Y': Vector((0, -1, 0)), '+Y': Vector((0, 1, 0)),
           '-X': Vector((-1, 0, 0)), '+X': Vector((1, 0, 0))}[facing]
    return fwd, Vector((-fwd.y, fwd.x, 0.0))


def _pct(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, int(q * (len(sorted_vals) - 1))))
    return sorted_vals[i]


def _median(vals):
    return sorted(vals)[len(vals) // 2] if vals else 0.0


def _smooth(vals, passes=2):
    out = list(vals)
    for _ in range(passes):
        nxt = list(out)
        for i in range(1, len(out) - 1):
            nxt[i] = (out[i - 1] + 2.0 * out[i] + out[i + 1]) * 0.25
        out = nxt
    return out


def _smooth_ring(vals, passes=1):
    out = list(vals)
    n = len(out)
    for _ in range(passes):
        out = [(out[(i - 1) % n] + 2.0 * out[i] + out[(i + 1) % n]) * 0.25 for i in range(n)]
    return out


def find_armature(ob):
    for mod in ob.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            return mod.object
    if ob.parent and ob.parent.type == 'ARMATURE':
        return ob.parent
    return None


def find_part(arm, part, keys=(), hmap=None):
    """Pose bone for a humanoid part ('upper_arm.l'), falling back to the
    legacy name candidates when the rig doesn't spell the part recognisably."""
    hm = rig.humanoid_map(arm) if hmap is None else hmap
    pb = hm.get(part) if part else None
    if pb is not None:
        return pb
    return _find_bone(arm, keys) if keys else None


def _find_bone(arm, keys):
    names = {b.name.lower(): b for b in arm.pose.bones}
    for k in keys:
        if k in names:
            return names[k]
    for k in keys:
        for n, b in names.items():
            if k in n:
                return b
    return None


# ------------------------------------------------- geometry extraction

def _bary_grid(k):
    out = []
    for i in range(k + 1):
        for j in range(k + 1 - i):
            out.append((i / k, j / k))
    return out


_BARY = {k: _bary_grid(k) for k in range(1, 6)}


def group_labels(ob):
    """{vertex group index: label} for a body mesh ('thigh.l', 'upper_arm.r').

    A group named after an ambiguous bone ("Left leg" is the thigh on a CATS
    rig and the shin on Mixamo) is labelled by the part its bone plays in the
    skeleton. Labelled by name alone, The Beast's thigh measuring fell back to
    every sample in the slab and read a 32 cm radius for a 12 cm thigh."""
    roles = rig.bone_labels(find_armature(ob))
    return {g.index: roles.get(g.name) or rig.group_label(g.name) for g in ob.vertex_groups}


def sample_body(ob, depsgraph, spacing=SPACING):
    """Area-weighted samples over the body surface, each tagged with the dominant
    vertex group of its triangle. Sampling the surface instead of the vertices
    matters: a 14k-vert base mesh leaves the cross-section bins far too sparse."""
    ev = ob.evaluated_get(depsgraph)
    try:
        me = ev.to_mesh()
    except Exception:
        return [], []
    try:
        me.calc_loop_triangles()
    except Exception:
        pass
    mw = ev.matrix_world.copy()
    gname = group_labels(ob)

    co = [mw @ v.co for v in me.vertices]
    dom_v = []
    for v in me.vertices:
        if v.groups:
            top = max(v.groups, key=lambda g: g.weight)
            dom_v.append(gname.get(top.group, ""))
        else:
            dom_v.append("")

    pts, dom = [], []
    tris = me.loop_triangles
    if not len(tris):
        ev.to_mesh_clear()
        return co, dom_v
    for t in tris:
        i0, i1, i2 = t.vertices
        a, b, c = co[i0], co[i1], co[i2]
        ab, ac = b - a, c - a
        area = ab.cross(ac).length * 0.5
        k = int(math.sqrt(max(area, 0.0) * 2.0) / spacing) + 1
        k = min(5, max(1, k))
        lab = dom_v[i0] or dom_v[i1] or dom_v[i2]
        for u, v in _BARY[k]:
            pts.append(a + ab * u + ac * v)
            dom.append(lab)
    ev.to_mesh_clear()
    return pts, dom


# Vertex groups of parts a garment is not made for: horns, animal ears, tails,
# wings, halos. A sample weighted to one is not body (as a label: a group not
# named after a humanoid part comes back as its own lower-cased name).
NONHUMAN = ("horn", "tail", "wing", "kemo", "mimi", "halo", "tsuno", "shippo")
CROWN_AXIS = 0.12    # crown searched within this share of the head's width of its axis
CROWN_MARGIN = 0.02  # the head-weighted top this far over the crown is not skull
CROWN_ABOVE = 0.25   # at most this share of the head surface over a crown


def _nonhuman(label):
    return bool(label) and any(k in label for k in NONHUMAN)


def skull_top(pts, dom, arm, hm=None):
    """Height of the crown of the skull: the top of the head-weighted surface
    on the skull's own vertical axis, the head bone's. Horns, animal ears
    and the like grow off that axis, so they do not raise it: The Beast's horns are in his
    body mesh and painted to the Head bone, and took his stature to 2.36 m
    and his head to 36 cm, with the crown of his skull at 2.23 m. None when
    there is no head to go by."""
    if arm is None:
        return None
    hm = hm if hm is not None else rig.humanoid_map(arm)
    hb = hm.get("head")
    if hb is None:
        return None
    base = arm.matrix_world @ hb.head
    head = [p for p, d in zip(pts, dom) if d.startswith("head") and p.z >= base.z]
    if len(head) < 50:
        return None
    # the skull's width just above the head bone, where nothing but skull
    # (and the face) is: horns and ears grow from higher up
    band = [p for p in head if p.z < base.z + 0.06]
    if len(band) < 20:
        return None
    xs = sorted((p - base).dot(Vector((1, 0, 0))) for p in band)
    ys = sorted((p - base).dot(Vector((0, 1, 0))) for p in band)
    width = min(_pct(xs, 0.98) - _pct(xs, 0.02), _pct(ys, 0.98) - _pct(ys, 0.02))
    reach = max(0.01, CROWN_AXIS * width)
    # on a surface the only head samples this near the axis, above the head
    # bone, are the crown's
    on_axis = [p.z for p in head if math.hypot(p.x - base.x, p.y - base.y) < reach]
    if len(on_axis) < 3:
        return None
    top = max(on_axis)
    # and only a crown with little over it: horns are thin next to a skull
    # (12 % of The Beast's head surface). A head open on top (Mao's bowl)
    # leaves nothing on the axis but the inside of the mouth, with most of
    # the head over it - that is no crown, and the top stays where it was
    zh = max(p.z for p in head)
    above = sum(1 for p in head if p.z > top)
    if top < base.z + 0.5 * (zh - base.z) or above > CROWN_ABOVE * len(head):
        return None
    return top


def drop_nonhuman(pts, dom, arm, hm=None):
    """The body samples without horns, animal ears, tails, wings and halos:
    those weighted to a group named for one, and anything standing over the
    crown of the skull (skull_top). An avatar with no such parts comes back
    unchanged, so its measurements do not move."""
    keep = [i for i, d in enumerate(dom) if not _nonhuman(d)]
    if len(keep) < len(dom) and len(keep) >= 200:
        pts, dom = [pts[i] for i in keep], [dom[i] for i in keep]
    crown = skull_top(pts, dom, arm, hm)
    if crown is not None and max(p.z for p in pts) > crown + CROWN_MARGIN:
        keep = [i for i, p in enumerate(pts) if p.z <= crown]
        pts, dom = [pts[i] for i in keep], [dom[i] for i in keep]
    return pts, dom


def guess_facing(arm, pts, dom):
    """Toe bones are the most reliable forward cue on a standing character."""
    if arm is not None:
        acc = Vector((0, 0, 0))
        mw = arm.matrix_world
        for b in arm.pose.bones:
            if "toe" in b.name.lower():
                d = (mw @ b.tail) - (mw @ b.head)
                d.z = 0.0
                if d.length > 1e-9:
                    acc += d.normalized()
        if acc.length > 0.5:
            acc.normalize()
            if abs(acc.y) >= abs(acc.x):
                return '-Y' if acc.y < 0 else '+Y'
            return '-X' if acc.x < 0 else '+X'
    if not pts:
        return '-Y'
    zs = [p.z for p in pts]
    zmin, h = min(zs), max(1e-6, max(zs) - min(zs))
    feet = [p for p in pts if p.z < zmin + 0.06 * h]
    core = [p for p in pts if zmin + 0.40 * h < p.z < zmin + 0.70 * h]
    if not feet or not core:
        return '-Y'
    cx, cy = _median([p.x for p in core]), _median([p.y for p in core])
    dx = sum(p.x for p in feet) / len(feet) - cx
    dy = sum(p.y for p in feet) / len(feet) - cy
    if abs(dy) >= abs(dx):
        return '-Y' if dy < 0 else '+Y'
    return '-X' if dx < 0 else '+X'


def build_profile(pts, dom, fwd, side, nbins=NBINS, nsec=NSEC, bin_top=None):
    """bin_top: the height the cross-sections are spread up to, when it is not
    the top of pts - the avatar's top with its horns or ears still on, so
    that taking them off the stature leaves every cross-section where it was
    (with the bins 6 % finer on The Beast his neck read 68 cm, not 82)."""
    zs = [p.z for p in pts]
    zmin, zmax = min(zs), max(zs)
    bin_top = max(zmax, bin_top or zmax)
    bin_h = max(1e-6, bin_top - zmin)

    keep = [i for i, d in enumerate(dom)
            if not any(k in d for k in EXCLUDE_TORSO)]
    if len(keep) < 200:            # unrigged mesh: fall back to everything
        keep = list(range(len(pts)))

    bins = [[] for _ in range(nbins)]
    for i in keep:
        p = pts[i]
        b = int((p.z - zmin) / bin_h * nbins)
        bins[min(nbins - 1, max(0, b))].append(p)

    cx, cy, sect, count, cover = [], [], [], [], []
    last_c = (0.0, 0.0)
    last_r = [0.05] * nsec
    for b in bins:
        count.append(len(b))
        if len(b) < 12:
            cx.append(last_c[0]); cy.append(last_c[1]); sect.append(list(last_r))
            cover.append(0.0)
            continue
        xs, ys = sorted(p.x for p in b), sorted(p.y for p in b)
        mx = (_pct(xs, 0.02) + _pct(xs, 0.98)) * 0.5
        my = (_pct(ys, 0.02) + _pct(ys, 0.98)) * 0.5
        buckets = [[] for _ in range(nsec)]
        for p in b:
            d = Vector((p.x - mx, p.y - my, 0.0))
            r = d.length
            if r < 1e-6:
                continue
            ang = math.atan2(d.dot(side), d.dot(fwd)) % (2.0 * math.pi)
            buckets[min(nsec - 1, int(ang / (2.0 * math.pi) * nsec))].append(r)
        rr = []
        for k in range(nsec):
            rr.append(_pct(sorted(buckets[k]), 0.90) if len(buckets[k]) >= 3 else 0.0)
        # fill empty sectors from their neighbours
        known = [k for k in range(nsec) if rr[k] > 0.0]
        cover.append(len(known) / float(nsec))
        if not known:
            rr = list(last_r)
        else:
            for k in range(nsec):
                if rr[k] <= 0.0:
                    near = min(known, key=lambda j: min(abs(j - k), nsec - abs(j - k)))
                    rr[k] = rr[near]
        rr = _smooth_ring(rr, 1)
        cx.append(mx); cy.append(my); sect.append(rr)
        last_c, last_r = (mx, my), rr

    cols = [_smooth([sect[i][k] for i in range(nbins)], 2) for k in range(nsec)]
    sect = [[cols[k][i] for k in range(nsec)] for i in range(nbins)]

    return {"zmin": zmin, "zmax": zmax, "height": max(1e-6, zmax - zmin), "bin_h": bin_h,
            "nbins": nbins, "nsec": nsec,
            "cx": _smooth(cx), "cy": _smooth(cy), "sect": sect,
            # per-bin sample count and the fraction of sectors that had samples:
            # a slice is only a real circumference where the ring is complete
            "count": count, "cover": cover}


# ------------------------------------------------- profile queries

def _bin_t(m, z):
    return (z - m["zmin"]) / max(1e-9, m.get("bin_h", m["height"])) * m["nbins"] - 0.5


def _lerp1(arr, t):
    n = len(arr)
    i = int(math.floor(t)); f = t - i
    return arr[min(n - 1, max(0, i))] * (1.0 - f) + arr[min(n - 1, max(0, i + 1))] * f


def center_at(m, z):
    t = _bin_t(m, z)
    return Vector((_lerp1(m["cx"], t), _lerp1(m["cy"], t), z))


def radius_at(m, z, theta=0.0):
    """Body radius at height z in direction theta (0 = forward, +CCW)."""
    t = _bin_t(m, z)
    n, nsec = m["nbins"], m["nsec"]
    i0 = min(n - 1, max(0, int(math.floor(t)))); f = t - math.floor(t)
    i1 = min(n - 1, max(0, i0 + 1))
    a = (theta % (2.0 * math.pi)) / (2.0 * math.pi) * nsec - 0.5
    k0 = int(math.floor(a)); g = a - k0
    k0 %= nsec; k1 = (k0 + 1) % nsec
    r0 = m["sect"][i0][k0] * (1 - g) + m["sect"][i0][k1] * g
    r1 = m["sect"][i1][k0] * (1 - g) + m["sect"][i1][k1] * g
    return r0 * (1 - f) + r1 * f


def girth_at(m, z, steps=48):
    """Circumference of the cross-section at height z."""
    prev = None; total = 0.0
    for i in range(steps + 1):
        th = 2.0 * math.pi * i / steps
        p = Vector((math.cos(th), math.sin(th), 0.0)) * radius_at(m, z, th)
        if prev is not None:
            total += (p - prev).length
        prev = p
    return total


def arc_width(m, z, th0, th1, steps=32):
    """Surface distance across the body from angle th0 to th1 at height z."""
    prev = None; total = 0.0
    for i in range(steps + 1):
        th = th0 + (th1 - th0) * i / steps
        p = Vector((math.cos(th), math.sin(th), 0.0)) * radius_at(m, z, th)
        if prev is not None:
            total += (p - prev).length
        prev = p
    return total


def slice_ok(m, z, min_cover=0.95, min_count=40):
    """Whether the cross-section at z is a complete ring of samples. Above the
    point where the head's skin weights take over, the masked profile thins
    to a partial ring and then to nothing, and the smoothed radii there are
    meaningless."""
    count, cover = m.get("count"), m.get("cover")
    if not count or not cover:
        return True
    i = int(round(_bin_t(m, z)))
    i = min(len(count) - 1, max(0, i))
    return count[i] >= min_count and cover[i] >= min_cover


def neck_girth(m):
    """Narrowest neck circumference above the shoulders (see neck_ring)."""
    return neck_ring(m)[0]


def neck_side_radius(m):
    """Half the neck's width, side to side, at the ring neck_girth reads."""
    z = neck_ring(m)[1]
    return max(radius_at(m, z, math.pi * 0.5), radius_at(m, z, -math.pi * 0.5))


def neck_ring(m):
    """True neck circumference: the narrowest slice above the shoulders. The
    'neck' landmark sits at the neck base and includes the trapezius, which is
    far too big to size a neckline from. Only near-complete rings are
    considered, and the scan stops once the head mask has eaten into the ring:
    past that the profile decays towards zero and would give a doll's neck.
    One missing sector is tolerated - on Mixamo-weighted rigs the head group
    dominates far down the neck, and demanding a perfect ring would end the
    scan at the trapezius and report the neck base as the neck."""
    z0 = z_of(m, "neck")
    best, best_z = girth_at(m, z0), z0
    z = z0
    while z < z0 + 0.13 and z < m["zmax"]:
        if not slice_ok(m, z, min_cover=0.90):
            break
        g = girth_at(m, z)
        if g < best:
            best, best_z = g, z
        z += 0.01
    return best, best_z


# ------------------------------------------------- figure

def figure_score(m):
    """Positive for a male figure, negative for a female one. Three ratios that
    differ reliably between adult bodies regardless of size: hip to chest girth,
    waist to hip girth, and shoulder width to hip width. Each term is scaled so
    that a typical figure scores about +-2 and a borderline one near 0."""
    zc, zw, zh, zs = (z_of(m, k) for k in ("chest", "waist", "hip", "shoulder"))
    chest, waist, hip = girth_at(m, zc), girth_at(m, zw), girth_at(m, zh)
    if min(chest, waist, hip) < 1e-6:
        return 0.0
    sh_w = radius_at(m, zs, math.pi * 0.5)
    hip_w = max(1e-6, radius_at(m, zh, math.pi * 0.5))
    s = (1.09 - hip / chest) * 10.0
    s += (waist / hip - 0.815) * 10.0
    s += (sh_w / hip_w - 1.045) * 10.0
    return s


def figure_guess(m):
    return 'MAN' if figure_score(m) >= 0.0 else 'WOMAN'


def figure(context, m=None):
    """The figure the blocks are drafted for: the scene override, or the guess."""
    choice = context.scene.cd.figure
    if choice != 'AUTO':
        return choice
    ob = context.scene.cd.avatar
    tag = ob.get("cd_figure") if ob is not None else None
    if tag in ('MAN', 'WOMAN'):
        return tag
    m = m or measure(context)
    if m is None:
        return 'WOMAN'
    return m.get("figure_auto") or figure_guess(m)


def z_of(m, name):
    lm = m.get("landmarks", {})
    if name in lm:
        return lm[name]
    return m["zmin"] + PROPORTIONS.get(name, 0.5) * m["height"]


# ------------------------------------------------- limbs

def limb_profile(pts, dom, keys, p0, p1, nbins=10):
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    L = axis.length
    if L < 1e-6:
        return None
    u = axis / L
    sel = [i for i, d in enumerate(dom) if any(k in d for k in keys)]
    if len(sel) < 20:
        sel = range(len(pts))
    bins = [[] for _ in range(nbins)]
    for i in sel:
        d = pts[i] - p0
        t = d.dot(u)
        if t < 0.0 or t > L:
            continue
        bins[min(nbins - 1, int(t / L * nbins))].append((d - u * t).length)
    rads, last = [], 0.05
    ok = False
    for b in bins:
        if len(b) < 4:
            rads.append(last)
        else:
            last = max(_pct(sorted(b), 0.85), 1e-4)
            rads.append(last); ok = True
    if not ok:
        return None
    # Near its root a limb merges into the torso, and how far the torso flesh
    # leaks into the limb's vertex groups is a weight-painting style: Mixamo
    # weights hand the whole deltoid (or half the glute) to the upper arm or
    # thigh, and the root bins then read a 50 cm biceps on a 161 cm figure.
    # Cap the root bins by the interior profile - a real limb never doubles
    # its girth in its top fifth. The uncapped root is kept separately: it is
    # wrong as a tube girth but right as the deltoid, which is what the
    # shoulder point of a bodice is drafted from.
    rad_root = rads[0]
    if len(rads) >= 7:
        cap = max(rads[3:7]) * 1.10
        for i in range(3):
            rads[i] = min(rads[i], cap)
    return {"p0": list(p0), "p1": list(p1), "len": L,
            "rad": _smooth(rads, 1), "rad_root": rad_root}


def head_size(pts, dom, fwd, side, zmax):
    """Length (crown down to the bottom of the head-weighted surface), depth
    (front to back) and width of the head, from the samples weighted to it."""
    head = [p for p, d in zip(pts, dom) if d == "head" or d.startswith("head")]
    if len(head) < 50:
        return None
    zs = sorted(p.z for p in head)
    z_lo = zs[int(0.02 * (len(zs) - 1))]
    top = [p for p in head if p.z > z_lo + 0.25 * (zmax - z_lo)]
    if len(top) < 30:
        return None
    fs = sorted(p.dot(fwd) for p in top)
    ss = sorted(p.dot(side) for p in top)
    # the middle of the head's box, for placing a hood over it (build's
    # HEAD anchors): halfway between the extremes front-back and side-side
    cf = (_pct(fs, 0.99) + _pct(fs, 0.01)) * 0.5
    cs = (_pct(ss, 0.99) + _pct(ss, 0.01)) * 0.5
    c = fwd * cf + side * cs
    return {"len": zmax - z_lo,
            "depth": _pct(fs, 0.99) - _pct(fs, 0.01),
            "width": _pct(ss, 0.99) - _pct(ss, 0.01),
            "center": [c.x, c.y, (zmax + z_lo) * 0.5], "z_lo": z_lo}


HAND_LABELS = ("hand", "thumb", "index", "mid", "ring", "pinky", "palm")


def palm_girth(pts, dom, elbow, wrist, nsec=24):
    """Girth round the palm of the left hand, just past the wrist, above the
    fingers: the widest of a few slices 2-6 cm along the forearm's line. The
    slice is measured as the polygon through each angular sector's furthest
    sample rather than as a circle, because a palm is flat."""
    ax = wrist - elbow
    if ax.length < 1e-6:
        return None
    ax.normalize()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = (ref - ax * ref.dot(ax)).normalized()
    v = ax.cross(u)
    hand = [p for p, d in zip(pts, dom)
            if d.endswith(".l") and d.startswith(HAND_LABELS)
            or (d.startswith("hand") and ("left" in d or d.endswith("_l")))]
    if len(hand) < 30:
        return None
    best = 0.0
    for t in (0.02, 0.03, 0.04, 0.05, 0.06):
        rad = [0.0] * nsec
        n = 0
        for p in hand:
            q = p - wrist
            a = q.dot(ax)
            if abs(a - t) > 0.006:
                continue
            q = q - ax * a
            if q.length > 0.10:
                continue
            k = int((math.atan2(q.dot(v), q.dot(u)) % (2 * math.pi)) / (2 * math.pi) * nsec) % nsec
            rad[k] = max(rad[k], q.length)
            n += 1
        if n < 12 or sum(1 for r in rad if r > 0) < nsec * 0.6:
            continue
        known = [k for k in range(nsec) if rad[k] > 0]
        for k in range(nsec):
            if rad[k] <= 0:
                j = min(known, key=lambda j: min(abs(j - k), nsec - abs(j - k)))
                rad[k] = rad[j]
        per = 0.0
        for k in range(nsec):
            a0, a1 = 2 * math.pi * k / nsec, 2 * math.pi * (k + 1) / nsec
            p0 = Vector((math.cos(a0), math.sin(a0))) * rad[k]
            p1 = Vector((math.cos(a1), math.sin(a1))) * rad[(k + 1) % nsec]
            per += (p1 - p0).length
        best = max(best, per)
    return best or None


def limb_radius_at(lp, t):
    return _lerp1(lp["rad"], t * len(lp["rad"]) - 0.5)


def limb_frame(lp):
    """(origin, axis, u, v) orthonormal frame for a limb."""
    p0, p1 = Vector(lp["p0"]), Vector(lp["p1"])
    ax = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = (ref - ax * ref.dot(ax)).normalized()
    v = ax.cross(u)
    return p0, ax, u, v


# ------------------------------------------------- top level

_CACHE = {}


def measure(context, ob=None, force=False):
    scn = context.scene
    ob = ob or scn.cd.avatar
    if ob is None or ob.type != 'MESH':
        return None
    # MEASURE_VERSION in the key: a .blend saved by an older version keeps
    # its measurement (The Beast measured with 0 of 8 limbs before the CATS
    # names were known) until the measuring code changes
    key = [ob.name, scn.frame_current, scn.cd.facing, MEASURE_VERSION]
    if not force and _CACHE.get("key") == key:
        return _CACHE.get("data")
    if not force and "cd_measure" in scn:
        try:
            data = json.loads(scn["cd_measure"])
            if data.get("key") == key:
                _CACHE["key"] = key; _CACHE["data"] = data
                return data
        except Exception:
            pass

    depsgraph = context.evaluated_depsgraph_get()
    pts, dom = sample_body(ob, depsgraph)
    if not pts:
        return None
    arm = find_armature(ob)
    # a head kept as its own mesh (usual on Booth avatars, for the face
    # shape keys) is part of the body being measured: without it the stature
    # is short by a head and every proportional fallback lands too low
    comps = companion_meshes(context, ob, arm)
    for c in comps:
        cp, cd = sample_body(c, depsgraph)
        pts += cp; dom += cd
    fwd, side = basis(scn.cd.facing)
    hm = rig.humanoid_map(arm)
    # no horns, animal ears, tails or wings: not in the stature, the head
    # a hood is sized to, or any cross-section
    bin_top = max(p.z for p in pts)
    pts, dom = drop_nonhuman(pts, dom, arm, hm)

    m = build_profile(pts, dom, fwd, side, bin_top=bin_top)

    lm = {}
    if arm is not None:
        mw = arm.matrix_world
        for name, cands in BONE_TABLE.items():
            b = find_part(arm, HUMANOID_LANDMARKS.get(name), cands, hm)
            if b is not None:
                lm[name] = (mw @ b.head).z
    m["landmarks"] = lm

    m["limbs"] = {}
    if arm is not None:
        mw = arm.matrix_world
        for name, (ka, kb) in LIMB_CHAINS.items():
            pa, pb_ = HUMANOID_CHAINS.get(name, (None, None))
            ba, bb = find_part(arm, pa, ka, hm), find_part(arm, pb_, kb, hm)
            if ba is None or bb is None:
                continue
            lp = limb_profile(pts, dom, LIMB_GROUPS.get(name, ()),
                              mw @ ba.head, mw @ bb.head)
            if lp:
                m["limbs"][name] = lp
        # the palm, which a long sleeve's cuff has to pass over: on anime
        # proportions the hand is far bigger than the wrist the cuff is
        # otherwise drafted from (Mao: wrist 14 cm, palm well over 20)
        fl = m["limbs"].get("farm_l")
        if fl:
            pg = palm_girth(pts, dom, Vector(fl["p0"]), Vector(fl["p1"]))
            if pg:
                m["palm_girth"] = pg
        if "arm_l" in m["limbs"]:
            lm["shoulder"] = Vector(m["limbs"]["arm_l"]["p0"]).z
    # the head, which a hood has to go over: anime heads are large against a
    # slim neck, so a hood sized from the neck girth comes out far too small
    hd = head_size(pts, dom, fwd, side, m["zmax"])
    if hd:
        m["head"] = hd
        if "thigh_l" in m["limbs"]:
            lm["crotch"] = Vector(m["limbs"]["thigh_l"]["p0"]).z
        if "calf_l" in m["limbs"]:
            lm["knee"] = Vector(m["limbs"]["calf_l"]["p0"]).z

    # The rig's waist bone sits low, near the navel. The anatomical waist - and
    # where a skirt or trouser waistband belongs - is the narrowest section
    # between hip and chest, so use that when the profile shows one.
    try:
        zh, zc = lm.get("hip"), lm.get("chest")
        if zh is not None and zc is not None and zc > zh + 0.08:
            best_z, best_g = None, 1e9
            z = zh + 0.03
            while z < zc - 0.02:
                g = girth_at(m, z)
                if g < best_g:
                    best_g, best_z = g, z
                z += 0.01
            if best_z is not None:
                lm["waist"] = best_z
    except Exception:
        pass
    # and the chest: the fullest section between waist and shoulder, not the
    # rig's chest bone. Where that bone sits is a rigging convention, not
    # anatomy - CC4 puts it at 71 % of stature and Mixamo at 76 %, which is
    # 8 cm on the same body and changes every armhole drafted from it. The
    # widest cross-section is the bust line whatever rig is underneath.
    try:
        zw, zs = lm.get("waist"), lm.get("shoulder")
        if zw is not None and zs is not None and zs > zw + 0.12:
            best_z, best_g = None, -1.0
            z = zw + 0.04
            while z < zs - 0.04:
                if slice_ok(m, z, min_cover=0.90):
                    g = girth_at(m, z)
                    if g > best_g:
                        best_g, best_z = g, z
                z += 0.01
            if best_z is not None:
                lm["chest"] = best_z
    except Exception:
        pass
    # likewise the hip: the widest section over the seat, not the pelvis bone
    try:
        zcr, zw = lm.get("crotch"), lm.get("waist")
        if zcr is not None and zw is not None and zw > zcr + 0.10:
            best_z, best_g = None, -1.0
            z = zcr + 0.02
            while z < zw - 0.05:
                g = girth_at(m, z)
                if g > best_g:
                    best_g, best_z = g, z
                z += 0.01
            if best_z is not None:
                lm["hip"] = best_z
    except Exception:
        pass
    m["landmarks"] = lm

    m["armature"] = arm.name if arm else ""
    m["companions"] = [c.name for c in comps]
    m["rig"] = rig.describe(arm) if arm else {"found": 0, "of": 17, "missing": [], "bones": {}}
    m["facing"] = scn.cd.facing
    m["figure_auto"] = figure_guess(m)
    m["key"] = key
    scn["cd_measure"] = json.dumps(m)
    _CACHE["key"] = key; _CACHE["data"] = m
    return m


def _head_span(ob):
    """Vertical extent (m) of a mesh's vertices weighted mostly to the head."""
    head = {g.index for g in ob.vertex_groups if rig.parse(g.name)[0] == "head"}
    if not head:
        return 0.0
    mw = ob.matrix_world
    zs = [(mw @ v.co).z for v in ob.data.vertices
          if v.groups and max(v.groups, key=lambda g: g.weight).group in head]
    return (max(zs) - min(zs)) if len(zs) > 20 else 0.0


def companion_meshes(context, ob, arm=None):
    """Other meshes deformed by the avatar's armature that are body parts of
    their own - a head kept separate for the face shape keys (Hanka, Mao,
    Vlau). Only looked for when the body itself has no head: its own
    head-weighted vertices span less than 10 cm (a neck stump). A mesh counts
    when nearly all its vertices are weighted to the head, neck or eyes; hair
    and accessories hang off their own bones. A face mesh carries eye groups,
    so it wins over anything else that qualifies."""
    arm = arm or find_armature(ob)
    if arm is None or _head_span(ob) >= 0.10:
        return []
    out = []
    for o in context.scene.objects:
        if o == ob or o.type != 'MESH' or o.cd.is_pattern or o.cd.is_garment or "cd_src" in o:
            continue
        if find_armature(o) != arm or len(o.data.vertices) < 500:
            continue
        if not o.visible_get():
            continue
        headish = {g.index for g in o.vertex_groups if rig.is_head_group(g.name)}
        if not headish:
            continue
        n = hits = 0
        for v in o.data.vertices:
            n += 1
            if v.groups and max(v.groups, key=lambda g: g.weight).group in headish:
                hits += 1
        if n and hits >= 0.85 * n:
            eyes = any(rig.parse(g.name)[0] not in ("head", "neck")
                       for g in o.vertex_groups if g.index in headish)
            out.append((eyes, n, o))
    if not out:
        return []
    out.sort(key=lambda t: (t[0], t[1]), reverse=True)
    head = out[0][2]
    proxy = _head_proxy(context, head, arm)
    return [head, proxy] if proxy is not None else [head]


PROXY_NAME = "CD_HeadProxy"
OPEN_SKULL = 0.25   # a hole this long round the top of a head mesh: no scalp


def _open_skull(ob):
    """Whether a head mesh is a bowl with no scalp (Mao: the top and back of
    the skull are left to the hair mesh, a 0.56 m hole between 1.40 and
    1.48 m). Its longest boundary loop runs that far round, in the upper half
    of the mesh; eyes and mouth leave only short loops."""
    import bmesh
    bm = bmesh.new()
    try:
        bm.from_mesh(ob.data)
        mw = ob.matrix_world
        zs = [(mw @ v.co).z for v in bm.verts]
        if not zs:
            return False
        z_mid = (min(zs) + max(zs)) * 0.5
        bnd = [e for e in bm.edges if e.is_boundary]
        seen, best = set(), (0.0, 0.0)
        adj = {}
        for e in bnd:
            for v in e.verts:
                adj.setdefault(v, []).append(e)
        for e in bnd:
            if e in seen:
                continue
            stack, per, zsum, n = [e], 0.0, 0.0, 0
            while stack:
                x = stack.pop()
                if x in seen:
                    continue
                seen.add(x)
                a, b = (mw @ x.verts[0].co), (mw @ x.verts[1].co)
                per += (a - b).length
                zsum += (a.z + b.z) * 0.5
                n += 1
                for v in x.verts:
                    stack += [y for y in adj[v] if y not in seen]
            if per > best[0]:
                best = (per, zsum / max(n, 1))
        return best[0] > OPEN_SKULL and best[1] > z_mid
    finally:
        bm.free()


def _shell_count(ob):
    """Connected pieces in a mesh."""
    me = ob.data
    parent = list(range(len(me.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    return len({find(i) for i in range(len(me.vertices))})


def collider_meshes(context, ob):
    """The avatar's other meshes that cloth should collide with: its separate
    head, or that head's closed proxy instead of it when there is one (with
    the nape below it, see _nape_proxy)."""
    comps = companion_meshes(context, ob)
    px = [c for c in comps if c.name == PROXY_NAME]
    if px:
        nape = _nape_proxy(context, comps[0], px[0], ob)
        return px + [nape] if nape is not None else px
    return comps


NAPE_PROXY = "CD_HeadProxyNape"
NAPE_OVERLAP = 0.02   # how far the nape's hull reaches up into the head proxy


def _nape_proxy(context, head, proxy, body):
    """The back of the head below its proxy, as a collider of its own.

    The proxy is the hull of the head's upper three quarters (the lower
    quarter is jaw and neck stump, which a hull would fill in under the
    chin), and it replaces the head as a collider. On Hanka the body mesh
    ends 2.5 cm below that cut, so nothing held cloth out of the nape in
    between: a hood's back neck sank into it and the head showed through
    the hood there (the 'gap at the nape' of Fases 4-5). This is the hull of
    the head's vertices behind its centre from just under the top of the
    body mesh to just above the proxy's cut: the nape, nothing under the
    chin, and not the neck stump inside the body's own neck (reaching down
    to the head mesh's bottom it held the back neckline out, and the back of
    the hoodie folded in two vertical creases). Only beside a closed head's proxy (an open skull's - Mao, Manuka -
    is left as it was). Not a companion mesh: colliders only, never measured.
    """
    import bpy
    import bmesh
    old = bpy.data.objects.get(NAPE_PROXY)
    if proxy.get("cd_open"):
        return None
    if old is not None and old.get("cd_src") == head.name:
        return old
    if old is not None:
        bpy.data.objects.remove(old)
    dg = context.evaluated_depsgraph_get()
    ev = head.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        pts = [ev.matrix_world @ v.co for v in me.vertices]
    finally:
        ev.to_mesh_clear()
    pz = [(proxy.matrix_world @ v.co).z for v in proxy.data.vertices]
    if not pts or not pz:
        return None
    z_cut = min(pz) + NAPE_OVERLAP
    eb = body.evaluated_get(dg)
    bme = eb.to_mesh()
    try:
        z_body = max((eb.matrix_world @ v.co).z for v in bme.vertices) if len(bme.vertices) else -1e9
    finally:
        eb.to_mesh_clear()
    z_from = z_body - NAPE_OVERLAP * 0.5
    fwd, _side = basis(context.scene.cd.facing)
    c = sum(pts, Vector()) / len(pts)
    pts = [p for p in pts if z_from < p.z < z_cut and (p - c).dot(fwd) <= 0.0]
    if len(pts) < 8:
        return None
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    try:
        bmesh.ops.convex_hull(bm, input=bm.verts[:])
    except Exception:
        bm.free()
        return None
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    if not bm.faces:
        bm.free()
        return None
    mesh = bpy.data.meshes.new(NAPE_PROXY)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(NAPE_PROXY, mesh)
    ob["cd_src"] = head.name
    context.scene.collection.objects.link(ob)
    ob.hide_render = True
    ob.display_type = 'WIRE'
    if proxy.parent is not None:
        mw = ob.matrix_world.copy()
        ob.parent = proxy.parent
        ob.parent_type = proxy.parent_type
        ob.parent_bone = proxy.parent_bone
        ob.matrix_world = mw
    return ob


def _head_proxy(context, head, arm):
    """A closed head to collide with and lay a hood on, when the head mesh
    has no scalp: the convex hull of its upper part, parented to the head
    bone so it follows the pose. Without it a hood sank into the bowl and
    its crown seam could never close (Mao). None for a closed head."""
    import bpy
    import bmesh
    old = bpy.data.objects.get(PROXY_NAME)
    if old is not None and old.get("cd_src") == head.name:
        return old
    open_skull = _open_skull(head)
    shells = _shell_count(head)
    # also for a head made of many loose shells (Hanka: 130 - face, skull,
    # eyes, lashes - with double walls 3-9 mm apart in the face): cloth
    # caught on the lashes and between the walls, and a hood's front came
    # down over her eyes in every variant tried
    if not open_skull and shells <= 1:
        return None
    if old is not None:
        bpy.data.objects.remove(old)
    dg = context.evaluated_depsgraph_get()
    ev = head.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        pts = [ev.matrix_world @ v.co for v in me.vertices]
    finally:
        ev.to_mesh_clear()
    z_lo, z_hi = min(p.z for p in pts), max(p.z for p in pts)
    pts = [p for p in pts if p.z > z_lo + 0.25 * (z_hi - z_lo)]
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    mesh = bpy.data.meshes.new(PROXY_NAME)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(PROXY_NAME, mesh)
    ob["cd_src"] = head.name
    ob["cd_open"] = bool(open_skull)
    context.scene.collection.objects.link(ob)
    ob.hide_render = True
    ob.display_type = 'WIRE'
    hb = next((b for b in arm.data.bones if rig.parse(b.name)[0] == "head"), None)
    if hb is not None:
        mw = ob.matrix_world.copy()
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = hb.name
        ob.matrix_world = mw
    return ob


_BODY_PARTS = 17   # rig.describe's list: trunk, head, and six parts per side


def _humanoid_share(ob):
    """How much of a humanoid body a mesh covers: the share of distinct body
    parts (hips, spine, each upper arm...) that dominate some of its vertices.
    Hair weighted to the head covers one part; a body covers them all."""
    lab = {}
    for g in ob.vertex_groups:
        part, side = rig.parse(g.name)
        if part and not part.startswith("finger_"):
            lab[g.index] = part + side
    seen = set()
    for v in ob.data.vertices:
        if v.groups:
            k = lab.get(max(v.groups, key=lambda g: g.weight).group)
            if k:
                seen.add(k)
    return min(1.0, len(seen) / float(_BODY_PARTS))


def mesh_height(ob):
    """World-space height of a mesh's bounding box."""
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return max(p.z for p in bb) - min(p.z for p in bb)


def auto_avatar(context):
    best, best_score = None, 0.0
    for ob in context.scene.objects:
        if ob.type != 'MESH' or ob.cd.is_pattern or ob.cd.is_garment or "cd_src" in ob:
            continue
        if not ob.visible_get() or len(ob.data.vertices) < 200:
            continue
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        h = max(p.z for p in bb) - min(p.z for p in bb)
        skinned = any(mod.type == 'ARMATURE' for mod in ob.modifiers)
        score = h * (2.0 if skinned else 1.0)
        if skinned:
            # Long hair, a tail or a coat can stand as tall as the body (Minase's
            # hair is 1 cm shorter than her body). The body is the mesh whose
            # weights sit on humanoid parts rather than on physics bones.
            score *= 0.25 + _humanoid_share(ob)
        if score > best_score:
            best_score, best = score, ob
    return best


def auto_facing(context, ob):
    depsgraph = context.evaluated_depsgraph_get()
    pts, dom = sample_body(ob, depsgraph)
    return guess_facing(find_armature(ob), pts, dom)


# ---------------------------------------------------------------- collision proxy

BODY_PROXY = "CD_BodyCollider"


def _nonhuman_islands(context, ob):
    """Vertex indices of the loose parts of the body mesh that stand over the
    crown of the skull: horns, animal ears, a halo modelled into the body
    (The Beast's two horns, 201 vertices each, 2.15 to 2.39 m over a skull
    that ends at 2.24). Only looked for when measuring found the body's top
    above the crown (drop_nonhuman); a part counts when it starts above the
    head bone and reaches past the crown."""
    m = measure(context, ob)
    if not m or m.get("bin_h", m["height"]) <= m["height"] + CROWN_MARGIN:
        return []
    arm = find_armature(ob)
    hb = rig.humanoid_map(arm).get("head") if arm is not None else None
    if hb is None:
        return []
    z_base = (arm.matrix_world @ hb.head).z
    crown = m["zmax"]
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        if len(me.vertices) != len(ob.data.vertices):
            return []
        zs = [(ev.matrix_world @ v.co).z for v in me.vertices]
    finally:
        ev.to_mesh_clear()
    me = ob.data
    parent = list(range(len(me.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    parts = {}
    for i in range(len(me.vertices)):
        parts.setdefault(find(i), []).append(i)
    out = []
    for vs in parts.values():
        lo = min(zs[i] for i in vs)
        hi = max(zs[i] for i in vs)
        if lo > z_base and hi > crown + CROWN_MARGIN and len(vs) < 0.10 * len(me.vertices):
            out += vs
    return out


def collision_body(context, ob):
    """The body for cloth to collide with and garments to be laid against:
    the avatar itself, or when it has horns or ears modelled into it, a copy
    without them (BODY_PROXY, deformed by the same armature). Those parts
    are left to go through the clothes - with them colliding, The Beast's
    horns held his hood up and it fell in over his face."""
    import bpy
    import bmesh
    old = bpy.data.objects.get(BODY_PROXY)
    if old is not None and old.get("cd_src") == ob.name:
        return old
    drop = _nonhuman_islands(context, ob)
    if old is not None:
        bpy.data.objects.remove(old)
    if not drop:
        return ob
    px = ob.copy()
    px.data = ob.data.copy()
    px.name = BODY_PROXY
    px.data.name = BODY_PROXY
    bm = bmesh.new()
    try:
        bm.from_mesh(px.data)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.verts[i] for i in drop], context='VERTS')
        bm.to_mesh(px.data)
    finally:
        bm.free()
    px["cd_src"] = ob.name
    context.scene.collection.objects.link(px)
    px.hide_render = True
    px.display_type = 'WIRE'
    return px


_BVH = {}


def body_bvh(context, ob=None):
    """World-space BVH of the avatar, for keeping arranged panels out of the body."""
    ob = ob or context.scene.cd.avatar
    if ob is None or ob.type != 'MESH':
        return None
    key = (ob.name, context.scene.frame_current)
    if _BVH.get("key") == key:
        return _BVH.get("tree")
    dg = context.evaluated_depsgraph_get()
    is_av = ob == context.scene.cd.avatar
    src = collision_body(context, ob) if is_av else ob
    ev = src.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        return None
    try:
        me.calc_loop_triangles()
    except Exception:
        pass
    mw = ev.matrix_world.copy()
    verts = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    ev.to_mesh_clear()
    # and a separate head (or its proxy): pushing welded seams out of the
    # body did not see Hanka's head at all
    try:
        extra = collider_meshes(context, ob) if is_av else []
    except Exception:
        extra = []
    for c in extra:
        ec = c.evaluated_get(dg)
        cm = ec.to_mesh()
        try:
            cm.calc_loop_triangles()
            base = len(verts)
            verts += [ec.matrix_world @ v.co for v in cm.vertices]
            tris += [tuple(base + i for i in t.vertices) for t in cm.loop_triangles]
        finally:
            ec.to_mesh_clear()
    if not tris:
        return None
    tree = BVHTree.FromPolygons(verts, tris)
    _BVH["key"] = key
    _BVH["tree"] = tree
    return tree


def torso_bvh(context, ob=None):
    """BVH of the torso only. Seam detection tests whether the body sits between
    two panel edges; including the arms would block legitimate side seams on a
    figure standing with its arms down."""
    ob = ob or context.scene.cd.avatar
    if ob is None or ob.type != 'MESH':
        return None
    key = (ob.name, context.scene.frame_current, "torso")
    if _BVH.get("tkey") == key:
        return _BVH.get("ttree")
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
        me.calc_loop_triangles()
    except Exception:
        return None
    mw = ev.matrix_world.copy()
    gname = group_labels(ob)
    excl = []
    for v in me.vertices:
        d = ""
        if v.groups:
            d = gname.get(max(v.groups, key=lambda g: g.weight).group, "")
        excl.append(any(k in d for k in EXCLUDE_TORSO))
    verts = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles
            if not (excl[t.vertices[0]] and excl[t.vertices[1]] and excl[t.vertices[2]])]
    ev.to_mesh_clear()
    if not tris:
        return None
    tree = BVHTree.FromPolygons(verts, tris)
    _BVH["tkey"] = key
    _BVH["ttree"] = tree
    return tree


def push_out(co, bvh, clearance, max_move=0.06):
    """Lift a point clear of the body along the surface normal.

    Only the shortfall is added; snapping the point onto nearest-surface +
    clearance instead would collapse whole rings of verts onto the same spot
    wherever geometry crowds the surface, such as a sleeve at the armpit.
    """
    hit = bvh.find_nearest(co)
    if hit is None or hit[0] is None:
        return co
    loc, nor = hit[0], hit[1]
    gap = (co - loc).dot(nor)
    if gap >= clearance:
        return co
    return co + nor * min(clearance - gap, max_move)
