# Clothing Design - arrangement and garment assembly.
#
# Flat pattern pieces are wrapped onto the measured body (MD's "arrangement"),
# joined into one mesh, and the seams become loose edges. Blender's cloth solver
# treats loose edges as sewing springs, so the panels stitch themselves together
# during simulation the way real pattern pieces are sewn together.
import bpy, bmesh, math, bisect
from mathutils import Vector
from . import avatar, patterns

GARMENT_PREFIX = "CD_Garment_"

TORSO_ANCHORS = {
    'TORSO_FRONT': (0.0, 1.0),
    'TORSO_LEFT':  (math.pi * 0.5, 1.0),
    'TORSO_BACK':  (math.pi, -1.0),
    'TORSO_RIGHT': (-math.pi * 0.5, 1.0),
    'HIP_FRONT':   (0.0, 1.0),
    'HIP_BACK':    (math.pi, -1.0),
}
LIMB_ANCHORS = {
    'ARM_L': ("arm_l", "farm_l"),
    'ARM_R': ("arm_r", "farm_r"),
    'LEG_L': ("thigh_l", "calf_l"),
    'LEG_R': ("thigh_r", "calf_r"),
}


# ---------------------------------------------------------------- arc mapping

class ArcMap:
    """Arc length along a body cross-section <-> angle, at one height."""

    def __init__(self, m, z, base_theta, ease, steps=200, span=math.pi * 1.25):
        self.th, self.s = [], []
        prev, acc = None, 0.0
        for i in range(steps + 1):
            th = base_theta - span + 2.0 * span * i / steps
            r = avatar.radius_at(m, z, th) + ease
            p = Vector((math.cos(th) * r, math.sin(th) * r))
            if prev is not None:
                acc += (p - prev).length
            prev = p
            self.th.append(th)
            self.s.append(acc)
        s0 = self._interp(self.th, self.s, base_theta)
        self.s = [x - s0 for x in self.s]

    @staticmethod
    def _interp(xs, ys, x):
        i = bisect.bisect_left(xs, x)
        if i <= 0:
            return ys[0]
        if i >= len(xs):
            return ys[-1]
        f = (x - xs[i - 1]) / max(1e-12, xs[i] - xs[i - 1])
        return ys[i - 1] * (1 - f) + ys[i] * f

    def arc_at(self, theta):
        return self._interp(self.th, self.s, theta)

    def theta_of(self, s):
        if s <= self.s[0]:
            return self.th[0]
        if s >= self.s[-1]:
            return self.th[-1]
        i = bisect.bisect_left(self.s, s)
        f = (s - self.s[i - 1]) / max(1e-12, self.s[i] - self.s[i - 1])
        return self.th[i - 1] * (1 - f) + self.th[i] * f


class LimbChain:
    """Polyline axis through one or more limb segments, with radius along it."""

    def __init__(self, m, keys):
        self.segs = []
        total = 0.0
        for k in keys:
            lp = m.get("limbs", {}).get(k)
            if lp:
                self.segs.append(lp)
                total += lp["len"]
        self.total = total

    def valid(self):
        return self.total > 1e-6

    def sample(self, t):
        """t in 0..1 along the whole chain -> (point, radius, axis)."""
        d = t * self.total
        for lp in self.segs:
            if d <= lp["len"] or lp is self.segs[-1]:
                p0, p1 = Vector(lp["p0"]), Vector(lp["p1"])
                ax = (p1 - p0)
                L = max(1e-9, ax.length)
                ax = ax / L
                u = d / lp["len"]
                return p0 + ax * d, avatar.limb_radius_at(lp, min(1.0, max(0.0, u))), ax
            d -= lp["len"]
        p0 = Vector(self.segs[0]["p0"])
        return p0, avatar.limb_radius_at(self.segs[0], 0.0), Vector((0, 0, -1))


# ---------------------------------------------------------------- wrapping

def _dir(fwd, side, th):
    return fwd * math.cos(th) + side * math.sin(th)


def piece_transform(ob, m, fwd, side):
    """Return f(Vector local) -> Vector world for one pattern piece."""
    f = _piece_transform(ob, m, fwd, side)
    if ob.cd.anchor == 'FREE' or m is None:
        return f                     # matrix_world already carries the scale
    # Width / Length (and the garment's Size) live in the object scale; the
    # pattern is in the local XZ plane
    sx, sz = ob.scale.x, ob.scale.z
    if abs(sx - 1.0) < 1e-6 and abs(sz - 1.0) < 1e-6:
        return f
    return lambda p: f(Vector((p.x * sx, p.y, p.z * sz)))


