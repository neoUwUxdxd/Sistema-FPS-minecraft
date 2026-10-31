"""
gunlib - biblioteca de modelado de armas para FPS Realista.

Define el formato de modelo (JSON) que lee el mod y una implementacion de
referencia del generador de mallas. El generador Java
(com.fpsrealista.client.model.MeshBuilder) sigue EXACTAMENTE el mismo algoritmo,
de modo que las vistas previas renderizadas aqui coinciden con el juego.

Unidades: centimetros. Ejes del modelo: +X derecha, +Y arriba, -Z hacia la boca
del canon. El anima del canon (bore) esta en x=0, y=0.

Primitivas:
  box      caja (opcionalmente con chaflan "bevel" en las aristas paralelas a "axis")
  cyl      cilindro / cono / tubo (radio interior "inner") a lo largo de un eje
  extrude  extrusion de un perfil 2D (poligono) a lo largo de un eje
  loft     transicion entre dos perfiles con el mismo numero de puntos
  decal    quad con textura completa (reticulas, marcas)

Ejes de perfil (u, v) segun "axis":
  axis z -> (x, y)      axis x -> (z, y)      axis y -> (x, z)
"""
import json
import math
import numpy as np

SMOOTH_DEG = 40.0


# ----------------------------------------------------------------------------
# Matematica
# ----------------------------------------------------------------------------
def rot_matrix(rx, ry, rz):
    """R = Rz * Ry * Rx (grados). Igual que Matrix4f().rotateZ().rotateY().rotateX()."""
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def to3(axis, u, v, a):
    if axis == "z":
        return (u, v, a)
    if axis == "x":
        return (a, v, u)
    return (u, a, v)  # y


def signed_area(p):
    s = 0.0
    n = len(p)
    for i in range(n):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s * 0.5


def triangulate(poly):
    """Ear clipping para poligonos simples en sentido antihorario. Devuelve indices."""
    n = len(poly)
    idx = list(range(n))
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        found = False
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-9:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if inside(poly[j], a, b, c):
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(k)
                found = True
                break
        if not found:
            # poligono degenerado: abanico de respaldo
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
            return tris
    if len(idx) == 3:
        tris.append((idx[0], idx[1], idx[2]))
    return tris


def norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if l < 1e-12:
        return (0.0, 1.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


# ----------------------------------------------------------------------------
# Generador de mallas (referencia). Cada quad: dict(mat, color, v=[(pos, uv, n)*4])
# ----------------------------------------------------------------------------
def loft_quads(axis, p0, p1, a0, a1, caps, smooth_deg, flip=False):
    """p0/p1: perfiles (lista de (u,v)) en sentido antihorario con igual longitud."""
    n = len(p0)
    quads = []
    # normales 2D de arista (exteriores para perfil CCW)
    en = []
    for i in range(n):
        du = p0[(i + 1) % n][0] - p0[i][0]
        dv = p0[(i + 1) % n][1] - p0[i][1]
        l = math.hypot(du, dv) or 1.0
        en.append((dv / l, -du / l))
    cos_t = math.cos(math.radians(smooth_deg))

    def vnormal(i, e):
        # normal del vertice i para la arista e (e == i o e == i-1)
        prev_e = (i - 1) % n
        nxt_e = i % n
        a, b = en[prev_e], en[nxt_e]
        if a[0] * b[0] + a[1] * b[1] >= cos_t:
            s = (a[0] + b[0], a[1] + b[1])
            l = math.hypot(*s) or 1.0
            return (s[0] / l, s[1] / l)
        return en[e]

    # perimetro acumulado para UV
    per = [0.0]
    for i in range(n):
        per.append(per[-1] + math.hypot(p0[(i + 1) % n][0] - p0[i][0], p0[(i + 1) % n][1] - p0[i][1]))

    sgn = -1.0 if flip else 1.0
    for e in range(n):
        i, j = e, (e + 1) % n
        ni = vnormal(i, e)
        nj = vnormal(j, e)
        verts = []
        for (pp, idx, a, nn, uu) in (
            (p0, i, a0, ni, per[e]),
            (p0, j, a0, nj, per[e + 1]),
            (p1, j, a1, nj, per[e + 1]),
            (p1, i, a1, ni, per[e]),
        ):
            pos = to3(axis, pp[idx][0], pp[idx][1], a)
            nrm = to3(axis, nn[0] * sgn, nn[1] * sgn, 0.0)
            verts.append((pos, (uu, a), nrm))
        quads.append(verts)

    if caps:
        tris = triangulate(p0)
        d = 1.0 if a1 >= a0 else -1.0
        for (pp, a, s) in ((p0, a0, -d), (p1, a1, d)):
            nrm = to3(axis, 0.0, 0.0, s * sgn)
            for (t0, t1, t2) in tris:
                vs = [(to3(axis, pp[t][0], pp[t][1], a), (pp[t][0], pp[t][1]), nrm) for t in (t0, t1, t2)]
                quads.append(vs + [vs[2]])
    return quads


def circle(cu, cv, r, seg, phase=0.0):
    return [(cu + r * math.cos(2 * math.pi * k / seg + phase), cv + r * math.sin(2 * math.pi * k / seg + phase)) for k in range(seg)]


def rect_profile(u0, v0, u1, v1, b):
    if b <= 0:
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    b = min(b, (u1 - u0) / 2 * 0.99, (v1 - v0) / 2 * 0.99)
    return [(u0 + b, v0), (u1 - b, v0), (u1, v0 + b), (u1, v1 - b),
            (u1 - b, v1), (u0 + b, v1), (u0, v1 - b), (u0, v0 + b)]


def part_quads(part):
    t = part["type"]
    sm = part.get("smooth", SMOOTH_DEG)
    if t == "box":
        f, to = part["from"], part["to"]
        lo = [min(f[i], to[i]) for i in range(3)]
        hi = [max(f[i], to[i]) for i in range(3)]
        dims = [hi[i] - lo[i] for i in range(3)]
        axis = part.get("axis") or "xyz"[int(np.argmax(dims))]
        b = part.get("bevel", 0.0)
        if axis == "z":
            prof, a0, a1 = rect_profile(lo[0], lo[1], hi[0], hi[1], b), lo[2], hi[2]
        elif axis == "x":
            prof, a0, a1 = rect_profile(lo[2], lo[1], hi[2], hi[1], b), lo[0], hi[0]
        else:
            prof, a0, a1 = rect_profile(lo[0], lo[2], hi[0], hi[2], b), lo[1], hi[1]
        q = loft_quads(axis, prof, prof, a0, a1, True, sm)
    elif t == "cyl":
        axis = part.get("axis", "z")
        cu, cv = part.get("c", [0.0, 0.0])
        r0 = part["r"]
        r1 = part.get("r2", r0)
        seg = part.get("seg", 16)
        ph = math.radians(part.get("phase", 0.0))
        a0, a1 = part["a"]
        sm = part.get("smooth", 60.0)
        po = circle(cu, cv, r0, seg, ph)
        p1 = circle(cu, cv, r1, seg, ph)
        inner = part.get("inner")
        if inner is None:
            q = loft_quads(axis, po, p1, a0, a1, True, sm)
        else:
            i1 = part.get("inner2", inner)
            q = loft_quads(axis, po, p1, a0, a1, False, sm)
            pi0 = circle(cu, cv, inner, seg, ph)
            pi1 = circle(cu, cv, i1, seg, ph)
            q += loft_quads(axis, pi0, pi1, a0, a1, False, sm, flip=True)
            d = 1.0 if a1 >= a0 else -1.0
            for (oo, ii, a, s) in ((po, pi0, a0, -d), (p1, pi1, a1, d)):
                nrm = to3(axis, 0.0, 0.0, s)
                for k in range(seg):
                    k2 = (k + 1) % seg
                    q.append([(to3(axis, *oo[k], a), oo[k], nrm), (to3(axis, *oo[k2], a), oo[k2], nrm),
                              (to3(axis, *ii[k2], a), ii[k2], nrm), (to3(axis, *ii[k], a), ii[k], nrm)])
    elif t in ("extrude", "loft"):
        axis = part.get("axis", "x")
        p0 = [tuple(p) for p in part["profile"]]
        p1 = [tuple(p) for p in part.get("profile2", part["profile"])]
        if signed_area(p0) < 0:
            p0 = p0[::-1]
            p1 = p1[::-1]
        a0, a1 = part["a"]
        q = loft_quads(axis, p0, p1, a0, a1, part.get("caps", True), sm)
    elif t == "decal":
        c = part["corners"]
        uv = part.get("uv", [0, 0, 1, 1])
        e1 = np.subtract(c[1], c[0])
        e2 = np.subtract(c[3], c[0])
        nrm = norm(np.cross(e1, e2))
        uvs = [(uv[0], uv[3]), (uv[2], uv[3]), (uv[2], uv[1]), (uv[0], uv[1])]
        q = [[(tuple(c[i]), uvs[i], nrm) for i in range(4)]]
    else:
        raise ValueError(t)

    # rotacion de la primitiva alrededor de su pivote
    rot = part.get("rot")
    if rot:
        R = rot_matrix(*rot)
        if "pivot" in part:
            pv = np.array(part["pivot"], dtype=float)
        else:
            allp = np.array([v[0] for qq in q for v in qq], dtype=float)
            pv = (allp.min(axis=0) + allp.max(axis=0)) * 0.5
        q = [[(tuple(R @ (np.array(p) - pv) + pv), uv, tuple(R @ np.array(n))) for (p, uv, n) in qq] for qq in q]
    return q


# ----------------------------------------------------------------------------
# DSL de modelado
# ----------------------------------------------------------------------------
class Bone:
    def __init__(self, model, name, parent, pivot):
        self.model = model
        self.name = name
        self.parent = parent
        self.pivot = list(map(float, pivot))
        self.parts = []
        self.rotation = [0.0, 0.0, 0.0]

    def _add(self, d, mat, tint, **kw):
        d["mat"] = mat
        if tint:
            d["tint"] = tint
        for k, v in kw.items():
            if v is not None:
                d[k] = v
        self.parts.append(d)
        return d

    def box(self, frm, to, mat, bevel=0.0, axis=None, tint=None, rot=None, pivot=None, smooth=None):
        return self._add({"type": "box", "from": list(frm), "to": list(to)}, mat, tint,
                         bevel=bevel or None, axis=axis, rot=rot, pivot=pivot, smooth=smooth)

    def cyl(self, axis, c, r, a, mat, r2=None, seg=16, inner=None, inner2=None, tint=None, rot=None,
            pivot=None, phase=None, smooth=None):
        return self._add({"type": "cyl", "axis": axis, "c": list(c), "r": r, "a": list(a), "seg": seg}, mat, tint,
                         r2=r2, inner=inner, inner2=inner2, rot=rot, pivot=pivot, phase=phase, smooth=smooth)

    def extrude(self, axis, profile, a, mat, tint=None, rot=None, pivot=None, smooth=None, profile2=None, caps=None):
        d = {"type": "loft" if profile2 else "extrude", "axis": axis,
             "profile": [list(map(lambda x: round(x, 4), p)) for p in profile], "a": list(a)}
        if profile2:
            d["profile2"] = [list(map(lambda x: round(x, 4), p)) for p in profile2]
        return self._add(d, mat, tint, rot=rot, pivot=pivot, smooth=smooth, caps=caps)

    def decal(self, corners, mat, uv=None, tint=None):
        return self._add({"type": "decal", "corners": [list(c) for c in corners]}, mat, tint, uv=uv)


class Model:
    def __init__(self, name):
        self.name = name
        self.bones = []
        self.locators = {}
        self.extra = {}

    def bone(self, name, parent=None, pivot=(0, 0, 0)):
        b = Bone(self, name, parent, pivot)
        self.bones.append(b)
        return b

    def locator(self, name, bone, pos):
        self.locators[name] = {"bone": bone, "pos": [round(float(x), 4) for x in pos]}

    def to_json(self):
        return {
            "format": 1,
            "name": self.name,
            "units": "cm",
            "bones": [{"name": b.name, "parent": b.parent, "pivot": b.pivot, "rotation": b.rotation,
                       "parts": b.parts} for b in self.bones],
            "locators": self.locators,
            **self.extra,
        }

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_json(), f, separators=(",", ":"))


def load_model(path):
    with open(path) as f:
        return json.load(f)


def mesh_from_json(mj):
    """Devuelve {bone: [(mat, tint, quads)]} con los quads generados."""
    out = {}
    for b in mj["bones"]:
        lst = []
        for idx, p in enumerate(b["parts"]):
            q = part_quads(p)
            lst.append((p["mat"], p.get("tint"), q, idx))
        out[b["name"]] = lst
    return out


# ----------------------------------------------------------------------------
# Utilidades de perfiles
# ----------------------------------------------------------------------------
def bezier(p0, p1, p2, n=6, include_start=True):
    pts = []
    for k in range(0 if include_start else 1, n + 1):
        t = k / n
        a = (1 - t) ** 2
        b = 2 * (1 - t) * t
        c = t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    return pts


def round_rect(u0, v0, u1, v1, r, n=3):
    """Rectangulo con esquinas redondeadas (perfil CCW)."""
    r = min(r, (u1 - u0) / 2 * 0.99, (v1 - v0) / 2 * 0.99)
    pts = []
    corners = [(u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)]
    for (cu, cv, st) in corners:
        for k in range(n + 1):
            a = math.radians(st + 90 * k / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts
