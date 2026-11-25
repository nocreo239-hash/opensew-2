# Clothing Design - parametric garment presets.
#
# Each preset returns pattern pieces sized from the measured avatar plus the
# seams joining them, so adding a garment gives a complete sewn set rather than
# loose panels. Panel local +X is always the character's LEFT; build.py mirrors
# that axis for back-facing panels so side seams meet correctly.
import math
from mathutils import Vector
from . import avatar, patterns



def _ellipse_circ(a, b):
    """Ramanujan's approximation."""
    return math.pi * (3.0 * (a + b) - math.sqrt(max(0.0, (3 * a + b) * (a + 3 * b))))


def _curve_len(pts):
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def _solve(fn, target, lo, hi, iters=40):
    """Bisection on a monotonically increasing fn."""
    if fn(lo) >= target:
        return lo
    if fn(hi) <= target:
        return hi
    for _ in range(iters):
        mid = (lo + hi) * 0.5
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


NECK_MAX_SHARE = 0.55   # widest sleeveless neckline, as a share of the half shoulder width
NECK_MIN_CLEAR = 0.015  # ...but at least this far out from the side of the neck


def _neck_half(girth, df, db, fac=1.12):
    """Half-width of a neckline whose opening measures fac x the neck girth."""
    return _solve(lambda w: 0.5 * _ellipse_circ(w, df) + 0.5 * _ellipse_circ(w, db),
                  girth * fac, 0.02, 0.30)


def _cap_pts(cw, cap_h):
    """A set-in sleeve cap: back half then front half, apex at x = 0.

    A real cap is an S-curve - hollowed just above the underarm, full and
    rounded over the head of the arm - and the front half is scooped a
    little deeper than the back, because the front armhole is. Drawn as a
    plain arc it comes out a tent, and a tent-shaped cap sewn into a curved
    armhole is what puts those diagonal creases across the shoulder.
    """
    back = patterns.bezier((cw * 0.5, 0.0), (cw * 0.44, cap_h * 0.30),
                           (cw * 0.28, cap_h * 0.95), (0.0, cap_h), 18)
    front = patterns.bezier((0.0, cap_h), (-cw * 0.24, cap_h * 0.95),
                            (-cw * 0.46, cap_h * 0.26), (-cw * 0.5, 0.0), 18)
    return front, back


def _cap_len(cw, cap_h):
    f, b = _cap_pts(cw, cap_h)
    return _curve_len(f) + _curve_len(b)


def _armhole_len(half, sh_x, arm_d, sh_drop):
    """Length of one armhole curve (front or back)."""
    c = patterns.bezier((half, -arm_d), (half, -arm_d * 0.45),
                        (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 24)
    return _curve_len(c)


def _seg(name, pts):
    return (name, [Vector(p) for p in pts])


def _measurements(m):
    z = {k: avatar.z_of(m, k) for k in ("neck", "shoulder", "chest", "waist", "hip", "knee", "crotch", "ankle")}
    g = {k: avatar.girth_at(m, z[k]) for k in ("neck", "chest", "waist", "hip")}
    # in-between hem lines for the length control: mid-thigh (shorts, a mini
    # dress) and mid-calf (a midi dress or coat)
    z["thigh"] = z["crotch"] + (z["knee"] - z["crotch"]) * 0.45
    z["calf"] = z["knee"] + (z["ankle"] - z["knee"]) * 0.5
    c = avatar.center_at(m, z["shoulder"])
    shoulder_half = 0.5 * m["height"] * 0.17
    lp = m.get("limbs", {}).get("arm_l")
    if lp:
        p0 = Vector(lp["p0"])
        # the deltoid: the uncapped limb root, not the biceps-safe tube radius
        r0 = lp.get("rad_root", avatar.limb_radius_at(lp, 0.0))
        shoulder_half = abs((p0 - avatar.center_at(m, p0.z)).length) + r0 * 0.6
    return z, g, shoulder_half


# ---------------------------------------------------------------- figure

# Drafting proportions that differ between men's and women's blocks. Girths
# always come from the avatar; these are the rules a cutter applies on top of
# them (Aldrich-style metric drafting, rounded to what the simulator resolves).
FIGURE = {
    'WOMAN': dict(
        neck_front=0.075, neck_back=0.022,      # scooped front, shallow back
        tank_front=0.095, tank_back=0.030,
        sh_drop=0.055, sh_x=0.93,               # sloped, narrower shoulder point
        top_extra=0.03,                         # cut past the hip: the stitch
                                                # phase hoists a top a few cm
        shape_waist=True,                       # side seams follow the waist in
        hem_hip=1.0,                            # hem cut to the hip girth
        tee_sleeve=0.15, sleeve_hem=0.82,       # short sleeve, narrow cuff
        rise=1.0,                               # trousers sit at the natural waist
    ),
    'MAN': dict(
        neck_front=0.060, neck_back=0.022,      # crew neck
        tank_front=0.085, tank_back=0.030,
        sh_drop=0.045, sh_x=1.0,                # squarer, full-width shoulder
        top_extra=0.065,                        # tops cover the hip, plus the
                                                # few cm the stitch hoists them
        shape_waist=False,                      # straight side seams
        hem_hip=0.98,                           # hem skims the hip
        tee_sleeve=0.20, sleeve_hem=0.88,       # longer sleeve, open cuff
        rise=0.78,                              # waistband below the natural waist
    ),
}


def _fig(m):
    return FIGURE.get(m.get("figure") or m.get("figure_auto") or 'WOMAN', FIGURE['WOMAN'])


UNDERARM_T = 0.10  # the sleeve's underarm line, as a fraction along the arm


def _sleeve_height(cap_h, length, arm_total):
    """Where the sleeve's centre sits, as a fraction along the arm, so that
    its UNDERARM line lands UNDERARM_T along the arm - just past the armpit.

    A limb piece is anchored at the centre of its bounding box (patterns.py
    centres every piece), and a sleeve runs from the cap top (+L/2) down to
    the cuff (-L/2), L = cap + length. Upstream returned a fixed 0.22 as if
    the underarm were the anchor: the underarm then landed about 0.3 of the
    arm *inside* the shoulder joint - in the torso - and the cap was crushed
    against the -0.25 clamp of the limb mapping. On a short arm (Mao) the
    seam has to drag the whole cap 15-20 cm back over the shoulder and the
    armpit stitches never close.
    """
    if arm_total <= 1e-6:
        return 0.0
    half = (length + cap_h) * 0.5
    return UNDERARM_T + (half - cap_h) / arm_total


def _side_curve(hem, waist, top, n=7):
    """A side seam from the hem up through the waist to the underarm, with a
    vertical tangent at each end and at the waist so the seam reads as one
    smooth line rather than a kink at the waist."""
    dy1 = (waist[1] - hem[1]) * 0.5
    dy2 = (top[1] - waist[1]) * 0.5
    a = patterns.bezier(hem, (hem[0], hem[1] + dy1), (waist[0], waist[1] - dy1), waist, n)
    b = patterns.bezier(waist, (waist[0], waist[1] + dy2), (top[0], top[1] - dy2), top, n)
    return a + b[1:]


def _sides(m, fit, half, hem_half, L, arm_d):
    """Left side seam (hem -> underarm) and its mirror (underarm -> hem). For a
    shaped figure the seam goes in at the waist when the panel reaches below
    it; the amount is the side seam's share of the chest-to-waist difference,
    capped so an unusually small waist never pinches the cloth."""
    z, g, _ = _measurements(m)
    f = _fig(m)
    L_w = z["shoulder"] + SHELF - z["waist"]
    if f["shape_waist"] and L > L_w + 0.05 and L_w > arm_d + 0.04:
        waist_half = g["waist"] * 0.5 * (1.0 + fit) * 0.5 + 0.010
        waist_half = max(waist_half, min(half, hem_half) - 0.022)
        waist_half = min(waist_half, half, hem_half)
        left = _side_curve((hem_half, -L), (waist_half, -L_w), (half, -arm_d))
    else:
        left = [Vector((hem_half, -L)), Vector((half, -arm_d))]
    right = [Vector((-p[0], p[1])) for p in reversed(left)]
    return ("side_L", [Vector(p) for p in left]), ("side_R", right)


def _hem_half(m, fit, half, length_to):
    """Hem width of a top: chest-based, but never narrower than the hips it
    has to pass when the hem reaches them."""
    z, g, _ = _measurements(m)
    f = _fig(m)
    if z[length_to] <= z["hip"] + 0.03:
        return max(half, g["hip"] * 0.5 * (1.0 + fit) * 0.5 * f["hem_hip"])
    return half


# ---------------------------------------------------------------- tops

SHELF = 0.040   # how far the top of the shoulder sits above the arm joint


def _bodice(m, fit, length_to, neck_depth, neck_half, arm_d, sh_x, sh_drop=0.050,
            hem_half=None, split_hem=False, hem_dip=0.0, split_neck=False,
            scye_x=None, extra_len=0.0):
    z, g, _ = _measurements(m)
    f = _fig(m)
    w = g["chest"] * 0.5 * (1.0 + fit)
    half = w * 0.5
    scye_x = half if scye_x is None else scye_x
    hem_half = _hem_half(m, fit, half, length_to) if hem_half is None else hem_half
    L = max(z["shoulder"] + SHELF - z[length_to], 0.12) + 0.03 + f["top_extra"] + extra_len

    armhole_L = patterns.bezier((scye_x, -arm_d), (scye_x, -arm_d * 0.45),
                                (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 12)
    armhole_R = [Vector((-p.x, p.y)) for p in reversed(armhole_L)]
    neck = patterns.bezier((neck_half, 0.0), (neck_half * 0.55, -neck_depth),
                           (-neck_half * 0.55, -neck_depth), (-neck_half, 0.0), 14)
    if split_neck:
        half_n = len(neck) // 2
        neck_l, neck_r = neck[:half_n + 1], neck[half_n:]
    # a crotch curve: the hem dips between the legs so it reaches the leg tops
    hem = ([_seg("leg_R", [(-hem_half, -L), (-hem_half * 0.35, -L - hem_dip * 0.45),
                           (0.0, -L - hem_dip)]),
            _seg("leg_L", [(0.0, -L - hem_dip), (hem_half * 0.35, -L - hem_dip * 0.45),
                           (hem_half, -L)])]
           if split_hem else
           [_seg("hem", [(-hem_half, -L), (hem_half, -L)])])
    side_L, side_R = _sides(m, fit, scye_x, hem_half, L, arm_d)
    segs = hem + [
        side_L,
        ("arm_L",          armhole_L),
        _seg("shoulder_L", [(sh_x, -sh_drop), (neck_half, 0.0)]),
    ] + ([("neck_L", neck_l), ("neck_R", neck_r)] if split_neck else [("neck", neck)]) + [
        _seg("shoulder_R", [(-neck_half, 0.0), (-sh_x, -sh_drop)]),
        ("arm_R",          armhole_R),
        side_R,
    ]
    return segs, dict(z=z, g=g, half=half, hem_half=hem_half, L=L, arm_d=arm_d,
                      sh_x=sh_x, sh_drop=sh_drop)


def _draft_top(m, fit, sleeveless=False, sh_ext=1.0):
    """Work out neckline, armhole and sleeve so the cap actually fits the armhole."""
    z, g, sh_half = _measurements(m)
    f = _fig(m)
    half = g["chest"] * 0.5 * (1.0 + fit) * 0.5
    sh_drop = f["sh_drop"]
    # Outerwear is cut to the shoulder tip or a little past it (sh_ext): a
    # shoulder seam that stops short leaves the deltoid outside the panel,
    # and the armhole curve then starts inboard of the shoulder, so the top
    # of the arm is bare between the body and the sleeve head.
    sh_x = min(sh_half * f["sh_x"] * sh_ext, half * 0.98)
    df = f["neck_front"] if not sleeveless else f["tank_front"]
    db = f["neck_back"] if not sleeveless else f["tank_back"]
    ng = avatar.neck_girth(m)
    neck_half = _neck_half(ng, df, db, 1.12 if not sleeveless else 1.35)
    if sleeveless:
        # A neck as thick as The Beast's (82 cm on a 2.36 m body, with
        # trapezius sloping out to the shoulder) put a sleeveless neckline at
        # 88 % of the shoulder width: the straps sat on the shoulder tip and
        # slid off down the arms. Elsewhere it is 17-46 %, so the cap only
        # touches bodies like his. Sleeved tops keep their neckline: narrowed,
        # the longer shoulder seam pulled the sleeves off the shoulders.
        # never so narrow the strap meets the side of the neck, though
        floor = avatar.neck_side_radius(m) + NECK_MIN_CLEAR
        neck_half = min(neck_half, max(sh_half * NECK_MAX_SHARE, floor))
        sh_x = min(sh_x, neck_half + 0.050)

    lp = m.get("limbs", {}).get("arm_l")
    biceps_r = avatar.limb_radius_at(lp, 0.12) if lp else 0.05
    biceps = 2.0 * math.pi * biceps_r

    # The armhole DEPTH is anatomy: the shoulder line down to the armpit,
    # plus a little drop for comfort. Solving the depth from a required
    # length instead - which is what this used to do - drives the underarm
    # down to the waist on a figure with a full arm, and the sleeve, sewn at
    # the armpit where it belongs, then cannot reach it: the armhole seam
    # never closes and the shoulder is left bare through the gap.
    if lp:
        z_armpit = Vector(lp["p0"]).z - lp.get("rad_root", biceps_r)
    else:
        z_armpit = z["chest"]
    anat = (z["shoulder"] + SHELF) - z_armpit + 0.03

    # The armhole has to measure the arm root it is sewn around, and it is
    # allowed to drop below the armpit to get there - but only so far. Left
    # to solve freely it reached the waist on a full arm; held to anatomy it
    # was too short for any sleeve to fit. So: solve the depth, but never
    # more than 10 cm below the armpit, and buy any remaining length
    # sideways at the scye rather than going deeper still.
    need = biceps * (1.35 if not sleeveless else 1.05)
    arm_d = _solve(lambda t: 2.0 * _armhole_len(half, sh_x, t, sh_drop),
                   need, max(0.10, anat), anat + 0.10)
    scye = _solve(lambda e: 2.0 * _armhole_len(half + e, sh_x, arm_d, sh_drop),
                  need, 0.0, 0.05)
    scye_x = half + scye
    ah = 2.0 * _armhole_len(scye_x, sh_x, arm_d, sh_drop)
    return dict(neck_half=neck_half, df=df, db=db, arm_d=arm_d, sh_x=sh_x,
                sh_drop=sh_drop, half=half, scye_x=scye_x, armhole=ah,
                biceps=biceps, biceps_r=biceps_r,
                sleeve_hem=f["sleeve_hem"], tee_sleeve=f["tee_sleeve"],
                palm=m.get("palm_girth"),
                arm_total=sum(m.get("limbs", {}).get(k, {}).get("len", 0.0)
                              for k in ("arm_l", "farm_l")))


PALM_EASE = 1.30   # a long sleeve's cuff against the palm it passes over
# A long sleeve asked for on a garment whose own sleeve is short (T-shirt,
# jumpsuit, dress) is laid much closer to the arm (ease 14 mm against the
# jacket's 32), and with the 1.3 cuff Manuka's hand caught it: the tunic with
# long sleeves came out with the seam under her left forearm 18 cm open.
PALM_EASE_CLOSE = 1.45
# A long sleeve is cut to the arm's length. Upstream cut it 8% longer, and
# Fase 2 a further 16% for a widened cuff, but both only made up for the cap
# that was crushed into the shoulder (see _sleeve_height); with the sleeve
# placed where it belongs that extra length piled up past the wrist and kept
# the cuff stitches from closing (Mao's hoodie). Measured with 1.0: Hanka's
# jacket reaches 1.01 of the arm, Mao's hoodie 1.07.
FLARE_LEN = 1.0    # extra length for a sleeve widened to clear the hand
LONG_SLEEVE = 1.0  # long sleeve against the arm


ELBOW_HEM = 1.0      # an elbow sleeve's hem against its width at the cap
SLEEVE_SHORT = 0.28   # a short sleeve, as a fraction of the whole arm
SLEEVE_ELBOW = 0.55   # just past the elbow


def _sleeve_len(spec, default, d, arm_total):
    """A sleeve length from the garment options: None keeps the preset's own,
    a number is metres, and 'short' / 'elbow' / 'long' are measured on the
    avatar's arm, so they mean the same on a 1.24 m and a 1.80 m body."""
    if spec is None:
        return default
    if not isinstance(spec, str):
        return spec
    arm = arm_total or d.get("arm_total") or 0.0
    if spec == "short":
        return max(0.08, arm * SLEEVE_SHORT) if arm else 0.15
    if spec == "elbow":
        return max(0.14, arm * SLEEVE_ELBOW) if arm else 0.28
    if spec == "long":
        return max(0.20, arm * LONG_SLEEVE * _flare_extra(d))
    raise ValueError("unknown sleeve length %r" % spec)


def _flare_extra(d):
    """A sleeve whose cuff had to be widened for a big hand is looser on the
    forearm and bunches more on the way down the arm (Mao's hoodie reached
    0.74 of her arm, her jacket 0.82, against ~1.0 on the other avatars), so
    it is cut a little longer. 1.0 when the cuff already clears the palm."""
    palm = d.get("palm")
    if palm and palm * PALM_EASE > max(d["biceps"] * 1.06, 0.05) * d.get("sleeve_hem", 0.90):
        return FLARE_LEN
    return 1.0


def _sleeve(d, fit, length, width_ease=1.06, straight=False, palm_ease=PALM_EASE):
    """A set-in sleeve, drafted the way one actually is: the sleeve is as
    wide as the arm needs, and the cap *height* is then solved so the cap
    measures the armhole it is sewn into.

    Doing it the other way round - fixing a shallow cap and widening the
    sleeve until it measured - is what produced a wide, droopy tube with a
    flat head: the only way a short cap reaches the length of an armhole is
    by getting very wide. Height first, width from the arm.
    """
    target = d["armhole"] * 1.02          # a little ease, eased in over the head
    # The sleeve has to be narrower than the armhole is long, or there is no
    # length left for the cap to rise in and it flattens into a tube sewn on
    # sideways. Width just clears the arm; the cap takes the rest.
    cw = max(d["biceps"] * width_ease, 0.05)
    cw = min(cw, target * 0.82)
    ceiling = d["arm_d"] * 0.95
    cap_h = _solve(lambda h: _cap_len(cw, h), target, 0.02, ceiling)
    if _cap_len(cw, cap_h) < target * 0.995:
        # even a full-height cap is too short for this armhole: the arm is
        # slim relative to the scye, so widen the sleeve to make up the rest
        cap_h = ceiling
        cw = _solve(lambda w: _cap_len(w, cap_h), target, cw, cw * 2.5)
    hw = cw * d.get("sleeve_hem", 0.90)
    # A long sleeve is cut past the wrist and ends over the hand, so its cuff
    # has to clear the palm. Drafted off the biceps alone it does on a
    # realistic figure (Nora: cuff 1.35x her palm) but not on anime
    # proportions - big hands, slim arms - where the cuff came out narrower
    # than the palm (Mao: 0.92x) and the hand's collision flung the sleeve
    # off the arm. 1.3x is the margin the bundled bodies already have.
    palm, arm_total = d.get("palm"), d.get("arm_total") or 0.0
    if palm and arm_total and length > arm_total * 0.9:
        hw = max(hw, palm * palm_ease)
    elif straight:
        # a sleeve ending at the elbow is cut straight: tapered to the cuff of
        # a long one, its hem was tighter than the elbow it ends on and the
        # tube rode up into the armpit (Manuka's jacket). Only when Elbow is
        # asked for, so a preset's own sleeve never changes on a short arm
        hw = max(hw, cw * ELBOW_HEM)
    front, back = _cap_pts(cw, cap_h)
    segs = [
        _seg("under_front", [(-cw * 0.5, 0.0), (-hw * 0.5, -length)]),
        _seg("hem",         [(-hw * 0.5, -length), (hw * 0.5, -length)]),
        _seg("under_back",  [(hw * 0.5, -length), (cw * 0.5, 0.0)]),
        ("cap_back",        back),
        ("cap_front",       front),
    ]
    return segs, cw, cap_h


def preset_tshirt(m, fit=0.14, sleeve_len=None, length_to="hip"):
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    front, info = _bodice(m, fit, length_to, d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"])
    back, _ = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"])
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sl = _sleeve_len(sleeve_len, d["tee_sleeve"], d, arm_total)
    sleeve, cw, cap_h = _sleeve(d, fit, sl, straight=(sleeve_len == "elbow"),
                                palm_ease=PALM_EASE_CLOSE if sleeve_len == "long" else PALM_EASE)
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    # limb pieces are placed by their centre, so drop the sleeve until its cap
    # apex meets the shoulder joint
    sleeve_h = _sleeve_height(cap_h, sl, arm_total)

    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.018),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.018),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sleeve_h, ease=0.014),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sleeve_h, ease=0.014),
    ]
    # flip says whether the two edges run in opposite directions along the outline
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
    ]
    return pieces, seams