def _piece_transform(ob, m, fwd, side):
    cd = ob.cd
    shift = Vector(cd.shift)

    if cd.anchor == 'FREE' or m is None:
        mw = ob.matrix_world.copy()
        return lambda p: mw @ p

    if cd.anchor in LIMB_ANCHORS:
        chain = LimbChain(m, LIMB_ANCHORS[cd.anchor])
        if not chain.valid():
            mw = ob.matrix_world.copy()
            return lambda p: mw @ p
        # outward direction: away from the body axis at the limb root
        root = Vector(chain.segs[0]["p0"])
        c = avatar.center_at(m, root.z)
        out = Vector((root.x - c.x, root.y - c.y, 0.0))
        if out.length < 1e-6:
            out = side.copy()
        out.normalize()
        spin = cd.spin
        ease = cd.ease
        wrap = cd.wrap

        base_t = cd.height          # fraction along the limb of the piece's centre
        # Reference radius taken once at the piece's centre. Deriving the wrap
        # angle from the local radius instead makes the tube spiral as the limb
        # tapers, so the fabric overlaps itself and self-collision shreds it.
        _p, _r, _a = chain.sample(max(0.0, min(1.0, base_t)))
        r_ref = max(1e-4, _r + ease)
        taper = cd.taper

        def limb_f(p):
            # past +-0.25 every vert used to land on one spot: a sleeve cap
            # above the shoulder joint and a cuff past the wrist were crushed
            t = max(-0.6, min(1.6, base_t + (-p.z) / chain.total))
            pos, r, ax = chain.sample(max(0.0, min(1.0, t)))
            if t < 0.0 or t > 1.0:                       # extend past the ends
                pos = pos + ax * ((t - (0.0 if t < 0 else 1.0)) * chain.total)
            u = out - ax * out.dot(ax)
            if u.length < 1e-6:
                u = side - ax * side.dot(ax)
            u.normalize()
            v = ax.cross(u)
            if v.dot(fwd) > 0.0:
                v = -v
            rr = r + ease
            # A constant angular span keeps a sleeve from spiralling, but a
            # trouser leg's pattern already tapers with the limb, so following
            # the local radius is what keeps its top edge the drafted length.
            r_ang = r_ref * (1.0 - taper) + rr * taper
            th = spin + (p.x / max(1e-4, r_ang)) * wrap
            wrapped = pos + (u * math.cos(th) + v * math.sin(th)) * rr
            if wrap < 0.999:
                # blend to a flat plate tangent to the limb; without this a Wrap of
                # 0 folds every vert onto one angle and the piece collapses to a line
                d0 = u * math.cos(spin) + v * math.sin(spin)
                tangent = -u * math.sin(spin) + v * math.cos(spin)
                flat = pos + d0 * rr + tangent * p.x
                wrapped = flat.lerp(wrapped, wrap)
            return wrapped + shift

        return limb_f

    if cd.anchor in ('HEAD_L', 'HEAD_R'):
        hf = _head_transform(ob, m, fwd, side)
        if hf is not None:
            return hf

    base_theta, xsign = TORSO_ANCHORS.get(cd.anchor, (0.0, 1.0))
    base_theta += cd.spin
    pleat = _pleat_map(ob) if cd.pleats > 0 else None
    clamp = math.radians(95.0)   # past this the panel leaves the body tangentially
                                 # instead of wrapping onto the opposite side
    # Above the shoulder joint the cross-section shrinks to the neck, so a panel
    # mapped by arc length there would wind around the throat. Hold the section
    # at its shoulder size instead: the panel floats over the shoulder shelf and
    # the simulation drops it onto the shoulders, which is where a collar belongs.
    z_cap = avatar.z_of(m, "shoulder") + 0.02
    z_anchor = m["zmin"] + cd.height * m["height"]
    ease, wrap = cd.ease, cd.wrap
    cache = {}
    loose = _loose_extent(ob, xsign) if (ob.get("cd_loose") and pleat is None
                                         and wrap >= 0.999) else None
    centre = base_theta - cd.spin
    lcache = {}
    # cd_loose "armhole": only the armhole is laid out loose (LOOSE_ARMHOLE_FADE)
    band = _armhole_band(ob, m) if (loose is not None and ob.get("cd_loose") == "armhole") else None

    def loose_ease(zq, pz):
        """Ease that lets the piece reach the side of the body at this height
        and no further (see LOOSE_SIDE)."""
        w = 1.0
        if band is not None:
            z0, fade = band
            if pz <= z0 - fade:
                return ease      # below the armhole: laid out as it always was
        lk = (round(zq * 200.0), round(pz * 100.0))
        e = lcache.get(lk)
        if e is not None:
            return e
        if band is not None:
            # worked out at the bucket's own height, not at whichever vert
            # reached it first: the fade changes fast with height, and the
            # two sides' verts reach a bucket in a different order (it left
            # one shoulder seam 12 mm off the mirror of the other)
            zq, pz = lk[0] / 200.0, lk[1] / 100.0
            w = max(0.0, min(1.0, (pz - (z0 - fade)) / fade))
        smin, smax = loose(pz)
        e = ease
        for _ in range(3):
            am = ArcMap(m, zq, base_theta, e)
            hi = am.arc_at(centre + LOOSE_SIDE)
            lo = am.arc_at(centre - LOOSE_SIDE)
            need = max(smax - hi, lo - smin, 0.0)
            if need < 0.002:
                break
            # an arc out to the side grows by its angle for each metre of radius
            e += need / LOOSE_SIDE
        e = ease + (e - ease) * w
        lcache[lk] = e
        return e

    def torso_f(p):
        z = z_anchor + p.z
        zq = min(z, z_cap)
        sink = 0.0
        if pleat is not None:
            px, sink = pleat(p.x, p.z)
            p = Vector((px, p.y, p.z))
        key = round(zq * 200.0)                           # 5 mm height buckets
        e_here = ease
        if loose is not None:
            e_here = loose_ease(zq, p.z)
            key = (key, round(e_here * 1000.0))
        am = cache.get(key)
        if am is None:
            am = ArcMap(m, zq, base_theta, e_here)
            cache[key] = am
        s = p.x * xsign
        c = avatar.center_at(m, zq)
        c.z = z
        s_max = am.arc_at(base_theta + clamp)
        s_min = am.arc_at(base_theta - clamp)
        if s > s_max or s < s_min:
            th_c = base_theta + (clamp if s > s_max else -clamp)
            r_c = avatar.radius_at(m, zq, th_c) + e_here
            edge = c + _dir(fwd, side, th_c) * r_c
            tang = _dir(fwd, side, th_c + math.pi * 0.5)
            wrapped = edge + tang * (s - (s_max if s > s_max else s_min))
            th = th_c
        else:
            th = am.theta_of(s)
            r = avatar.radius_at(m, zq, th) + e_here - sink
            wrapped = c + _dir(fwd, side, th) * r
        if wrap < 0.999:
            r0 = avatar.radius_at(m, zq, base_theta) + ease
            flat = c + _dir(fwd, side, base_theta) * r0 + _dir(fwd, side, base_theta + math.pi * 0.5) * s
            wrapped = flat.lerp(wrapped, wrap)
        return wrapped + shift

    return torso_f


