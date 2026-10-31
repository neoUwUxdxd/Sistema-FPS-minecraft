"""
Renderizador por software (numpy) para previsualizar modelos de armas y
animaciones fuera de Minecraft. Reproduce la misma iluminacion difusa de dos
luces que usa el shader de entidades de Minecraft.

Uso:
  python3 tools/preview.py <modelo.json> [salida.png]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import gunlib  # noqa: E402

ASSETS = os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "assets", "fpsrealista")
_TEX = {}


def load_materials():
    with open(os.path.join(ASSETS, "gunmodels", "materials.json")) as f:
        return json.load(f)


MATS = load_materials()


def tex(name):
    if name not in _TEX:
        m = MATS[name]
        path = m["texture"].split(":", 1)[1]
        img = Image.open(os.path.join(ASSETS, path)).convert("RGBA")
        _TEX[name] = np.asarray(img, np.float32) / 255.0
    return _TEX[name]


def hex_color(h):
    if not h:
        return np.array([1.0, 1.0, 1.0, 1.0])
    h = h.lstrip("#")
    v = [int(h[i:i + 2], 16) / 255.0 for i in range(0, len(h), 2)]
    if len(v) == 3:
        v.append(1.0)
    return np.array(v)


# Luces del shader de entidades (Lighting.setupFor3DItems / nivel), espacio vista
LIGHT0 = np.array([0.2, 1.0, -0.7]); LIGHT0 /= np.linalg.norm(LIGHT0)
LIGHT1 = np.array([-0.2, 1.0, 0.7]); LIGHT1 /= np.linalg.norm(LIGHT1)


def shade(n):
    l = np.maximum(0, n @ LIGHT0) * 0.6 + np.maximum(0, n @ LIGHT1) * 0.6
    return np.minimum(1.0, l + 0.4)


class Raster:
    def __init__(self, w, h, bg=(70, 78, 90)):
        self.w, self.h = w, h
        self.color = np.zeros((h, w, 3), np.float32)
        y = np.linspace(0, 1, h)[:, None, None]
        self.color[:] = np.array(bg, np.float32)[None, None, :] / 255.0 * (1.1 - 0.35 * y)
        self.depth = np.full((h, w), np.inf, np.float32)

    def tri(self, sp, wz, uv, col, texture, alpha_blend=False, emissive=False):
        """sp: 3x2 pixel coords, wz: 3 view depths (positivos), uv: 3x2, col: 3x3 (rgb ya iluminado)."""
        x0, y0 = np.floor(sp.min(axis=0)).astype(int)
        x1, y1 = np.ceil(sp.max(axis=0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, self.w - 1), min(y1, self.h - 1)
        if x0 > x1 or y0 > y1:
            return
        (ax, ay), (bx, by), (cx, cy) = sp
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            return
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        px, py = xs + 0.5, ys + 0.5
        l0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
        l1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
        l2 = 1 - l0 - l1
        m = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not m.any():
            return
        iw = 1.0 / wz
        pw = l0 * iw[0] + l1 * iw[1] + l2 * iw[2]
        z = 1.0 / pw
        zb = self.depth[y0:y1 + 1, x0:x1 + 1]
        m &= z < zb
        if not m.any():
            return
        b0 = l0 * iw[0] * z
        b1 = l1 * iw[1] * z
        b2 = l2 * iw[2] * z
        u = b0 * uv[0, 0] + b1 * uv[1, 0] + b2 * uv[2, 0]
        v = b0 * uv[0, 1] + b1 * uv[1, 1] + b2 * uv[2, 1]
        th, tw = texture.shape[:2]
        tx = (np.floor((u % 1.0) * tw).astype(int)) % tw
        ty = (np.floor((v % 1.0) * th).astype(int)) % th
        t = texture[ty, tx]
        c = (b0[..., None] * col[0] + b1[..., None] * col[1] + b2[..., None] * col[2])
        rgb = t[..., :3] * c
        a = t[..., 3]
        if alpha_blend:
            m &= a > 0.01
            dst = self.color[y0:y1 + 1, x0:x1 + 1]
            out = rgb * a[..., None] + dst * (1 - a[..., None])
            if emissive:
                out = dst + rgb * a[..., None]
            dst[m] = out[m]
        else:
            m &= a > 0.1
            self.color[y0:y1 + 1, x0:x1 + 1][m] = rgb[m]
            zb[m] = z[m]

    def image(self):
        return Image.fromarray((np.clip(self.color, 0, 1) * 255).astype(np.uint8), "RGB")


# ----------------------------------------------------------------------------
# Jerarquia de huesos
# ----------------------------------------------------------------------------
def T(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def R(rx, ry, rz):
    m = np.eye(4)
    m[:3, :3] = gunlib.rot_matrix(rx, ry, rz)
    return m


def S(s):
    m = np.eye(4)
    m[0, 0] = m[1, 1] = m[2, 2] = s
    return m


def bone_matrices(mj, pose=None):
    """pose: {bone: (pos(3), rot(3))} desplazamientos de animacion."""
    pose = pose or {}
    by = {b["name"]: b for b in mj["bones"]}
    mats = {}

    def get(name):
        if name in mats:
            return mats[name]
        b = by[name]
        parent = get(b["parent"]) if b.get("parent") else np.eye(4)
        p = np.array(b["pivot"])
        ap, ar = pose.get(name, ((0, 0, 0), (0, 0, 0)))
        rr = np.add(b.get("rotation", [0, 0, 0]), ar)
        m = parent @ T(p) @ T(ap) @ R(*rr) @ T(-p)
        mats[name] = m
        return m

    for b in mj["bones"]:
        get(b["name"])
    return mats


def locator_pos(mj, mats, name):
    loc = mj["locators"][name]
    return (mats[loc["bone"]] @ np.array([*loc["pos"], 1.0]))[:3]


# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
class Camera:
    def __init__(self, w, h, fov=70.0, ortho=None):
        self.w, self.h = w, h
        self.fov = fov
        self.ortho = ortho  # media altura visible (unidades) si ortografica

    def project(self, p):
        """p: Nx3 en espacio vista (-Z delante)."""
        if self.ortho:
            s = (self.h / 2) / self.ortho
            x = self.w / 2 + p[:, 0] * s
            y = self.h / 2 - p[:, 1] * s
            return np.stack([x, y], 1), 100.0 - p[:, 2]
        f = (self.h / 2) / math.tan(math.radians(self.fov) / 2)
        z = -p[:, 2]
        x = self.w / 2 + p[:, 0] * f / z
        y = self.h / 2 - p[:, 1] * f / z
        return np.stack([x, y], 1), z


def draw_mesh(rs, cam, mj, view, mesh=None, pose=None, hidden=()):
    """view: matriz 4x4 modelo->vista."""
    mesh = mesh or gunlib.mesh_from_json(mj)
    mats = bone_matrices(mj, pose)
    later = []
    for bname, parts in mesh.items():
        if bname in hidden:
            continue
        M = view @ mats[bname]
        Nm = M[:3, :3]
        for (mat, tint, quads, idx) in parts:
            mdef = MATS[mat]
            texture = tex(mat)
            kind = mdef["type"]
            sc = mdef["scale"]
            ou = (idx * 0.618034) % 1.0
            ov = (idx * 0.414214) % 1.0
            colr = hex_color(tint)
            for q in quads:
                P = np.array([v[0] for v in q], float)
                Pv = (M @ np.c_[P, np.ones(4)].T).T[:, :3]
                if not cam.ortho and (Pv[:, 2] > -0.06).any():
                    continue
                n = np.array([v[2] for v in q], float) @ Nm.T
                n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
                if kind in ("decal", "emissive_decal"):
                    uv = np.array([v[1] for v in q], float)
                else:
                    uv = np.array([v[1] for v in q], float) / sc + [ou, ov]
                    uv[:, 1] = -uv[:, 1]
                if kind.startswith("emissive"):
                    lit = np.ones(4)
                else:
                    lit = shade(n)
                col = lit[:, None] * colr[None, :3]
                sp, wz = cam.project(Pv)
                item = (sp, wz, uv, col, texture, kind)
                if kind in ("translucent", "decal", "emissive_decal"):
                    later.append(item)
                else:
                    for tri in ((0, 1, 2), (0, 2, 3)):
                        t = list(tri)
                        rs.tri(sp[t], wz[t], uv[t], col[t], texture)
    for (sp, wz, uv, col, texture, kind) in later:
        for tri in ((0, 1, 2), (0, 2, 3)):
            t = list(tri)
            rs.tri(sp[t], wz[t], uv[t], col[t], texture, alpha_blend=True, emissive=(kind == "emissive_decal"))
    return mats


def model_bounds(mj, mesh=None):
    mesh = mesh or gunlib.mesh_from_json(mj)
    mats = bone_matrices(mj)
    pts = []
    for bname, parts in mesh.items():
        M = mats[bname]
        for (_, _, quads, _) in parts:
            for q in quads:
                for v in q:
                    pts.append((M @ np.array([*v[0], 1.0]))[:3])
    pts = np.array(pts)
    return pts.min(0), pts.max(0)


def render_sheet(mj, out, w=1400, h=900):
    mesh = gunlib.mesh_from_json(mj)
    lo, hi = model_bounds(mj, mesh)
    c = (lo + hi) / 2
    L = (hi - lo).max()
    img = Image.new("RGB", (w, h))
    # vista lateral derecha (ortografica)
    hw, hh = w, h // 2
    cam = Camera(hw, hh, ortho=L * 0.30)
    rs = Raster(hw, hh)
    view = R(0, -90, 0) @ T(-c)
    draw_mesh(rs, cam, mj, view, mesh)
    img.paste(rs.image(), (0, 0))
    # vista 3/4 en perspectiva (izquierda)
    cam = Camera(w // 2, hh, fov=30)
    rs = Raster(w // 2, hh)
    view = T((0, 0, -L * 2.0)) @ R(18, 0, 0) @ R(0, 120, 0) @ T(-c)
    draw_mesh(rs, cam, mj, view, mesh)
    img.paste(rs.image(), (0, hh))
    # vista 3/4 trasera superior
    rs = Raster(w // 2, hh)
    view = T((0, 0, -L * 2.0)) @ R(25, 0, 0) @ R(0, -35, 0) @ T(-c)
    draw_mesh(rs, cam, mj, view, mesh)
    img.paste(rs.image(), (w // 2, hh))
    img.save(out)


if __name__ == "__main__":
    mj = gunlib.load_model(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "preview.png"
    render_sheet(mj, out)
    print("ok", out)
