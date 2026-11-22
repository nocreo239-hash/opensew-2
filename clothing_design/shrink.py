# Clothing Design - hide the avatar's body under a garment.
#
# Skin poking through clothes is the first thing a buyer notices. Two ways out,
# both driven by the same test - which body vertices does the garment cover:
#
#   * a shape key on the body, Shrink_<garment>, that pulls covered skin in
#     behind the cloth (for your own avatar, or to preview);
#   * a mask in the body's UV space, black where the body is hidden for good,
#     for Modular Avatar's Mesh Cutter to delete those polygons in Unity. The
#     mask is all that ships with the outfit: the avatar's body is someone
#     else's work and is never exported.
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

REACH = 0.15          # how far outside the skin the cloth may be and still cover it: a
                      # sweater hangs 8-10 cm off the small of the back (Hanka)
INSIDE = 0.04         # how far inside the skin cloth may sit (it pokes through) and still count
CLEARANCE = 0.004     # the shape key leaves this much between skin and cloth
MAX_PULL = 0.03       # and never pulls skin in further than this
EDGE_MARGIN = 0.035   # the mask keeps skin this close (along the cloth) to a hem or opening
FACING = 0.2          # cloth must face roughly the same way as the skin it covers


def _evaluated_world(context, ob):
    """World-space vertices, vertex normals and triangles of ob as shown."""
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        mw = ev.matrix_world
        nm = mw.to_3x3().inverted_safe().transposed()
        me.calc_loop_triangles()
        co = [mw @ v.co for v in me.vertices]
        no = [(nm @ v.normal).normalized() for v in me.vertices]
        tris = [tuple(t.vertices) for t in me.loop_triangles]
        edges_count = {}
        for p in me.polygons:
            for k in p.edge_keys:
                edges_count[k] = edges_count.get(k, 0) + 1
        boundary = [k for k, n in edges_count.items() if n == 1]
    finally:
        ev.to_mesh_clear()
    return co, no, tris, boundary


class Cover:
    """Where the garments cover the body.

    For every body vertex: gap (signed distance from the skin out to the
    cloth along the skin's normal; negative where the skin pokes through),
    or None where no cloth covers it; and edge, how far the covering cloth is
    from the nearest hem or opening."""

    def __init__(self, context, body, garments):
        self.body = body
        bco, bno, _, _ = _evaluated_world(context, body)
        self.n = len(bco)
        self.normals = bno
        verts, tris, edge_pts = [], [], []
        for g in garments:
            # without its thickness: the solidify closes every hem and opening
            # with a rim, and the cloth would have no edge left to keep away from
            sol = [(m, m.show_viewport) for m in g.modifiers if m.type == 'SOLIDIFY']
            for m, _ in sol:
                m.show_viewport = False
            try:
                gco, _, gtris, gboundary = _evaluated_world(context, g)
            finally:
                for m, vis in sol:
                    m.show_viewport = vis
            base = len(verts)
            verts += gco
            tris += [(a + base, b + base, c + base) for a, b, c in gtris]
            for a, b in gboundary:
                pa, pb = gco[a], gco[b]
                steps = max(1, int((pa - pb).length / 0.005))
                edge_pts += [pa.lerp(pb, i / steps) for i in range(steps + 1)]
        self.gap = [None] * self.n
        self.edge = [0.0] * self.n
        if not tris:
            return
        bvh = BVHTree.FromPolygons(verts, tris)
        kd = None
        if edge_pts:
            kd = KDTree(len(edge_pts))
            for i, p in enumerate(edge_pts):
                kd.insert(p, i)
            kd.balance()
        for i in range(self.n):
            p, nrm = bco[i], bno[i]
            if nrm.length < 0.5:
                continue
            start = p - nrm * INSIDE
            hit, hn, _, dist = bvh.ray_cast(start, nrm, INSIDE + REACH)
            if hit is None:
                continue
            # a sleeve seen sideways from the ribs, or the inside of a skirt
            # seen from the thigh, is not cloth over this skin: the cloth has
            # to face the same way (either side of a single layer)
            if abs(hn.dot(nrm)) < FACING:
                continue
            self.gap[i] = dist - INSIDE
            self.edge[i] = kd.find(hit)[2] if kd is not None else 1.0

        self.edge_points = len(edge_pts)

    def covered(self):
        return [g is not None for g in self.gap]

    def hidden(self, margin=EDGE_MARGIN):
        """Body vertices hidden for good: covered, and far enough from every
        hem and opening that no pose shows them."""
        return [g is not None and e >= margin for g, e in zip(self.gap, self.edge)]


