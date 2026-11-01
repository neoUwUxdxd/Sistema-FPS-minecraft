"""
Conversion de las primitivas de gunlib a cubos (lo unico que admite la geometria de Bedrock).

Todo se calcula en el espacio del modelo original (cm, +X derecha, +Y arriba, -Z boca del canon).
La conversion al espacio de Bedrock se hace despues en build_bedrock.py.

Cada cubo: dict(lo=[x,y,z], hi=[x,y,z], rot=(a,b,c)|None, pivot=[x,y,z]|None, mat, tint, decal_uv)
  - cilindros  -> cuadrados girados sobre el eje (12 u 8 lados)
  - tubos      -> anillo de 12 tablillas (p. ej. el tubo del punto rojo queda hueco)
  - extrusiones-> laminas finas a lo largo de la dimension mas larga del perfil
  - cajas con chaflan -> dos cubos cruzados
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gunlib  # noqa: E402

BAND = 0.32       # grosor de lamina (cm) para extrusiones
MERGE_TOL = 0.05  # tolerancia para fusionar laminas consecutivas (cm)


def to3(axis, u, v, a):
    return list(gunlib.to3(axis, u, v, a))


def box_from_uva(axis, u0, u1, v0, v1, a0, a1):
    p0 = to3(axis, u0, v0, a0)
    p1 = to3(axis, u1, v1, a1)
    lo = [min(p0[i], p1[i]) for i in range(3)]
    hi = [max(p0[i], p1[i]) for i in range(3)]
    return lo, hi


def axis_rot(axis, deg):
    return {"x": (deg, 0, 0), "y": (0, deg, 0), "z": (0, 0, deg)}[axis]


def compose_rot(r1, r2):
    """Rotacion combinada R2*R1 expresada en angulos (Rz*Ry*Rx)."""
    import numpy as np
    R = gunlib.rot_matrix(*r2) @ gunlib.rot_matrix(*r1)
    return euler(R)


def euler(R):
    """Descompone R = Rz(c) Ry(b) Rx(a) -> (a, b, c) grados."""
    sb = -R[2][0]
    sb = max(-1.0, min(1.0, sb))
    b = math.asin(sb)
    if abs(sb) < 0.99999:
        a = math.atan2(R[2][1], R[2][2])
        c = math.atan2(R[1][0], R[0][0])
    else:
        a = math.atan2(-R[1][2], R[1][1])
        c = 0.0
    return (math.degrees(a), math.degrees(b), math.degrees(c))


def intervals_at(poly, v):
    """Intervalos en u donde la recta horizontal v corta el poligono."""
    xs = []
    n = len(poly)
    for i in range(n):
        (u0, v0), (u1, v1) = poly[i], poly[(i + 1) % n]
        if (v0 <= v < v1) or (v1 <= v < v0):
            t = (v - v0) / (v1 - v0)
            xs.append(u0 + t * (u1 - u0))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def principal_angle(poly):
    """Angulo (grados) del eje principal del contorno y su centroide."""
    n = len(poly)
    L = cu = cv = 0.0
    for i in range(n):
        (u0, v0), (u1, v1) = poly[i], poly[(i + 1) % n]
        l = math.hypot(u1 - u0, v1 - v0)
        L += l
        cu += (u0 + u1) / 2 * l
        cv += (v0 + v1) / 2 * l
    cu /= L or 1
    cv /= L or 1
    suu = svv = suv = 0.0
    for i in range(n):
        (u0, v0), (u1, v1) = poly[i], poly[(i + 1) % n]
        l = math.hypot(u1 - u0, v1 - v0)
        du, dv = (u0 + u1) / 2 - cu, (v0 + v1) / 2 - cv
        suu += du * du * l
        svv += dv * dv * l
        suv += du * dv * l
    ang = 0.5 * math.degrees(math.atan2(2 * suv, suu - svv))
    # angulo del eje mayor en [-90, 90]; preferimos el mas cercano a los ejes del perfil
    if ang > 45:
        ang -= 90
    elif ang < -45:
        ang += 90
    return ang, (cu, cv)


def slice_profile(poly):
    """Devuelve rectangulos (u0,u1,v0,v1) que aproximan el poligono."""
    us = [p[0] for p in poly]
    vs = [p[1] for p in poly]
    swap = (max(us) - min(us)) > (max(vs) - min(vs))
    if swap:  # laminas a lo largo de la dimension larga
        poly = [(p[1], p[0]) for p in poly]
        us, vs = vs, us
    vmin, vmax = min(vs), max(vs)
    n = max(1, int(math.ceil((vmax - vmin) / BAND)))
    h = (vmax - vmin) / n
    rects = []
    open_ = []  # rects actuales [u0,u1,v0,v1]
    for k in range(n):
        vb0 = vmin + k * h
        vb1 = vb0 + h
        iv = intervals_at(poly, (vb0 + vb1) * 0.5)
        if len(open_) == len(iv) and all(abs(o[0] - a) < MERGE_TOL and abs(o[1] - b) < MERGE_TOL
                                         for o, (a, b) in zip(open_, iv)):
            for o in open_:
                o[3] = vb1
            continue
        rects.extend(open_)
        open_ = [[a, b, vb0, vb1] for (a, b) in iv]
    rects.extend(open_)
    if swap:
        rects = [(r[2], r[3], r[0], r[1]) for r in rects]
    return [tuple(r) for r in rects if r[1] - r[0] > 1e-3 and r[3] - r[2] > 1e-3]


def part_cubes(p):
    t = p["type"]
    mat = p["mat"]
    tint = p.get("tint")
    out = []

    def add(lo, hi, rot=None, pivot=None, decal_uv=None):
        out.append({"lo": lo, "hi": hi, "rot": rot, "pivot": pivot, "mat": mat, "tint": tint, "decal_uv": decal_uv})

    if t == "box":
        f, to = p["from"], p["to"]
        lo = [min(f[i], to[i]) for i in range(3)]
        hi = [max(f[i], to[i]) for i in range(3)]
        dims = [hi[i] - lo[i] for i in range(3)]
        axis = p.get("axis") or "xyz"[dims.index(max(dims))]
        b = p.get("bevel", 0.0)
        ai = "xyz".index(axis)
        cross = [i for i in range(3) if i != ai]
        if b >= 0.12 and min(dims[cross[0]], dims[cross[1]]) > 3 * b:
            b = min(b, dims[cross[0]] / 2 * 0.9, dims[cross[1]] / 2 * 0.9)
            for shrink in cross:
                l2, h2 = list(lo), list(hi)
                l2[shrink] += b
                h2[shrink] -= b
                add(l2, h2)
        else:
            add(lo, hi)
    elif t == "cyl":
        axis = p.get("axis", "z")
        cu, cv = p.get("c", [0.0, 0.0])
        r0 = p["r"]
        r1 = p.get("r2", r0)
        a0, a1 = p["a"]
        phase = p.get("phase", 0.0)
        inner = p.get("inner")
        L = abs(a1 - a0)
        nseg = 1 if abs(r1 - r0) < 0.05 else max(2, int(math.ceil(L / 1.0)))
        for s in range(nseg):
            sa0 = a0 + (a1 - a0) * s / nseg
            sa1 = a0 + (a1 - a0) * (s + 1) / nseg
            r = r0 + (r1 - r0) * (s + 0.5) / nseg
            mid = (sa0 + sa1) * 0.5
            piv = to3(axis, cu, cv, mid)
            if inner is not None and inner > 0.6 * r and r > 0.9:
                n = 12
                w = 2 * r * math.tan(math.pi / n) * 1.12
                rm = (r + inner) * 0.5
                th = r - inner
                for i in range(n):
                    lo, hi = box_from_uva(axis, cu + rm - th / 2, cu + rm + th / 2, cv - w / 2, cv + w / 2, sa0, sa1)
                    add(lo, hi, axis_rot(axis, phase + 360.0 * i / n), piv)
            else:
                k = 3 if r > 0.9 else 2
                h = r * (0.88 if k == 3 else 0.84)
                for i in range(k):
                    lo, hi = box_from_uva(axis, cu - h, cu + h, cv - h, cv + h, sa0, sa1)
                    ang = phase + 90.0 * i / k
                    add(lo, hi, axis_rot(axis, ang) if abs(ang) > 1e-6 else None, piv)
    elif t in ("extrude", "loft"):
        axis = p.get("axis", "x")
        p0 = [tuple(q) for q in p["profile"]]
        if "profile2" in p:
            p1 = [tuple(q) for q in p["profile2"]]
            p0 = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(p0, p1)]
        a0, a1 = p["a"]
        theta, (cu, cv) = principal_angle(p0)
        if abs(theta) < 4.0 or abs(theta) > 86.0:
            for (u0, u1, v0, v1) in slice_profile(p0):
                lo, hi = box_from_uva(axis, u0, u1, v0, v1, min(a0, a1), max(a0, a1))
                add(lo, hi)
        else:
            # laminas alineadas con el eje principal de la silueta (evita el efecto sierra)
            ct, st_ = math.cos(math.radians(-theta)), math.sin(math.radians(-theta))
            rp = [(cu + (u - cu) * ct - (v - cv) * st_, cv + (u - cu) * st_ + (v - cv) * ct) for (u, v) in p0]
            piv = to3(axis, cu, cv, (a0 + a1) * 0.5)
            rot = {"z": (0, 0, theta), "x": (-theta, 0, 0), "y": (0, -theta, 0)}[axis]
            for (u0, u1, v0, v1) in slice_profile(rp):
                lo, hi = box_from_uva(axis, u0, u1, v0, v1, min(a0, a1), max(a0, a1))
                add(lo, hi, rot, piv)
    elif t == "decal":
        c = p["corners"]
        lo = [min(q[i] for q in c) for i in range(3)]
        hi = [max(q[i] for q in c) for i in range(3)]
        d = [hi[i] - lo[i] for i in range(3)]
        ax = d.index(min(d))
        lo[ax] -= 0.01
        hi[ax] += 0.01
        add(lo, hi, decal_uv={"uv": p.get("uv", [0, 0, 1, 1]), "axis": ax, "corners": c})
    else:
        raise ValueError(t)

    # rotacion de la propia primitiva (gira todos sus cubos alrededor de su pivote)
    if p.get("rot"):
        if "pivot" in p:
            pv = list(p["pivot"])
        else:
            q = gunlib.part_quads(p)
            pts = [v[0] for qq in q for v in qq]
            # part_quads ya aplica la rotacion; el centro de la caja envolvente sin rotar
            q0 = gunlib.part_quads({k: v for k, v in p.items() if k != "rot"})
            pts = [v[0] for qq in q0 for v in qq]
            pv = [(min(pp[i] for pp in pts) + max(pp[i] for pp in pts)) / 2 for i in range(3)]
        R2 = tuple(p["rot"])
        import numpy as np
        Rm = gunlib.rot_matrix(*R2)
        for cb in out:
            if cb["rot"] is None:
                cb["rot"] = R2
                cb["pivot"] = pv
            else:
                # componer: primero la rotacion del cubo (alrededor de su pivote), luego la de la primitiva
                cp = np.array(cb["pivot"], float)
                cb["pivot"] = list(Rm @ (cp - np.array(pv)) + np.array(pv))
                cb["rot"] = compose_rot(cb["rot"], R2)
                # el cubo gira alrededor de su nuevo pivote: hay que mover el cubo junto con el pivote
                shift = np.array(cb["pivot"]) - cp
                cb["lo"] = list(np.array(cb["lo"]) + shift)
                cb["hi"] = list(np.array(cb["hi"]) + shift)
    return out


def model_cubes(mj):
    """{bone: [cubos]} para todo el modelo."""
    res = {}
    for b in mj["bones"]:
        lst = []
        for p in b["parts"]:
            lst.extend(part_cubes(p))
        res[b["name"]] = lst
    return res


def cube_quads(cb):
    """Quads (en espacio del modelo) de un cubo, para la vista previa de validacion."""
    import numpy as np
    lo, hi = cb["lo"], cb["hi"]
    c = [[lo[0] if i & 1 == 0 else hi[0], lo[1] if i & 2 == 0 else hi[1], lo[2] if i & 4 == 0 else hi[2]] for i in range(8)]
    faces = [((0, 2, 6, 4), (-1, 0, 0)), ((1, 5, 7, 3), (1, 0, 0)), ((0, 4, 5, 1), (0, -1, 0)),
             ((2, 3, 7, 6), (0, 1, 0)), ((0, 1, 3, 2), (0, 0, -1)), ((4, 6, 7, 5), (0, 0, 1))]
    R = gunlib.rot_matrix(*cb["rot"]) if cb["rot"] else np.eye(3)
    pv = np.array(cb["pivot"] if cb["pivot"] is not None else [0, 0, 0], float)
    quads = []
    for (f, n) in faces:
        vs = []
        for i in f:
            p = R @ (np.array(c[i], float) - pv) + pv
            # uv planar simple para la vista previa
            uv = (p[0] + p[2], p[1]) if n[1] == 0 else (p[0], p[2])
            vs.append((tuple(p), uv, tuple(R @ np.array(n, float))))
        quads.append(vs)
    return quads