# A loose top (T-shirt, hoodie, jacket: pieces marked cd_loose) is laid out
# reaching the side of the body - this far round from its own centre - and no
# further. Cut straight from the chest, its panels are much wider than a waist
# that goes in (The Beast: 1.8 m of cloth round a 1.05 m waist); wrapped at the
# waist's radius each one ran a quarter turn past the side, front and back
# crossed there, and sewing them folded the surplus into a fin down the side
# seam whose bottom stuck out at the hem as a tab. Where a piece is wider than
# the body there it is laid further out instead, as a loose tube, the way the
# garment actually hangs.
LOOSE_SIDE = math.pi * 0.5


# A jumpsuit's bodice and a cape's panels (cd_loose "armhole") are laid out
# loose only at the armhole, fading back to their own ease over this share
# of the height below the armpit. Their armholes are cut out past the side
# to measure a full arm (_draft_top's scye) and, wrapped round the body, the
# front's armhole landed on the back and the back's on the front: on the
# bundled man 71 of the jumpsuit's 72 armhole stitches (26 of the cape's 64)
# ran from the sleeve cap across the armpit to the wrong side, the armhole
# never closed at the capped force and the full-force re-sew left a sleeve
# off the shoulder (jumpsuit) or slid the cape off it. Laid loose there,
# 18/72 and 7/64. Waist, hips and crotch stay as they were laid: the legs
# are sewn to them, and the cape hangs open from there.
LOOSE_ARMHOLE_FADE = 0.05


def _armhole_band(ob, m):
    """(local z of the bottom of the piece's armholes, fade) or None."""
    sz = ob.scale.z
    zs = [ob.data.vertices[i].co.z * sz
          for seg in ("arm_L", "arm_R") for i in patterns.segment_verts(ob, seg)]
    if not zs:
        return None
    return min(zs), LOOSE_ARMHOLE_FADE * m["height"]


def _loose_extent(ob, xsign):
    """f(local z) -> (min, max) arc position of the piece around that height."""
    sx, sz = ob.scale.x, ob.scale.z
    pts = sorted((v.co.z * sz, v.co.x * sx * xsign) for v in ob.data.vertices)
    if not pts:
        return None
    zs = [p[0] for p in pts]
    win = 0.02 * max(1.0, getattr(ob.cd, "res_scale", 1.0))

    def f(pz):
        i0 = bisect.bisect_left(zs, pz - win)
        i1 = bisect.bisect_right(zs, pz + win)
        if i1 <= i0:
            j = min(max(bisect.bisect_left(zs, pz), 0), len(zs) - 1)
            i0, i1 = j, j + 1
        xs = [pts[i][1] for i in range(i0, i1)]
        return min(xs), max(xs)
    return f