def shrink_key(body, cover, name, clearance=CLEARANCE, max_pull=MAX_PULL, smooth=2):
    """Add (or replace) the shape key `name` on body: covered skin pulled in
    along its rest normal until it is `clearance` behind the cloth."""
    me = body.data
    if me.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    key = me.shape_keys.key_blocks.get(name)
    if key is None:
        key = body.shape_key_add(name=name, from_mix=False)
    basis = me.shape_keys.reference_key
    pull = [0.0] * len(me.vertices)
    if cover.n != len(me.vertices):
        return key, 0
    for i, g in enumerate(cover.gap):
        if g is not None and g < clearance:
            pull[i] = min(max_pull, clearance - g)
    # soften the step where the pull starts, only among covered vertices:
    # the skin outside the cloth is never moved
    nbr = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        nbr[a].append(b)
        nbr[b].append(a)
    cov = cover.covered()
    for _ in range(smooth):
        nxt = list(pull)
        for i in range(len(pull)):
            if not cov[i] or pull[i] == 0.0:
                continue
            ns = [pull[j] for j in nbr[i] if cov[j]]
            if ns:
                nxt[i] = max(pull[i], (pull[i] + sum(ns)) / (1 + len(ns)))
        pull = nxt
    # the pull goes along the rest-pose normal, in the body's own space
    n_local = [v.normal for v in me.vertices]
    moved = 0
    for i, kv in enumerate(key.data):
        base = basis.data[i].co
        if pull[i] > 0.0:
            kv.co = base - n_local[i].normalized() * pull[i]
            moved += 1
        else:
            kv.co = base.copy()
    key.value = 1.0
    return key, moved


def mask_images(body, hidden, size=1024, uv_name=None):
    """One mask per material slot that has hidden polygons, in the body's UV
    map: black where a polygon is hidden (all its corners hidden), white
    everywhere else. Returns {material index: list of size*size floats, 1 = keep}."""
    me = body.data
    uvl = me.uv_layers.get(uv_name) if uv_name else me.uv_layers.active
    if uvl is None and me.uv_layers:
        uvl = me.uv_layers[0]
    if uvl is None:
        return {}
    out = {}
    for p in me.polygons:
        if not all(hidden[v] for v in p.vertices):
            continue
        img = out.get(p.material_index)
        if img is None:
            img = out[p.material_index] = bytearray(b"\xff") * (size * size)
        pts = [(uvl.data[li].uv.x * size, uvl.data[li].uv.y * size) for li in p.loop_indices]
        for k in range(1, len(pts) - 1):
            _fill_tri(img, size, pts[0], pts[k], pts[k + 1])
        # the corners themselves, for Mesh Cutter's per-vertex lookup
        for x, y in pts:
            _dot(img, size, x, y, 2)
    return out


def _fill_tri(img, size, a, b, c):
    xs = (a[0], b[0], c[0]); ys = (a[1], b[1], c[1])
    x0, x1 = max(0, int(math.floor(min(xs)))), min(size - 1, int(math.ceil(max(xs))))
    y0, y1 = max(0, int(math.floor(min(ys)))), min(size - 1, int(math.ceil(max(ys))))
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(den) < 1e-12:
        return
    for y in range(y0, y1 + 1):
        py = y + 0.5
        row = y * size
        for x in range(x0, x1 + 1):
            px = x + 0.5
            w0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / den
            w1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / den
            if w0 >= -0.02 and w1 >= -0.02 and 1.0 - w0 - w1 >= -0.02:
                img[row + x] = 0


def _dot(img, size, x, y, r):
    for yy in range(int(y) - r, int(y) + r + 1):
        for xx in range(int(x) - r, int(x) + r + 1):
            if 0 <= xx < size and 0 <= yy < size:
                img[yy * size + xx] = 0


def save_mask(pixels, size, path):
    """Write a grey mask (bytes, 255 keep / 0 delete, rows bottom-up like
    Blender's UVs) as a PNG through Blender's own image writer."""
    img = bpy.data.images.new("CD_Mask_tmp", size, size, alpha=False, float_buffer=False)
    try:
        flat = [0.0] * (size * size * 4)
        for i, v in enumerate(pixels):
            f = v / 255.0
            j = i * 4
            flat[j] = flat[j + 1] = flat[j + 2] = f
            flat[j + 3] = 1.0
        img.pixels.foreach_set(flat)
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
    finally:
        bpy.data.images.remove(img)
