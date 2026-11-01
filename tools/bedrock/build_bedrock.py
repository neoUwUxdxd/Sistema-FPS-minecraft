"""
Genera el add-on de Bedrock (Behavior Pack + Resource Pack) a partir de los mismos
modelos, animaciones, texturas y sonidos del mod de Java.

Uso:  python3 tools/bedrock/build_bedrock.py
Salida: bedrock/FPS_Realista_BP, bedrock/FPS_Realista_RP y dist/FPS_Realista.mcaddon

Convenciones (derivadas de la geometria vanilla de Bedrock: frente -Z, brazo derecho en -X,
y valores de rotacion identicos a los de Java con el eje Y invertido):
  posicion   (x, y, z) del modelo  ->  (-x, y, z) * escala
  rotacion   (a, b, c) del modelo  ->  (-a, -b, c)      (orden X, luego Y, luego Z)
"""
import json
import math
import os
import random
import shutil
import sys
import zipfile
import zlib

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import animlib  # noqa: E402
import cubes  # noqa: E402
import fpview  # noqa: E402
import gunlib  # noqa: E402
import preview  # noqa: E402
from tuning import FP_TUNING, TP_TUNING  # noqa: E402

JAVA_ASSETS = os.path.join(REPO, "src", "main", "resources", "assets", "fpsrealista")
OUT = os.path.join(REPO, "bedrock")
BP = os.path.join(OUT, "FPS_Realista_BP")
RP = os.path.join(OUT, "FPS_Realista_RP")
DIST = os.path.join(REPO, "dist")
NS = "fps"

S_PX = 16.0 / 0.9375          # px de modelo por metro (el jugador se dibuja a escala 0.9375)
K = S_PX * 0.01               # px por cm del modelo del arma
D = 8.0                       # densidad de textura del atlas (px por cm)
SW = 128                      # tamano de cada muestra de material en el atlas
FPS = 30.0                    # muestreo de animaciones

VERSION = [1, 0, 0]
MIN_ENGINE = [1, 21, 130]
SCRIPT_API = "2.4.0"

GUNS = ["pistol_9mm", "carbine_556", "rifle_762", "shotgun_12g", "sniper_308"]
NAMES = {
    "pistol_9mm": ("Pistola 9 mm", "9mm Pistol"),
    "carbine_556": ("Carabina táctica 5,56", "5.56 Tactical Carbine"),
    "rifle_762": ("Fusil de asalto 7,62", "7.62 Assault Rifle"),
    "shotgun_12g": ("Escopeta de corredera cal. 12", "12 Gauge Pump Shotgun"),
    "sniper_308": ("Rifle de precisión .308", ".308 Precision Rifle"),
}
AMMO = {
    "ammo_9mm": ("Cartuchos 9×19 mm", "9x19mm Rounds"),
    "ammo_556": ("Cartuchos 5,56×45 mm", "5.56x45mm Rounds"),
    "ammo_762": ("Cartuchos 7,62×39 mm", "7.62x39mm Rounds"),
    "ammo_12g": ("Cartuchos del calibre 12", "12 Gauge Shells"),
    "ammo_308": ("Cartuchos .308 Win", ".308 Win Rounds"),
    "gun_parts": ("Piezas de arma", "Gun Parts"),
}
CASING = {"pistol_9mm": "casing_pistol", "carbine_556": "casing_rifle", "rifle_762": "casing_rifle",
          "shotgun_12g": "casing_shell", "sniper_308": "casing_rifle"}
ADS_TIME = {"pistol_9mm": 0.16, "carbine_556": 0.24, "rifle_762": 0.27, "shotgun_12g": 0.26, "sniper_308": 0.38}
KICK = {"pistol_9mm": 1.0, "carbine_556": 1.0, "rifle_762": 1.25, "shotgun_12g": 2.4, "sniper_308": 2.8}
SCOPED = {"sniper_308"}


# =============================================================================
# Utilidades de conversion
# =============================================================================
def r6(x):
    return float(round(float(x), 5))


def cp(p, k=K):
    return [r6(-p[0] * k), r6(p[1] * k), r6(p[2] * k)]


def cr(r):
    return [r6(-r[0]), r6(-r[1]), r6(r[2])]


def euler_of(R):
    return cubes.euler(R)


def bedrock_values_from_Bspace(R):
    """Valores de rotacion de Bedrock para una matriz expresada directamente en el espacio de Bedrock.
    Bedrock aplica R = Rz(-c) Ry(b) Rx(-a)."""
    a, b, c = euler_of(R)
    return [r6(-a), r6(b), r6(-c)]


def R_bed(a, b, c):
    """Matriz (espacio Bedrock) de unos valores de rotacion de Bedrock."""
    return gunlib.rot_matrix(-a, b, -c)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


# =============================================================================
# Atlas de texturas por arma
# =============================================================================
def load_mats():
    with open(os.path.join(JAVA_ASSETS, "gunmodels", "materials.json")) as f:
        return json.load(f)


