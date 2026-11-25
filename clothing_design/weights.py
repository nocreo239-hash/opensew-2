# Clothing Design - robust skin weight transfer (body -> garment).
#
# The method is "Robust Skin Weights Transfer via Weight Inpainting"
# (Abdrashitov, Raichstat, Monsen, Hill - SIGGRAPH Asia 2023 Technical
# Communications), as used by the Robust Weight Transfer add-on for Blender by
# sentfromspacevr (GPL-2.0-or-later, https://github.com/sentfromspacevr/
# robust-weight-transfer), itself based on the paper's sample code by Rinat
# Abdrashitov (MIT). This is a re-implementation that needs nothing Blender
# does not ship: numpy for the algebra, mathutils.bvhtree for the closest
# points and a small conjugate-gradient solver instead of scipy/libigl.
#
#   1. match: every garment vertex takes the weights at the closest point of
#      the body surface, if that point is close enough and its normal agrees
#      (either way round: a garment's normals may face in or out);
#   2. inpaint: the vertices with no good match - armpits, crotch, cloth that
#      hangs away from the body - get weights that minimise the bi-Laplacian
#      energy with the matched ones held fixed, so they blend smoothly instead
#      of copying whichever bone happens to be nearest.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DIST = 0.05          # metres: farther than this from the body is "unmatched"
ANGLE = 35.0         # degrees between garment and body normals


def _tri_mesh(me, mw):
    me.calc_loop_triangles()
    V = np.array([mw @ v.co for v in me.vertices], dtype=np.float64).reshape(-1, 3)
    F = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64).reshape(-1, 3)
    return V, F


def _vertex_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], n)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(ln, 1e-12)


def _weights_matrix(ob, me, names):
    """#verts x len(names) array of ob's weights for the groups in names."""
    col = {n: i for i, n in enumerate(names)}
    gname = {g.index: g.name for g in ob.vertex_groups}
    W = np.zeros((len(me.vertices), len(names)))
    for v in me.vertices:
        for g in v.groups:
            j = col.get(gname.get(g.group))
            if j is not None:
                W[v.index, j] = g.weight
    return W


def _cotan_laplacian(V, F):
    """Cotangent Laplacian as COO triplets (negative semi-definite: L x sums
    w_ij (x_j - x_i)) and the lumped (barycentric) mass per vertex."""
    rows, cols, vals = [], [], []
    area = np.zeros(len(V))
    for a, b, c in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        i, j, k = F[:, a], F[:, b], F[:, c]
        u, w = V[i] - V[k], V[j] - V[k]
        cross = np.linalg.norm(np.cross(u, w), axis=1)
        cot = np.einsum('ij,ij->i', u, w) / np.maximum(cross, 1e-12)
        cot = np.clip(cot, -1e3, 1e3) * 0.5        # the angle at k, opposite edge ij
        rows += [i, j, i, j]; cols += [j, i, i, j]; vals += [cot, cot, -cot, -cot]
    tri = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) * 0.5
    for k in range(3):
        np.add.at(area, F[:, k], tri / 3.0)
    return (np.concatenate(rows), np.concatenate(cols), np.concatenate(vals),
            np.maximum(area, 1e-12))


def _sparse(r, c, v, n):
    """(matvec, diagonal) of the sparse matrix given as COO triplets:
    duplicates summed once, rows sorted, one gather and one segmented sum per
    product."""
    key = r * n + c
    uk, inv = np.unique(key, return_inverse=True)
    vals = np.bincount(inv, weights=v)
    rows, cols = uk // n, uk % n
    starts = np.searchsorted(rows, np.arange(n))
    nonempty = np.bincount(rows, minlength=n) > 0
    diag = np.zeros(n)
    on = rows == cols
    diag[rows[on]] = vals[on]

    def mv(X):
        prod = vals[:, None] * X[cols]
        out = np.zeros((n, X.shape[1]))
        out[nonempty] = np.add.reduceat(prod, starts[nonempty], axis=0)
        return out
    return mv, diag, (rows, cols, vals)


