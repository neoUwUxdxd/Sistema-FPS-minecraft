"""Pistola 9mm de armazon de polimero (accion por percutor lanzado)."""
from common import Model, save, screw  # noqa: F401

m = Model("pistol_9mm")
body = m.bone("body")
PO = "polymer"

# ---------------------------------------------------------------- armazon
body.box((-1.2, -2.1, -9.2), (1.2, -0.95, 6.8), PO, bevel=0.3, axis="z")
for z in (-8.6, -7.6, -6.6):
    body.box((-0.95, -2.13, z), (0.95, -2.08, z + 0.5), "bore", axis="y")
body.box((-1.22, -1.75, -9.2), (-1.18, -1.45, -3.2), "bore", axis="x")
body.box((1.18, -1.75, -9.2), (1.22, -1.45, -3.2), "bore", axis="x")
body.cyl("z", (0, -1.45), 0.36, (-9.25, -9.18), "steel", seg=12, tint="#777777")
# guardamonte
body.box((-0.45, -4.4, -3.7), (0.45, -2.0, -2.95), PO, bevel=0.2, axis="x", rot=(-12, 0, 0))
body.box((-0.45, -4.45, -3.55), (0.45, -3.9, 1.9), PO, bevel=0.2, axis="z")
# empunadura
grip = [(1.3, -2.1), (6.6, -1.35), (7.6, -1.15), (7.95, -1.7), (7.15, -2.45), (9.55, -11.35), (9.35, -11.9),
        (4.6, -11.9), (4.2, -10.6), (3.85, -9.55), (3.55, -9.15), (3.35, -7.95), (3.0, -7.45), (2.75, -6.1),
        (2.45, -5.65), (2.3, -4.4), (1.75, -3.7)]
body.extrude("x", grip, (-1.5, 1.5), "grip", smooth=35)
body.extrude("x", [(1.7, -2.1), (6.6, -1.4), (7.1, -2.4), (2.2, -3.6)], (-1.53, 1.53), PO)
# retenida de corredera, palanca de desmontaje, retenida de cargador
body.box((-1.32, -1.25, -1.9), (-1.2, -0.78, 1.4), "steel", bevel=0.05, axis="z", tint="#3a3a3a")
body.box((-1.33, -1.5, -0.3), (-1.2, -0.95, 0.4), "steel", bevel=0.05, axis="z", tint="#3a3a3a")
body.box((1.2, -1.45, -3.6), (1.28, -1.05, -2.6), "steel", bevel=0.05, axis="z", tint="#3a3a3a")
body.box((-1.6, -3.1, 1.5), (-1.48, -2.5, 2.5), PO, bevel=0.1, axis="z")
screw(body, 1.21, -1.7, 3.8, r=0.14)
screw(body, -1.21, -1.7, 3.8, r=0.14)
# canon: capucha visible por la ventana de expulsion y corona en la boca
body.box((-0.55, 1.2, -2.4), (0.55, 1.93, 0.9), "steel", bevel=0.1, axis="z", tint="#8e8e8e")
body.cyl("z", (0, 0), 0.55, (-9.6, -9.0), "steel", seg=16, inner=0.25, tint="#8e8e8e")
body.cyl("z", (0, 0), 0.26, (-9.55, -8.5), "bore", seg=10)

# ---------------------------------------------------------------- corredera
sl = m.bone("slide", "body")
prof = [(-1.25, -0.95), (1.25, -0.95), (1.25, 1.35), (0.85, 1.95), (-0.85, 1.95), (-1.25, 1.35)]
sl.extrude("z", prof, (-9.0, 8.6), "blued", tint="#d0d0d0", smooth=20)
nose = [(-1.05, -0.95), (1.05, -0.95), (1.05, 1.2), (0.7, 1.7), (-0.7, 1.7), (-1.05, 1.2)]
sl.extrude("z", nose, (-9.6, -9.0), "blued", tint="#d0d0d0", profile2=prof)
for k in range(7):
    z = 4.6 + k * 0.48
    sl.box((1.24, -0.6, z), (1.28, 1.25, z + 0.2), "bore", axis="x")
    sl.box((-1.28, -0.6, z), (-1.24, 1.25, z + 0.2), "bore", axis="x")