def _head_transform(ob, m, fwd, side):
    """A hood half laid over its side of the head (anchors HEAD_L / HEAD_R).

    The torso wrap is a vertical cylinder: it can lay a hood beside the
    head or behind it, never over it, and every attempt to sew one from
    there pulled the hood down the back or through the face (Fase 2). Here
    the draft is stood up beside the head in the sagittal plane - its neck
    point on the neck's centre, face edge forward - and every point pushed
    out sideways onto an ellipsoid the size of the measured head (the neck
    below it), then off that surface by the piece's ease. The crown edges
    of the two halves meet over the top of the head, where they are sewn."""
    hd = m.get("head")
    if not hd or "center" not in hd:
        return None
    cd = ob.cd
    left = cd.anchor == 'HEAD_L'
    ssign = 1.0 if left else -1.0          # side points to the avatar's left
    fsign = -1.0 if left else 1.0          # the left half is drafted face at -X
    ox, oz = cd.dome_origin
    z_neck = avatar.z_of(m, "neck")
    # the draft's neck point goes where it is sewn: the neckline, at the top
    # of the shoulders, not the middle of the neck
    z0 = avatar.z_of(m, "shoulder") + 0.04
    cn = avatar.center_at(m, z0)
    cn = Vector((cn.x, cn.y, z0))
    hc = Vector(hd["center"])
    a = max(0.04, hd["depth"] * 0.5)
    b = max(0.04, hd["width"] * 0.5)
    c = max(0.05, hd["len"] * 0.5)
    # a neckline sits wider than the neck itself
    # (the girth at the measured neck height can be the shoulders' - 0.67 m
    # on Hanka - which stood the hood out like a box; neck_girth is the neck)
    rn = avatar.neck_girth(m) / (2.0 * math.pi) * 1.35
    up = Vector((0.0, 0.0, 1.0))
    ease = cd.ease
    shift = Vector(cd.shift)
    bvh = _head_bvh(m, hc, b, z0)

    def head_f(p):
        f_amt = (p.x - ox) * fsign
        u = p.z - oz
        X = cn + fwd * f_amt + up * u
        rel = X - hc
        qf = rel.dot(fwd) / a
        qz = rel.z / c
        lat = b * math.sqrt(max(0.0, 1.0 - qf * qf - qz * qz))
        if X.z < hc.z:
            # the neck under the head: never closer in than the neck itself
            lat = max(lat, rn * math.sqrt(max(0.0, 1.0 - (rel.dot(fwd) / max(a, rn)) ** 2)))
        if bvh is not None:
            # the real outside of the head (and neck) along this line: an
            # anime jaw sticks out past any ellipsoid fitted to the skull, and
            # 17% of Mao's hood started inside her head and stayed caught
            hit = bvh.ray_cast(X + side * (ssign * 0.5), side * (-ssign), 0.5)
            if hit[0] is not None:
                lat = max(lat, (hit[0] - X).dot(side * ssign))
        S = X + side * (ssign * lat)
        # off the surface by the ease, away from the head's centre (at the
        # neck, away from the neck's axis)
        ctr = hc if X.z >= hc.z else Vector((cn.x, cn.y, X.z))
        n = S - ctr
        if n.length < 1e-6:
            n = side * ssign
        return S + n.normalized() * ease + shift
    return head_f


def _head_bvh(m, hc, half_w, z_min):
    """BVH of the avatar's head and neck surface (body plus a separate head
    mesh), for laying a hood over it: triangles above the neckline and within
    reach of the head's centre, so a ray at shoulder height does not land on
    the shoulders. Nothing over the crown of the skull (m["zmax"]): horns
    and animal ears are left to go through the hood, not hold it out."""
    import bpy
    from mathutils.bvhtree import BVHTree
    ctx = bpy.context
    av = ctx.scene.cd.avatar
    if av is None:
        return None
    obs = [av]
    try:
        obs = [avatar.collision_body(ctx, av)]
        # the nape's collider only collides: laying the hood over it as well
        # held the back neckline out, and the back of Hanka's hoodie folded
        # in two vertical creases from the neck to the hem
        obs += [c for c in avatar.collider_meshes(ctx, av) if c.name != avatar.NAPE_PROXY]
    except Exception:
        pass
    dg = ctx.evaluated_depsgraph_get()
    verts, tris = [], []
    reach = max(half_w * 1.6, 0.08)
    z_top = m["zmax"] + 0.01
    for o in obs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        try:
            mw = ev.matrix_world
            me.calc_loop_triangles()
            base = len(verts)
            co = [mw @ v.co for v in me.vertices]
            keep = {}
            for t in me.loop_triangles:
                pts = [co[i] for i in t.vertices]
                if min(q.z for q in pts) < z_min or max(q.z for q in pts) > z_top:
                    continue
                c = (pts[0] + pts[1] + pts[2]) / 3.0
                if math.hypot(c.x - hc.x, c.y - hc.y) > reach:
                    continue
                ids = []
                for i in t.vertices:
                    if i not in keep:
                        keep[i] = len(verts)
                        verts.append(co[i])
                    ids.append(keep[i])
                tris.append(ids)
        finally:
            ev.to_mesh_clear()
    if len(tris) < 20:
        return None
    return BVHTree.FromPolygons(verts, tris)


