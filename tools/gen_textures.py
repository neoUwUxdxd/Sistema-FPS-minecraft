"""
Genera todas las texturas del mod de forma procedural:
  - Materiales de armas (512x512, perfectamente repetibles via ruido FFT periodico)
  - Fogonazos, reticulas, overlay de mira telescopica, hitmarker
  - Particulas (trazadora, agujero de bala, casquillo, humo)
  - Iconos de municion (16x16 pixel-art)
Uso: python3 tools/gen_textures.py
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "assets", "fpsrealista")
TEX = os.path.join(ROOT, "textures")
RNG = np.random.default_rng(1337)
N = 512


def periodic_noise(n, falloff, rng=RNG, aniso=(1.0, 1.0)):
    """Ruido 1/f^falloff periodico (tileable). aniso estira frecuencias por eje."""
    w = rng.standard_normal((n, n))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(n)[:, None] * aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * aniso[0]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    F *= 1.0 / (f ** falloff)
    F[0, 0] = 0
    r = np.real(np.fft.ifft2(F))
    r -= r.mean()
    r /= (np.abs(r).max() + 1e-9)
    return r


def band_noise(n, lo, hi, rng=RNG):
    w = rng.standard_normal((n, n))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.fftfreq(n)[None, :] * n
    f = np.sqrt(fx * fx + fy * fy)
    F *= ((f >= lo) & (f <= hi))
    r = np.real(np.fft.ifft2(F))
    r /= (np.abs(r).max() + 1e-9)
    return r


def scratches(n, count, length, rng=RNG, angle_spread=math.pi):
    img = Image.new("L", (n * 3, n * 3), 0)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.uniform(n, 2 * n, 2)
        a = rng.uniform(0, angle_spread)
        L = rng.uniform(length * 0.3, length)
        # rasguno ligeramente curvo
        pts = []
        for k in range(8):
            t = k / 7
            pts.append((x + math.cos(a) * L * t + math.sin(a) * 4 * math.sin(t * 3),
                        y + math.sin(a) * L * t - math.cos(a) * 4 * math.sin(t * 3)))
        d.line(pts, fill=int(rng.uniform(60, 255)), width=1)
    a = np.asarray(img, dtype=np.float32) / 255.0
    # plegar el lienzo 3x3 para que sea repetible
    out = np.zeros((n, n), np.float32)
    for i in range(3):
        for j in range(3):
            out = np.maximum(out, a[i * n:(i + 1) * n, j * n:(j + 1) * n])
    return out


def to_img(rgb, alpha=None):
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    if alpha is None:
        return Image.fromarray(rgb, "RGB").convert("RGBA")
    a = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def colorize(base, h, spec=None):
    """base: (r,g,b); h: campo de luminancia [-1,1] -> imagen."""
    base = np.array(base, np.float32)
    out = base[None, None, :] * (1.0 + h[..., None])
    if spec is not None:
        out += spec[..., None] * 255
    return out


def save(img, *path):
    p = os.path.join(TEX, *path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p, optimize=True)
    return p


def mcmeta(path, blur=True):
    with open(path + ".mcmeta", "w") as f:
        json.dump({"texture": {"blur": blur, "clamp": False}}, f)


# ----------------------------------------------------------------------------
# Materiales
# ----------------------------------------------------------------------------
def mat_anodized():
    g = periodic_noise(N, 1.2) * 0.06 + band_noise(N, 120, 256) * 0.05
    s = scratches(N, 90, 120) * 0.10 + scratches(N, 400, 25) * 0.05
    sparkle = (band_noise(N, 200, 256) > 0.55) * 0.04
    return colorize((40, 41, 44), g, s + sparkle)


def mat_polymer():
    g = periodic_noise(N, 1.0) * 0.08 + band_noise(N, 90, 200) * 0.09
    s = scratches(N, 40, 60) * 0.05
    return colorize((34, 34, 35), g, s)


def mat_grip():
    # textura punteada agresiva (stippling) tipo empunadura de polimero
    st = band_noise(N, 40, 70)
    bump = np.where(st > 0.15, 0.22, -0.18) + band_noise(N, 150, 256) * 0.06
    return colorize((36, 36, 37), bump)


def mat_parkerized():
    g = periodic_noise(N, 0.8) * 0.10 + band_noise(N, 100, 256) * 0.12
    s = scratches(N, 120, 80) * 0.12
    return colorize((52, 54, 50), g, s)


def mat_blued():
    streak = periodic_noise(N, 1.4, aniso=(0.06, 1.0)) * 0.10
    g = periodic_noise(N, 1.1) * 0.05
    s = scratches(N, 70, 140, angle_spread=0.3) * 0.12
    return colorize((38, 41, 50), streak + g, s)


def mat_steel():
    streak = periodic_noise(N, 1.2, aniso=(0.03, 1.0)) * 0.12
    g = band_noise(N, 150, 256) * 0.04
    s = scratches(N, 150, 100) * 0.10
    return colorize((150, 152, 156), streak + g, s)


def mat_wood():
    n = N
    y = np.arange(n)[:, None] / n
    x = np.arange(n)[None, :] / n
    warp = periodic_noise(n, 1.6) * 0.9
    rings = np.sin((y * 24 + warp * 2.5) * 2 * math.pi)
    rings = np.sign(rings) * np.abs(rings) ** 0.6
    fiber = periodic_noise(n, 1.0, aniso=(0.04, 1.0)) * 0.25
    pores = (band_noise(n, 160, 256) * periodic_noise(n, 0.6, aniso=(0.02, 1.0)) > 0.12) * -0.2
    h = rings * 0.13 + fiber + pores + periodic_noise(n, 1.8) * 0.15
    base = np.array((108, 60, 32), np.float32)
    out = base[None, None, :] * (1.0 + h[..., None])
    # variacion de tono (mas rojizo en zonas oscuras)
    out[..., 0] += (h * 18)
    out += scratches(n, 30, 60)[..., None] * 25
    return out


def mat_brass():
    streak = periodic_noise(N, 1.2, aniso=(0.05, 1.0)) * 0.08
    tarnish = periodic_noise(N, 2.0) * 0.12
    return colorize((188, 146, 66), streak + tarnish, scratches(N, 40, 40) * 0.08)


def mat_copper():
    return colorize((176, 102, 58), periodic_noise(N, 1.5) * 0.10 + band_noise(N, 150, 256) * 0.05)


def mat_rubber():
    g = band_noise(N, 100, 256) * 0.08 + periodic_noise(N, 1.2) * 0.04
    return colorize((26, 26, 27), g)


def mat_fde():
    g = periodic_noise(N, 1.0) * 0.07 + band_noise(N, 90, 200) * 0.06
    s = scratches(N, 60, 70) * 0.06
    return colorize((150, 128, 96), g, s)


def mat_bore():
    return colorize((10, 10, 11), periodic_noise(N, 1.0) * 0.3)


def mat_white():
    return np.full((N, N, 3), 255.0)


def mat_shell():
    # vaina plastica roja de cartucho del calibre 12 con estrias
    y = np.arange(N)[:, None] / N
    ridges = np.sin(y * 2 * math.pi * 40) * 0.05
    return colorize((150, 26, 22), ridges + periodic_noise(N, 1.3) * 0.08)


def mat_glass():
    y = np.arange(N)[:, None] / N
    x = np.arange(N)[None, :] / N
    grad = (np.sin((x + y) * 2 * math.pi) * 0.5 + 0.5)
    rgb = np.zeros((N, N, 3), np.float32)
    rgb[..., 0] = 40 + 60 * grad
    rgb[..., 1] = 70 + 50 * grad
    rgb[..., 2] = 110 + 80 * grad
    alpha = np.full((N, N), 45.0) + grad * 40
    return rgb, alpha


MATERIALS = {
    # nombre: (funcion, cm por repeticion, tipo)
    "anodized": (mat_anodized, 9.0, "solid"),
    "polymer": (mat_polymer, 9.0, "solid"),
    "grip": (mat_grip, 4.0, "solid"),
    "parkerized": (mat_parkerized, 9.0, "solid"),
    "blued": (mat_blued, 12.0, "solid"),
    "steel": (mat_steel, 8.0, "solid"),
    "wood": (mat_wood, 22.0, "solid"),
    "brass": (mat_brass, 3.0, "solid"),
    "copper": (mat_copper, 3.0, "solid"),
    "rubber": (mat_rubber, 6.0, "solid"),
    "fde": (mat_fde, 9.0, "solid"),
    "bore": (mat_bore, 4.0, "solid"),
    "shell": (mat_shell, 3.0, "solid"),
    "glass": (mat_glass, 4.0, "translucent"),
    "emissive": (mat_white, 4.0, "emissive"),
}


def gen_materials():
    meta = {}
    for name, (fn, scale, kind) in MATERIALS.items():
        r = fn()
        if isinstance(r, tuple):
            img = to_img(*r)
        else:
            img = to_img(r)
        p = save(img, "gun", f"{name}.png")
        mcmeta(p, blur=True)
        meta[name] = {"texture": f"fpsrealista:textures/gun/{name}.png", "scale": scale, "type": kind}
    # decals (textura completa en un quad)
    meta["reticle_dot"] = {"texture": "fpsrealista:textures/gun/reticle_dot.png", "scale": 1.0, "type": "emissive_decal"}
    meta["marking"] = {"texture": "fpsrealista:textures/gun/marking.png", "scale": 1.0, "type": "decal"}
    out = os.path.join(ROOT, "gunmodels", "materials.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(meta, f, indent=1)
    return meta


def gen_reticle():
    S = 128
    y, x = np.mgrid[0:S, 0:S]
    r = np.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5)
    core = np.exp(-(r / 3.2) ** 2)
    halo = np.exp(-(r / 9) ** 2) * 0.35
    a = np.clip(core + halo, 0, 1)
    rgb = np.zeros((S, S, 3))
    rgb[..., 0] = 255
    rgb[..., 1] = 40 + 200 * core
    rgb[..., 2] = 30 + 180 * core
    save(to_img(rgb, a * 255), "gun", "reticle_dot.png")

    # marcas grabadas (selector SAFE/SEMI/AUTO etc.) en blanco sobre transparente
    img = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((6, 4), "SAFE   SEMI   AUTO", fill=(220, 220, 220, 200))
    d.text((6, 26), "CAL 5.56 NATO  FPS-R", fill=(200, 200, 200, 170))
    d.text((6, 44), "7.62x39   9x19   12GA", fill=(200, 200, 200, 170))
    save(img, "gun", "marking.png")


# ----------------------------------------------------------------------------
# Efectos
# ----------------------------------------------------------------------------
def gen_muzzle_flash():
    for k in range(4):
        rng = np.random.default_rng(100 + k)
        S = 256
        y, x = np.mgrid[0:S, 0:S]
        cx = cy = S / 2
        ang = np.arctan2(y - cy, x - cx)
        r = np.hypot(x - cx, y - cy) / (S / 2)
        prongs = rng.integers(4, 7)
        spikes = np.zeros_like(r)
        for p in range(prongs):
            a0 = rng.uniform(0, 2 * math.pi)
            w = rng.uniform(0.10, 0.22)
            d = np.angle(np.exp(1j * (ang - a0)))
            length = rng.uniform(0.55, 1.0)
            spikes = np.maximum(spikes, np.exp(-(d / w) ** 2) * np.clip(1 - r / length, 0, 1) ** 1.3)
        core = np.exp(-(r / 0.22) ** 2)
        turb = periodic_noise(S, 1.1, rng=rng) * 0.35 + 0.65
        inten = np.clip((core * 1.2 + spikes) * turb, 0, 1)
        rgb = np.zeros((S, S, 3))
        rgb[..., 0] = 255
        rgb[..., 1] = 120 + 135 * inten ** 0.6
        rgb[..., 2] = 30 + 200 * inten ** 2.2
        save(to_img(rgb * inten[..., None] ** 0.25, inten * 255), "effect", f"muzzle_flash_{k}.png")
    # fogonazo lateral (vista lateral, cono)
    S = 256
    y, x = np.mgrid[0:S, 0:S] / S
    yy = (y - 0.5) * 2
    width = 0.12 + x * 0.5
    inten = np.exp(-(yy / width) ** 2) * np.clip(1 - x, 0, 1) ** 1.5
    inten *= periodic_noise(S, 1.2, rng=np.random.default_rng(7)) * 0.4 + 0.75
    inten = np.clip(inten * 1.3, 0, 1)
    rgb = np.zeros((S, S, 3))
    rgb[..., 0] = 255
    rgb[..., 1] = 130 + 125 * inten
    rgb[..., 2] = 40 + 200 * inten ** 2
    save(to_img(rgb, inten * 255), "effect", "muzzle_flash_side.png")


def gen_hud():
    # overlay de mira telescopica: negro con circulo transparente, reticula mil-dot
    S = 1024
    img = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    y, x = np.mgrid[0:S, 0:S]
    r = np.hypot(x - S / 2, y - S / 2) / (S / 2)
    alpha = np.clip((r - 0.93) / 0.07, 0, 1)
    # vineteado y aberracion en el borde
    vign = np.clip((r - 0.6) / 0.33, 0, 1) ** 2 * 0.55
    a = np.clip(np.maximum(alpha, vign), 0, 1)
    base = np.zeros((S, S, 4), np.uint8)
    base[..., 3] = (a * 255).astype(np.uint8)
    img = Image.fromarray(base, "RGBA")
    d = ImageDraw.Draw(img)
    c = S // 2
    col = (5, 5, 5, 255)
    # hilos gruesos exteriores y finos interiores
    d.rectangle([0, c - 5, c - 180, c + 5], fill=col)
    d.rectangle([c + 180, c - 5, S, c + 5], fill=col)
    d.rectangle([c - 5, c + 180, c + 5, S], fill=col)
    d.rectangle([c - 5, 0, c + 5, c - 180], fill=col)
    d.line([c - 180, c, c + 180, c], fill=col, width=2)
    d.line([c, c - 180, c, c + 180], fill=col, width=2)
    for k in range(1, 5):
        o = k * 40
        for (px, py) in ((c + o, c), (c - o, c), (c, c + o), (c, c - o)):
            d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=col)
    # punto rojo iluminado central
    d.ellipse([c - 3, c - 3, c + 3, c + 3], fill=(255, 40, 30, 255))
    save(img, "gui", "scope_overlay.png")

    # hitmarker
    S = 64
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for (a, b) in (((8, 8), (24, 24)), ((56, 8), (40, 24)), ((8, 56), (24, 40)), ((56, 56), (40, 40))):
        d.line([a, b], fill=(255, 255, 255, 255), width=4)
    save(img, "gui", "hitmarker.png")


def gen_particles():
    # trazadora: gradiente horizontal brillante
    W, H = 64, 16
    y, x = np.mgrid[0:H, 0:W]
    v = np.exp(-((y - H / 2 + 0.5) / 3.0) ** 2)
    u = np.clip(x / W, 0, 1) ** 0.6
    a = v * u
    rgb = np.zeros((H, W, 3))
    rgb[..., 0] = 255
    rgb[..., 1] = 200 + 55 * v
    rgb[..., 2] = 120 + 135 * v ** 3
    save(to_img(rgb, a * 255), "particle", "tracer.png")

    # agujeros de bala (4 variantes)
    for k in range(4):
        rng = np.random.default_rng(500 + k)
        S = 32
        y, x = np.mgrid[0:S, 0:S]
        ang = np.arctan2(y - S / 2 + 0.5, x - S / 2 + 0.5)
        rr = np.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5)
        jag = 1 + 0.25 * np.sin(ang * rng.integers(5, 9) + rng.uniform(0, 6)) + 0.1 * rng.standard_normal(rr.shape)
        hole = rr < 3.2 * jag
        ring = (rr < 7.5 * jag) & ~hole
        cracks = np.zeros_like(rr, bool)
        for _ in range(rng.integers(3, 6)):
            a0 = rng.uniform(0, 2 * math.pi)
            d = np.abs(np.angle(np.exp(1j * (ang - a0))))
            cracks |= (d < 0.08) & (rr < rng.uniform(9, 15))
        rgb = np.zeros((S, S, 3))
        alpha = np.zeros((S, S))
        rgb[ring | cracks] = (45, 40, 36)
        alpha[ring | cracks] = 150
        alpha[ring] = 150 * np.clip(1 - (rr[ring] / (7.5 * jag[ring])) ** 2, 0.2, 1)
        rgb[hole] = (8, 7, 6)
        alpha[hole] = 255
        save(to_img(rgb, alpha), "particle", f"bullet_hole_{k}.png")

    # casquillo (sprite lateral)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([3, 6, 12, 9], fill=(200, 158, 70, 255))
    d.rectangle([3, 6, 12, 6], fill=(240, 205, 120, 255))
    d.rectangle([12, 5, 13, 10], fill=(170, 130, 55, 255))
    d.rectangle([2, 7, 3, 8], fill=(150, 110, 45, 255))
    save(img, "particle", "casing.png")
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 5, 10, 10], fill=(160, 30, 25, 255))
    d.rectangle([10, 5, 13, 10], fill=(200, 160, 70, 255))
    d.rectangle([2, 5, 10, 5], fill=(200, 60, 50, 255))
    save(img, "particle", "shotshell.png")

    # humo del canon
    for k in range(4):
        rng = np.random.default_rng(900 + k)
        S = 32
        n = periodic_noise(S, 1.3, rng=rng)
        y, x = np.mgrid[0:S, 0:S]
        rr = np.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5) / (S / 2)
        a = np.clip((1 - rr) * (0.7 + 0.5 * n), 0, 1) ** 1.5
        rgb = np.full((S, S, 3), 200.0) + n[..., None] * 30
        save(to_img(rgb, a * 200), "particle", f"gun_smoke_{k}.png")


# ----------------------------------------------------------------------------
# Iconos de municion (16x16)
# ----------------------------------------------------------------------------
def draw_round(d, x, y, length, case_len, w, case_col, tip_col):
    d.rectangle([x, y, x + w - 1, y + case_len - 1], fill=case_col)
    d.rectangle([x, y, x, y + case_len - 1], fill=tuple(min(255, c + 45) for c in case_col))
    d.rectangle([x, y + case_len - 1, x + w - 1, y + case_len - 1], fill=tuple(max(0, c - 50) for c in case_col))
    bl = length - case_len
    for k in range(bl):
        t = k / max(1, bl - 1)
        ww = max(1, round(w * (1 - t * 0.6)))
        off = (w - ww) // 2
        d.rectangle([x + off, y - 1 - k, x + off + ww - 1, y - 1 - k], fill=tip_col)


def gen_ammo_icons():
    brass = (198, 152, 64)
    copper = (180, 106, 60)
    steel = (110, 105, 95)
    specs = {
        "ammo_9mm": [(3, 9, 6, 4, 3, brass, copper), (8, 10, 6, 4, 3, brass, copper), (12, 8, 6, 4, 3, brass, (90, 90, 95))],
        "ammo_556": [(2, 13, 11, 8, 3, brass, copper), (7, 14, 11, 8, 3, brass, copper), (11, 13, 11, 8, 3, brass, (60, 140, 70))],
        "ammo_762": [(2, 13, 10, 7, 3, steel, copper), (7, 14, 10, 7, 3, steel, copper), (11, 13, 10, 7, 3, steel, copper)],
        "ammo_308": [(3, 14, 13, 9, 3, brass, copper), (9, 14, 13, 9, 3, brass, (40, 40, 40))],
    }
    for name, rounds in specs.items():
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for (x, ybot, length, case_len, w, cc, tc) in rounds:
            draw_round(d, x, ybot - case_len + 1, length, case_len, w, cc, tc)
        save(img, "item", f"{name}.png")
    # cartuchos del 12
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, yt in ((1, 3), (6, 2), (11, 3)):
        d.rectangle([x, yt, x + 3, yt + 9], fill=(170, 30, 25, 255))
        d.rectangle([x, yt, x, yt + 9], fill=(210, 70, 60, 255))
        d.rectangle([x, yt + 9, x + 3, yt + 12], fill=(205, 160, 70, 255))
        d.rectangle([x, yt + 12, x + 3, yt + 12], fill=(140, 100, 40, 255))
    save(img, "item", "ammo_12g.png")
    # piezas de fabricacion
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 6, 13, 9], fill=(70, 72, 76, 255))
    d.rectangle([2, 6, 13, 6], fill=(140, 142, 148, 255))
    d.rectangle([4, 9, 6, 13], fill=(55, 56, 60, 255))
    d.rectangle([10, 4, 12, 6], fill=(90, 92, 96, 255))
    save(img, "item", "gun_parts.png")


def gen_logo():
    S = 256
    img = Image.new("RGBA", (S, S), (24, 26, 30, 255))
    d = ImageDraw.Draw(img)
    for r in range(110, 60, -8):
        d.ellipse([S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r], outline=(200, 40, 30, 255), width=3)
    d.line([20, S / 2, S - 20, S / 2], fill=(230, 230, 230, 255), width=4)
    d.line([S / 2, 20, S / 2, S - 20], fill=(230, 230, 230, 255), width=4)
    d.ellipse([S / 2 - 6, S / 2 - 6, S / 2 + 6, S / 2 + 6], fill=(255, 50, 40, 255))
    img.save(os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "logo.png"))


if __name__ == "__main__":
    gen_materials()
    gen_reticle()
    gen_muzzle_flash()
    gen_hud()
    gen_particles()
    gen_ammo_icons()
    gen_logo()
    print("texturas generadas en", os.path.abspath(TEX))
