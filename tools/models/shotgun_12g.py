"""Escopeta de corredera calibre 12 (cargador tubular, culata de madera)."""
import math

from common import Model, save, screw  # noqa: F401

m = Model("shotgun_12g")
body = m.bone("body")
BL = "blued"
WD = "wood"

# ---------------------------------------------------------------- receptor
rec = [(-1.65, -3.3), (1.65, -3.3), (1.65, 1.5), (1.2, 2.05), (0.35, 2.15), (-0.35, 2.15), (-1.2, 2.05), (-1.65, 1.5)]
body.extrude("z", rec, (-6.0, 13.0), BL, smooth=30)
body.box((-0.3, 2.1, -5.5), (0.3, 2.18, 12.6), "bore", axis="z")
# ventana de expulsion y portal de carga
body.box((1.63, -0.9, -2.5), (1.68, 1.3, 4.5), "bore", axis="x")
body.box((-1.2, -3.33, -4.5), (1.2, -3.28, 6.0), "bore", axis="y")
body.box((-0.9, -3.36, -4.0), (0.9, -3.3, 5.5), "steel", axis="y", tint="#8a7a50")
for (z, y) in ((10.0, -1.6), (2.0, -2.6), (8.0, -2.6)):
    screw(body, 1.66, y, z, r=0.2)
    screw(body, -1.66, y, z, r=0.2)
# canon con banda ventilada y punto de mira
body.cyl("z", (0, 0), 1.02, (-6.0, -52.0), BL, seg=18, inner=0.92)
body.cyl("z", (0, 0), 0.91, (-6.0, -51.9), "bore", seg=12)
body.box((-0.35, 1.0, -50.0), (0.35, 1.45, -8.0), BL, bevel=0.08, axis="z")
for k in range(14):
    z = -48.5 + k * 3.0
    body.box((-0.3, 0.9, z), (0.3, 1.0, z + 0.9), "bore", axis="z")
body.cyl("y", (0, -51.3), 0.26, (1.45, 1.75), "brass", seg=12, tint="#ffffff")
body.cyl("y", (0, -51.3), 0.24, (1.75, 1.9), "brass", seg=12, r2=0.1, tint="#ffffff")
# tubo cargador, abrazadera y tapon
body.cyl("z", (0, -2.3), 0.95, (-6.0, -46.0), BL, seg=16)
body.cyl("z", (0, -2.3), 1.12, (-46.0, -48.6), BL, seg=20)
for k in range(8):
    a = k * 45
    body.box((-0.08, -1.2, -48.4), (0.08, -1.1, -46.2), "steel", axis="z", rot=(0, 0, a), pivot=(0, -2.3, -47.3),
             tint="#888888")
body.extrude("z", [(-1.15, -3.4), (1.15, -3.4), (1.25, 1.05), (-1.25, 1.05)], (-38.0, -40.0), BL)

# ---------------------------------------------------------------- guardamonte y empunadura
body.box((-0.5, -5.4, 2.5), (0.5, -5.0, 9.8), BL, bevel=0.15, axis="z")
body.box((-0.5, -5.4, 2.3), (0.5, -3.2, 2.9), BL, bevel=0.15, axis="y")
body.box((-0.95, -3.6, 2.0), (0.95, -3.25, 13.0), "steel", bevel=0.1, axis="z", tint="#555555")
body.cyl("x", (9.6, -4.1), 0.3, (-0.65, 0.65), "steel", seg=10, tint="#aa2222")
stock = [(13.0, 2.0), (16.0, 1.9), (49.8, -0.4), (50.2, -1.0), (50.2, -12.6), (47.5, -12.6), (28.0, -6.6),
         (20.0, -6.3), (17.5, -8.2), (16.2, -8.6), (14.3, -7.8), (13.2, -5.2), (13.0, -3.3)]
body.extrude("x", stock, (-2.0, 2.0), WD, smooth=30)
body.extrude("x", [(50.0, -0.9), (52.6, -0.7), (52.7, -12.8), (50.0, -12.8)], (-2.08, 2.08), "rubber")
body.cyl("x", (44.0, -10.0), 0.55, (-2.05, -1.95), "steel", seg=12, tint="#888888")

# ---------------------------------------------------------------- piezas moviles
trig = m.bone("trigger", "body", pivot=(0, -3.4, 5.6))
trig.extrude("x", [(5.3, -3.4), (5.8, -3.4), (5.9, -4.1), (5.6, -4.9), (5.15, -5.0), (5.3, -4.5), (5.4, -4.0)],
             (-0.28, 0.28), "steel", tint="#4a4a4a")

pump = m.bone("pump", "body")
ring = []
for a in range(-90, 271, 20):
    r = 2.0 if -45 < a < 225 else 2.0
    ring.append((r * 1.05 * math.cos(math.radians(a)), -2.3 + 2.0 * math.sin(math.radians(a))))
pump.extrude("z", ring[:-1], (-14.0, -32.0), WD, smooth=30, tint="#d8b090")
for k in range(9):
    z = -30.5 + k * 1.8
    pump.cyl("z", (0, -2.3), 2.03, (z, z + 0.45), WD, seg=18, r2=2.03, tint="#6a4030")
pump.box((1.0, -2.6, -14.0), (1.3, -1.9, -6.0), "steel", axis="z", tint="#999999")
pump.box((-1.3, -2.6, -14.0), (-1.0, -1.9, -6.0), "steel", axis="z", tint="#999999")
pump.box((1.0, -2.0, -6.5), (1.66, -0.4, 4.0), "steel", axis="z", tint="#bbbbbb")

shell = m.bone("shell", "body")
shell.cyl("z", (0.0, -5.4), 0.95, (-1.0, 4.6), "shell", seg=14)
shell.cyl("z", (0.0, -5.4), 1.0, (4.6, 5.9), "brass", seg=14)
shell.cyl("z", (0.0, -5.4), 1.1, (5.9, 6.05), "brass", seg=14)

# ---------------------------------------------------------------- localizadores
m.locator("aim", "body", (0, 1.95, 12.6))
m.locator("muzzle", "body", (0, 0, -52.2))
m.locator("eject", "body", (1.7, 0.2, 1.0))
m.locator("rh", "body", (0.0, -6.4, 16.2))
m.locator("lh", "pump", (-0.5, -5.0, -23.0))
m.locator("lh_shell", "shell", (-0.5, -6.5, 2.5))
m.locator("pivot", "body", (0, -3.0, 12.0))

m.extra["hidden"] = ["shell"]
m.extra["flash"] = {"size": 9.0}
m.extra["view"] = {
    "hip": {"pos": [0.16, -0.115, -0.31], "rot": [0.0, 2.0, -4.0]},
    "sprint": {"pos": [0.06, -0.19, -0.16], "rot": [-12.0, 38.0, 18.0]},
    "eye_relief": 0.20,
    "arms": {"scale_w": 0.30, "scale_l": 1.05,
             "right": {"anchor": [0.30, -0.46, 0.30], "twist": 0.0},
             "left": {"anchor": [-0.06, -0.58, -0.12], "twist": 0.0}},
}
save(m)