def _pleat_map(ob):
    """Knife pleats for a piece: f(x, z) -> (x on the outside, inward depth).

    The piece is cut wide - each pleat is a face that shows plus two layers
    the same width folded under it - and placed already folded: the face at
    the piece's radius, the first under-layer running back one layer gap in,
    the second running forward again two gaps in. Pleats are spaced across
    the piece's width at each height (the width read off the piece's own
    outline, top and bottom), so a flared panel fans its pleats out to the
    hem. The cloth's rest shape is this folded state, which is what keeps
    the pleats pressed through the simulation."""
    cd = ob.cd
    n, a, gap = cd.pleats, cd.pleat_face, cd.pleat_gap
    xs = [v.co.x for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    if not xs:
        return None
    z_top, z_bot = max(zs), min(zs)
    band = max(1e-4, (z_top - z_bot) * 0.03)
    top = [x for x, z in zip(xs, zs) if z > z_top - band]
    bot = [x for x, z in zip(xs, zs) if z < z_bot + band]
    w_top = (max(top) - min(top)) if top else (max(xs) - min(xs))
    w_bot = (max(bot) - min(bot)) if bot else w_top
    L = max(1e-4, z_top - z_bot)
    under = (1.0 - a) * 0.5

    def where(x, z):
        t = min(1.0, max(0.0, (z_top - z) / L))
        W = w_top + (w_bot - w_top) * t
        # shifted half a face, so both edges of the piece fall in the middle
        # of a face: unshifted, one edge ended on the innermost layer and the
        # side seam there joined two hidden layers, leaving a slit between
        # the faces (the tiered skirt's side)
        u = (x / max(1e-6, W) + 0.5) * n + a * 0.5
        k = min(max(math.floor(u), 0), n)
        return k, u - k, W

    def f(x, z):
        k, r, W = where(x, z)                      # r: 0..1 within this pleat
        if r < a:                                  # the face
            vis, depth = r, 0.0
        elif r < a + under:                        # folding back under the face
            vis, depth = a - (r - a), gap
        else:                                      # and forward again
            vis, depth = a - under + (r - a - under), gap * 2.0
        vis_W = W * a                              # the outside width at this height
        x_out = ((k + vis / a - 0.5) / n - 0.5) * vis_W
        return x_out, depth
    f.pleat = lambda x, z: where(x, z)[0]          # which pleat a point is in
    return f


def fold_params(ob, idx):
    """Where the points of an edge of a pleated piece land along it once the
    piece is folded: (positions in metres from the first point, length).

    Only for an edge that runs across the pleats (a ruffle's gathered top):
    its faces show and the layers folded under them lie behind, so the edge
    is as long as its faces laid end to end, and a hidden point sits under
    the face point with the same outside x. None for an edge that stays on
    one layer - a face (sewn to its stretch of a yoke), a hidden layer (sewn
    to the next) or a side edge - which is sewn as it is cut."""
    pleat = _pleat_map(ob)
    if pleat is None or len(idx) < 2:
        return None
    sx, sz = abs(ob.scale.x), abs(ob.scale.z)
    vs = ob.data.vertices
    fold = [pleat(vs[i].co.x, vs[i].co.z) for i in idx]
    face = [j for j, (_, d) in enumerate(fold) if d == 0.0]
    # across the pleats: faces of more than one pleat. A face's own edge can
    # end a point into the fold beside it (the pleated skirt's narrow faces
    # on the man), and is still sewn flat
    if len({pleat.pleat(vs[idx[j]].co.x, vs[idx[j]].co.z) for j in face}) < 2:
        return None
    pts = [(fold[j][0] * sx, vs[idx[j]].co.z * sz) for j in face]
    acc = [0.0]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.hypot(x1 - x0, z1 - z0))
    xf = [p[0] for p in pts]
    up = xf[-1] >= xf[0]
    s = []
    for x, _ in fold:
        x *= sx
        # the face points' outside x runs one way along the edge: find the
        # pair this point lies between
        if (x <= xf[0]) == up:
            s.append(0.0)
            continue
        if (x >= xf[-1]) == up:
            s.append(acc[-1])
            continue
        for j in range(1, len(xf)):
            if (x <= xf[j]) == up:
                d = xf[j] - xf[j - 1]
                f = (x - xf[j - 1]) / d if abs(d) > 1e-9 else 0.0
                s.append(acc[j - 1] + (acc[j] - acc[j - 1]) * min(1.0, max(0.0, f)))
                break
        else:
            s.append(acc[-1])
    return s, acc[-1]


# ---------------------------------------------------------------- assembly

def garment_pieces(context, garment=None):
    g = garment or context.scene.cd.garment_name
    return [ob for ob in context.scene.objects
            if ob.cd.is_pattern and ob.cd.garment == g]


def has_hood(context, garment=None):
    """Whether a garment has hood pieces (laid on the head: HEAD_L, HEAD_R)."""
    return any(p.cd.anchor.startswith('HEAD') for p in garment_pieces(context, garment))


def garment_object(context, garment=None, create=True):
    g = garment or context.scene.cd.garment_name
    name = GARMENT_PREFIX + g
    ob = bpy.data.objects.get(name)
    if ob is None and create:
        me = bpy.data.meshes.new(name)
        ob = bpy.data.objects.new(name, me)
        ob.cd.is_garment = True
        ob.cd.garment = g
        me.materials.append(patterns.fabric_material())
        patterns.move_to_collection(ob, patterns.get_collection(context, patterns.GARMENT_COLL))
    return ob


def _chain_bmverts(ob, seg, vmap, closed=False):
    idx = patterns.segment_verts(ob, seg, closed)
    return [vmap[i] for i in idx if i in vmap]


def _gather_pairs(seam, A, Bc, rev):
    """Stitch pairs for a seam with a gathered edge on one side, or None.

    A pleated edge running across its pleats (a ruffle's top) is sewn by
    where its points land once folded (fold_params), so each point is
    stitched to the point of the other edge right outside it: the layers
    folded under a face are tacked down with it, as gathers are sewn. Paired
    by their place in the flat cut instead, the folded points were pulled
    sideways out of their folds by up to a pleat's depth while sewing."""
    sides = []
    for ob, chain in ((seam.obj_a, A), (seam.obj_b, Bc)):
        fp = None
        if ob.cd.pleats > 0:
            idx = patterns.segment_verts(ob, seam.seg_a if ob is seam.obj_a and chain is A
                                         else seam.seg_b, seam.closed)
            if len(idx) == len(chain):
                fp = fold_params(ob, idx)
        sides.append(fp)
    if sides[0] is None and sides[1] is None:
        return None

    def params(fp, chain, reverse):
        n = len(chain)
        if fp is None:
            t = [i / max(1, n - 1) for i in range(n)]
        else:
            s, total = fp
            t = [x / max(1e-9, total) for x in s]
            if reverse:
                t = [1.0 - x for x in reversed(t)]
        return t

    tA = params(sides[0], A, False)
    tB = params(sides[1], Bc, rev)

    def nearest(ts, x):
        i = bisect.bisect_left(ts, x)
        if i <= 0:
            return 0
        if i >= len(ts):
            return len(ts) - 1
        return i if ts[i] - x < x - ts[i - 1] else i - 1

    pairs = []
    # the plain side's params rise along it; the gathered side's need not
    # (a hidden layer runs back), so look points up on the plain side, or on
    # a sorted copy when both are gathered
    oA = sorted(range(len(tA)), key=lambda i: tA[i])
    sA = [tA[i] for i in oA]
    oB = sorted(range(len(tB)), key=lambda i: tB[i])
    sB = [tB[i] for i in oB]
    for i, a in enumerate(A):
        pairs.append((a, Bc[oB[nearest(sB, tA[i])]]))
    for j, b in enumerate(Bc):
        pairs.append((A[oA[nearest(sA, tB[j])]], b))
    return pairs