MATS = load_mats()
_TILE = {}


def tile(mat):
    if mat not in _TILE:
        path = MATS[mat]["texture"].split(":", 1)[1]
        _TILE[mat] = Image.open(os.path.join(JAVA_ASSETS, path)).convert("RGBA")
    return _TILE[mat]


def hex_rgba(h):
    if not h:
        return (255, 255, 255, 255)
    h = h.lstrip("#")
    v = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
    return tuple(v + [255] * (4 - len(v)))


def make_swatch(mat, tint):
    m = MATS[mat]
    tpx = max(8, int(round(m["scale"] * D)))
    t = tile(mat).resize((tpx, tpx), Image.LANCZOS)
    sw = Image.new("RGBA", (SW, SW))
    for y in range(0, SW, tpx):
        for x in range(0, SW, tpx):
            sw.paste(t, (x, y))
    arr = np.asarray(sw, np.float32)
    tr = np.array(hex_rgba(tint), np.float32) / 255.0
    arr[..., :3] *= tr[:3]
    if m["type"] == "emissive":
        arr[..., :3] = np.array(hex_rgba(tint)[:3], np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def fabric_swatch(base, seed):
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((SW, SW))
    y, x = np.mgrid[0:SW, 0:SW]
    weave = (np.sin(x * 1.6) * np.sin(y * 1.6)) * 0.05
    camo = np.zeros((SW, SW))
    for _ in range(14):
        cx, cy, r = rng.uniform(0, SW), rng.uniform(0, SW), rng.uniform(8, 26)
        camo += np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (r * r))) * rng.uniform(-0.25, 0.25)
    h = weave + camo + n * 0.04
    rgb = np.array(base, np.float32)[None, None, :] * (1 + h[..., None])
    a = np.full((SW, SW, 1), 255.0)
    return Image.fromarray(np.clip(np.concatenate([rgb, a], -1), 0, 255).astype(np.uint8), "RGBA")


def glove_swatch():
    rng = np.random.default_rng(77)
    n = rng.standard_normal((SW, SW)) * 0.05
    y, x = np.mgrid[0:SW, 0:SW]
    stitch = ((x % 32) < 1) * 0.15
    rgb = np.array((52, 52, 55), np.float32)[None, None, :] * (1 + n[..., None] + stitch[..., None])
    a = np.full((SW, SW, 1), 255.0)
    return Image.fromarray(np.clip(np.concatenate([rgb, a], -1), 0, 255).astype(np.uint8), "RGBA")


class Atlas:
    def __init__(self):
        self.slots = {}      # key -> (x, y, w, h)
        self.images = []     # (key, image)
        self.cursor = [0, 0, 0]  # x, y, row height
        self.width = 1024

    def add(self, key, img):
        if key in self.slots:
            return self.slots[key]
        w, h = img.size
        x, y, rh = self.cursor
        if x + w > self.width:
            x, y, rh = 0, y + rh, 0
        self.slots[key] = (x, y, w, h)
        self.images.append((key, img))
        self.cursor = [x + w, y, max(rh, h)]
        return self.slots[key]

    def build(self):
        hgt = self.cursor[1] + self.cursor[2]
        H = 1
        while H < hgt:
            H *= 2
        out = Image.new("RGBA", (self.width, H))
        for key, img in self.images:
            x, y, w, h = self.slots[key]
            out.paste(img, (x, y))
        return out


# =============================================================================
# Brazos tacticos (manga + guante) en el espacio local del brazo de Minecraft
# =============================================================================
def arm_boxes(side):
    """Cajas en unidades de 1/16 de bloque, eje Y del brazo (mano en y=10)."""
    if side == "right":
        x0, x1 = -3.0, 1.0
    else:
        x0, x1 = -1.0, 3.0
    return [
        ("sleeve", (x0, -24.0, -2.0), (x1, 6.0, 2.0)),
        ("sleeve", (x0 - 0.25, 5.2, -2.25), (x1 + 0.25, 6.4, 2.25)),   # puno
        ("glove", (x0 + 0.1, 6.2, -1.9), (x1 - 0.1, 10.0, 1.9)),
        ("glove", (x0 + 0.4, 8.4, -2.1), (x1 - 0.4, 9.7, -1.85)),      # protector de nudillos
        ("glove", (x0 + 0.2, 9.4, -1.6), (x1 - 0.2, 10.6, 1.4)),       # dedos
    ]


# =============================================================================
# Geometria
# =============================================================================
def face_uv(atlas_slot, wcm, hcm, rnd):
    x, y, w, h = atlas_slot
    pw = max(0.5, min(w - 2.0, wcm * D))
    ph = max(0.5, min(h - 2.0, hcm * D))
    ox = x + 1 + rnd.random() * max(0.0, w - 2 - pw)
    oy = y + 1 + rnd.random() * max(0.0, h - 2 - ph)
    return {"uv": [r6(ox), r6(oy)], "uv_size": [r6(pw), r6(ph)]}


