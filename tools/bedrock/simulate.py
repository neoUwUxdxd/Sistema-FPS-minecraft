"""
Simulador de verificacion del add-on de Bedrock.

Interpreta los archivos generados (geometria, animaciones con Molang, attachable) siguiendo las
convenciones de Bedrock y renderiza la vista en primera persona pasando por la pose vanilla del
brazo (rightItem). Sirve para comprobar sin el juego que la cadena de transformaciones, el atlas
y las expresiones Molang son coherentes.

Uso: python3 tools/bedrock/simulate.py <arma> [clip] [t]
"""
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gunlib  # noqa: E402
import preview  # noqa: E402

RP = os.path.join(os.path.dirname(os.path.dirname(HERE)), "bedrock", "FPS_Realista_RP")
S_PX = 16.0 / 0.9375


# =============================================================================
# Interprete minimo de Molang
# =============================================================================
TOKEN = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][-+]?\d+)?f?)|('(?:[^'])*')|([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*)|(\?\?|&&|\|\||==|!=|<=|>=|->|[-+*/()?:!<>,=;]))")


class Molang:
    def __init__(self, ctx):
        self.ctx = ctx  # dict nombre->valor (v.x, c.x, q.x) y funciones

    def tokens(self, s):
        out, pos = [], 0
        s = s.strip()
        while pos < len(s):
            m = TOKEN.match(s, pos)
            if not m or m.end() == pos:
                raise SyntaxError(f"Molang: token invalido en '{s[pos:pos + 20]}'")
            pos = m.end()
            num, st, ident, op = m.groups()
            if num is not None:
                out.append(("num", float(num.rstrip("f"))))
            elif st is not None:
                out.append(("str", st[1:-1]))
            elif ident is not None:
                out.append(("id", ident.lower()))
            else:
                out.append(("op", op))
        return out

    def run(self, s):
        """Ejecuta sentencias (con ';' y asignaciones) o evalua una expresion."""
        if isinstance(s, (int, float)):
            return float(s)
        result = 0.0
        stmts = [x for x in s.split(";") if x.strip()]
        for stmt in stmts:
            self.toks = self.tokens(stmt)
            self.i = 0
            # asignacion
            if len(self.toks) > 2 and self.toks[0][0] == "id" and self.toks[1] == ("op", "="):
                name = self.alias(self.toks[0][1])
                self.i = 2
                val = self.ternary()
                self.ctx[name] = val
                result = val
            else:
                result = self.ternary()
            if self.i != len(self.toks):
                raise SyntaxError(f"Molang: sobra '{self.toks[self.i:]}' en '{stmt}'")
        return result

    @staticmethod
    def alias(n):
        for a, b in (("variable.", "v."), ("query.", "q."), ("context.", "c."), ("temp.", "t.")):
            if n.startswith(a):
                return b + n[len(a):]
        return n

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def eat(self, op=None):
        t = self.peek()
        if op is not None and t != ("op", op):
            raise SyntaxError(f"Molang: se esperaba '{op}' y llego {t}")
        self.i += 1
        return t

    def ternary(self):
        c = self.coalesce()
        if self.peek() == ("op", "?"):
            self.eat("?")
            a = self.ternary()
            if self.peek() == ("op", ":"):
                self.eat(":")
                b = self.ternary()
            else:
                b = 0.0
            return a if c else b
        return c

    def coalesce(self):
        a = self.orr()
        while self.peek() == ("op", "??"):
            self.eat()
            b = self.orr()
            a = b if a is None else a
        return a

    def orr(self):
        a = self.andd()
        while self.peek() == ("op", "||"):
            self.eat()
            b = self.andd()
            a = 1.0 if (self.num(a) or self.num(b)) else 0.0
        return a

    def andd(self):
        a = self.cmp()
        while self.peek() == ("op", "&&"):
            self.eat()
            b = self.cmp()
            a = 1.0 if (self.num(a) and self.num(b)) else 0.0
        return a

    def cmp(self):
        a = self.add()
        while self.peek()[0] == "op" and self.peek()[1] in ("==", "!=", "<", ">", "<=", ">="):
            op = self.eat()[1]
            b = self.add()
            x, y = self.num(a), self.num(b)
            a = float({"==": x == y, "!=": x != y, "<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y}[op])
        return a

    def add(self):
        a = self.mul()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.eat()[1]
            b = self.mul()
            a = self.num(a) + self.num(b) if op == "+" else self.num(a) - self.num(b)
        return a

    def mul(self):
        a = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.eat()[1]
            b = self.unary()
            a = self.num(a) * self.num(b) if op == "*" else (self.num(a) / self.num(b) if self.num(b) else 0.0)
        return a

    def unary(self):
        t = self.peek()
        if t == ("op", "-"):
            self.eat()
            return -self.num(self.unary())
        if t == ("op", "!"):
            self.eat()
            return 0.0 if self.num(self.unary()) else 1.0
        return self.atom()

    @staticmethod
    def num(x):
        return 0.0 if x is None else float(x)

    def atom(self):
        t = self.eat()
        if t[0] == "num":
            return t[1]
        if t[0] == "str":
            return t[1]
        if t == ("op", "("):
            v = self.ternary()
            self.eat(")")
            return v
        if t[0] == "id":
            name = self.alias(t[1])
            if self.peek() == ("op", "("):
                self.eat("(")
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.ternary())
                    while self.peek() == ("op", ","):
                        self.eat()
                        args.append(self.ternary())
                self.eat(")")
                return self.call(name, args)
            if name in self.ctx:
                return self.ctx[name]
            if name.startswith(("v.", "t.")):
                return None
            if name.startswith(("q.", "c.")):
                if name not in self.ctx:
                    raise NameError(f"Molang: consulta desconocida {name}")
            return 0.0
        raise SyntaxError(f"Molang: token inesperado {t}")

    def call(self, name, args):
        f = {
            "math.sin": lambda a: math.sin(math.radians(a)),
            "math.cos": lambda a: math.cos(math.radians(a)),
            "math.clamp": lambda v, lo, hi: max(lo, min(hi, v)),
            "math.random": lambda a, b: (a + b) / 2,
            "math.sqrt": math.sqrt,
            "math.abs": abs,
            "math.min": min,
            "math.max": max,
            "math.lerp": lambda a, b, t: a + (b - a) * t,
        }
        if name in f:
            return float(f[name](*[self.num(a) for a in args]))
        if name in self.ctx and callable(self.ctx[name]):
            return self.ctx[name](*args)
        raise NameError(f"Molang: funcion desconocida {name}")


# =============================================================================
# Evaluacion de animaciones
# =============================================================================
def sample_channel(ch, t, mol):
    if ch is None:
        return None
    if isinstance(ch, (int, float, str)):
        v = mol.run(ch) if isinstance(ch, str) else float(ch)
        return [v, v, v]
    if isinstance(ch, list):
        return [mol.num(mol.run(c)) if isinstance(c, str) else float(c) for c in ch]
    # fotogramas clave
    keys = sorted((float(k), v) for k, v in ch.items())

    def val(v):
        if isinstance(v, dict):
            v = v.get("post", v.get("pre"))
        return [float(x) for x in v]
    if t <= keys[0][0]:
        return val(keys[0][1])
    if t >= keys[-1][0]:
        return val(keys[-1][1])
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            a, b = val(v0), val(v1)
            return [a[i] + (b[i] - a[i]) * f for i in range(3)]
    return val(keys[-1][1])


def R_bed(a, b, c):
    return gunlib.rot_matrix(-a, b, -c)


def M4(R=None, t=(0, 0, 0)):
    m = np.eye(4)
    if R is not None:
        m[:3, :3] = R
    m[:3, 3] = t
    return m


def bone_world(geo_bones, anim_vals):
    """anim_vals: {bone: (pos, rot, scale)} sumados. Devuelve matrices bone->espacio raiz."""
    by = {b["name"]: b for b in geo_bones}
    out = {}

    def get(n):
        if n in out:
            return out[n]
        b = by[n]
        parent = get(b["parent"]) if b.get("parent") else np.eye(4)
        pv = np.array(b.get("pivot", [0, 0, 0]), float)
        pos, rot, sc = anim_vals.get(n, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
        rr = np.add(b.get("rotation", [0, 0, 0]), rot)
        S = np.diag([sc[0], sc[1], sc[2], 1.0])
        m = parent @ M4(t=pv + np.array(pos)) @ M4(R_bed(*rr)) @ S @ M4(t=-pv)
        out[n] = m
        return m
    for b in geo_bones:
        get(b["name"])
    return out


def evaluate(gun, clip=None, t=0.0, state=None):
    att = json.load(open(os.path.join(RP, "attachables", gun + ".json")))["minecraft:attachable"]["description"]
    anims = json.load(open(os.path.join(RP, "animations", gun + ".animation.json")))["animations"]
    state = state or {}
    ctx = {"c.is_first_person": state.get("fp", 1.0), "q.delta_time": 1 / 60, "q.is_sneaking": state.get("sneak", 0.0),
           "q.is_sprinting": state.get("sprint", 0.0), "q.life_time": 0.0,
           "q.property": lambda name: {"fps:shot": 0, "fps:mode": 0, "fps:empty": 0, "fps:anim": 0, "fps:seq": 0}.get(name, 0),
           "c.item_slot": 0, "q.item_slot_to_bone_name": lambda *a: 0}
    mol = Molang(ctx)
    # integrar pre_animation unos segundos para estabilizar v.ads / v.spr
    for _ in range(120):
        for line in att["scripts"]["pre_animation"]:
            mol.run(line)
    if clip:
        ctx["v.clip"] = 1.0
    vals = {}

    def apply(anim_key, weight, tt):
        a = anims[att["animations"][anim_key]]
        for bn, chs in a.get("bones", {}).items():
            p = sample_channel(chs.get("position"), tt, mol)
            r = sample_channel(chs.get("rotation"), tt, mol)
            s = sample_channel(chs.get("scale"), tt, mol)
            cur = vals.get(bn, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
            np_ = [cur[0][i] + (p[i] * weight if p else 0) for i in range(3)]
            nr_ = [cur[1][i] + (r[i] * weight if r else 0) for i in range(3)]
            ns_ = [cur[2][i] * (s[i] if s else 1) for i in range(3)]
            vals[bn] = (np_, nr_, ns_)

    for entry in att["scripts"]["animate"]:
        if isinstance(entry, str):
            if entry in ("actions", "fire_ctrl"):
                continue
            apply(entry, 1.0, t)
        else:
            (k, expr), = entry.items()
            w = mol.num(mol.run(expr))
            if w > 0:
                apply(k, w, t)
    if clip:
        apply(clip, 1.0, t)
    return vals, mol


def fp_item_frame():
    """Marco de rightItem en el espacio del cuerpo (pose vanilla de 1a persona)."""
    R_arm = R_bed(95.0, -45.0, 115.0)
    p = np.array([-5.0, 22.0, 0.0]) + np.array([13.5, -10.0, 12.0]) + R_arm @ np.array([-1.0, -7.0, 0.0])
    return M4(R_arm, p)


def render(gun, clip=None, t=0.0, state=None, w=640, h=360, title=None):
    geo = json.load(open(os.path.join(RP, "models", "entity", gun + ".geo.json")))["minecraft:geometry"][0]
    tex = np.asarray(Image.open(os.path.join(RP, "textures", "fps", "guns", gun + ".png")).convert("RGBA"), np.float32) / 255.0
    TW, TH = geo["description"]["texture_width"], geo["description"]["texture_height"]
    vals, mol = evaluate(gun, clip, t, state)
    mats = bone_world(geo["bones"], vals)
    eye = np.array([0.0, 27.65, 0.0])
    item = fp_item_frame()
    # camara: espacio cuerpo B (mira a +Z) -> vista (m, mira a -Z)
    to_view = np.diag([1.0 / S_PX, 1.0 / S_PX, -1.0 / S_PX, 1.0]) @ M4(t=-eye)
    cam = preview.Camera(w, h, fov=70)
    rs = preview.Raster(w, h, bg=(120, 150, 185))
    faces = {"west": ((0, 2, 6, 4), (-1, 0, 0)), "east": ((1, 5, 7, 3), (1, 0, 0)), "down": ((0, 4, 5, 1), (0, -1, 0)),
             "up": ((2, 3, 7, 6), (0, 1, 0)), "north": ((0, 1, 3, 2), (0, 0, -1)), "south": ((4, 6, 7, 5), (0, 0, 1))}
    for b in geo["bones"]:
        M = to_view @ item @ mats[b["name"]]
        for c in b.get("cubes", []):
            o = np.array(c["origin"], float)
            s = np.array(c["size"], float)
            corners = np.array([[o[0] + (s[0] if i & 1 else 0), o[1] + (s[1] if i & 2 else 0), o[2] + (s[2] if i & 4 else 0)]
                                for i in range(8)])
            if "rotation" in c:
                pv = np.array(c["pivot"], float)
                Rc = R_bed(*c["rotation"])
                corners = (Rc @ (corners - pv).T).T + pv
            Pv = (M @ np.c_[corners, np.ones(8)].T).T[:, :3]
            for fname, (idx, n) in faces.items():
                fuv = c["uv"].get(fname)
                if not fuv:
                    continue
                P = Pv[list(idx)]
                if (P[:, 2] > -0.03).any():
                    continue
                nn = M[:3, :3] @ (Rc @ np.array(n, float) if "rotation" in c else np.array(n, float))
                nn /= (np.linalg.norm(nn) + 1e-9)
                u0, v0 = fuv["uv"]
                du, dv = fuv["uv_size"]
                uv = np.array([[u0, v0 + dv], [u0 + du, v0 + dv], [u0 + du, v0], [u0, v0]]) / [TW, TH]
                lit = preview.shade(nn[None, :])[0]
                col = np.full((4, 3), lit)
                sp, wz = cam.project(P)
                for tri in ((0, 1, 2), (0, 2, 3)):
                    tt = list(tri)
                    rs.tri(sp[tt], wz[tt], uv[tt], col[tt], tex)
    img = rs.image()
    if title:
        from PIL import ImageDraw
        ImageDraw.Draw(img).text((6, 4), title, fill=(255, 255, 255))
    return img


if __name__ == "__main__":
    gun = sys.argv[1]
    outdir = os.path.join(os.path.dirname(HERE), "out")
    os.makedirs(outdir, exist_ok=True)
    ims = [render(gun, title="cadera (Bedrock)"), render(gun, state={"sneak": 1.0}, title="ADS (agachado)"),
           render(gun, state={"sprint": 1.0}, title="carrera")]
    if len(sys.argv) > 2:
        ims.append(render(gun, clip=sys.argv[2], t=float(sys.argv[3]) if len(sys.argv) > 3 else 0.5, title=sys.argv[2]))
    W, H = ims[0].size
    sheet = Image.new("RGB", (W * 2, H * ((len(ims) + 1) // 2)))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % 2) * W, (i // 2) * H))
    p = os.path.join(outdir, f"bedrock_{gun}.png")
    sheet.save(p)
    print(p)
