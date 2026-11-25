# Left/right symmetry of the presets' seams: every stitch of a freshly laid
# out garment should have a mirror twin on the other side of the body. A seam
# whose chains drop a different corner on each side (segments hold their
# start corner only; see CDSeam.closed) shows up here as stitches without a
# twin, and once sewn as a strap or a sleeve pulled off to one side (The
# Beast's tank, dress and coat, fase 9). Still failing on purpose for the
# presets not yet closed (tshirt, skirts, trousers, jumpsuit, jacket, hoodie,
# cape): same defect, left for a separate change.
#
#   blender -b --python tests/test_seam_symmetry.py [-- --figure WOMAN | --fbx PATH --drop Outfit]
#                                                    [--only TANK,DRESS] [--sew]
#
# --sew also sews each garment and prints, per side, how far the cloth stands
# off the body (a fin or bunching down one side seam) - information only.
import bpy, sys, os, collections
from mathutils import Vector, kdtree

bpy.ops.preferences.addon_enable(module="clothing_design")
from clothing_design import avatar, library, build, patterns

TOL = 0.012      # a twin within this of the mirrored stitch
CENTRE = 0.02    # stitches this close to the centre line mirror onto themselves

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
FIG = arg("--fbx") or arg("--figure", "WOMAN")
DROP = {n.strip().lower() for n in (arg("--drop") or "").split(",") if n.strip()}
ONLY = set(arg("--only").upper().split(",")) if arg("--only") else None
SEW = "--sew" in argv

fails = []


def load():
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="clothing_design")
    if FIG in ("WOMAN", "MAN"):
        bpy.ops.cd.import_character(figure=FIG)
        return
    bpy.ops.import_scene.fbx(filepath=FIG)
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.name.lower() in DROP:
            bpy.data.objects.remove(o)
    bpy.context.view_layer.objects.active = None
    bpy.ops.cd.set_avatar()


def stitches(g):
    me = g.data
    used = set()
    for p in me.polygons:
        used.update(p.edge_keys)
    mw = g.matrix_world
    return [((mw @ me.vertices[a].co), (mw @ me.vertices[b].co))
            for a, b in (e.vertices[:] for e in me.edges if e.key not in used)]


def unmatched(st):
    mids = [(a + b) * 0.5 for a, b in st]
    kd = kdtree.KDTree(len(mids))
    for i, c in enumerate(mids):
        kd.insert(c, i)
    kd.balance()
    out = []
    for c in mids:
        if abs(c.x) < CENTRE:
            continue
        _, _, d = kd.find(Vector((-c.x, c.y, c.z)))
        if d > TOL:
            out.append((c, d))
    return out


def seam_ends(ctx):
    """name -> (first stitch end, last stitch end, stitch spacing) of every
    seam, laid out on the body as build.sync_garment pairs them."""
    scn = ctx.scene
    m = avatar.measure(ctx)
    fwd, side = avatar.basis(scn.cd.facing)
    out = {}
    for seam in scn.cd.seams:
        if not seam.enabled or not seam.obj_a or not seam.obj_b:
            continue
        def chain(ob, seg):
            f = build.piece_transform(ob, m, fwd, side)
            return [f(ob.data.vertices[i].co.copy())
                    for i in patterns.segment_verts(ob, seg, seam.closed)]
        A, B = chain(seam.obj_a, seam.seg_a), chain(seam.obj_b, seam.seg_b)
        if len(A) < 2 or len(B) < 2:
            continue
        step = sum((A[i + 1] - A[i]).length for i in range(len(A) - 1)) / (len(A) - 1)
        out[seam.name] = (A[0], A[-1], step)
    return out


def mirror_name(n):
    t = n.replace("_L", "\0").replace("_R", "_L").replace("\0", "_R")
    return t


def corner_mismatch(ends):
    """Seams whose two ends do not land on the mirror of their twin's ends:
    one side dropped a corner the other kept."""
    bad = []
    for n, (a, b, step) in ends.items():
        tw = ends.get(mirror_name(n))
        if tw is None or mirror_name(n) == n:
            continue
        ma, mb = (Vector((-tw[0].x, tw[0].y, tw[0].z)), Vector((-tw[1].x, tw[1].y, tw[1].z)))
        d = max(min((a - ma).length, (a - mb).length), min((b - ma).length, (b - mb).length))
        if d > 0.75 * step:
            bad.append((n, d, step))
    return bad


def standoff(ctx, g):
    """Per side: cloth verts more than 5 cm off the body, and the 95th
    percentile of the distance, over the torso."""
    bvh = avatar.body_bvh(ctx)
    m = avatar.measure(ctx)
    zt, zb = avatar.z_of(m, "shoulder"), avatar.z_of(m, "hip")
    ev = g.evaluated_get(ctx.evaluated_depsgraph_get())
    mw = ev.matrix_world
    side = collections.defaultdict(list)
    for v in ev.data.vertices:
        p = mw @ v.co
        if not (zb <= p.z <= zt) or abs(p.x) < 0.02:
            continue
        loc = bvh.find_nearest(p)[0]
        if loc is not None:
            side["L" if p.x > 0 else "R"].append((p - loc).length)
    res = {}
    for k, ds in side.items():
        ds.sort()
        res[k] = (sum(1 for d in ds if d > 0.05), ds[int(len(ds) * 0.95)] if ds else 0.0, len(ds))
    return res


load()
fig = os.path.basename(FIG)
for key in library.PRESETS:
    if ONLY and key not in ONLY:
        continue
    load()
    ctx = bpy.context
    try:
        bpy.ops.cd.add_garment(preset=key, fit=0.10)
    except Exception as e:
        print("  FAIL %s %s raised %s" % (fig, key, e)); fails.append(key); continue
    g = build.garment_object(ctx, create=False)
    st = stitches(g)
    bad = unmatched(st)
    cm = corner_mismatch(seam_ends(ctx))
    ok = not cm
    print(("  ok   " if ok else "  FAIL ") + "%s %-10s seam ends off their mirror: %d%s"
          % (fig, key.lower(), len(cm),
             "".join("  [%s %.0f mm, stitch %.0f mm]" % (n, d * 1000, sp * 1000) for n, d, sp in cm)))
    print("  info %s %-10s %d stitches, %d more than %.0f mm from a mirror twin"
          % (fig, key.lower(), len(st), len(bad), TOL * 1000))
    if not ok:
        fails.append(key)
    if SEW:
        bpy.ops.cd.sew()
        g = build.garment_object(ctx, create=False)
        so = standoff(ctx, g)
        print("  info %s %-10s off the body >5cm  L %d  R %d   p95  L %.0f mm  R %.0f mm"
              % (fig, key.lower(), so.get("L", (0,))[0], so.get("R", (0,))[0],
                 so.get("L", (0, 0))[1] * 1000, so.get("R", (0, 0))[1] * 1000))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