def bedrock_cube(cb, atlas, slot_key, rnd, decal_slot=None, transparent_slot=None):
    lo, hi = cb["lo"], cb["hi"]
    size = [hi[i] - lo[i] for i in range(3)]
    origin = [-hi[0] * K, lo[1] * K, lo[2] * K]
    c = {"origin": [r6(v) for v in origin], "size": [r6(s * K) for s in size]}
    if cb["rot"] is not None:
        c["pivot"] = cp(cb["pivot"])
        c["rotation"] = cr(cb["rot"])
    slot = atlas.slots[slot_key]
    sx, sy, sz = size
    faces = {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}
    uv = {}
    for name, (w, h) in faces.items():
        uv[name] = face_uv(slot, w, h, rnd)
    if cb.get("decal_uv"):
        du = cb["decal_uv"]
        dx, dy, dw, dh = decal_slot
        u0, v0, u1, v1 = du["uv"]
        rect = {"uv": [r6(dx + u0 * dw), r6(dy + v0 * dh)], "uv_size": [r6((u1 - u0) * dw), r6((v1 - v0) * dh)]}
        ax = du["axis"]
        tx, ty, _, _ = transparent_slot
        blank = {"uv": [tx, ty], "uv_size": [1, 1]}
        for name in uv:
            uv[name] = blank
        if ax == 0:
            uv["east"] = rect
            uv["west"] = rect
        elif ax == 1:
            uv["up"] = rect
            uv["down"] = rect
        else:
            uv["north"] = rect
            uv["south"] = rect
    c["uv"] = uv
    return c


def build_geometry(gun, mj, atlas, rnd, arm_geo):
    cbs = cubes.model_cubes(mj)
    rest = preview.bone_matrices(mj)
    locs = mj["locators"]
    piv = fpview.loc_world(mj, rest, np.eye(4), "pivot")

    # muestras del atlas
    for lst in cbs.values():
        for cb in lst:
            key = (cb["mat"], cb.get("tint"))
            if MATS[cb["mat"]]["type"] in ("decal", "emissive_decal"):
                continue
            if key not in atlas.slots:
                atlas.add(key, make_swatch(cb["mat"], cb.get("tint")))
    marking = Image.open(os.path.join(JAVA_ASSETS, "textures", "gun", "marking.png")).convert("RGBA").resize((128, 32))
    reticle = Image.open(os.path.join(JAVA_ASSETS, "textures", "gun", "reticle_dot.png")).convert("RGBA").resize((32, 32))
    atlas.add("decal:marking", marking)
    atlas.add("decal:reticle_dot", reticle)
    atlas.add("transparent", Image.new("RGBA", (4, 4)))
    atlas.add(("sleeve", None), fabric_swatch((128, 118, 88), 5))
    atlas.add(("glove", None), glove_swatch())
    if gun in SCOPED:
        sc = Image.open(os.path.join(JAVA_ASSETS, "textures", "gui", "scope_overlay.png")).convert("RGBA").resize((256, 256))
        atlas.add("scope", sc)

    bones = [
        {"name": "root", "pivot": [0, 0, 0], "binding": "q.item_slot_to_bone_name(c.item_slot)"},
        {"name": "place", "parent": "root", "pivot": [0, 0, 0]},
        {"name": "kick", "parent": "place", "pivot": cp(piv)},
        {"name": "gun_anim", "parent": "kick", "pivot": cp(piv)},
    ]
    for b in mj["bones"]:
        parent = b["parent"] or "gun_anim"
        bone = {"name": b["name"], "parent": parent, "pivot": cp(b["pivot"])}
        normal, glass = [], []
        for cb in cbs[b["name"]]:
            mt = MATS[cb["mat"]]["type"]
            if mt in ("decal", "emissive_decal"):
                normal.append(bedrock_cube(cb, atlas, "transparent", rnd, atlas.slots["decal:" + cb["mat"]],
                                           atlas.slots["transparent"]))
            elif mt == "translucent":
                glass.append(bedrock_cube(cb, atlas, (cb["mat"], cb.get("tint")), rnd))
            else:
                normal.append(bedrock_cube(cb, atlas, (cb["mat"], cb.get("tint")), rnd))
        bone["cubes"] = normal
        bl = {}
        for ln, l in locs.items():
            if l["bone"] == b["name"] and ln in ("muzzle", "eject"):
                bl[ln] = cp(l["pos"])
        if bl:
            bone["locators"] = bl
        bones.append(bone)
        if glass:
            bones.append({"name": "glass_" + b["name"], "parent": b["name"], "pivot": cp(b["pivot"]), "cubes": glass})

    # brazos
    for side in ("right", "left"):
        sw_cm = arm_geo["sw"] / 0.01 / 16.0
        sl_cm = arm_geo["sl"] / 0.01 / 16.0
        cl = []
        for (kind, a, b) in arm_boxes(side):
            lo = [a[0] * sw_cm, a[1] * sl_cm, a[2] * sw_cm]
            hi = [b[0] * sw_cm, b[1] * sl_cm, b[2] * sw_cm]
            cl.append(bedrock_cube({"lo": lo, "hi": hi, "rot": None}, atlas, (kind, None), rnd))
        bones.append({"name": "arm_" + side[0], "parent": "gun_anim", "pivot": [0, 0, 0], "cubes": cl})

    if gun in SCOPED:
        # overlay de mira telescopica fijado a la camara (espacio de vista)
        z = -0.12 * S_PX
        half = 0.16 * S_PX
        sx, sy, w, h = atlas.slots["scope"]
        bones.append({"name": "scope_view", "parent": "root", "pivot": [0, 0, 0], "cubes": [{
            "origin": [r6(-half), r6(-half), r6(z)], "size": [r6(2 * half), r6(2 * half), 0],
            "uv": {"north": {"uv": [sx, sy], "uv_size": [w, h]}, "south": {"uv": [sx, sy], "uv_size": [w, h]}}}]})
        # cortinas negras para tapar fuera del circulo con pantallas anchas
        tx, ty, _, _ = atlas.slots[("bore", None)] if ("bore", None) in atlas.slots else atlas.slots["transparent"]
        for sgn in (-1, 1):
            bones[-1]["cubes"].append({
                "origin": [r6(sgn * half if sgn > 0 else -half * 4), r6(-half * 2), r6(z)],
                "size": [r6(half * 3), r6(half * 4), 0],
                "uv": {"north": {"uv": [tx + 1, ty + 1], "uv_size": [1, 1]}, "south": {"uv": [tx + 1, ty + 1], "uv_size": [1, 1]}}})
    return bones