def preset_tank(m, fit=0.10, length_to="hip"):
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit, sleeveless=True)
    front, info = _bodice(m, fit, length_to, d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"])
    back, _ = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"])
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.014),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.014),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
    ]
    return pieces, seams


# ---------------------------------------------------------------- bottoms

REF_HEIGHT = 1.65   # the skirts' lengths in metres are for a body this tall


def _len_scale(m):
    """Skirt lengths, yokes and tiers are drafted in metres for a 1.65 m body;
    on a small avatar the same 45 cm skirt reached Manuka's (1.24 m) knees and
    hung off her like a tent, so they scale with the height."""
    return min(1.25, max(0.6, m["height"] / REF_HEIGHT))

SKIRT_HIP_EASE = 1.04   # the plain skirt over the hips


def preset_skirt(m, fit=0.10, length=0.45, flare=1.35):
    z, g, _ = _measurements(m)
    top = g["waist"] * 0.5 * (1.0 + fit)
    bot = top * flare
    L = length * _len_scale(m)
    # The straight side has to clear the hips on the way down. On Manuka
    # (waist 39 cm, hips 63 cm) it measured 49 cm round at the hip line: the
    # side seam could never close over her and the skirt hung open on one
    # side. Where the hips are wider than the line, the side curves out
    # through them and the hem is at least that wide.
    dh = min(max(z["waist"] - z["hip"], 0.0), L * 0.8)
    hip = g["hip"] * 0.5 * (1.0 + fit) * SKIRT_HIP_EASE
    hip_pt = None
    if dh > 0.02 and hip > top + (bot - top) * dh / L:
        bot = max(bot, hip * 1.05)
        hip_pt = (hip * 0.5, -dh)

    def side(sign):
        pts = [(bot * 0.5, -L)] + ([hip_pt] if hip_pt else []) + [(top * 0.5, 0.0)]
        pts = [(sign * x, y) for x, y in pts]
        return pts if sign > 0 else pts[::-1]

    def half_panel():
        return [
            _seg("hem",    [(-bot * 0.5, -L), (bot * 0.5, -L)]),
            _seg("side_L", side(1.0)),
            _seg("waist",  [(top * 0.5, 0.0), (-top * 0.5, 0.0)]),
            _seg("side_R", side(-1.0)),
        ]
    h = m["height"]
    hgt = (z["waist"] - L * 0.5 - m["zmin"]) / h
    pieces = [
        dict(name="Front", segs=half_panel(), anchor='TORSO_FRONT', height=hgt, ease=0.016),
        dict(name="Back",  segs=half_panel(), anchor='TORSO_BACK',  height=hgt, ease=0.016),
    ]
    seams = [("Front", "side_L", "Back", "side_L", False),
             ("Front", "side_R", "Back", "side_R", False)]
    return pieces, seams


PLEAT_FACE = 0.5   # share of each knife pleat on the outside


PLEAT_YOKE = 0.08  # depth of the plain yoke the pleats hang from
PLEAT_MIN_FACE = 0.036  # narrowest pleat face: two mesh edges at the default resolution.
                        # A stitch segment shorter than that has fewer than two
                        # points and its seam is skipped - on Manuka's 39 cm waist
                        # ten pleats left faces of 2.5 cm, the yoke tacks were lost
                        # and the pleated panels slid down to her thighs


