"""
Vista previa en primera persona: reproduce la cadena de transformaciones de
com.fpsrealista.client.render.FirstPersonRenderer (posicion de cadera / ADS,
animacion del arma y brazos con IK) para ajustar poses y animaciones.

Uso:
  python3 tools/fpview.py <arma> [clip] [n_fotogramas]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import animlib  # noqa: E402
import gunlib  # noqa: E402
from preview import Camera, Raster, R, S, T, bone_matrices, draw_mesh, shade  # noqa: E402

ASSETS = os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "assets", "fpsrealista")
OUTDIR = os.path.join(os.path.dirname(__file__), "out")

# Brazos de Minecraft (unidades de bloque, espacio local del ModelPart)
ARM_W = 4 / 16.0


def lerp(a, b, t):
    return np.add(a, np.multiply(np.subtract(b, a), t))


def rotation_to(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -0.9999:
        return -np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def axis_angle(axis, ang):
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def gun_matrix(mj, ads=0.0, sprint=0.0, gun_pose=((0, 0, 0), (0, 0, 0)), proc_pos=(0, 0, 0), proc_rot=(0, 0, 0)):
    v = mj["view"]
    rest = bone_matrices(mj)
    aim = (rest[mj["locators"]["aim"]["bone"]] @ np.array([*mj["locators"]["aim"]["pos"], 1]))[:3]
    piv = (rest[mj["locators"]["pivot"]["bone"]] @ np.array([*mj["locators"]["pivot"]["pos"], 1]))[:3]
    ads_pos = np.array([0, 0, -v["eye_relief"]]) - aim * 0.01
    pos = lerp(v["hip"]["pos"], ads_pos, ads)
    rot = lerp(v["hip"]["rot"], (0, 0, 0), ads)
    pos = lerp(pos, v["sprint"]["pos"], sprint)
    rot = lerp(rot, v["sprint"]["rot"], sprint)
    ap, ar = gun_pose
    M = T(np.add(pos, proc_pos)) @ R(*rot) @ S(0.01) @ T(piv) @ R(*proc_rot) @ T(ap) @ R(*ar) @ T(-piv)
    return M


def arm_matrix(hand_pos, anchor, side, twist_deg, scale_w, scale_l, slim=False):
    """Coloca el brazo (ModelPart de Minecraft) con la mano en hand_pos apuntando desde anchor."""
    d = np.subtract(hand_pos, anchor)
    d = d / np.linalg.norm(d)
    Rm = axis_angle(d, math.radians(twist_deg)) @ rotation_to(np.array([0, 1.0, 0]), d)
    if side == "right":
        cx = -0.5 / 16 if slim else -1 / 16
    else:
        cx = 0.5 / 16 if slim else 1 / 16
    hand_local = np.array([cx, 10 / 16, 0])
    M = np.eye(4)
    M[:3, :3] = Rm @ np.diag([scale_w, scale_l, scale_w])
    M[:3, 3] = hand_pos - M[:3, :3] @ hand_local
    return M


def draw_arm(rs, cam, M, side, sleeve=(52, 78, 140), skin=(196, 150, 120)):
    x0, x1 = (-3 / 16, 1 / 16) if side == "right" else (-1 / 16, 3 / 16)
    lo = np.array([x0, -2 / 16, -2 / 16])
    hi = np.array([x1, 10 / 16, 2 / 16])
    # mano (piel) en el ultimo cuarto, manga el resto
    for (ya, yb, col) in ((lo[1], 6.5 / 16, sleeve), (6.5 / 16, hi[1], skin)):
        a = np.array([lo[0], ya, lo[2]])
        b = np.array([hi[0], yb, hi[2]])
        corners = np.array([[a[0] if i & 1 == 0 else b[0], a[1] if i & 2 == 0 else b[1], a[2] if i & 4 == 0 else b[2]]
                            for i in range(8)])
        faces = [((0, 2, 6, 4), (-1, 0, 0)), ((1, 5, 7, 3), (1, 0, 0)), ((0, 4, 5, 1), (0, -1, 0)),
                 ((2, 3, 7, 6), (0, 1, 0)), ((0, 1, 3, 2), (0, 0, -1)), ((4, 6, 7, 5), (0, 0, 1))]
        Pv = (M @ np.c_[corners, np.ones(8)].T).T[:, :3]
        for (f, n) in faces:
            P = Pv[list(f)]
            if (P[:, 2] > -0.02).any():
                continue
            nn = M[:3, :3] @ np.array(n, float)
            nn /= np.linalg.norm(nn)
            c = np.array(col) / 255.0
            # cara "frontal" (-Z local) un poco mas clara para ver la orientacion
            if n == (0, 0, -1):
                c = c * 1.15
            lit = shade(nn[None, :])[0]
            colv = np.tile(c * lit, (4, 1))
            sp, wz = cam.project(P)
            white = np.ones((2, 2, 4), np.float32)
            for tri in ((0, 1, 2), (0, 2, 3)):
                t = list(tri)
                rs.tri(sp[t], wz[t], np.zeros((3, 2)), colv[t], white)


def loc_world(mj, mats, M, name):
    loc = mj["locators"][name]
    return (M @ mats[loc["bone"]] @ np.array([*loc["pos"], 1.0]))[:3]


def render_fp(mj, mesh, w=640, h=360, ads=0.0, sprint=0.0, clip=None, t=0.0, title=None, hidden=()):
    v = mj["view"]
    pose, ik, vis = ({}, {}, {})
    if clip is not None:
        pose, ik, vis = animlib.sample_clip(clip, t)
    gun_pose = pose.pop("gun", ((0, 0, 0), (0, 0, 0)))
    pose.pop("camera", None)
    hidden = (set(hidden) | set(mj.get("hidden", [])) | {b for b, on in vis.items() if not on}) - {b for b, on in vis.items() if on}
    cam = Camera(w, h, fov=70.0)
    rs = Raster(w, h, bg=(120, 150, 185))
    M = gun_matrix(mj, ads, sprint, gun_pose)
    mats = draw_mesh(rs, cam, mj, M, mesh, pose, hidden)
    arms = v["arms"]
    for side, rest, key in (("right", "rh", "right_hand"), ("left", "lh", "left_hand")):
        p = loc_world(mj, mats, M, rest)
        if key in ik:
            tgt, wgt = ik[key]
            p = lerp(p, loc_world(mj, mats, M, tgt), wgt)
        a = arms[side]
        anchor = lerp(a["anchor"], a.get("anchor_ads", a["anchor"]), ads)
        AM = arm_matrix(p, anchor, side, a["twist"], arms["scale_w"], arms["scale_l"])
        draw_arm(rs, cam, AM, side)
    img = rs.image()
    d = ImageDraw.Draw(img)
    d.line([w / 2 - 6, h / 2, w / 2 + 6, h / 2], fill=(255, 255, 255))
    d.line([w / 2, h / 2 - 6, w / 2, h / 2 + 6], fill=(255, 255, 255))
    if title:
        d.text((6, 4), title, fill=(255, 255, 255))
    return img


def sheet(images, cols, path):
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    out = Image.new("RGB", (w * cols, h * rows))
    for i, im in enumerate(images):
        out.paste(im, ((i % cols) * w, (i // cols) * h))
    out.save(path)
    return path


def load(gun):
    mj = gunlib.load_model(os.path.join(ASSETS, "gunmodels", gun + ".json"))
    ap = os.path.join(ASSETS, "gunanims", gun + ".json")
    clips = json.load(open(ap))["clips"] if os.path.exists(ap) else {}
    return mj, clips


if __name__ == "__main__":
    gun = sys.argv[1]
    mj, clips = load(gun)
    mesh = gunlib.mesh_from_json(mj)
    os.makedirs(OUTDIR, exist_ok=True)
    if len(sys.argv) > 2:
        name = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
        clip = clips[name]
        L = clip["length"]
        ims = [render_fp(mj, mesh, clip=clip, t=L * i / (n - 1), title=f"{name} t={L * i / (n - 1):.2f}")
               for i in range(n)]
        print(sheet(ims, 4, os.path.join(OUTDIR, f"{gun}_{name}.png")))
    else:
        ims = [render_fp(mj, mesh, title="cadera"), render_fp(mj, mesh, ads=1.0, title="ADS"),
               render_fp(mj, mesh, sprint=1.0, title="sprint"), render_fp(mj, mesh, ads=0.5, title="ADS 50%")]
        print(sheet(ims, 2, os.path.join(OUTDIR, f"{gun}_poses.png")))