# =============================================================================
# Transformaciones de primera y tercera persona
# =============================================================================
def fp_root():
    """Transformacion del hueso raiz (unido a rightItem) que pone el espacio de vista en su sitio.
    Pose vanilla del brazo en 1a persona: animation.player.first_person.empty_hand."""
    t = FP_TUNING
    R_arm = R_bed(95.0, -45.0, 115.0)
    p = np.array([-5.0, 22.0, 0.0]) + np.array([13.5, -10.0, 12.0]) + R_arm @ np.array([-1.0, -7.0, 0.0])
    eye = np.array([0.0, t["eye_height_px"], 0.0])
    Ry180 = gunlib.rot_matrix(0, 180, 0)
    R_root = R_arm.T @ Ry180
    off = R_arm.T @ (eye - p)
    return off, bedrock_values_from_Bspace(R_root)


def tp_root(mj):
    t = TP_TUNING
    R_arm = R_bed(*t["arm_rot"])
    rest = preview.bone_matrices(mj)
    rh = fpview.loc_world(mj, rest, np.eye(4), "rh")
    rh_u = np.array(cp(rh))
    k = t["scale"]
    off = -R_arm.T @ (rh_u * k) + R_arm.T @ np.array(t["hand_offset_px"])
    return off, bedrock_values_from_Bspace(R_arm.T), k


# =============================================================================
# Animaciones
# =============================================================================
def view_place(mj, ads, sprint=0.0):
    v = mj["view"]
    rest = preview.bone_matrices(mj)
    aim = fpview.loc_world(mj, rest, np.eye(4), "aim")
    ads_pos = np.array([0, 0, -v["eye_relief"]]) - aim * 0.01
    pos = fpview.lerp(v["hip"]["pos"], ads_pos, ads)
    rot = fpview.lerp(v["hip"]["rot"], (0, 0, 0), ads)
    pos = fpview.lerp(pos, v["sprint"]["pos"], sprint)
    rot = fpview.lerp(rot, v["sprint"]["rot"], sprint)
    return np.array(pos, float), np.array(rot, float)


def arm_transforms(mj, ads, gun_pose, pose, ik):
    """Transformaciones (pos cm, rot grados) de los huesos de brazo relativas a gun_anim."""
    v = mj["view"]
    pos, rot = view_place(mj, ads)
    rest = preview.bone_matrices(mj)
    piv = fpview.loc_world(mj, rest, np.eye(4), "pivot")
    Pf = preview.T(pos) @ preview.R(*rot) @ preview.S(0.01)
    ap, ar = gun_pose
    A = preview.T(piv) @ preview.T(ap) @ preview.R(*ar) @ preview.T(-piv)
    M = Pf @ A
    mats = preview.bone_matrices(mj, pose)
    Minv = np.linalg.inv(M)
    res = {}
    arms = v["arms"]
    for side, restloc, key in (("right", "rh", "right_hand"), ("left", "lh", "left_hand")):
        hand = fpview.loc_world(mj, mats, M, restloc)
        if key in ik:
            tgt, w = ik[key]
            if tgt in mj["locators"]:
                hand = fpview.lerp(hand, fpview.loc_world(mj, mats, M, tgt), w)
        a = arms[side]
        anchor = fpview.lerp(a["anchor"], a.get("anchor_ads", a["anchor"]), ads)
        AM = fpview.arm_matrix(np.array(hand, float), np.array(anchor, float), side, a["twist"], arms["scale_w"], arms["scale_l"])
        AG = Minv @ AM
        L = AG[:3, :3] @ np.diag([1.0 / (arms["scale_w"] / 0.01), 1.0 / (arms["scale_l"] / 0.01), 1.0 / (arms["scale_w"] / 0.01)])
        # ortonormalizar
        u, _, vt = np.linalg.svd(L)
        Rm = u @ vt
        res[side] = (AG[:3, 3], euler_of(Rm))
    return res