def preset_pleated_skirt(m, fit=0.10, length=0.45, flare=1.30, pleats=10):
    """Knife-pleated skirt on a plain yoke.

    The yoke fits the waist like the plain skirt and carries the weight. The
    pleated panels are cut 1/PLEAT_FACE times their finished width and placed
    already folded (build._pleat_map), so the pleats are the cloth's rest
    shape and stay pressed. At the top each pleat's face is sewn to its
    stretch of the yoke and the two layers folded under it are sewn to each
    other, which is how a pleat is stitched down: without the yoke the faces
    had nothing to hang from, the pleated top crumpled inward and the skirt
    slid off the hips while it settled."""
    z, g, _ = _measurements(m)
    sc = _len_scale(m)
    Y = PLEAT_YOKE * sc
    length = length * sc
    top = g["waist"] * 0.5 * (1.0 + fit)
    z_yoke = z["waist"] - Y
    yoke_bot = max(top, avatar.girth_at(m, z_yoke) * 0.5 * (1.0 + fit))
    # the hem has to pass the hips with room for the folded layers
    bot = max(yoke_bot * flare, g["hip"] * 0.5 * (1.0 + fit) * 1.12)
    L = max(0.10, length - Y)
    pleats = max(4, min(pleats, int(yoke_bot / (PLEAT_MIN_FACE * m.get("res_scale", 1.0)))))
    k = 1.0 / PLEAT_FACE
    under = (1.0 - PLEAT_FACE) * 0.5

    # build._pleat_map starts half a face in, so the faces are: a half face,
    # pleats-1 whole ones and another half; the yoke is split to match
    face_w = [0.5] + [1.0] * (pleats - 1) + [0.5]

    def yoke():
        step = yoke_bot / pleats
        bottom, x = [], -yoke_bot * 0.5
        for j, fw in enumerate(face_w):
            bottom.append(_seg("y%d" % j, [(x, -Y), (x + fw * step, -Y)]))
            x += fw * step
        return bottom + [
            _seg("side_L", [(yoke_bot * 0.5, -Y), (top * 0.5, 0.0)]),
            _seg("waist",  [(top * 0.5, 0.0), (-top * 0.5, 0.0)]),
            _seg("side_R", [(-top * 0.5, 0.0), (-yoke_bot * 0.5, -Y)]),
        ]

    def panel():
        T, B = yoke_bot * k, bot * k
        P = T / pleats
        def xu(u):                     # flat x of pleat coordinate u
            return (u - PLEAT_FACE * 0.5) * P - T * 0.5
        # the top edge runs right to left, split at every fold: pa = a face,
        # pb = the layer folding back under it, pf = the layer coming forward
        cuts = [("pa%d" % pleats, xu(pleats + PLEAT_FACE * 0.5))]
        for j in range(pleats - 1, -1, -1):
            cuts += [("pf%d" % j, xu(j + 1)),
                     ("pb%d" % j, xu(j + PLEAT_FACE + under)),
                     ("pa%d" % j, xu(j + PLEAT_FACE))]
        topedge = []
        for i, (name, x_from) in enumerate(cuts):
            x_to = cuts[i + 1][1] if i + 1 < len(cuts) else -T * 0.5
            topedge.append(_seg(name, [(x_from, 0.0), (x_to, 0.0)]))
        return [
            _seg("hem",    [(-B * 0.5, -L), (B * 0.5, -L)]),
            _seg("side_L", [(B * 0.5, -L), (T * 0.5, 0.0)]),
        ] + topedge + [
            _seg("side_R", [(-T * 0.5, 0.0), (-B * 0.5, -L)]),
        ]

    h_yoke = (z["waist"] - Y * 0.5 - m["zmin"]) / m["height"]
    h_pl = (z_yoke - L * 0.5 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Yoke_F", segs=yoke(), anchor='TORSO_FRONT', height=h_yoke, ease=0.016),
        dict(name="Yoke_B", segs=yoke(), anchor='TORSO_BACK',  height=h_yoke, ease=0.016),
        # room for the two folded layers inside the face
        dict(name="Front", segs=panel(), anchor='TORSO_FRONT', height=h_pl, ease=0.030,
             pleats=pleats, pleat_face=PLEAT_FACE),
        dict(name="Back",  segs=panel(), anchor='TORSO_BACK',  height=h_pl, ease=0.030,
             pleats=pleats, pleat_face=PLEAT_FACE),
    ]
    seams = [("Yoke_F", "side_L", "Yoke_B", "side_L", False),
             ("Yoke_F", "side_R", "Yoke_B", "side_R", False),
             ("Front", "side_L", "Back", "side_L", False),
             ("Front", "side_R", "Back", "side_R", False)]
    for yk, pc in (("Yoke_F", "Front"), ("Yoke_B", "Back")):
        # the yoke's bottom runs left to right, the panel's top right to
        # left; the two folded layers also run opposite ways in 3D
        for j in range(pleats + 1):
            seams.append((yk, "y%d" % j, pc, "pa%d" % j, True))
        for j in range(pleats):
            seams.append((pc, "pb%d" % j, pc, "pf%d" % j, True))
    return pieces, seams


TIER_GATHER = 1.6   # each ruffle tier against the edge it is gathered onto
RUFFLE_FOLD = 0.02  # depth of one gather fold (about a mesh edge)
RUFFLE_GAP = 0.012  # between its layers
RUFFLE_OVER = 0.03  # a ruffle hangs this far past the band it is sewn over
RUFFLE_OUT = 0.012  # and is laid this much further out
TIER_FLARE = 1.15   # how much wider each tier shows than the one above (1.28
                    # ballooned and bunched at the sides again)


def preset_tiered_skirt(m, fit=0.10, length=0.55, tiers=3):
    """Ruffled skirt in tiers on a plain yoke: every tier is a straight strip
    TIER_GATHER times longer than the edge above it, so sewing it on gathers
    it into ruffles - the seam pairs its points by proportion, and the longer
    edge bunches up between the stitches."""
    z, g, _ = _measurements(m)
    sc = _len_scale(m)
    length = length * sc
    top = g["waist"] * 0.5 * (1.0 + fit)
    Y = PLEAT_YOKE * sc
    z_yoke = z["waist"] - Y
    yoke_bot = max(top, avatar.girth_at(m, z_yoke) * 0.5 * (1.0 + fit))
    tier_h = max(0.06, (length - Y) / tiers)

    def strip(w, h, top_name):
        return [
            _seg("hem",    [(-w * 0.5, -h), (w * 0.5, -h)]),
            _seg("side_L", [(w * 0.5, -h), (w * 0.5, 0.0)]),
            _seg(top_name, [(w * 0.5, 0.0), (-w * 0.5, 0.0)]),
            _seg("side_R", [(-w * 0.5, 0.0), (-w * 0.5, -h)]),
        ]

    yoke = [
        _seg("hem",    [(-yoke_bot * 0.5, -Y), (yoke_bot * 0.5, -Y)]),
        _seg("side_L", [(yoke_bot * 0.5, -Y), (top * 0.5, 0.0)]),
        _seg("waist",  [(top * 0.5, 0.0), (-top * 0.5, 0.0)]),
        _seg("side_R", [(-top * 0.5, 0.0), (-yoke_bot * 0.5, -Y)]),
    ]
    h_yoke = (z["waist"] - Y * 0.5 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Yoke_F", segs=yoke, anchor='TORSO_FRONT', height=h_yoke, ease=0.016),
        dict(name="Yoke_B", segs=yoke, anchor='TORSO_BACK',  height=h_yoke, ease=0.016),
    ]
    seams = [("Yoke_F", "side_L", "Yoke_B", "side_L", False),
             ("Yoke_F", "side_R", "Yoke_B", "side_R", False)]
    vis, above, z_top = yoke_bot, ("Yoke_F", "Yoke_B"), z_yoke
    for t in range(tiers):
        # each tier is a plain band carrying the next tier, with a gathered
        # ruffle sewn on over it at the top and hanging RUFFLE_OVER past the
        # band, so it covers the seam below: gathers alone (however deep)
        # left the tiers running together into one straight skirt
        w = vis * TIER_GATHER
        band_top, vis = vis, vis * TIER_FLARE
        h_band = (z_top - tier_h * 0.5 - m["zmin"]) / m["height"]
        rh = tier_h + RUFFLE_OVER * sc
        h_ruf = (z_top - rh * 0.5 - m["zmin"]) / m["height"]
        e = 0.016 + 0.010 * t
        bf, bb = "Band%d_F" % (t + 1), "Band%d_B" % (t + 1)
        rf, rb = "Tier%d_F" % (t + 1), "Tier%d_B" % (t + 1)
        band = [
            _seg("hem",    [(-vis * 0.5, -tier_h), (vis * 0.5, -tier_h)]),
            _seg("side_L", [(vis * 0.5, -tier_h), (band_top * 0.5, 0.0)]),
            _seg("top",    [(band_top * 0.5, 0.0), (-band_top * 0.5, 0.0)]),
            _seg("side_R", [(-band_top * 0.5, 0.0), (-vis * 0.5, -tier_h)]),
        ]
        a = vis / w
        n = max(3, int(round(w * (1.0 - a) * 0.5 / RUFFLE_FOLD)))
        gat = dict(pleats=n, pleat_face=a, pleat_gap=RUFFLE_GAP)
        pieces += [
            dict(name=bf, segs=band, anchor='TORSO_FRONT', height=h_band, ease=e),
            dict(name=bb, segs=band, anchor='TORSO_BACK',  height=h_band, ease=e),
            dict(name=rf, segs=strip(w, rh, "top"), anchor='TORSO_FRONT', height=h_ruf,
                 ease=e + RUFFLE_OUT, **gat),
            dict(name=rb, segs=strip(w, rh, "top"), anchor='TORSO_BACK', height=h_ruf,
                 ease=e + RUFFLE_OUT, **gat),
        ]
        seams += [(bf, "side_L", bb, "side_L", False),
                  (bf, "side_R", bb, "side_R", False),
                  (rf, "side_L", rb, "side_L", False),
                  (rf, "side_R", rb, "side_R", False),
                  (above[0], "hem", bf, "top", True, True),
                  (above[1], "hem", bb, "top", True, True),
                  (above[0], "hem", rf, "top", True, True),
                  (above[1], "hem", rb, "top", True, True)]
        above, z_top = (bf, bb), z_top - tier_h
    return pieces, seams


SHORTS_FLARE = 1.25   # hem of shorts against the thigh it ends on


def _leg_hem(z, lp, length_to, L, fit, ankle_w):
    """Hem width of a trouser or jumpsuit leg. Full length it goes round the
    ankle; shorts or knee length go round the thigh where they end (L below
    the crotch, which can be a little past the landmark on a short body),
    with a little flare so they don't cling."""
    if z[length_to] <= z["knee"] - 0.01 or not lp:
        return ankle_w
    frac = L / max(0.05, z["crotch"] - z["knee"])
    hem_r = avatar.limb_radius_at(lp, min(0.95, 0.1 + 0.9 * frac))
    return max(ankle_w, math.pi * hem_r * (1.0 + fit) * SHORTS_FLARE)


