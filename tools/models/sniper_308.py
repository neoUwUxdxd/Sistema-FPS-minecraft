"""Rifle de cerrojo .308 de precision (canon pesado, freno de boca, mira 3-12x)."""
import math

from common import Model, picatinny, save, screw  # noqa: F401

m = Model("sniper_308")
body = m.bone("body")
FD = "fde"
BL = "blued"
AN = "anodized"

# ---------------------------------------------------------------- accion cilindrica
body.cyl("z", (0, 0), 1.7, (-9.0, 12.0), BL, seg=22)
body.box((1.55, -0.6, -1.0), (1.72, 1.2, 6.0), "bore", axis="x")
body.box((-1.2, 1.55, -9.0), (1.2, 1.9, 12.0), BL, bevel=0.2, axis="z")
picatinny(body, -9.0, 12.0, 1.9, 1.05, mat=AN)
body.cyl("z", (0, 0), 1.85, (-9.0, -10.2), BL, seg=18)
# canon pesado conico y freno de boca
body.cyl("z", (0, 0), 1.45, (-10.2, -62.0), BL, r2=1.0, seg=20)
body.cyl("z", (0, 0), 1.35, (-62.0, -68.5), BL, seg=8, phase=22.5, inner=0.5)
body.cyl("z", (0, 0), 0.49, (-62.0, -68.4), "bore", seg=10)
for z in (-63.2, -65.0, -66.8):
    body.box((-1.4, -0.45, z), (1.4, 0.45, z + 1.0), "bore", axis="x")

# ---------------------------------------------------------------- culata de polimero FDE
fore = [(-9.0, -1.2), (-40.0, -1.2), (-40.6, -2.0), (-40.2, -4.6), (-38.0, -5.4), (-9.0, -6.0)]
body.extrude("x", fore, (-2.2, 2.2), FD, smooth=30)
body.extrude("x", [(-9.0, -1.0), (14.0, -1.0), (14.0, -6.2), (-9.0, -6.2)], (-2.3, 2.3), FD)
grip = [(9.0, -5.5), (13.5, -5.5), (14.5, -6.6), (15.6, -13.0), (15.2, -13.7), (11.8, -13.5), (11.4, -12.5),
        (10.6, -8.5), (9.8, -7.2)]
body.extrude("x", grip, (-1.6, 1.6), "grip", smooth=30)
butt = [(14.0, -1.0), (44.0, -1.0), (44.2, -13.6), (40.0, -13.6), (32.0, -9.5), (27.0, -9.2), (20.0, -9.0),
        (16.0, -7.6), (14.0, -6.2)]
body.extrude("x", butt, (-2.2, 2.2), FD, smooth=30)
body.extrude("x", [(18.0, -1.0), (40.0, -1.0), (40.0, 1.8), (19.5, 1.8)], (-1.9, 1.9), FD, tint="#d8d8d8")
body.cyl("y", (1.5, 22.0), 0.22, (-1.0, 0.2), "steel", seg=8, tint="#888888")
body.cyl("y", (-1.5, 22.0), 0.22, (-1.0, 0.2), "steel", seg=8, tint="#888888")
body.extrude("x", [(44.1, -0.9), (45.8, -0.9), (45.9, -13.7), (44.1, -13.7)], (-2.25, 2.25), "rubber")
for z in (-30.0, 36.0):
    body.cyl("x", (z, -4.5), 0.45, (2.18, 2.3), "steel", seg=12, tint="#555555")
    body.cyl("x", (z, -4.5), 0.45, (-2.3, -2.18), "steel", seg=12, tint="#555555")
# bipode plegado
body.box((-0.9, -6.9, -38.0), (0.9, -6.0, -35.0), AN, bevel=0.2, axis="x")
for sx in (-1, 1):
    body.cyl("z", (sx * 0.65, -6.6), 0.32, (-35.0, -16.0), AN, seg=10)
    body.cyl("z", (sx * 0.65, -6.6), 0.4, (-16.0, -15.2), "rubber", seg=10)
# guardamonte
body.box((-0.5, -8.6, 2.0), (0.5, -8.2, 9.6), AN, bevel=0.15, axis="z")
body.box((-0.5, -8.6, 1.8), (0.5, -6.0, 2.4), AN, bevel=0.15, axis="y")

# ---------------------------------------------------------------- mira telescopica
sc = m.bone("scope", "body")
Y = 5.6
for z in (-6.5, 6.5):
    sc.box((-1.25, 2.75, z - 1.1), (1.25, 3.6, z + 1.1), AN, bevel=0.2, axis="z")
    sc.cyl("z", (0, Y), 1.85, (z - 1.0, z + 1.0), AN, seg=22)
    sc.box((-0.6, 3.4, z - 0.9), (0.6, 4.2, z + 0.9), AN, bevel=0.2, axis="z")
    sc.cyl("x", (z, 3.15), 0.45, (1.25, 1.9), "steel", seg=10, tint="#4a4a4a")