def keyframes(samples, tol=0.004):
    """samples: [(t, [x,y,z])] -> fotogramas clave lineales, quitando puntos intermedios colineales."""
    if len(samples) <= 2:
        return {f"{r6(t):g}": [r6(x) for x in v] for (t, v) in samples}
    out = [samples[0]]
    for i in range(1, len(samples) - 1):
        t0, v0 = out[-1]
        t, v = samples[i]
        t1, v1 = samples[i + 1]
        f = (t - t0) / (t1 - t0) if t1 > t0 else 0
        pred = [v0[k] + (v1[k] - v0[k]) * f for k in range(3)]
        if max(abs(pred[k] - v[k]) for k in range(3)) > tol:
            out.append((t, v))
    out.append(samples[-1])
    return {f"{r6(t):g}": [r6(x) for x in v] for (t, v) in out}


def convert_clip(gun, mj, name, clip):
    L = clip["length"]
    n = max(2, int(math.ceil(L * FPS)) + 1)
    times = [min(L, i / FPS) for i in range(n)]
    if times[-1] < L:
        times.append(L)
    bones_pos, bones_rot, bones_scale = {}, {}, {}
    model_bones = {b["name"] for b in mj["bones"]}
    hidden = set(mj.get("hidden", []))
    for t in times:
        pose, ik, vis = animlib.sample_clip(clip, t)
        gp = pose.get("gun", ((0, 0, 0), (0, 0, 0)))
        for bn, (pp, rr) in pose.items():
            target = "gun_anim" if bn == "gun" else bn
            if target != "gun_anim" and target not in model_bones:
                continue
            bones_pos.setdefault(target, []).append((t, cp(pp)))
            bones_rot.setdefault(target, []).append((t, cr(rr)))
        for bn in hidden | set(vis.keys()):
            if bn in model_bones:
                on = vis.get(bn, bn not in hidden)
                bones_scale.setdefault(bn, []).append((t, [1.0, 1.0, 1.0] if on else [0.0, 0.0, 0.0]))
        poses = {k: v for k, v in pose.items() if k != "gun"}
        arms = arm_transforms(mj, 0.0, gp, poses, ik)
        for side, (tp, er) in arms.items():
            bn = "arm_" + side[0]
            bones_pos.setdefault(bn, []).append((t, cp(tp)))
            bones_rot.setdefault(bn, []).append((t, cr(er)))
    bones = {}
    for bn in set(bones_pos) | set(bones_scale):
        d = {}
        if bn in bones_pos:
            d["position"] = keyframes(bones_pos[bn])
            d["rotation"] = keyframes(bones_rot[bn])
        if bn in bones_scale:
            d["scale"] = {f"{r6(t):g}": v for (t, v) in bones_scale[bn]}
        bones[bn] = d
    anim = {"animation_length": r6(L), "bones": bones}
    snd, part = {}, {}
    for (t, ev) in clip.get("sounds", []):
        key = f"{r6(t):g}"
        if ev == "!eject":
            part.setdefault(key, []).append({"effect": "casing", "locator": "eject"})
        elif not ev.startswith("!"):
            snd.setdefault(key, []).append({"effect": ev.split(":", 1)[1]})
    if name == "fire":
        part.setdefault("0", []).append({"effect": "flash", "locator": "muzzle"})
        part.setdefault("0", []).append({"effect": "smoke", "locator": "muzzle"})
    if snd:
        anim["sound_effects"] = {k: (v[0] if len(v) == 1 else v) for k, v in snd.items()}
    if part:
        anim["particle_effects"] = {k: (v[0] if len(v) == 1 else v) for k, v in part.items()}
    return anim, sorted({ev.split(":", 1)[1] for (_, ev) in clip.get("sounds", []) if not ev.startswith("!")})


def fm(x):
    """Numero para Molang sin notacion exponencial."""
    t = f"{float(x):.5f}".rstrip("0").rstrip(".")
    return "0" if t in ("", "-0") else t