def preset_trousers(m, fit=0.14, length_to="ankle"):
    """Hip yoke plus four leg panels. Leg tubes on their own slide straight off a
    tapering thigh; trousers are held up at the waist, so the yoke is what makes
    the garment stay where it belongs."""
    z, g, _ = _measurements(m)
    lp = m.get("limbs", {}).get("thigh_l")
    thigh_r = avatar.limb_radius_at(lp, 0.1) if lp else 0.09
    calf = m.get("limbs", {}).get("calf_l")
    ankle_r = avatar.limb_radius_at(calf, 0.95) if calf else 0.045

    f = _fig(m)
    # where the waistband sits: at the natural waist, or a way down towards
    # the hip for a man's low rise; the band is cut to the girth at that height
    rise = max(0.10, (z["waist"] - z["crotch"]) * f["rise"])
    z_top = z["crotch"] + rise
    hip_w = g["hip"] * 0.5 * (1.0 + fit)
    waist_w = avatar.girth_at(m, z_top) * 0.5 * (1.0 + fit * 0.5)
    L = max(0.15, z["crotch"] - z[length_to])
    top_w = math.pi * thigh_r * (1.0 + fit)
    bot_w = _leg_hem(z, lp, length_to, L, fit, math.pi * ankle_r * (1.0 + fit) * 1.15)

    def yoke():
        return [
            _seg("leg_R",  [(-hip_w * 0.5, -rise), (0.0, -rise)]),
            _seg("leg_L",  [(0.0, -rise), (hip_w * 0.5, -rise)]),
            _seg("side_L", [(hip_w * 0.5, -rise), (waist_w * 0.5, 0.0)]),
            _seg("waist",  [(waist_w * 0.5, 0.0), (-waist_w * 0.5, 0.0)]),
            _seg("side_R", [(-waist_w * 0.5, 0.0), (-hip_w * 0.5, -rise)]),
        ]

    # Only the outer part of a leg top joins the yoke; the inner part is the
    # crotch seam that joins the two legs. Sewing the whole leg top to the yoke
    # forces the surplus into a gather at the hip.
    out_len = min(hip_w * 0.5, top_w * 0.92)
    in_len = max(0.0, top_w - out_len)

    def leg(front=True):
        segs = [
            _seg("hem",    [(-bot_w * 0.5, -L), (bot_w * 0.5, -L)]),
            _seg("seam_a", [(bot_w * 0.5, -L), (top_w * 0.5, 0.0)]),
        ]
        x0 = top_w * 0.5
        if front:      # top edge runs outer -> inner
            segs.append(_seg("top_out", [(x0, 0.0), (x0 - out_len, 0.0)]))
            segs.append(_seg("top_in",  [(x0 - out_len, 0.0), (-x0, 0.0)]))
        else:          # back panel is mirrored: inner -> outer
            segs.append(_seg("top_in",  [(x0, 0.0), (x0 - in_len, 0.0)]))
            segs.append(_seg("top_out", [(x0 - in_len, 0.0), (-x0, 0.0)]))
        segs.append(_seg("seam_b", [(-top_w * 0.5, 0.0), (-bot_w * 0.5, -L)]))
        return segs

    leg_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0)
                    for k in ("thigh_l", "calf_l"))
    leg_h = (L * 0.5) / leg_total if leg_total > 1e-6 else 0.25
    yoke_h = (z_top - rise * 0.5 - m["zmin"]) / m["height"]
    fs, bs = -math.pi * 0.5, math.pi * 0.5

    pieces = [
        dict(name="Hip_Front", segs=yoke(), anchor='HIP_FRONT', height=yoke_h, ease=0.016),
        dict(name="Hip_Back",  segs=yoke(), anchor='HIP_BACK',  height=yoke_h, ease=0.016),
        dict(name="Leg_L_Front", segs=leg(True),  anchor='LEG_L', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_L_Back",  segs=leg(False), anchor='LEG_L', height=leg_h, ease=0.016, spin=bs, taper=1.0),
        dict(name="Leg_R_Front", segs=leg(True),  anchor='LEG_R', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_R_Back",  segs=leg(False), anchor='LEG_R', height=leg_h, ease=0.016, spin=bs, taper=1.0),
    ]
    seams = [
        ("Hip_Front", "side_L", "Hip_Back", "side_L", False),
        ("Hip_Front", "side_R", "Hip_Back", "side_R", False),
        ("Leg_L_Front", "seam_a", "Leg_L_Back", "seam_b", True),
        ("Leg_L_Front", "seam_b", "Leg_L_Back", "seam_a", True),
        ("Leg_R_Front", "seam_a", "Leg_R_Back", "seam_b", True),
        ("Leg_R_Front", "seam_b", "Leg_R_Back", "seam_a", True),
        # yoke to leg tops, then the crotch seams joining the two legs
        ("Hip_Front", "leg_L", "Leg_L_Front", "top_out"),
        ("Hip_Front", "leg_R", "Leg_R_Front", "top_out"),
        ("Hip_Back", "leg_L", "Leg_L_Back", "top_out"),
        ("Hip_Back", "leg_R", "Leg_R_Back", "top_out"),
        ("Leg_L_Front", "top_in", "Leg_R_Front", "top_in"),
        ("Leg_L_Back", "top_in", "Leg_R_Back", "top_in"),
    ]
    return pieces, seams


def preset_jumpsuit(m, fit=0.10, sleeve_len=0.17, length_to="ankle"):
    """One piece: a bodice running shoulder to crotch, with four leg panels sewn
    to its split hem and to each other at the crotch."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    lp0 = m.get("limbs", {}).get("thigh_l")
    _thigh_r = avatar.limb_radius_at(lp0, 0.1) if lp0 else 0.09
    _top_w = math.pi * _thigh_r * (1.0 + fit)
    _in_len = max(0.09, _top_w * 0.28)
    # The bodice hem is sewn to the leg tops, so take its length from them, then
    # trade width for a crotch dip so the V-half still measures out_len.
    _out_len = _top_w - _in_len
    _dip = min(0.055, _out_len * 0.30)

    def _v_half(dip):
        # half-width whose three-point V (hem corner, mid dip, centre) measures out_len
        return _solve(lambda hh: _curve_len([Vector((hh, 0.0)), Vector((hh * 0.35, -dip * 0.45)),
                                             Vector((0.0, -dip))]), _out_len, 0.02, 0.60)
    hem_half = _v_half(_dip)
    front, info = _bodice(m, fit, "crotch", d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"], hem_half=hem_half, split_hem=True, hem_dip=_dip)
    back, _ = _bodice(m, fit, "crotch", d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"], hem_half=_v_half(_dip * 1.25), split_hem=True,
                      hem_dip=_dip * 1.25)
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    straight, close = sleeve_len == "elbow", sleeve_len == "long"
    sleeve_len = _sleeve_len(sleeve_len, 0.17, d, arm_total)
    sleeve, cw, cap_h = _sleeve(d, fit, sleeve_len, straight=straight,
                                palm_ease=PALM_EASE_CLOSE if close else PALM_EASE)

    lp = m.get("limbs", {}).get("thigh_l")
    thigh_r = avatar.limb_radius_at(lp, 0.1) if lp else 0.09
    calf = m.get("limbs", {}).get("calf_l")
    ankle_r = avatar.limb_radius_at(calf, 0.95) if calf else 0.045
    L = max(0.15, z["crotch"] - z[length_to])
    top_w = math.pi * thigh_r * (1.0 + fit)
    bot_w = _leg_hem(z, lp, length_to, L, fit, math.pi * ankle_r * (1.0 + fit) * 1.15)
    in_len = _in_len
    out_len = max(0.02, top_w - in_len)

    def leg(front_panel=True):
        segs = [
            _seg("hem",    [(-bot_w * 0.5, -L), (bot_w * 0.5, -L)]),
            _seg("seam_a", [(bot_w * 0.5, -L), (top_w * 0.5, 0.0)]),
        ]
        x0 = top_w * 0.5
        if front_panel:
            segs.append(_seg("top_out", [(x0, 0.0), (x0 - out_len, 0.0)]))
            segs.append(_seg("top_in",  [(x0 - out_len, 0.0), (-x0, 0.0)]))
        else:
            segs.append(_seg("top_in",  [(x0, 0.0), (x0 - in_len, 0.0)]))
            segs.append(_seg("top_out", [(x0 - in_len, 0.0), (-x0, 0.0)]))
        segs.append(_seg("seam_b", [(-top_w * 0.5, 0.0), (-bot_w * 0.5, -L)]))
        return segs

    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sleeve_h = _sleeve_height(cap_h, sleeve_len, arm_total)
    leg_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("thigh_l", "calf_l"))
    leg_h = (L * 0.5) / leg_total if leg_total > 1e-6 else 0.25
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    fs, bs = -math.pi * 0.5, math.pi * 0.5

    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.018),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.018),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sleeve_h, ease=0.014),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sleeve_h, ease=0.014),
        dict(name="Leg_L_Front", segs=leg(True),  anchor='LEG_L', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_L_Back",  segs=leg(False), anchor='LEG_L', height=leg_h, ease=0.016, spin=bs, taper=1.0),
        dict(name="Leg_R_Front", segs=leg(True),  anchor='LEG_R', height=leg_h, ease=0.016, spin=fs, taper=1.0),
        dict(name="Leg_R_Back",  segs=leg(False), anchor='LEG_R', height=leg_h, ease=0.016, spin=bs, taper=1.0),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
        ("Leg_L_Front", "seam_a", "Leg_L_Back", "seam_b", True),
        ("Leg_L_Front", "seam_b", "Leg_L_Back", "seam_a", True),
        ("Leg_R_Front", "seam_a", "Leg_R_Back", "seam_b", True),
        ("Leg_R_Front", "seam_b", "Leg_R_Back", "seam_a", True),
        ("Front", "leg_L", "Leg_L_Front", "top_out"),
        ("Front", "leg_R", "Leg_R_Front", "top_out"),
        ("Back", "leg_L", "Leg_L_Back", "top_out"),
        ("Back", "leg_R", "Leg_R_Back", "top_out"),
        ("Leg_L_Front", "top_in", "Leg_R_Front", "top_in"),
        ("Leg_L_Back", "top_in", "Leg_R_Back", "top_in"),
    ]
    return pieces, seams


def preset_rectangle(m, fit=0.0):
    w = m["height"] * 0.28
    h = m["height"] * 0.35
    segs = [
        _seg("bottom", [(-w * 0.5, -h * 0.5), (w * 0.5, -h * 0.5)]),
        _seg("right",  [(w * 0.5, -h * 0.5), (w * 0.5, h * 0.5)]),
        _seg("top",    [(w * 0.5, h * 0.5), (-w * 0.5, h * 0.5)]),
        _seg("left",   [(-w * 0.5, h * 0.5), (-w * 0.5, -h * 0.5)]),
    ]
    z = avatar.z_of(m, "chest")
    return [dict(name="Panel", segs=segs, anchor='TORSO_FRONT',
                 height=(z - m["zmin"]) / m["height"], ease=0.02)], []


def _arc_angle(m, z, s):
    """Rough arc-length to angle at one height, for placing half panels."""
    r = max(0.02, avatar.radius_at(m, z, 0.0))
    return s / r


def preset_dress(m, fit=0.10, length_to="knee", flare=1.45, sleeve_len=0.0):
    """A-line shift dress: one panel front and back, flared from the underarm down."""
    z, g, _ = _measurements(m)
    straight, close = sleeve_len == "elbow", sleeve_len == "long"
    if sleeve_len == "none":
        sleeve_len = 0.0
    if isinstance(sleeve_len, str):
        # a named length is measured on the arm, from the sleeved draft
        d = _draft_top(m, fit)
        arm = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
        sleeve_len = _sleeve_len(sleeve_len, 0.0, d, arm)
    else:
        d = _draft_top(m, fit, sleeveless=(sleeve_len <= 0.0))
    hem_half = g["hip"] * 0.5 * (1.0 + fit) * 0.5 * flare
    front, info = _bodice(m, fit, length_to, d["df"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"), sh_drop=d["sh_drop"],
                          hem_half=hem_half)
    back, _ = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"), sh_drop=d["sh_drop"],
                      hem_half=hem_half)
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.020),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.020),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
    ]
    if sleeve_len > 0.0:
        sleeve, cw, cap_h = _sleeve(d, fit, sleeve_len, straight=straight,
                                    palm_ease=PALM_EASE_CLOSE if close else PALM_EASE)
        arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
        sh = _sleeve_height(cap_h, sleeve_len, arm_total)
        pieces += [dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.014),
                   dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.014)]
        seams += [("Sleeve_L", "cap_front", "Front", "arm_L", True),
                  ("Sleeve_L", "cap_back", "Back", "arm_L", False),
                  ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
                  ("Sleeve_R", "cap_front", "Front", "arm_R", False),
                  ("Sleeve_R", "cap_back", "Back", "arm_R", True),
                  ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True)]
    return pieces, seams


LAPEL_V = 0.08     # depth of the jacket's open V below the front neck
HEM_VENT = 0.05    # open vent left at the jacket's hem


def _open_front(m, fit, d, length_to, overlap=0.02, close_to=None, extra_len=0.0):
    """Two front halves with a centre opening, for a jacket or hoodie."""
    z, g, _ = _measurements(m)
    f = _fig(m)
    half = g["chest"] * 0.5 * (1.0 + fit) * 0.5
    hem_half = _hem_half(m, fit, half, length_to)
    L = max(z["shoulder"] + SHELF - z[length_to], 0.12) + 0.03 + f["top_extra"] + extra_len
    arm_d, sh_x, sh_drop = d["arm_d"], d["sh_x"], d["sh_drop"]
    scye_x = d.get("scye_x", half)
    nh = d["neck_half"]
    side_L, _ = _sides(m, fit, scye_x, hem_half, L, arm_d)
    # one HALF of the front: centre front (with a little overlap) out to the side
    armhole = patterns.bezier((scye_x, -arm_d), (scye_x, -arm_d * 0.45),
                              (sh_x + 0.035, -sh_drop - 0.02), (sh_x, -sh_drop), 12)
    # The front neck is cut to the same depth as any other top. It was
    # deepened by 4.5 cm at one point to keep lapels off an inner collar,
    # and that is what made the jacket slide: a 12 cm V has nothing to catch
    # on, so the garment runs down the body until the armholes stop it, and
    # the shoulders end up bare. Measured against a t-shirt on the same
    # avatar, this is the whole difference.
    df = d["df"]
    neck = patterns.bezier((nh, 0.0), (nh * 0.62, -df * 0.85),
                           (nh * 0.22, -df), (0.0, -df), 10)
    # The front edge is cut in three: open above the button, closed at it,
    # open below. A jacket that is stitched shut from throat to hem is a
    # pullover; one button holds it on the body and still shows lapels above
    # and a vent below, which is how a jacket is actually worn.
    # A short V above the closure: upstream left the lapel loose from the
    # neck to 5 cm above the waist with one 9 cm "button" stitch, and that
    # 20 cm free edge hangs off the chest and crosses over the other front
    # (Hanka). Now the V is 8 cm and the front is closed down to a short vent
    # at the hem, like a zipped jacket. (Closing only to the waist left a
    # slit from the chest down on Hanka, whose waist sits high.)
    btn_top = min(df + LAPEL_V, L - 0.10)
    btn_bot = max(L - HEM_VENT if close_to is None else min(close_to, L - HEM_VENT), btn_top + 0.09)
    left = [
        _seg("hem",      [(-overlap, -L), (hem_half, -L)]),
        side_L,
        ("arm_L",        armhole),
        _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]),
        ("neck_L",       neck),
        _seg("lapel_L",  [(0.0, -df), (0.0, -btn_top)]),
        _seg("button_L", [(0.0, -btn_top), (0.0, -btn_bot)]),
        _seg("vent_L",   [(0.0, -btn_bot), (-overlap, -L)]),
    ]
    right = [(n.replace("_L", "_R"), [Vector((-p[0], p[1])) for p in reversed(pts)])
             for n, pts in left]
    right = list(reversed(right))
    return left, right, L, half, overlap


def preset_jacket(m, fit=0.12, length_to="hip", sleeve_len=None, closed_front=True):
    """Jacket: two front halves, a back and long sleeves. The fronts are sewn
    together below the lapel V - a buttoned jacket. An unfastened open front
    is marginal physics on any dress form (nothing anchors it against the
    sleeves' weight, and it slides off one run in three); pass
    closed_front=False if you want one anyway and style it by hand."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    # a sewn-shut front is butted edge to edge; only an open one gets the
    # button-stand overlap, or the seam crosses the panels into a knot
    left, right, L, half, overlap = _open_front(m, fit, d, length_to,
                                                overlap=0.0 if closed_front else 0.02)
    back, info = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                         sh_drop=d["sh_drop"])
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    # cut past the wrist: a long sleeve takes up several centimetres bunching
    # over the elbow, so one drafted to the arm's length settles short of it
    sl = _sleeve_len(sleeve_len, max(0.20, arm_total * LONG_SLEEVE * _flare_extra(d)), d, arm_total)
    sleeve, cw, cap_h = _sleeve(d, fit, sl, straight=(sleeve_len == "elbow"))
    sh = _sleeve_height(cap_h, sl, arm_total)
    body_h = (z["shoulder"] + SHELF - L * 0.5 - m["zmin"]) / m["height"]
    # Each half is centred on its own bounding box (patterns.py), so with no
    # spin both halves sat on the centre front, crossed over each other: the
    # left half's centre edge started on the right of the body. Sewing the
    # closure then dragged one panel through the other into the diagonal fold
    # seen on Hanka. Spin each half out by half its width, open or closed.
    off = _arc_angle(m, z["chest"], (half - overlap) * 0.5)
    pieces = [
        dict(name="Front_L", segs=left,  anchor='TORSO_FRONT', height=body_h, ease=0.034, spin=off),
        dict(name="Front_R", segs=right, anchor='TORSO_FRONT', height=body_h, ease=0.034, spin=-off),
        dict(name="Back",    segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.034),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.032),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.032),
    ]
    seams = [
        ("Front_L", "side_L", "Back", "side_L", False),
        ("Front_R", "side_R", "Back", "side_R", False),
        ("Front_L", "shoulder_L", "Back", "shoulder_L", False),
        ("Front_R", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front_L", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front_R", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
    ]
    if closed_front:
        # just the button: the lapels above it and the vent below stay open
        seams.append(("Front_L", "button_L", "Front_R", "button_R", True))
    return pieces, seams


COAT_FLARE = 1.22   # coat hem against the hips it hangs from
COAT_VENT = 0.24    # back vent and front opening start this far below the hip
                    # line (as cut: sewing hoists a long garment ~13 cm, so
                    # 10 cm opened the back at the seat on the default woman)
COAT_EXTRA = 0.12   # cut past the knee by the same hoist, so the hem ends there


def _back_halves(m, fit, d, length_to, hem_half, vent_from, extra_len=0.0):
    """Left and right back of a coat: sewn up the centre back from the neck
    to vent_from (distance below the shoulder top), open below it so the
    skirt can part over the legs - a single back panel reaching the knee is a
    tube the legs have to stretch."""
    back, info = _bodice(m, fit, length_to, d["db"], d["neck_half"], d["arm_d"], d["sh_x"],
                         scye_x=d.get("scye_x"), sh_drop=d["sh_drop"], hem_half=hem_half,
                         extra_len=extra_len)
    L = info["L"]
    segs = dict(back)
    db, nh = d["db"], d["neck_half"]
    neck = patterns.bezier((nh, 0.0), (nh * 0.55, -db), (0.0, -db), (0.0, -db), 8)
    vent_from = min(max(vent_from, db + 0.10), L - 0.06)
    left = [
        _seg("hem",        [(0.0, -L), (hem_half, -L)]),
        ("side_L",         segs["side_L"]),
        ("arm_L",          segs["arm_L"]),
        ("shoulder_L",     segs["shoulder_L"]),
        ("neck_L",         neck),
        _seg("cb_L",       [(0.0, -db), (0.0, -vent_from)]),
        _seg("vent_L",     [(0.0, -vent_from), (0.0, -L)]),
    ]
    right = [(n.replace("_L", "_R"), [Vector((-p[0], p[1])) for p in reversed(pts)])
             for n, pts in left]
    return left, list(reversed(right)), info


def preset_coat(m, fit=0.14, length_to="knee", sleeve_len=None):
    """Long coat: the jacket's closed front carried down to the knee, flared
    from the waist so the skirt clears the hips and thighs, and a back in two
    halves with a vent from below the hip, so the hem can open over the legs
    instead of wrapping them like a tube."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    hip_half = g["hip"] * 0.5 * (1.0 + fit) * 0.5
    hem_half = hip_half * COAT_FLARE
    # closed down to just below the hip, open over the legs like a real coat
    close_to = z["shoulder"] + SHELF - z["hip"] + COAT_VENT
    left, right, L, half, overlap = _open_front(m, fit, d, length_to, overlap=0.0, close_to=close_to,
                                                extra_len=COAT_EXTRA)
    # widen the fronts' hem to the coat's flare (the jacket's hem is cut to the hip)
    def flare(segs, sign):
        out = []
        for n, pts in segs:
            if n.startswith("hem"):
                pts = [Vector((p[0] if abs(p[0]) < 1e-6 else sign * hem_half, p[1])) for p in pts]
            elif n.startswith("side"):
                side, _ = _sides(m, fit, d.get("scye_x", half), hem_half, L, d["arm_d"])
                pts = side[1] if sign > 0 else [Vector((-p[0], p[1])) for p in reversed(side[1])]
            out.append((n, [Vector(p) for p in pts]))
        return out
    left, right = flare(left, 1.0), flare(right, -1.0)
    vent_from = z["shoulder"] + SHELF - z["hip"] + COAT_VENT
    back_l, back_r, info = _back_halves(m, fit, d, length_to, hem_half, vent_from, COAT_EXTRA)
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    sl = _sleeve_len(sleeve_len, max(0.20, arm_total * LONG_SLEEVE * _flare_extra(d)), d, arm_total)
    sleeve, cw, cap_h = _sleeve(d, fit, sl, straight=(sleeve_len == "elbow"))
    sh = _sleeve_height(cap_h, sl, arm_total)
    body_h = (z["shoulder"] + SHELF - L * 0.5 - m["zmin"]) / m["height"]
    off = _arc_angle(m, z["chest"], half * 0.5)
    pieces = [
        dict(name="Front_L", segs=left,  anchor='TORSO_FRONT', height=body_h, ease=0.036, spin=off),
        dict(name="Front_R", segs=right, anchor='TORSO_FRONT', height=body_h, ease=0.036, spin=-off),
        dict(name="Back_L",  segs=back_l, anchor='TORSO_BACK', height=body_h, ease=0.036, spin=-off),
        dict(name="Back_R",  segs=back_r, anchor='TORSO_BACK', height=body_h, ease=0.036, spin=off),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=0.034),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=0.034),
    ]
    seams = [
        ("Front_L", "side_L", "Back_L", "side_L", False),
        ("Front_R", "side_R", "Back_R", "side_R", False),
        ("Front_L", "shoulder_L", "Back_L", "shoulder_L", False),
        ("Front_R", "shoulder_R", "Back_R", "shoulder_R", False),
        ("Back_L", "cb_L", "Back_R", "cb_R", True),
        ("Front_L", "button_L", "Front_R", "button_R", True),
        ("Sleeve_L", "cap_front", "Front_L", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back_L", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front_R", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back_R", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
    ]
    return pieces, seams


# Share of the girth taken by each corset panel, centre front to centre back
# (one side; the front panel is whole, the back is split at the lacing). At
# the bust the front panels take more: the bust is in front, and a panel
# that only interpolates from the top edge to the waist squeezes it and the
# bust pushes the corset down until it sits under it (default woman).
CORSET_SHARES = (("Front", 0.20), ("SideF", 0.15), ("SideB", 0.15), ("Back", 0.10))
CORSET_BUST = (("Front", 0.23), ("SideF", 0.165), ("SideB", 0.135), ("Back", 0.085))
CORSET_CINCH = 0.97   # waist taken in against the measured waist, never eased:
                      # the waist is what holds a corset up. With the dialog's
                      # ease on it too (x1.10 x 0.97 = +6.7 %) it cinched
                      # nothing, and on a V torso, whose girth grows only 2.5 %
                      # in the 9 cm under the waist (The Beast), it hung on the
                      # hips (on a woman the hips and bust hid it)
CORSET_DIP = 0.035    # sweetheart dip at the top and busk point at the bottom
CORSET_OVER = 0.02    # top edge above the bust's fullest line (women)
CORSET_HIGH_HIP = 0.05  # bottom edge above the hip line
CORSET_PIT = 0.03     # top edge this far under the armpit, at the sides and back
CORSET_MAN_PIT = 0.06  # men's overbust top: this far under the armpit at least.
                       # Drafted from a sleeveless armhole it fell 13-15 cm under
                       # the armpit on heavy-armed men (The Beast, the default
                       # man), under the pecs: the overbust was an underbust
UNDERBUST_DROP = 0.60  # underbust top: this share of the way down from the armpit to the waist


def _corset_panel(top_w, bust_w, waist_w, bot_w, Lb, Lw, L, dip_top=0.0, dip_bot=0.0,
                  drop_l=0.0, drop_r=0.0):
    """A vertical corset panel: straight bottom and top (or a centre dip), the
    two long edges shaped through the bust and in to the waist. e_L is the +X
    edge, bottom to top; e_R the -X edge, top to bottom."""
    def edge(drop):
        lb = max(Lb, drop + 0.02)
        low = _side_curve((bot_w * 0.5, -L), (waist_w * 0.5, -Lw), (bust_w * 0.5, -lb))
        dy = (lb - drop) * 0.5
        high = patterns.bezier((bust_w * 0.5, -lb), (bust_w * 0.5, -lb + dy),
                               (top_w * 0.5, -drop - dy), (top_w * 0.5, -drop), 5)
        return low + high[1:]
    left = edge(drop_l)
    right = [Vector((-p[0], p[1])) for p in reversed(edge(drop_r))]
    if dip_bot > 0.0:
        bottom = [Vector((-bot_w * 0.5, -L)), Vector((0.0, -L - dip_bot)), Vector((bot_w * 0.5, -L))]
    else:
        bottom = [Vector((-bot_w * 0.5, -L)), Vector((bot_w * 0.5, -L))]
    if dip_top > 0.0:
        top = patterns.bezier((top_w * 0.5, 0.0), (top_w * 0.25, 0.012), (top_w * 0.12, -dip_top),
                              (0.0, -dip_top), 6)
        top = top + [Vector((-p[0], p[1])) for p in reversed(top[:-1])]
    else:
        top = [Vector((top_w * 0.5, -drop_l)), Vector((-top_w * 0.5, -drop_r))]
    return [("bottom", bottom), ("e_L", [Vector(p) for p in left]), ("top", top), ("e_R", right)]


def preset_corset(m, fit=-0.02, top_to="underarm", length_to="hip"):
    """Overbust corset in seven panels: a whole front with a sweetheart top and
    a busk point, side-front and side-back panels, and the back in two halves
    joined at the centre (where the lacing would be). Cut to the girths at the
    top, waist and hip, with the waist cinched; use a stiff fabric."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, max(fit, 0.0), sleeveless=True)
    top_z = z["shoulder"] + SHELF - d["arm_d"] - 0.025
    underbust = top_to == "underbust"
    man = m.get("figure", m.get("figure_auto")) == 'MAN'
    arm0 = m.get("limbs", {}).get("arm_l")
    if underbust:
        # under the bust: a share of the way down from the armpit to the
        # waist (the measured "chest" line is no guide: on Hanka it is 4 cm
        # under the shoulder), never above the bust line, and at least 6 cm
        # above the waist (which is what decides on Manuka)
        pit0 = (Vector(arm0["p0"]).z - arm0["rad"][0]) if arm0 else z["chest"]
        top_z = pit0 - (pit0 - z["waist"]) * UNDERBUST_DROP
        top_z = max(min(top_z, z["chest"] - 0.02), z["waist"] + 0.06)
    elif not man:
        # an overbust corset covers the bust; the drafted underarm can sit
        # below the bust's fullest line (default woman: 1.11 m against a bust
        # at 1.20 m), which made it an underbust that hung under the breasts
        top_z = min(max(top_z, z["chest"] + CORSET_OVER), z["shoulder"] - 0.05)
    elif arm0:
        # a man's overbust reaches under the arm too, not just to the drafted
        # armhole (on The Beast 15 cm under the armpit)
        top_z = max(top_z, Vector(arm0["p0"]).z - arm0["rad"][0] - CORSET_MAN_PIT)
    # a corset ends on the high hip; its bottom is cut to the girth where it
    # actually ends (cut to the full hip it stood off the body like a peplum)
    bot_z = z[length_to] + CORSET_HIGH_HIP
    L = max(0.15, top_z - bot_z)
    Lw = min(max(top_z - z["waist"], 0.05), L - 0.05)
    Lb = min(max(top_z - z["chest"], 0.03), Lw - 0.04)
    g_top = avatar.girth_at(m, top_z)
    g_bust = max(g["chest"], g_top)
    man_over = man and not underbust and z["chest"] > top_z
    if underbust or man_over:
        # the bust line is above the top edge: take the panels' second width
        # halfway to the waist, at the girth there. A man's overbust too: his
        # chest line (the lats' widest) sits over the top edge, and cut to
        # that girth 3 cm under the edge the top stood 20 % (The Beast) to
        # 40 % wide and crumpled under the pecs
        Lb = Lw * 0.5
        g_bust = avatar.girth_at(m, top_z - Lb)
    k = 1.0 + fit
    # a man's overbust has no bust over it to hold it: its top and ribs hug,
    # like the waist (eased, The Beast's top stood 3 cm off under the pecs
    # and flared, and the ribs folded across the back)
    k_top = min(k, 1.0) if man_over else k
    tops, busts, waists, bots = {}, {}, {}, {}
    bust_share = dict(CORSET_BUST)
    norm = bust_share["Front"] + 2 * (bust_share["SideF"] + bust_share["SideB"] + bust_share["Back"])
    for name, share in CORSET_SHARES:
        # the top edge runs at (women) or just under the bust: front-weighted
        # too, or the side and back panels stand off at the top of the seams
        tops[name] = g_top * k_top * bust_share[name] / norm
        busts[name] = g_bust * k_top * bust_share[name] / norm
        waists[name] = g["waist"] * min(k, 1.0) * CORSET_CINCH * share
        bots[name] = avatar.girth_at(m, bot_z + 0.02) * k * share
    # under the arm the top drops to below the armpit (it rode 1-2.5 cm up
    # into it on the default woman, where the side seam folded): the front
    # panel keeps its height, the side-front slopes down to the side seam,
    # the side-back and back panels sit at the lower height
    arm = m.get("limbs", {}).get("arm_l")
    drop = 0.0
    if arm and not underbust:
        pit = Vector(arm["p0"]).z - arm["rad"][0]
        drop = max(0.0, top_z - (pit - CORSET_PIT))
    def panel(name, front=False, dl=0.0, dr=0.0):
        return _corset_panel(tops[name], busts[name], waists[name], bots[name], Lb, Lw, L,
                             (0.0 if underbust else CORSET_DIP) if front else 0.0,
                             CORSET_DIP if front else 0.0,
                             dl, dr)
    def h_of(segs):
        # each panel is placed by the centre of its own box: the front's busk
        # point makes its box reach lower, and placed like the others it sat
        # 17 mm high against its neighbours
        ys = [p[1] for _, pts in segs for p in pts]
        return (top_z + (min(ys) + max(ys)) * 0.5 - m["zmin"]) / m["height"]
    zc = z["waist"]
    a_sf = _arc_angle(m, zc, (waists["Front"] + waists["SideF"]) * 0.5)
    a_bk = _arc_angle(m, zc, waists["Back"] * 0.5)
    a_sb = _arc_angle(m, zc, waists["Back"] + waists["SideB"] * 0.5)
    e = 0.012
    pf = panel("Front", True)
    psf_l = panel("SideF", dl=drop)            # +X (side seam) edge dropped
    psf_r = panel("SideF", dr=drop)            # on the right piece +X faces the front
    psb = panel("SideB", dl=drop, dr=drop)
    pbk = panel("Back", dl=drop, dr=drop)
    pieces = [
        dict(name="Front",   segs=pf, anchor='TORSO_FRONT', height=h_of(pf), ease=e),
        dict(name="SideF_L", segs=psf_l, anchor='TORSO_FRONT', height=h_of(psf_l), ease=e, spin=a_sf),
        dict(name="SideF_R", segs=psf_r, anchor='TORSO_FRONT', height=h_of(psf_r), ease=e, spin=-a_sf),
        dict(name="SideB_L", segs=psb, anchor='TORSO_BACK',  height=h_of(psb), ease=e, spin=-a_sb),
        dict(name="SideB_R", segs=psb, anchor='TORSO_BACK',  height=h_of(psb), ease=e, spin=a_sb),
        dict(name="Back_L",  segs=pbk, anchor='TORSO_BACK',  height=h_of(pbk), ease=e, spin=-a_bk),
        dict(name="Back_R",  segs=pbk, anchor='TORSO_BACK',  height=h_of(pbk), ease=e, spin=a_bk),
    ]
    # +X runs towards the avatar's left on every piece, front and back, so
    # neighbours meet e_L to e_R (opposite directions: reversed), except at
    # the side seams, where a front and a back panel meet edge to edge with
    # their outer edges (both e_L on the left, both e_R on the right).
    # closed: through both corners, or the reversed seams sew one row off
    # and the top edge steps 12-17 mm at every seam
    seams = [
        ("Front",   "e_L", "SideF_L", "e_R", True,  True),
        ("Front",   "e_R", "SideF_R", "e_L", True,  True),
        ("SideF_L", "e_L", "SideB_L", "e_L", False, True),
        ("SideF_R", "e_R", "SideB_R", "e_R", False, True),
        ("SideB_L", "e_R", "Back_L",  "e_L", True,  True),
        ("SideB_R", "e_L", "Back_R",  "e_R", True,  True),
        ("Back_L",  "e_R", "Back_R",  "e_L", True,  True),
    ]
    return pieces, seams


HOOD_SPAN = 0.96   # hood panel front-to-back against the head's depth (Nora's)
HOOD_LEN = 0.99    # hood height against the head's length, before the crown's rise


HOOD_BRIM = 1.0     # the brim reaches the front of the head (0.85 left Hanka's and
                    # Mao's hoods worse)
HOOD_PEAK = 1.10    # face edge top, forward of its bottom: a worn hood's brim
                    # rests on the forehead; leaning back (0.86, as upstream)
                    # the opening sat behind the hairline and the hood slid
                    # off the back of a round head (Hanka)


def _hood(neck_f, neck_b, height, face_first, min_span=0.0, peak=0.86, face_top=0.0,
          head_sil=None):
    """One side of a hood. face_first puts the face opening at +X.

    The neck edge is cut to the necklines it will be sewn to, front and back
    separately, not from the neck girth: a hood cut larger than its neckline
    drags the front neck up into a crease, and one cut to the average of a
    deep front and a shallow back gathers at one and stretches at the other.
    """
    depth = (neck_f + neck_b) * 0.5
    dip = depth * 0.10
    depth_f = math.sqrt(max(1e-6, neck_f ** 2 - dip ** 2))
    depth_b = math.sqrt(max(1e-6, neck_b ** 2 - dip ** 2))
    ftop = max(depth_f * peak, face_top)
    face = _seg("face", [(depth_f, 0.0), (ftop, height)])

    def crown_pts(back):
        return patterns.bezier((ftop, height), (depth * 0.15, height * 1.12),
                               (-depth * 0.95 - back, height * 0.72), (-depth_b, 0.0), 14)

    def span(back):
        xs = [p[0] for p in crown_pts(back)] + [depth_f, -depth_b]
        return max(xs) - min(xs)

    back = 0.0
    # The neck edge is fixed by the neckline; a big head on a slim neck needs
    # the crown to reach further back than that neckline would carry it, or
    # the hood cannot cover the head (Mao: 0.76x her head's depth).
    if min_span > span(0.0):
        back = _solve(span, min_span, 0.0, min_span * 2.0)
    pts = crown_pts(back)
    if head_sil is not None:
        pts = _crown_round_head(pts, *head_sil)
    crown = ("crown", pts)
    segs = [
        _seg("neck_back",  [(-depth_b, 0.0), (0.0, -dip)]),
        _seg("neck_front", [(0.0, -dip), (depth_f, 0.0)]),
        face, crown,
    ]
    if face_first:
        return segs
    return [(n, [Vector((-p[0], p[1])) for p in pts]) for n, pts in segs]


def _crown_round_head(pts, hf, hz, a, c, margin):
    """Push the crown curve out round the head's side silhouette.

    Worn up, each half is laid beside the head and pushed out sideways
    (build._head_transform); the halves only meet where the draft lies
    outside the head's outline seen from the side. The crown curve cut
    through that outline in its upper back quarter, so the crown seam
    started with the head between its two sides - 13.6 cm apart on the
    default woman, 16.4 on Hanka, 15 on Mao - and the cloth, which rests in
    the shape it is placed in, had to stretch or drag the face back to close
    it. Each point inside the head's ellipse (a forward, c up, centred at
    hf, hz from the draft's neck point) plus margin moves out radially to
    it; points already outside stay, and so do the two ends."""
    out = [Vector(p) for p in pts]
    for i in range(1, len(out) - 1):
        dx, dy = out[i].x - hf, out[i].y - hz
        r = math.hypot(dx, dy)
        if r < 1e-6:
            continue
        ux, uy = dx / r, dy / r
        need = 1.0 / math.sqrt((ux / a) ** 2 + (uy / c) ** 2) + margin
        if r < need:
            out[i] = Vector((hf + ux * need, hz + uy * need))
    return out


HOOD_EASE = 0.025   # how far the hood is laid off the head
HOOD_RISE = 1.05    # worn hood height against neckline-to-crown


def _draft_origin(segs):
    """Where the draft's origin lands in the piece once create_panel centres
    it on its bounding box, as local (X, Z)."""
    xs = [p[0] for _, pts in segs for p in pts]
    ys = [p[1] for _, pts in segs for p in pts]
    return (-(min(xs) + max(xs)) * 0.5, -(min(ys) + max(ys)) * 0.5)


HOODIE_SLEEVE_EASE = 0.034   # the hoodie's long sleeve, laid over a T-shirt's
SHORT_SLEEVE_EASE = 0.014    # a short sleeve against the arm


def _hood_pieces(m, z, ng, nh, dfh, dbh):
    """The hoodie's two hood halves, sized to the head and to a neckline of
    half-width nh and depths dfh (front) and dbh (back). Returns
    (hood_l, hood_r, head_h); shared by the hoodie and the cape."""
    # the hood's neck edge has to measure the same as the neckline it joins
    nl_f = _curve_len(patterns.bezier((nh, 0.0), (nh * 0.55, -dfh),
                                      (-nh * 0.55, -dfh), (-nh, 0.0), 14)) * 0.5
    nl_b = _curve_len(patterns.bezier((nh, 0.0), (nh * 0.55, -dbh),
                                      (-nh * 0.55, -dbh), (-nh, 0.0), 14)) * 0.5
    hood_f, hood_b = max(0.03, nl_f / 1.005), max(0.03, nl_b / 1.005)
    hood_h = max(0.12, ng * 0.62)
    head = m.get("head")
    hood_span = 0.0
    if head:
        # sized to the head as well as the neck: an anime neck is slim for its head
        hood_h = max(hood_h, head["len"] * HOOD_LEN)
        hood_span = head["depth"] * HOOD_SPAN
        # worn up it has to reach from the neckline it is sewn to over the
        # crown: the head's own length (chin to crown) is 0.20 m on the
        # default woman, the neckline to the crown 0.29 m
        # (to the crown of the head itself: the avatar's top can be hair or
        # ears - 5 cm higher on Hanka - and the extra cloth caved in)
        crown = head.get("z_lo", m["zmax"] - head["len"]) + head["len"]
        hood_h = max(hood_h, (crown - (z["shoulder"] + SHELF)) * HOOD_RISE)
    head_h = (z["neck"] + ng * 0.30 - m["zmin"]) / m["height"]
    face_top = 0.0
    if head and "center" in head:
        # the brim reaches the forehead: measured from the neckline's centre,
        # where the draft's origin goes, to the front of the head. Drafted
        # from the neck alone it ended at the temples on an anime head and
        # the hood slid off the back (Hanka)
        fwd, _side = avatar.basis(m.get("facing", '-Y'))
        c0 = avatar.center_at(m, z["shoulder"] + SHELF)
        face_top = ((Vector(head["center"]).dot(fwd) + head["depth"] * 0.5) - c0.dot(fwd)) * HOOD_BRIM
    sil = None
    if head and "center" in head:
        # the head's side outline in the draft's frame (origin at the
        # neckline's centre, X forward, Y up), for the crown to clear
        hc = Vector(head["center"])
        sil = (hc.dot(fwd) - c0.dot(fwd), hc.z - (z["shoulder"] + SHELF),
               head["depth"] * 0.5, head["len"] * 0.5, HOOD_EASE + 0.01)
        # not on a head with no scalp (it has a closed proxy): Mao's crown
        # closed with the plain curve (3 stitches open, at the neckline) and
        # rounding it opened 15-31, with her outline from the bowl or the
        # proxy alike. Woman and Hanka went from 1-3 open to 0 with it
        import bpy
        px = bpy.data.objects.get(avatar.PROXY_NAME)
        if px is not None and px.get("cd_open"):
            sil = None
    hood_l = _hood(hood_f, hood_b, hood_h, False, hood_span, HOOD_PEAK, face_top, sil)
    hood_r = _hood(hood_f, hood_b, hood_h, True, hood_span, HOOD_PEAK, face_top, sil)
    return hood_l, hood_r, head_h


def preset_hoodie(m, fit=0.20, length_to="hip", sleeve_len=None):
    """Sweater body with long sleeves and a two-panel hood."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    ng = avatar.neck_girth(m)
    nh = d["neck_half"] * 1.12
    dfh, dbh = d["df"] * 1.15, d["db"] * 1.3
    front, info = _bodice(m, fit, length_to, dfh, nh, d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                          sh_drop=d["sh_drop"], split_neck=True)
    back, _ = _bodice(m, fit, length_to, dbh, nh, d["arm_d"], d["sh_x"], scye_x=d.get("scye_x"),
                      sh_drop=d["sh_drop"], split_neck=True)
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    # cut past the wrist: a long sleeve takes up several centimetres bunching
    # over the elbow, so one drafted to the arm's length settles short of it
    sl = _sleeve_len(sleeve_len, max(0.20, arm_total * LONG_SLEEVE * _flare_extra(d)), d, arm_total)
    sleeve, cw, cap_h = _sleeve(d, fit, sl, straight=(sleeve_len == "elbow"))
    sh = _sleeve_height(cap_h, sl, arm_total)
    # a short or elbow sleeve is laid close to the arm like a T-shirt's: at
    # the long sleeve's 34 mm, with no forearm and hand to hold it, Manuka's
    # elbow sleeves rode up and stayed open underneath
    s_ease = HOODIE_SLEEVE_EASE if sl > arm_total * 0.9 or not arm_total else SHORT_SLEEVE_EASE
    body_h = (z["shoulder"] + SHELF - info["L"] * 0.5 - m["zmin"]) / m["height"]
    hood_l, hood_r, head_h = _hood_pieces(m, z, ng, nh, dfh, dbh)
    pieces = [
        dict(name="Front", segs=front, anchor='TORSO_FRONT', height=body_h, ease=0.036),
        dict(name="Back",  segs=back,  anchor='TORSO_BACK',  height=body_h, ease=0.036),
        dict(name="Sleeve_L", segs=sleeve, anchor='ARM_L', height=sh, ease=s_ease),
        dict(name="Sleeve_R", segs=sleeve, anchor='ARM_R', height=sh, ease=s_ease),
        # worn up, laid over the head (build._head_transform): the torso's
        # cylinder wrap could only put the hood beside or behind the head
        dict(name="Hood_L", segs=hood_l, anchor='HEAD_L', height=head_h, ease=HOOD_EASE,
             dome_origin=_draft_origin(hood_l)),
        dict(name="Hood_R", segs=hood_r, anchor='HEAD_R', height=head_h, ease=HOOD_EASE,
             dome_origin=_draft_origin(hood_r)),
    ]
    seams = [
        ("Front", "side_L", "Back", "side_L", False),
        ("Front", "side_R", "Back", "side_R", False),
        ("Front", "shoulder_L", "Back", "shoulder_L", False),
        ("Front", "shoulder_R", "Back", "shoulder_R", False),
        ("Sleeve_L", "cap_front", "Front", "arm_L", True),
        ("Sleeve_L", "cap_back", "Back", "arm_L", False),
        ("Sleeve_L", "under_front", "Sleeve_L", "under_back", True),
        ("Sleeve_R", "cap_front", "Front", "arm_R", False),
        ("Sleeve_R", "cap_back", "Back", "arm_R", True),
        ("Sleeve_R", "under_front", "Sleeve_R", "under_back", True),
        ("Hood_L", "crown", "Hood_R", "crown"),
        ("Hood_L", "neck_front", "Front", "neck_L"),
        ("Hood_R", "neck_front", "Front", "neck_R"),
        ("Hood_L", "neck_back", "Back", "neck_L"),
        ("Hood_R", "neck_back", "Back", "neck_R"),
    ]
    return pieces, seams


CAPE_FLARE = 1.25    # each half-front's hem against a quarter of the hips
CAPE_BACK_FLARE = 1.6   # the back is fuller, and laid further out (CAPE_BACK_EASE)
CAPE_BACK_EASE = 0.06   # so its wide sides fall over the fronts instead of through them
CAPE_CLOSE = 0.12    # how far down from the neck the fronts are fastened
CAPE_EASE = 0.045    # laid off the body: it goes over whatever is worn under it
CAPE_ARM = 0.50      # the flap over each arm, as a fraction of the whole arm
CAPE_ARM_FLARE = 1.6 # its hem against its width at the shoulder
CAPE_ARM_EASE = 0.03
CAPE_EXTRA = 0.12    # past the hip: the coat's extra length for the same settling


def _cape_sleeve(d, fit, armhole, length, arm_ease):
    """A flap over the arm, sewn into the cape's armhole and left open
    underneath: a set-in cap (sized to the armhole it is sewn into) flaring
    to a wide hem. Laid round the arm as a tube with a slit underneath, its
    hem is kept under one turn round the arm where it can be (the flare is
    capped; the width at the cap is the armhole's), or the flat piece wraps
    past itself and the cloth starts inside its own other half."""
    d2 = dict(d, armhole=armhole / 1.02)
    segs, cw, cap_h = _sleeve(d2, fit, length, width_ease=1.25, straight=True)
    turn = 2.0 * math.pi * (d.get("biceps_r", 0.05) + arm_ease)
    hw = max(cw, min(cw * CAPE_ARM_FLARE, turn * 0.9))
    caps = [sg for sg in segs if sg[0].startswith("cap_")]
    return [
        _seg("under_front", [(-cw * 0.5, 0.0), (-hw * 0.5, -length)]),
        _seg("hem",         [(-hw * 0.5, -length), (hw * 0.5, -length)]),
        _seg("under_back",  [(hw * 0.5, -length), (cw * 0.5, 0.0)]),
    ] + caps, cw, cap_h


def preset_cape(m, fit=0.10, length_to="knee", arms=True):
    """Hooded cape: a back and two fronts hanging from the shoulders, fastened
    from the neck to the chest and open below, with the hoodie's hood.

    Drafted from the avatar like every preset (no pattern from elsewhere):
    the front and back meet only at the shoulder seams, and the sides are
    left open below the armpit. A flap sewn into each armhole and open
    underneath falls over the arm to the elbow (arms=False leaves the arm
    bare, a tabard).
    The fronts reach about a quarter of the hips round each; the back is
    fuller and laid a little further out, so where its sides run past the
    body's sides (they are laid out flat from there) they pass outside the
    fronts instead of through them, and fall over them."""
    z, g, _ = _measurements(m)
    d = _draft_top(m, fit)
    ng = avatar.neck_girth(m)
    nh = d["neck_half"] * 1.12
    dfh, dbh = d["df"] * 1.15, d["db"] * 1.3
    sh_x, sh_drop, arm_d = d["sh_x"], d["sh_drop"], d["arm_d"]
    top = z["shoulder"] + SHELF
    L = max(0.20, top - z[length_to])
    if z[length_to] < z["hip"] - 0.05:
        # past the hip it settles shorter, like the coat (Hanka's knee-length
        # cape ended 13 cm above her knee): cut it longer by the same amount
        L += CAPE_EXTRA * _len_scale(m)
    H = max(sh_x * 1.1, g["hip"] * 0.25 * (1.0 + fit) * CAPE_FLARE)
    HB = max(H, g["hip"] * 0.25 * (1.0 + fit) * CAPE_BACK_FLARE)
    close = min(CAPE_CLOSE * _len_scale(m), L * 0.4)

    neck_f = patterns.bezier((nh, 0.0), (nh * 0.55, -dfh), (-nh * 0.55, -dfh), (-nh, 0.0), 14)
    neck_b = patterns.bezier((nh, 0.0), (nh * 0.55, -dbh), (-nh * 0.55, -dbh), (-nh, 0.0), 14)
    hf, hb = len(neck_f) // 2, len(neck_b) // 2
    # the closure starts where the neck curve actually ends at the centre
    # (3/4 of dfh, not dfh): starting lower left a 2 cm jump that was taken
    # into the neck and closure edges, and their seams no longer matched
    yc = neck_f[hf].y
    # the side runs straight down from the shoulder tip past the armpit,
    # where the arm leaves the body, and only then flares to the hem
    pit = (sh_x * 1.04, -arm_d)
    side_L, side_bL = [(H, -L), pit], [(HB, -L), pit]
    arm_L = [pit, (sh_x, -sh_drop)]

    def mirror(segs):
        return [(n.replace("_L", "_R"), [Vector((-p[0], p[1])) for p in reversed(pts)])
                for n, pts in reversed(segs)]

    back = [
        _seg("hem",        [(-HB, -L), (HB, -L)]),
        _seg("side_L",     side_bL),
        _seg("arm_L",      arm_L),
        _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]),
        ("neck_L",         neck_b[:hb + 1]),
        ("neck_R",         neck_b[hb:]),
        _seg("shoulder_R", [(-nh, 0.0), (-sh_x, -sh_drop)]),
        _seg("arm_R",      [(-x, y) for x, y in reversed(arm_L)]),
        _seg("side_R",     [(-x, y) for x, y in reversed(side_bL)]),
    ]
    front_l = [
        _seg("hem",        [(0.0, -L), (H, -L)]),
        _seg("side_L",     side_L),
        _seg("arm_L",      arm_L),
        _seg("shoulder_L", [(sh_x, -sh_drop), (nh, 0.0)]),
        ("neck_L",         neck_f[:hf + 1]),
        _seg("close_L",    [(0.0, yc), (0.0, yc - close)]),
        _seg("open_L",     [(0.0, yc - close), (0.0, -L)]),
    ]
    front_r = mirror(front_l)

    hood_l, hood_r, head_h = _hood_pieces(m, z, ng, nh, dfh, dbh)
    body_h = (top - L * 0.5 - m["zmin"]) / m["height"]
    off = _arc_angle(m, z["chest"], H * 0.5)
    pieces = [
        dict(name="Front_L", segs=front_l, anchor='TORSO_FRONT', height=body_h, ease=CAPE_EASE, spin=off),
        dict(name="Front_R", segs=front_r, anchor='TORSO_FRONT', height=body_h, ease=CAPE_EASE, spin=-off),
        dict(name="Back",    segs=back,    anchor='TORSO_BACK',  height=body_h, ease=CAPE_BACK_EASE),
        dict(name="Hood_L", segs=hood_l, anchor='HEAD_L', height=head_h, ease=HOOD_EASE,
             dome_origin=_draft_origin(hood_l)),
        dict(name="Hood_R", segs=hood_r, anchor='HEAD_R', height=head_h, ease=HOOD_EASE,
             dome_origin=_draft_origin(hood_r)),
    ]
    seams = [
        ("Front_L", "shoulder_L", "Back", "shoulder_L", False),
        ("Front_R", "shoulder_R", "Back", "shoulder_R", False),
        ("Front_L", "close_L", "Front_R", "close_R", True),
        ("Hood_L", "crown", "Hood_R", "crown"),
        ("Hood_L", "neck_front", "Front_L", "neck_L"),
        ("Hood_R", "neck_front", "Front_R", "neck_R"),
        ("Hood_L", "neck_back", "Back", "neck_L"),
        ("Hood_R", "neck_back", "Back", "neck_R"),
    ]
    arm_total = sum(m.get("limbs", {}).get(k, {}).get("len", 0.0) for k in ("arm_l", "farm_l"))
    if arms and arm_total:
        hole = _curve_len([Vector(p) for p in arm_L]) * 2.0
        sl = arm_total * CAPE_ARM
        flap, cw, cap_h = _cape_sleeve(d, fit, hole, sl, CAPE_ARM_EASE)
        sh = _sleeve_height(cap_h, sl, arm_total)
        pieces += [dict(name="Sleeve_L", segs=flap, anchor='ARM_L', height=sh, ease=CAPE_ARM_EASE),
                   dict(name="Sleeve_R", segs=flap, anchor='ARM_R', height=sh, ease=CAPE_ARM_EASE)]
        # sewn into the armhole only: underneath it stays open, a cape
        seams += [("Sleeve_L", "cap_front", "Front_L", "arm_L", True),
                  ("Sleeve_L", "cap_back", "Back", "arm_L", False),
                  ("Sleeve_R", "cap_front", "Front_R", "arm_R", False),
                  ("Sleeve_R", "cap_back", "Back", "arm_R", True)]
    return pieces, seams


def preset_underbust(m, fit=-0.02, length_to="hip"):
    """Underbust corset: the corset's seven panels with the top edge under
    the bust instead of over it."""
    return preset_corset(m, fit=fit, top_to="underbust", length_to=length_to)


PRESETS = {
    'TSHIRT':    ("T-Shirt",   preset_tshirt),
    'TANK':      ("Tank Top",  preset_tank),
    'SKIRT':     ("Skirt",     preset_skirt),
    'PLEATED':   ("Pleated Skirt", preset_pleated_skirt),
    'TIERED':    ("Ruffled Skirt", preset_tiered_skirt),
    'TROUSERS':  ("Trousers",  preset_trousers),
    'JUMPSUIT':  ("Jumpsuit",  preset_jumpsuit),
    'DRESS':     ("Dress",     preset_dress),
    'JACKET':    ("Jacket",    preset_jacket),
    'HOODIE':    ("Hoodie",    preset_hoodie),
    'COAT':      ("Long Coat", preset_coat),
    'CORSET':    ("Corset",    preset_corset),
    'UNDERBUST': ("Underbust Corset", preset_underbust),
    'CAPE':      ("Hooded Cape", preset_cape),
    'RECTANGLE': ("Flat Panel", preset_rectangle),
}

# ---------------------------------------------------------------- options
# The Length and Sleeves controls of Add Garment. "Regular" is always the
# preset as drafted; Short and Long change one argument of the preset, and
# the hint is what the dialog shows for that garment.

LENGTH_OPTIONS = {
    'TSHIRT':   ({'length_to': "waist"},  {'length_to': "thigh"},  "Short: cropped at the waist. Long: a tunic to mid-thigh"),
    'TANK':     ({'length_to': "waist"},  {'length_to': "thigh"},  "Short: cropped at the waist. Long: a tunic to mid-thigh"),
    'HOODIE':   ({'length_to': "waist"},  {'length_to': "thigh"},  "Short: cropped at the waist. Long: a tunic to mid-thigh"),
    'JACKET':   ({'length_to': "waist"},  {'length_to': "thigh"},  "Short: to the waist. Long: to mid-thigh"),
    'COAT':     ({'length_to': "thigh"},  {'length_to': "calf"},   "Short: mid-thigh. Long: mid-calf"),
    'DRESS':    ({'length_to': "thigh"},  {'length_to': "calf"},   "Short: mid-thigh. Long: mid-calf"),
    'TROUSERS': ({'length_to': "thigh"},  {'length_to': "knee"},   "Short: shorts to mid-thigh. Long: to the knee (Regular is full length)"),
    'JUMPSUIT': ({'length_to': "thigh"},  {'length_to': "knee"},   "Short: shorts to mid-thigh. Long: to the knee (Regular is full length)"),
    'SKIRT':    ({'length': 0.70},        {'length': 1.45},        "Short: a mini. Long: below the knee"),
    'PLEATED':  ({'length': 0.70},        {'length': 1.45},        "Short: a mini. Long: below the knee"),
    'CAPE':     ({'length_to': "hip"},    {'length_to': "calf"},   "Short: a capelet to the hip. Long: mid-calf"),
    'TIERED':   ({'length': 0.75},        {'length': 1.35},        "Short: a mini. Long: below the knee"),
}
# skirt lengths are factors on the preset's own length
_LENGTH_FACTOR = {'length'}

SLEEVE_PRESETS = {'TSHIRT', 'JUMPSUIT', 'DRESS', 'JACKET', 'COAT', 'HOODIE'}
SLEEVELESS_OK = {'DRESS'}       # presets that can drop the sleeves altogether
SLEEVE_SPEC = {'NONE': "none", 'SHORT': "short", 'ELBOW': "elbow", 'LONG': "long"}


def has_length(preset):
    return preset in LENGTH_OPTIONS


def has_sleeves(preset):
    return preset in SLEEVE_PRESETS


def length_hint(preset):
    return LENGTH_OPTIONS[preset][2] if preset in LENGTH_OPTIONS else ""


def preset_kwargs(preset, length='REGULAR', sleeves='REGULAR'):
    """Keyword arguments for PRESETS[preset] from the dialog's choices.
    Choices that don't apply to the garment are ignored, so an outfit can
    pass the same ones to every piece."""
    import inspect
    fn = PRESETS[preset][1]
    params = inspect.signature(fn).parameters
    kw = {}
    if length in ('SHORT', 'LONG') and preset in LENGTH_OPTIONS:
        for k, v in LENGTH_OPTIONS[preset][0 if length == 'SHORT' else 1].items():
            kw[k] = params[k].default * v if k in _LENGTH_FACTOR else v
    if sleeves in SLEEVE_SPEC and preset in SLEEVE_PRESETS:
        if sleeves != 'NONE' or preset in SLEEVELESS_OK:
            kw['sleeve_len'] = SLEEVE_SPEC[sleeves]
    return kw


LENGTH_ITEMS = [('SHORT', "Short", "Shorter than the preset"),
                ('REGULAR', "Regular", "The preset as drafted"),
                ('LONG', "Long", "Longer than the preset")]
SLEEVE_ITEMS = [('REGULAR', "Regular", "The preset's own sleeves"),
                ('NONE', "None", "Sleeveless (dresses only)"),
                ('SHORT', "Short", "A short sleeve, about a quarter of the arm"),
                ('ELBOW', "Elbow", "Just past the elbow"),
                ('LONG', "Long", "To the wrist")]


# Complete outfits: (label, figure, [(preset, ease), ...]) worn from the inside out.
# Trousers and skirts are worn FIRST, tops untucked over the waistband -
# the order people actually dress in. A top sewn under the trousers leaves
# its hem beneath the waistband, and trousers closing over a slippery shirt
# instead of skin slide down a low-rise hip exactly like beltless trousers
# over an untucked shirt do in life.
OUTFITS = {
    'M_CASUAL':  ("Casual",         'MAN',   [('TROUSERS', 0.12), ('TSHIRT', 0.10), ('JACKET', 0.13)]),
    'M_STREET':  ("Streetwear",     'MAN',   [('TROUSERS', 0.14), ('TSHIRT', 0.10), ('HOODIE', 0.22)]),
    'M_WORK':    ("Workwear",       'MAN',   [('TSHIRT', 0.10), ('JUMPSUIT', 0.14)]),
    'M_LAYERED': ("Full Layers",    'MAN',   [('TROUSERS', 0.13), ('TANK', 0.07), ('TSHIRT', 0.12),
                                              ('JACKET', 0.15)]),
    'W_CASUAL':  ("Casual",         'WOMAN', [('TROUSERS', 0.10), ('TANK', 0.08), ('JACKET', 0.12)]),
    'W_SUMMER':  ("Summer",         'WOMAN', [('SKIRT', 0.10), ('TANK', 0.08)]),
    'W_DRESSED': ("Dress & Jacket", 'WOMAN', [('DRESS', 0.09), ('JACKET', 0.13)]),
    'W_STREET':  ("Streetwear",     'WOMAN', [('TROUSERS', 0.12), ('TSHIRT', 0.10), ('HOODIE', 0.20)]),
    'W_WORK':    ("Workwear",       'WOMAN', [('TSHIRT', 0.10), ('JUMPSUIT', 0.12)]),
}

FIGURE_LABEL = {'MAN': "Man", 'WOMAN': "Woman"}


def outfit_items(figure=None):
    """Enum items for the outfits of one figure (or all of them)."""
    return [(k, "%s (%s)" % (v[0], FIGURE_LABEL[v[1]]),
             "Build %s for a %s: %s" % (v[0], FIGURE_LABEL[v[1]].lower(),
                                        ", ".join(p for p, _ in v[2])))
            for k, v in OUTFITS.items() if figure in (None, v[1])]


OUTFIT_ITEMS = outfit_items()

PRESET_ITEMS = [(k, v[0], "Add a %s pattern set" % v[0]) for k, v in PRESETS.items()]