def inpaint(V, F, W, matched, order=2, iters=2000, tol=1e-6):
    """Weights for the unmatched vertices: minimise x^T Q x with the matched
    rows of W fixed, Q = -L (order 1, harmonic) or -L + L M^-1 L (order 2,
    the paper's). Jacobi-preconditioned conjugate gradient on the free rows,
    all bones at once."""
    n = len(V)
    r, c, v, mass = _cotan_laplacian(V, F)
    L, Ld, (lr, lc, lv) = _sparse(r, c, v, n)
    if order == 1:
        def Q(X):
            return -L(X)
        qdiag = -Ld
    else:
        def Q(X):
            LX = L(X)
            return -LX + L(LX / mass[:, None])
        # diag(L M^-1 L)_i = sum_j L_ij^2 / m_j
        qdiag = -Ld + np.bincount(lr, weights=lv * lv / mass[lc], minlength=n)

    free = ~matched
    if not free.any():
        return W.copy()
    fixed = W * matched[:, None]
    b = -Q(fixed)[free]
    pre = 1.0 / np.maximum(qdiag[free], 1e-30)[:, None]

    def A(Xf):
        full = np.zeros_like(W)
        full[free] = Xf
        return Q(full)[free]

    x = W[free].copy()
    res = b - A(x)
    z = res * pre
    p = z.copy()
    rz = np.einsum('ij,ij->j', res, z)
    b2 = np.maximum(np.einsum('ij,ij->j', b, b), 1e-30)
    for _ in range(iters):
        Ap = A(p)
        alpha = rz / np.maximum(np.einsum('ij,ij->j', p, Ap), 1e-30)
        x += p * alpha
        res -= Ap * alpha
        if np.all(np.einsum('ij,ij->j', res, res) / b2 < tol * tol):
            break
        z = res * pre
        rz_new = np.einsum('ij,ij->j', res, z)
        p = z + p * (rz_new / np.maximum(rz, 1e-30))
        rz = rz_new
    out = W.copy()
    out[free] = x
    return out


def transfer(body_ob, body_me, garment_ob, garment_me, bones, dist=DIST, angle=ANGLE,
             extra=()):
    """Robust weights from the body to the garment, both as evaluated meshes
    in the same pose. Returns (#garment verts x len(bones) weights, matched
    mask). Only the bones in `bones` (deform bones the body uses) count.
    `extra` is more (object, evaluated mesh) sources taken together with the
    body - a head kept as its own mesh, so a hood gets the head's weights
    instead of the neck stump's."""
    Vs, Fs, Ws = [], [], []
    off = 0
    for o, me in ((body_ob, body_me),) + tuple(extra):
        V, F = _tri_mesh(me, o.matrix_world)
        if not len(F):
            continue
        Vs.append(V)
        Fs.append(F + off)
        Ws.append(_weights_matrix(o, me, bones))
        off += len(V)
    Vb, Fb, Wb = np.vstack(Vs), np.vstack(Fs), np.vstack(Ws)
    Vg, Fg = _tri_mesh(garment_me, garment_ob.matrix_world)
    Nb = _vertex_normals(Vb, Fb)
    Ng = _vertex_normals(Vg, Fg)

    bvh = BVHTree.FromPolygons([Vector(p) for p in Vb], Fb.tolist(), all_triangles=True)
    W = np.zeros((len(Vg), len(bones)))
    matched = np.zeros(len(Vg), dtype=bool)
    cos_lim = np.cos(np.radians(angle))
    for i, p in enumerate(Vg):
        hit = bvh.find_nearest(Vector(p), dist * 4.0)
        loc, nrm, fi, d = hit
        if loc is None:
            continue
        a, b_, c = Fb[fi]
        bary = _barycentric(np.array(loc), Vb[a], Vb[b_], Vb[c])
        W[i] = bary[0] * Wb[a] + bary[1] * Wb[b_] + bary[2] * Wb[c]
        nb = bary[0] * Nb[a] + bary[1] * Nb[b_] + bary[2] * Nb[c]
        nb /= max(np.linalg.norm(nb), 1e-12)
        if d <= dist and abs(float(nb @ Ng[i])) >= cos_lim:
            matched[i] = True
    if matched.any() and not matched.all():
        used = np.flatnonzero(W.max(axis=0) > 1e-4)   # solve only for bones in play
        W[:, used] = inpaint(Vg, Fg, W[:, used], matched)
    W = np.clip(W, 0.0, None)
    s = W.sum(axis=1, keepdims=True)
    W = np.where(s > 1e-8, W / np.maximum(s, 1e-8), W)
    return W, matched


def _barycentric(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-20:
        return np.array([1.0, 0.0, 0.0])
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return np.array([1.0 - v - w, v, w])