for k in range(4):
    z = -8.4 + k * 0.48
    sl.box((1.24, -0.4, z), (1.28, 1.15, z + 0.2), "bore", axis="x")
    sl.box((-1.28, -0.4, z), (-1.24, 1.15, z + 0.2), "bore", axis="x")
# ventana de expulsion
sl.box((-0.6, 1.94, -2.6), (0.95, 1.97, 1.2), "bore", axis="y")
sl.box((1.24, 0.35, -2.6), (1.27, 1.3, 1.2), "bore", axis="x")
# miras con puntos de tritio
sl.box((-0.2, 1.9, -8.95), (0.2, 2.5, -8.25), "steel", bevel=0.08, axis="y", tint="#303030")
sl.cyl("z", (0, 2.22), 0.1, (-8.26, -8.22), "emissive", seg=8, tint="#5cff74")
for sx in (-1, 1):
    sl.box((sx * 0.22, 1.9, 7.4), (sx * 0.78, 2.5, 8.25), "steel", bevel=0.08, axis="y", tint="#303030")
    sl.cyl("z", (sx * 0.5, 2.22), 0.1, (8.25, 8.29), "emissive", seg=8, tint="#5cff74")
sl.box((-0.78, 1.9, 8.1), (0.78, 2.15, 8.3), "steel", bevel=0.05, axis="x", tint="#303030")
# placa del percutor
sl.box((-0.7, -0.6, 8.6), (0.7, 1.0, 8.65), "polymer", axis="z", tint="#999999")

# ---------------------------------------------------------------- piezas moviles
trig = m.bone("trigger", "body", pivot=(0, -2.2, -1.6))
trig.extrude("x", [(-1.9, -2.2), (-1.4, -2.2), (-1.25, -2.9), (-1.5, -3.7), (-1.9, -3.85), (-1.85, -3.4),
                   (-1.95, -2.8)], (-0.28, 0.28), PO)
trig.box((-0.08, -3.5, -1.95), (0.08, -2.7, -1.7), "steel", axis="y", tint="#555555")

mag = m.bone("magazine", "body", pivot=(0, -2.0, 4.0))
mag.extrude("x", [(1.95, -2.0), (5.45, -2.0), (8.6, -11.8), (4.95, -11.8)], (-1.05, 1.05), "blued")
mag.extrude("x", [(4.55, -11.85), (9.25, -11.85), (9.35, -12.6), (4.45, -12.6)], (-1.4, 1.4), PO, tint="#d0d0d0")
mag.cyl("z", (0, -1.6), 0.45, (2.4, 4.4), "brass", seg=12)
mag.cyl("z", (0, -1.6), 0.45, (1.4, 2.4), "copper", r2=0.2, seg=12)

# ---------------------------------------------------------------- localizadores
m.locator("aim", "slide", (0, 2.45, 8.25))
m.locator("muzzle", "body", (0, 0, -9.8))
m.locator("eject", "slide", (1.3, 1.6, -0.6))
m.locator("rh", "body", (0.0, -6.8, 5.6))
m.locator("lh", "body", (-0.9, -7.6, 3.6))
m.locator("lh_mag", "magazine", (-0.4, -12.9, 6.9))
m.locator("lh_slide", "slide", (-0.6, 2.2, 6.4))
m.locator("pivot", "body", (0, -4.0, 4.0))

m.extra["empty_pose"] = {"slide": [0, 0, 2.6]}
m.extra["flash"] = {"size": 4.0}
m.extra["view"] = {
    "hip": {"pos": [0.12, -0.085, -0.30], "rot": [1.0, 5.0, -4.0]},
    "sprint": {"pos": [0.10, -0.20, -0.26], "rot": [-35.0, 15.0, 10.0]},
    "eye_relief": 0.33,
    "arms": {"scale_w": 0.25, "scale_l": 1.05,
             "right": {"anchor": [0.24, -0.50, 0.10], "anchor_ads": [0.12, -0.42, 0.10], "twist": 0.0},
             "left": {"anchor": [-0.14, -0.52, 0.06], "anchor_ads": [-0.14, -0.42, 0.10], "twist": 0.0}},
}
save(m)