def lerp_expr(h, a, s=None):
    """Expresion Molang hip->ads (v.e) y -> carrera (v.se)."""
    e = f"({fm(h)} + ({fm(a)} - {fm(h)}) * v.e)"
    if s is not None:
        e = f"({e} * (1 - v.se) + {fm(s)} * v.se)"
    return e


def procedural_anims(gun, mj, fp_off, fp_rot, tp_off, tp_rot, tp_scale):
    hip_p, hip_r = view_place(mj, 0.0)
    ads_p, ads_r = view_place(mj, 1.0)
    spr_p, spr_r = view_place(mj, 0.0, 1.0)
    hp, ap_, sp = cp(hip_p, S_PX), cp(ads_p, S_PX), cp(spr_p, S_PX)
    hr, ar_, sr = cr(hip_r), cr(ads_r), cr(spr_r)
    place_pos = []
    place_rot = []
    breath = ["math.sin(q.life_time * 63) * 0.025 * (1 - v.e * 0.7)", "math.sin(q.life_time * 126) * 0.018 * (1 - v.e * 0.7)", "0"]
    for i in range(3):
        place_pos.append(f"c.is_first_person ? ({lerp_expr(hp[i], ap_[i], sp[i])} + {breath[i]}) : 0")
        place_rot.append(f"c.is_first_person ? {lerp_expr(hr[i], ar_[i], sr[i])} : 0")
    root = {
        "position": [f"c.is_first_person ? {fm(fp_off[i])} : {fm(tp_off[i])}" for i in range(3)],
        "rotation": [f"c.is_first_person ? {fm(fp_rot[i])} : {fm(tp_rot[i])}" for i in range(3)],
        "scale": f"c.is_first_person ? 1 : {fm(tp_scale)}",
    }
    bones = {
        "root": root,
        "place": {"position": place_pos, "rotation": place_rot},
        "kick": {"position": [0, 0, f"v.kb * 0.6 * {fm(S_PX)}"],
                 "rotation": ["-v.kp", "-v.ky", "v.kr"]},
        "arm_r": {"scale": "c.is_first_person ? 1 : 0"},
        "arm_l": {"scale": "c.is_first_person ? 1 : 0"},
    }
    if gun in SCOPED:
        bones["kick"]["scale"] = "v.scoped ? 0 : 1"
        bones["scope_view"] = {"scale": "v.scoped ? 1 : 0"}
    names = {b["name"] for b in mj["bones"]}
    if "selector" in names:
        bones["selector"] = {"rotation": ["q.property('fps:mode') * 40", 0, 0]}
    for hb in mj.get("hidden", []):
        bones[hb] = {"scale": "(v.clip ?? 0) ? 1 : 0"}
    proc = {"loop": True, "bones": bones}

    # brazos en reposo: interpolacion cadera <-> apuntado
    none = ((0, 0, 0), (0, 0, 0))
    h = arm_transforms(mj, 0.0, none, {}, {})
    a = arm_transforms(mj, 1.0, none, {}, {})
    arms = {"loop": True, "bones": {}}
    for side in ("right", "left"):
        hp_, hr_ = cp(h[side][0]), cr(h[side][1])
        ap2, ar2 = cp(a[side][0]), cr(a[side][1])
        arms["bones"]["arm_" + side[0]] = {
            "position": [lerp_expr(hp_[i], ap2[i]) for i in range(3)],
            "rotation": [lerp_expr(hr_[i], ar2[i]) for i in range(3)],
        }
    empty = None
    if mj.get("empty_pose"):
        empty = {"loop": True, "bones": {bn: {"position": cp(v)} for bn, v in mj["empty_pose"].items()}}
    return proc, arms, empty


def pre_animation(gun):
    ads = ADS_TIME[gun]
    kick = KICK[gun]
    lines = [
        "v.dt = math.clamp(q.delta_time, 0, 0.05);",
        "v.busy = v.clip ?? 0;",
        f"v.ads = math.clamp((v.ads ?? 0) + ((q.is_sneaking && !v.busy && !q.is_sprinting) ? v.dt / {ads} : -v.dt * 1.3 / {ads}), 0, 1);",
        "v.e = v.ads * v.ads * (3 - 2 * v.ads);",
        "v.spr = math.clamp((v.spr ?? 0) + ((q.is_sprinting && v.ads < 0.1 && !v.busy) ? v.dt * 5 : -v.dt * 6), 0, 1);",
        "v.se = v.spr * v.spr * (3 - 2 * v.spr);",
        "v.shot = q.property('fps:shot');",
        "v.trig = (v.ready ?? 0) && ((v.last_shot ?? 0) != v.shot);",
        "v.last_shot = v.shot;",
        "v.ready = 1;",
        f"v.kf = {kick} * (1 - 0.45 * v.e);",
        # muelles de retroceso (Euler semi-implicito)
        "v.kbv = (v.kbv ?? 0) + (v.trig ? 1.1 * v.kf : 0);",
        "v.kbv = v.kbv + (-260 * (v.kb ?? 0) - 17.7 * v.kbv) * v.dt;",
        "v.kb = (v.kb ?? 0) + v.kbv * v.dt;",
        "v.kpv = (v.kpv ?? 0) + (v.trig ? 70 * v.kf * math.random(0.8, 1.2) : 0);",
        "v.kpv = v.kpv + (-220 * (v.kp ?? 0) - 13.3 * v.kpv) * v.dt;",
        "v.kp = (v.kp ?? 0) + v.kpv * v.dt;",
        "v.kyv = (v.kyv ?? 0) + (v.trig ? 25 * v.kf * math.random(-1, 1) : 0);",
        "v.kyv = v.kyv + (-200 * (v.ky ?? 0) - 14.1 * v.kyv) * v.dt;",
        "v.ky = (v.ky ?? 0) + v.kyv * v.dt;",
        "v.krv = (v.krv ?? 0) + (v.trig ? 45 * v.kf * math.random(-1, 1) : 0);",
        "v.krv = v.krv + (-180 * (v.kr ?? 0) - 10.7 * v.krv) * v.dt;",
        "v.kr = (v.kr ?? 0) + v.krv * v.dt;",
        f"v.scoped = {'c.is_first_person && v.e > 0.92' if gun in SCOPED else '0'};",
    ]
    return lines