sc.cyl("z", (0, Y), 1.5, (-14.0, 13.0), AN, seg=24)
sc.cyl("z", (0, Y), 1.5, (-14.0, -18.5), AN, r2=2.6, seg=28)
sc.cyl("z", (0, Y), 2.6, (-18.5, -24.5), AN, seg=28, inner=2.25)
sc.cyl("z", (0, Y), 2.28, (-21.5, -21.45), "glass", seg=28)
sc.cyl("z", (0, Y), 1.5, (13.0, 15.5), AN, r2=2.1, seg=26)
sc.cyl("z", (0, Y), 2.1, (15.5, 21.5), AN, seg=26, inner=1.8)
sc.cyl("z", (0, Y), 2.2, (17.0, 19.0), "rubber", seg=26)
sc.cyl("z", (0, Y), 1.82, (20.5, 20.55), "glass", seg=26)
sc.cyl("y", (0, -0.5), 1.0, (Y + 1.3, Y + 2.5), AN, seg=18)
sc.cyl("y", (0, -0.5), 1.15, (Y + 2.5, Y + 3.4), AN, seg=24, tint="#c0c0c0")
sc.cyl("x", (-0.5, Y), 1.0, (1.3, 2.5), AN, seg=18)
sc.cyl("x", (-0.5, Y), 1.15, (2.5, 3.3), AN, seg=24, tint="#c0c0c0")
sc.cyl("x", (-0.5, Y), 1.1, (-3.0, -1.3), AN, seg=22)
sc.box((-1.25, Y - 1.3, -2.2), (1.25, Y + 1.3, 1.2), AN, bevel=0.5, axis="z")
sc.cyl("z", (0, Y), 1.75, (12.0, 13.2), AN, seg=26, tint="#c8c8c8")
sc.box((1.6, Y - 0.25, 12.2), (2.6, Y + 0.25, 12.9), AN, bevel=0.1, axis="x")

# ---------------------------------------------------------------- piezas moviles
trig = m.bone("trigger", "body", pivot=(0, -6.0, 5.6))
trig.extrude("x", [(5.4, -6.0), (5.8, -6.0), (5.9, -6.7), (5.6, -7.6), (5.15, -7.7), (5.3, -7.2), (5.4, -6.6)],
             (-0.26, 0.26), "steel", tint="#4a4a4a")

bolt = m.bone("bolt", "body", pivot=(0, 0, 0))
bolt.cyl("z", (0, 0), 0.95, (-1.0, 14.5), "steel", seg=16, tint="#c8c8c8")
bolt.cyl("z", (0, 0), 1.25, (12.0, 15.8), BL, seg=16)
bolt.box((0.6, -0.4, 11.0), (4.2, 0.4, 12.0), "steel", bevel=0.2, axis="x", rot=(0, 0, -30), pivot=(0.6, 0, 11.5),
         tint="#b0b0b0")
bolt.cyl("z", (3.6, -2.0), 0.95, (10.6, 12.4), BL, seg=16)
bolt.cyl("x", (11.5, -2.0), 0.95, (2.75, 4.45), BL, seg=16)

mag = m.bone("magazine", "body", pivot=(0, -6.0, 2.0))
mag.box((-1.5, -9.4, -2.2), (1.5, -5.8, 5.8), BL, bevel=0.2, axis="y")
mag.box((-1.62, -10.0, -2.4), (1.62, -9.4, 6.0), AN, bevel=0.2, axis="z")
mag.cyl("z", (0, -4.9), 0.42, (-1.2, 5.0), "brass", seg=12)
mag.cyl("z", (0, -4.9), 0.42, (-2.6, -1.2), "copper", r2=0.12, seg=12)

# ---------------------------------------------------------------- localizadores
m.locator("aim", "scope", (0, Y, 21.5))
m.locator("muzzle", "body", (0, 0, -68.7))
m.locator("eject", "body", (1.8, 0.4, 2.0))
m.locator("rh", "body", (0.0, -9.6, 12.8))
m.locator("lh", "body", (-0.6, -6.3, -26.0))
m.locator("lh_mag", "magazine", (-0.5, -10.4, 1.8))
m.locator("rh_bolt", "bolt", (3.6, -2.0, 12.2))
m.locator("pivot", "body", (0, -4.0, 10.0))

m.extra["flash"] = {"size": 6.0}
m.extra["view"] = {
    "hip": {"pos": [0.165, -0.115, -0.40], "rot": [0.0, 2.0, -4.0]},
    "sprint": {"pos": [0.06, -0.20, -0.17], "rot": [-12.0, 38.0, 18.0]},
    "eye_relief": 0.09,
    "arms": {"scale_w": 0.30, "scale_l": 1.05,
             "right": {"anchor": [0.30, -0.46, 0.30], "twist": 0.0},
             "left": {"anchor": [-0.06, -0.58, -0.12], "twist": 0.0}},
}
save(m)