def under_bvh(context, garment):
    """BVH of the body plus every garment worn under this one, at their
    current shapes.

    An outer garment arranged against the bare body starts only its own ease
    away from the skin, while the shirt beneath it occupies a shell several
    times thicker than that - so the jacket is laid out inside the shirt and
    the simulation has no way to sort that out afterwards. Arranging against
    what is actually underneath is what makes layering hold.
    """
    from mathutils.bvhtree import BVHTree
    scn = context.scene
    av = scn.cd.avatar
    # the nape's collider (avatar._nape_proxy) only for a garment with a
    # hood (has_hood): arranged against it as well, a coat's back neck, laid
    # 2.4 cm under it on Hanka, was moved by up to 12 mm to clear it by the
    # coat's ease; from there
    # its back sleeve caps stalled with 10 stitches open (up to 20 cm), it
    # was re-sewn at full force and came out off the shoulders with the
    # neckline wide open (fase 9, since a1ce3d1)
    nape = has_hood(context, garment)
    ob_g = bpy.data.objects.get(GARMENT_PREFIX + garment)
    layer = ob_g.cd.layer if ob_g is not None else 0
    unders = [o for o in scn.objects
              if o.cd.is_garment and o.data and len(o.data.vertices)
              and o.cd.garment != garment and o.cd.layer < layer]
    if not unders:
        return avatar.body_bvh(context, nape=nape)
    from . import sim as _sim
    verts, tris = [], []
    for src in [av] + unders:
        if src is None or src.type != 'MESH':
            continue
        # Measure the under-layer by its simulation cage, not its display
        # shape. A finalized garment carries subdivision and solidify, and
        # arranging the next layer against that inflated shell laid a
        # t-shirt 20 cm low - the same garment sewn over an unfinalized one
        # sat correctly. What is underneath should not depend on whether it
        # happens to have been finalized yet.
        with _sim.sim_cage_only(src):
            context.view_layer.update()
            dg = context.evaluated_depsgraph_get()
            ev = src.evaluated_get(dg)
            try:
                me = ev.to_mesh()
                me.calc_loop_triangles()
            except Exception:
                continue
            mw = ev.matrix_world
            base = len(verts)
            verts += [mw @ v.co for v in me.vertices]
            tris += [tuple(base + i for i in t.vertices) for t in me.loop_triangles]
            ev.to_mesh_clear()
    if not tris:
        return avatar.body_bvh(context, nape=nape)
    return BVHTree.FromPolygons(verts, tris)


UV_PACKED = "UVMap"     # every piece laid flat once in 0..1, for painting a texture
UV_FABRIC = "Fabric"    # the pattern in metres (1 unit = 1 m), for a tiling fabric
UV_MARGIN = 0.02        # metres of pattern kept between pieces in UVMap


def uv_layout(pieces):
    """Where each pattern piece goes in the packed UV map: name -> (u, v, k),
    the UV of the piece's centre and UV units per metre of pattern.

    The pieces are already flat patterns, so their outlines are the UV
    islands as they are, without stretch. All pieces share one scale - a
    texture has the same density on a sleeve as on the back - and are
    shelf-packed tallest first into a square."""
    rects = []
    for ob in pieces:
        xs = [v.co.x * ob.scale.x for v in ob.data.vertices] or [0.0]
        zs = [v.co.z * ob.scale.z for v in ob.data.vertices] or [0.0]
        rects.append((ob.name, max(xs) - min(xs), max(zs) - min(zs),
                      (min(xs) + max(xs)) * 0.5, (min(zs) + max(zs)) * 0.5))
    if not rects:
        return {}
    area = sum((w + UV_MARGIN) * (h + UV_MARGIN) for _, w, h, _, _ in rects)
    widest = max(w for _, w, _, _, _ in rects) + UV_MARGIN
    side = max(widest, math.sqrt(area) * 1.15)
    place, x, y, row_h = {}, UV_MARGIN, UV_MARGIN, 0.0
    for name, w, h, cx, cz in sorted(rects, key=lambda r: -r[2]):
        if x + w + UV_MARGIN > side and x > UV_MARGIN:
            x, y, row_h = UV_MARGIN, y + row_h + UV_MARGIN, 0.0
        place[name] = (x + w * 0.5 - cx, y + h * 0.5 - cz)
        x += w + UV_MARGIN
        row_h = max(row_h, h)
    size = max(side, y + row_h + UV_MARGIN)
    k = 1.0 / size
    return {n: (px * k, pz * k, k) for n, (px, pz) in place.items()}


def is_locked(ob):
    """Sewn (frozen by Sew) or finished (bound to the rig by Finalize)."""
    return bool(ob.cd.sewn or any(m.type == 'ARMATURE' for m in ob.modifiers))