ACTIONS = [
    # (estado, codigo de fps:anim, clip)
    ("draw", 1, "draw"), ("reload", 2, "reload"), ("reload_empty", 3, "reload_empty"), ("inspect", 4, "inspect"),
    ("cycle", 5, "cycle"), ("shell_start", 6, "reload_start"), ("shell_loop", 7, "reload_loop"),
    ("shell_end", 8, "reload_end"),
]


def controllers(gun, clips):
    states = {"default": {"on_entry": ["v.clip = 0;"], "transitions": []}}
    for (state, code, clipname) in ACTIONS:
        an = clipname if clipname != "cycle" else None
        if clipname == "cycle":
            an = "pump" if "pump" in clips else ("bolt" if "bolt" in clips else None)
        if an is None or an not in clips:
            continue
        states["default"]["transitions"].append(
            {state: f"q.property('fps:anim') == {code} && q.property('fps:seq') != (v.seq ?? 0)"})
        states[state] = {
            "animations": [an],
            "on_entry": ["v.clip = 1;", "v.seq = q.property('fps:seq');"],
            "transitions": [{"default": "q.all_animations_finished || q.property('fps:seq') != v.seq"}],
            "blend_transition": 0.08,
        }
    act = {"initial_state": "default", "states": states}
    fire = {"initial_state": "init", "states": {
        "init": {"transitions": [{"w0": "q.property('fps:shot') == 0"}, {"w1": "q.property('fps:shot') == 1"}]},
        "w0": {"transitions": [{"f1": "q.property('fps:shot') == 1"}]},
        "w1": {"transitions": [{"f0": "q.property('fps:shot') == 0"}]},
        "f0": {"animations": ["fire"], "transitions": [{"f1": "q.property('fps:shot') == 1"}]},
        "f1": {"animations": ["fire"], "transitions": [{"f0": "q.property('fps:shot') == 0"}]},
    }}
    return {
        f"controller.animation.{NS}.{gun}.actions": act,
        f"controller.animation.{NS}.{gun}.fire": fire,
    }


