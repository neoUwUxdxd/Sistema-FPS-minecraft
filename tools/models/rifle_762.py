"""Fusil de asalto 7.62x39 (receptor estampado, madera, piston de recorrido largo)."""
import math

from common import Model, save, screw  # noqa: F401

m = Model("rifle_762")
body = m.bone("body")
PK = "parkerized"
WD = "wood"
DARK = "#b8b8b8"

# ---------------------------------------------------------------- receptor estampado
body.box((-1.55, -2.4, -10.0), (1.55, 0.9, 13.5), PK, bevel=0.15, axis="z", tint=DARK)
arc = [(1.5 * math.cos(math.radians(a)), 0.9 + 0.75 * math.sin(math.radians(a))) for a in range(0, 181, 20)]
body.extrude("z", [(-1.5, 0.85), (1.5, 0.85)] + arc[:0] + [p for p in arc], (-4.0, 13.2), PK, smooth=30)
body.cyl("z", (0, 1.15), 0.38, (13.2, 13.9), "steel", seg=10, tint="#666666")
for z in (-8.6, -7.4):
    body.box((1.54, -1.6, z - 0.3), (1.58, -0.9, z + 0.3), "bore", axis="x", tint="#444444")
    body.box((-1.58, -1.6, z - 0.3), (-1.54, -0.9, z + 0.3), "bore", axis="x", tint="#444444")
for (z, y) in ((-9.4, -0.3), (-9.4, -1.8), (-5.0, -1.8), (10.5, -1.6), (12.6, -0.4), (2.0, -2.0)):
    screw(body, 1.56, y, z, r=0.16, mat=PK)
    screw(body, -1.56, y, z, r=0.16, mat=PK)
# ventana de expulsion
body.box((1.54, -0.2, -2.5), (1.58, 0.85, 4.6), "bore", axis="x")
# bloque y alza de mira trasera
body.box((-1.2, 0.9, -10.0), (1.2, 2.3, -6.0), PK, bevel=0.3, axis="z", tint=DARK)
body.box((-0.9, 2.3, -9.7), (0.9, 2.55, -6.0), PK, bevel=0.05, axis="z")
body.box((-0.9, 2.55, -6.35), (-0.14, 2.95, -6.0), PK, bevel=0.04, axis="y")
body.box((0.14, 2.55, -6.35), (0.9, 2.95, -6.0), PK, bevel=0.04, axis="y")
body.box((-0.35, 2.3, -9.4), (0.35, 2.75, -8.6), "steel", bevel=0.1, axis="x", tint="#555555")

# ---------------------------------------------------------------- canon, gases, guardamanos
body.cyl("z", (0, 0), 0.8, (-10.0, -45.0), "blued", seg=16)
body.cyl("z", (0, 2.0), 0.72, (-10.0, -34.0), PK, seg=14, tint=DARK)
top = [(1.32 * math.cos(math.radians(a)), 2.0 + 1.32 * math.sin(math.radians(a))) for a in range(-20, 201, 20)]
body.extrude("z", top, (-11.2, -27.5), WD, tint="#c99a7a", smooth=30)
low = [(-2.0, -2.45), (2.0, -2.45), (2.15, -0.7), (1.85, 1.0), (-1.85, 1.0), (-2.15, -0.7)]
body.extrude("z", low, (-10.6, -30.0), WD, smooth=30)
for z in (-15.0, -17.0, -19.0, -21.0):
    body.box((2.0, -2.0, z), (2.16, -0.9, z + 0.9), WD, axis="x", tint="#7a5040")
    body.box((-2.16, -2.0, z), (-2.0, -0.9, z + 0.9), WD, axis="x", tint="#7a5040")
body.extrude("z", [(-2.1, -2.5), (2.1, -2.5), (2.2, 1.1), (-2.2, 1.1)], (-10.0, -10.6), PK, tint=DARK)
body.extrude("z", [(-2.15, -2.5), (2.15, -2.5), (2.25, 1.1), (-2.25, 1.1)], (-30.0, -31.2), PK, tint=DARK)
# bloque de gases y varilla de limpieza
body.box((-1.1, -0.95, -36.5), (1.1, 2.7, -33.0), PK, bevel=0.35, axis="z", tint=DARK)
body.cyl("z", (0, 2.0), 0.6, (-36.5, -37.0), PK, seg=12)
body.cyl("z", (0, -1.3), 0.26, (-31.0, -44.6), "steel", seg=8, tint="#888888")
body.cyl("z", (0, -1.3), 0.38, (-44.6, -45.1), "steel", seg=8, tint="#888888")
# mira delantera con capucha
body.box((-0.9, -1.6, -44.5), (0.9, 1.4, -41.5), PK, bevel=0.3, axis="z", tint=DARK)
body.cyl("z", (0, 2.4), 0.95, (-43.7, -42.5), PK, seg=16, inner=0.78)
body.box((-0.12, 1.4, -43.25), (0.12, 2.85, -43.0), "steel", axis="y", tint="#444444")
# freno de boca oblicuo
body.cyl("z", (0, 0), 1.0, (-45.0, -49.0), PK, seg=16, inner=0.45, tint=DARK)
body.cyl("z", (0, 0), 0.44, (-45.0, -48.9), "bore", seg=10)
for z in (-46.0, -47.3):
    body.box((-1.02, -0.3, z), (-0.6, 0.5, z + 0.8), "bore", axis="z")
body.box((0.0, 0.6, -48.9), (0.9, 1.02, -45.2), "bore", axis="z", rot=(0, 0, -40), pivot=(0, 0, -47))

# ---------------------------------------------------------------- empunadura, guardamonte, culata
grip = [(2.8, -2.4), (6.2, -2.4), (6.6, -2.9), (8.9, -10.9), (8.4, -11.6), (5.6, -11.4), (5.0, -10.4), (3.2, -4.2)]
body.extrude("x", grip, (-1.4, 1.4), WD, tint="#9a5a3a", smooth=30)
body.box((-0.45, -4.6, -1.2), (0.45, -4.2, 4.6), PK, bevel=0.12, axis="z", tint=DARK)
body.box((-0.45, -4.6, -1.4), (0.45, -2.4, -0.9), PK, bevel=0.12, axis="y", tint=DARK)
body.box((-0.6, -2.95, -9.8), (0.6, -2.4, -8.6), PK, bevel=0.1, axis="z", tint=DARK)
stock = [(13.5, 0.8), (17.0, 0.6), (46.6, -1.6), (46.6, -11.5), (44.0, -11.4), (24.0, -5.6), (17.0, -3.7), (13.5, -2.4)]
body.extrude("x", stock, (-1.85, 1.85), WD, smooth=25)
body.extrude("x", [(46.5, -1.55), (47.4, -1.5), (47.4, -11.6), (46.5, -11.6)], (-1.9, 1.9), PK, tint=DARK)

# ---------------------------------------------------------------- piezas moviles
trig = m.bone("trigger", "body", pivot=(0, -2.4, 0.8))
trig.extrude("x", [(0.7, -2.4), (1.2, -2.4), (1.3, -3.1), (1.0, -3.9), (0.6, -4.1), (0.75, -3.6), (0.85, -3.0)],
             (-0.26, 0.26), "steel", tint="#4a4a4a")

sel = m.bone("selector", "body", pivot=(1.62, 0.2, 9.3))
sel.box((1.57, -0.7, 0.8), (1.67, 0.45, 9.6), PK, bevel=0.04, axis="z", tint=DARK)
sel.box((1.57, -1.2, 0.8), (1.75, -0.6, 2.0), PK, bevel=0.04, axis="z", tint=DARK)

bolt = m.bone("bolt", "body")
bolt.box((1.5, 0.0, -2.2), (1.57, 0.7, 4.4), "steel", axis="x", tint="#a8a8a8")
bolt.cyl("x", (4.8, 0.35), 0.33, (1.55, 2.8), "steel", seg=10, tint="#9a9a9a")
bolt.cyl("x", (4.8, 0.35), 0.55, (2.6, 3.4), "steel", seg=12, tint="#9a9a9a")

mag = m.bone("magazine", "body", pivot=(0, -2.3, -9.2))
mag_prof = [(-2.8, -2.2), (-3.3, -7.0), (-4.7, -12.0), (-6.9, -17.0), (-9.2, -21.0),
            (-15.8, -20.6), (-13.5, -16.6), (-11.3, -11.8), (-10.0, -7.0), (-9.6, -2.2)]
mag.extrude("x", mag_prof, (-1.2, 1.2), PK, tint="#9c7a68", smooth=25)
mag.extrude("x", [(-9.3, -20.8), (-15.9, -20.4), (-16.1, -21.2), (-9.3, -21.6)], (-1.35, 1.35), PK, tint="#7a6052")
for (z0, y0, z1, y1) in ((-4.0, -9.0, -10.4, -9.0), (-5.6, -14.0, -12.2, -14.0)):
    mag.box((1.18, y0, z1), (1.28, y0 + 0.35, z0), PK, axis="z", tint="#8a6a58")
    mag.box((-1.28, y0, z1), (-1.18, y0 + 0.35, z0), PK, axis="z", tint="#8a6a58")
mag.cyl("z", (0, -1.7), 0.39, (-3.4, -6.6), "steel", seg=10, tint="#88aa88")
mag.cyl("z", (0, -1.7), 0.39, (-6.6, -8.4), "copper", r2=0.08, seg=10)

# ---------------------------------------------------------------- localizadores
m.locator("aim", "body", (0, 2.86, -6.0))
m.locator("muzzle", "body", (0, 0, -49.2))
m.locator("eject", "body", (1.6, 0.4, 1.0))
m.locator("rh", "body", (0.0, -7.1, 5.6))
m.locator("lh", "body", (-0.6, -2.9, -20.0))
m.locator("lh_mag", "magazine", (-0.4, -19.0, -12.6))
m.locator("rh_bolt", "bolt", (3.2, 0.35, 5.2))
m.locator("pivot", "body", (0, -2.0, 3.0))

m.extra["flash"] = {"size": 7.0}
m.extra["view"] = {
    "hip": {"pos": [0.17, -0.105, -0.31], "rot": [0.0, 2.0, -4.0]},
    "sprint": {"pos": [0.06, -0.19, -0.18], "rot": [-12.0, 38.0, 18.0]},
    "eye_relief": 0.36,
    "arms": {"scale_w": 0.30, "scale_l": 1.05,
             "right": {"anchor": [0.30, -0.46, 0.30], "twist": 0.0},
             "left": {"anchor": [-0.06, -0.58, -0.12], "twist": 0.0}},
}
save(m)