def sync_garment(context, report=None, garment=None):
    """Rebuild the 3D garment from its pattern pieces."""
    scn = context.scene
    g = garment or scn.cd.garment_name
    pieces = garment_pieces(context, g)
    if not pieces:
        if report:
            report({'WARNING'}, "No pattern pieces in garment '%s'" % g)
        return None

    m = avatar.measure(context)
    fwd, side = avatar.basis(scn.cd.facing)
    bvh = under_bvh(context, g) if scn.cd.keep_off_body else None

    bm = bmesh.new()
    dl = bm.verts.layers.deform.verify()
    uv_pack = bm.loops.layers.uv.new(UV_PACKED)
    uv_fab = bm.loops.layers.uv.new(UV_FABRIC)
    layout = uv_layout(pieces)
    vmaps = {}
    group_names = []
    for ob in pieces:
        gi = len(group_names)
        group_names.append(ob.name)
        f = piece_transform(ob, m, fwd, side)
        vmap = {}
        clear = max(ob.cd.ease, 0.002)
        for v in ob.data.vertices:
            p = f(v.co.copy())
            if bvh is not None:
                p = avatar.push_out(p, bvh, clear)
            nv = bm.verts.new(p)
            nv[dl][gi] = 1.0
            vmap[v.index] = nv
        bm.verts.ensure_lookup_table()
        ox, oz, k = layout[ob.name]
        sx, sz = ob.scale.x, ob.scale.z
        for poly in ob.data.polygons:
            try:
                face = bm.faces.new([vmap[i] for i in poly.vertices])
            except ValueError:
                continue
            for loop, i in zip(face.loops, poly.vertices):
                co = ob.data.vertices[i].co
                x, z = co.x * sx, co.z * sz
                loop[uv_fab].uv = (x, z)
                loop[uv_pack].uv = (ox + x * k, oz + z * k)
        vmaps[ob.name] = vmap

    # --- sewing springs: loose edges between paired segment chains
    n_sew = 0
    for seam in scn.cd.seams:
        if not seam.enabled or not seam.obj_a or not seam.obj_b:
            continue
        if seam.obj_a.name not in vmaps or seam.obj_b.name not in vmaps:
            continue
        A = _chain_bmverts(seam.obj_a, seam.seg_a, vmaps[seam.obj_a.name], seam.closed)
        B = _chain_bmverts(seam.obj_b, seam.seg_b, vmaps[seam.obj_b.name], seam.closed)
        if len(A) < 2 or len(B) < 2:
            continue
        rev = seam.flip
        if seam.auto_flip:
            def _cost(bb):
                n, tot = 9, 0.0
                for k in range(n):
                    u = k / (n - 1)
                    pa = A[min(len(A) - 1, int(round(u * (len(A) - 1))))]
                    pb = bb[min(len(bb) - 1, int(round(u * (len(bb) - 1))))]
                    tot += (pa.co - pb.co).length
                return tot
            rev = _cost(list(reversed(B))) < _cost(B)
        Bc = list(reversed(B)) if rev else B
        N = max(len(A), len(Bc))
        made = set()
        pairs = _gather_pairs(seam, A, Bc, rev)
        if pairs is None:
            pairs = []
            for i in range(N):
                t = i / (N - 1)
                pairs.append((A[min(len(A) - 1, int(round(t * (len(A) - 1))))],
                              Bc[min(len(Bc) - 1, int(round(t * (len(Bc) - 1))))]))
        for a, b in pairs:
            if a is b:
                continue
            key = (a, b) if id(a) < id(b) else (b, a)
            if key in made:
                continue
            made.add(key)
            try:
                bm.edges.new((a, b))
                n_sew += 1
            except ValueError:
                pass

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    ob = garment_object(context, g)
    if ob.name not in scn.objects:
        patterns.move_to_collection(ob, patterns.get_collection(context, patterns.GARMENT_COLL))
    ob.matrix_world.identity()

    # keep modifiers, replace geometry
    for mod in ob.modifiers:
        if mod.type == 'CLOTH':
            try:
                mod.point_cache.frame_end = mod.point_cache.frame_start
            except Exception:
                pass
    for vg in list(ob.vertex_groups):
        ob.vertex_groups.remove(vg)
    for name in group_names:
        ob.vertex_groups.new(name=name)

    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    if not ob.data.materials:
        ob.data.materials.append(patterns.fabric_material())
    for p in ob.data.polygons:
        p.use_smooth = True

    ob.cd.is_garment = True
    ob.cd.garment = g
    ob.cd.res_scale = max((p.cd.res_scale for p in pieces), default=1.0)
    ob.cd.sewn = False          # flat pieces again: open to live updates
    ob.cd.draft = False
    ob["cd_sewing_edges"] = n_sew
    try:
        from . import sim as _sim
        _sim.add_subdivision(ob, scn.cd.subdiv_levels, scn.cd.subdiv_render)
    except Exception as e:
        print("[clothing_design] subdivision failed:", e)
    if report:
        report({'INFO'}, "%s: %d verts, %d faces, %d sewing springs"
               % (ob.name, len(ob.data.vertices), len(ob.data.polygons), n_sew))
    return ob


def loose_edges(me):
    used = set()
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            used.add((min(vs[i], vs[i - 1]), max(vs[i], vs[i - 1])))
    return [e.index for e in me.edges
            if (min(e.vertices), max(e.vertices)) not in used]