# =============================================================================
# Iconos
# =============================================================================
def render_icon(mj, size=128):
    mesh = gunlib.mesh_from_json(mj)
    lo, hi = preview.model_bounds(mj, mesh)
    c = (lo + hi) / 2
    L = (hi - lo).max()
    S = size * 2
    cam = preview.Camera(S, S, ortho=L * 0.52)
    rs = preview.Raster(S, S)
    view = preview.R(-30, 0, 0) @ preview.R(0, -90, 0) @ preview.R(0, 0, 0) @ preview.T(-c)
    view = preview.R(0, 0, 30) @ preview.R(0, -90, 0) @ preview.T(-c)
    preview.draw_mesh(rs, cam, mj, view, mesh)
    rgb = np.clip(rs.color, 0, 1)
    alpha = np.isfinite(rs.depth).astype(np.float32)
    rgb = rgb * 1.35  # los iconos se ven mejor algo mas claros
    img = Image.fromarray((np.dstack([np.clip(rgb, 0, 1), alpha]) * 255).astype(np.uint8), "RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    # contorno suave para que destaque en el inventario
    a = np.asarray(img)[..., 3].astype(np.float32)
    out = Image.new("RGBA", (size, size))
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sh = np.zeros((size, size, 4), np.uint8)
    sh[..., 3] = (np.clip(a, 0, 255) * 0.5).astype(np.uint8)
    shadow = Image.fromarray(sh, "RGBA")
    out.paste(shadow, (2, 2), shadow)
    out.alpha_composite(img)
    return out


# =============================================================================
# Ensamblado
# =============================================================================
def load_clips(gun):
    with open(os.path.join(JAVA_ASSETS, "gunanims", gun + ".json")) as f:
        return json.load(f)["clips"]


def build_gun(gun):
    mj = gunlib.load_model(os.path.join(JAVA_ASSETS, "gunmodels", gun + ".json"))
    clips = load_clips(gun)
    rnd = random.Random(zlib.crc32(gun.encode()))
    atlas = Atlas()
    arm_geo = {"sw": mj["view"]["arms"]["scale_w"], "sl": mj["view"]["arms"]["scale_l"]}
    bones = build_geometry(gun, mj, atlas, rnd, arm_geo)
    tex = atlas.build()
    tex_rel = f"textures/{NS}/guns/{gun}"
    os.makedirs(os.path.join(RP, os.path.dirname(tex_rel)), exist_ok=True)
    tex.save(os.path.join(RP, tex_rel + ".png"), optimize=True)
    geo_id = f"geometry.{NS}.{gun}"
    geo = {"format_version": "1.16.0", "minecraft:geometry": [{
        "description": {"identifier": geo_id, "texture_width": tex.size[0], "texture_height": tex.size[1],
                        "visible_bounds_width": 6, "visible_bounds_height": 4, "visible_bounds_offset": [0, 1, 0]},
        "bones": bones}]}
    write_json(os.path.join(RP, "models", "entity", f"{gun}.geo.json"), geo)

    fp_off, fp_rot = fp_root()
    tp_off, tp_rot, tp_scale = tp_root(mj)
    proc, arms_idle, empty = procedural_anims(gun, mj, fp_off, fp_rot, tp_off, tp_rot, tp_scale)
    anims = {f"animation.{NS}.{gun}.procedural": proc, f"animation.{NS}.{gun}.arms_idle": arms_idle}
    if empty:
        anims[f"animation.{NS}.{gun}.empty"] = empty
    sound_names = set()
    clip_keys = {}
    for name, clip in clips.items():
        a, sn = convert_clip(gun, mj, name, clip)
        anims[f"animation.{NS}.{gun}.{name}"] = a
        clip_keys[name] = f"animation.{NS}.{gun}.{name}"
        sound_names |= set(sn)
    write_json(os.path.join(RP, "animations", f"{gun}.animation.json"), {"format_version": "1.8.0", "animations": anims})
    ctrls = controllers(gun, clips)
    write_json(os.path.join(RP, "animation_controllers", f"{gun}.animation_controllers.json"),
               {"format_version": "1.10.0", "animation_controllers": ctrls})

    anim_refs = {"procedural": f"animation.{NS}.{gun}.procedural", "arms_idle": f"animation.{NS}.{gun}.arms_idle",
                 "actions": f"controller.animation.{NS}.{gun}.actions", "fire_ctrl": f"controller.animation.{NS}.{gun}.fire"}
    for name, key in clip_keys.items():
        anim_refs[name] = key
    if empty:
        anim_refs["empty"] = f"animation.{NS}.{gun}.empty"
    animate = ["procedural", {"arms_idle": "1 - (v.clip ?? 0)"}, "actions", "fire_ctrl"]
    if empty:
        animate.insert(2, {"empty": "q.property('fps:empty') * (1 - (v.clip ?? 0))"})
    att = {"format_version": "1.10.0", "minecraft:attachable": {"description": {
        "identifier": f"{NS}:{gun}",
        "item": {f"{NS}:{gun}": "query.is_owner_identifier_any('minecraft:player')"},
        "materials": {"default": "entity_alphatest", "glass": "entity_alphablend", "enchanted": "entity_alphatest_glint"},
        "textures": {"default": tex_rel, "enchanted": "textures/misc/enchanted_item_glint"},
        "geometry": {"default": geo_id},
        "animations": anim_refs,
        "scripts": {"pre_animation": pre_animation(gun), "animate": animate},
        "sound_effects": {s: f"{NS}.{s}" for s in sorted(sound_names)},
        "particle_effects": {"casing": f"{NS}:{CASING[gun]}", "flash": f"{NS}:muzzle_flash", "smoke": f"{NS}:muzzle_smoke"},
        "render_controllers": [f"controller.render.{NS}.gun"],
    }}}
    write_json(os.path.join(RP, "attachables", f"{gun}.json"), att)

    icon = render_icon(mj)
    icon.save(os.path.join(RP, "textures", NS, "items", gun + ".png"))
    ncubes = sum(len(b.get("cubes", [])) for b in bones)
    print(f"  {gun}: {ncubes} cubos, atlas {tex.size[0]}x{tex.size[1]}, {len(clips)} clips")
    return sound_names


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(RP, "textures", NS, "items"), exist_ok=True)
    print("Generando armas:")
    for g in GUNS:
        build_gun(g)
    import packs  # noqa: E402  (BP, partes comunes del RP y empaquetado)
    packs.build_all(sys.modules[__name__])


if __name__ == "__main__":
    main()
