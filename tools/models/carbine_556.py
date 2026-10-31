"""Carabina 5.56 tactica (estilo AR-15 con guardamanos M-LOK y punto rojo)."""
from common import Model, picatinny, mlok_slots, screw, save, rect_profile  # noqa: F401

m = Model("carbine_556")
body = m.bone("body")

AN = "anodized"
# ---------------------------------------------------------------- receptor superior
body.box((-1.25, -1.3, -9.0), (1.25, 1.95, 9.2), AN, bevel=0.35, axis="z")
picatinny(body, -9.0, 9.2, 1.95, 1.05)
# ventana de expulsion (rebaje oscuro) y deflector de vainas
body.box((1.24, -0.55, -3.9), (1.28, 1.05, 1.9), "bore", axis="x")
body.box((1.25, -0.2, 2.0), (1.8, 1.55, 3.3), AN, bevel=0.25, axis="y")
# tapa guardapolvo abierta colgando
body.box((1.27, -1.45, -3.9), (1.4, -0.65, 1.9), AN, bevel=0.05, axis="z", rot=(0, 0, -28), pivot=(1.3, -0.62, 0))
# asistente de cierre (forward assist)
body.box((0.9, 0.35, 3.3), (1.55, 1.75, 6.1), AN, bevel=0.3, axis="z")
body.cyl("z", (1.45, 1.05), 0.55, (3.4, 6.4), AN, seg=14)
body.cyl("z", (1.45, 1.05), 0.6, (6.4, 7.0), "steel", seg=14, tint="#8a8a8a")
# tuerca del canon visible por delante
body.cyl("z", (0, 0.2), 1.4, (-9.3, -9.0), "parkerized", seg=12)

# ---------------------------------------------------------------- receptor inferior
body.box((-1.4, -3.0, -7.6), (1.4, -1.3, 8.6), AN, bevel=0.25, axis="z", tint="#e4e4e4")
body.extrude("x", [(-7.6, -1.3), (-1.2, -1.3), (-1.2, -5.9), (-1.7, -6.7), (-7.9, -6.7), (-8.3, -6.1), (-7.8, -3.2)],
             (-1.45, 1.45), AN, smooth=20)
body.box((-1.4, -2.5, -9.0), (1.4, -1.3, -7.6), AN, bevel=0.3, axis="x")
body.box((-1.4, -3.4, 6.2), (1.4, -1.3, 9.6), AN, bevel=0.3, axis="z")
# guardamonte
body.box((-0.5, -4.95, -1.0), (0.5, -4.55, 4.4), AN, bevel=0.15, axis="z")
body.box((-0.5, -4.95, -1.25), (0.5, -2.95, -0.65), AN, bevel=0.15, axis="y")
# empunadura de pistola (texturizada)
grip = [(2.9, -2.9), (6.7, -2.9), (7.5, -3.5), (9.9, -11.1), (9.6, -11.8), (6.2, -11.7), (5.7, -9.7),
        (5.05, -7.9), (5.25, -7.15), (4.55, -6.0), (3.35, -4.3), (2.85, -3.5)]
body.extrude("x", grip, (-1.35, 1.35), "grip", smooth=35)
body.extrude("x", [(6.1, -11.55), (9.65, -11.55), (9.75, -12.05), (6.1, -12.0)], (-1.38, 1.38), "polymer")
# selector, retenida de cerrojo, retenida de cargador, pasadores
body.cyl("x", (-0.8, -2.2), 0.36, (1.4, 1.62), "steel", seg=10, tint="#777777")
body.box((-1.62, -2.65, -1.25), (-1.45, -1.55, -0.25), AN, bevel=0.05, axis="z")
for (z, y) in ((-8.3, -1.9), (7.6, -2.0), (1.0, -2.4), (3.6, -2.3)):
    screw(body, 1.41, y, z)
    screw(body, -1.41, y, z)
# marcas del selector
body.decal([(-1.42, -2.95, 2.2), (-1.42, -2.95, 7.2), (-1.42, -1.95, 7.2), (-1.42, -1.95, 2.2)], "marking",
           uv=[0.0, 0.0, 0.55, 0.30])
body.decal([(-1.46, -6.0, -7.4), (-1.46, -6.0, -1.8), (-1.46, -5.2, -1.8), (-1.46, -5.2, -7.4)], "marking",
           uv=[0.0, 0.36, 0.75, 0.62])

# ---------------------------------------------------------------- tubo amortiguador y culata
body.cyl("z", (0, 0.55), 1.5, (9.2, 26.0), AN, seg=20)
body.cyl("z", (0, 0.55), 1.78, (9.2, 9.95), "parkerized", seg=12)
body.box((-1.65, -0.9, 9.2), (1.65, 1.1, 9.5), "parkerized", bevel=0.2, axis="z")
stock = m.bone("stock", "body")
stock.extrude("x", [(16.5, 2.45), (28.0, 2.45), (28.7, 2.65), (28.8, -8.9), (28.1, -9.7), (26.7, -9.5), (25.6, -5.6),
                    (24.4, -2.6), (22.8, -1.5), (16.5, -1.45)], (-1.9, 1.9), "polymer", smooth=25)
stock.extrude("x", [(17.2, 2.0), (23.0, 2.0), (23.0, -1.0), (17.2, -1.0)], (-1.95, 1.95), "polymer", tint="#cfcfcf")
stock.extrude("x", [(28.6, 2.75), (29.9, 2.8), (30.0, -9.6), (28.6, -9.7)], (-2.0, 2.0), "rubber")
stock.box((-0.45, -1.95, 14.0), (0.45, -1.3, 18.6), "polymer", bevel=0.15, axis="z")
stock.cyl("x", (20.0, 0.55), 0.55, (-1.98, -1.88), "steel", seg=12, tint="#666666")
stock.cyl("x", (20.0, 0.55), 0.55, (1.88, 1.98), "steel", seg=12, tint="#666666")

# ---------------------------------------------------------------- canon, guardamanos y bocacha
body.cyl("z", (0, 0), 0.78, (-9.0, -46.0), "blued", seg=16)
body.cyl("z", (0, 0), 0.86, (-45.5, -46.0), "blued", seg=16)
body.extrude("z", rect_profile(-2.05, -2.35, 2.05, 1.95, 0.85), (-9.2, -38.0), AN, smooth=20)
body.box((-1.6, -1.9, -38.05), (1.6, 1.5, -37.98), "bore", axis="z")
picatinny(body, -38.0, -9.2, 1.95, 1.05)
mlok_slots(body, -36.5, -11.0, 2.05, -0.2, 0.8, 5, side=1)
mlok_slots(body, -36.5, -11.0, -2.05, -0.2, 0.8, 5, side=-1)
for z in (-12.0, -20.0, -28.0, -36.0):
    screw(body, 2.06, 1.3, z, r=0.15)
    screw(body, -2.06, 1.3, z, r=0.15)
# bocacha apagallamas tipo jaula
body.cyl("z", (0, 0), 1.05, (-46.0, -50.5), "parkerized", seg=16, inner=0.42)
body.cyl("z", (0, 0), 0.41, (-46.0, -50.4), "bore", seg=10)
for ang in (-50, 0, 50, 180):
    body.box((-0.2, 0.7, -50.1), (0.2, 1.09, -47.2), "bore", axis="z", rot=(0, 0, ang), pivot=(0, 0, -48.6))
body.cyl("z", (0, 0), 1.12, (-46.0, -46.5), "parkerized", seg=12)

# ---------------------------------------------------------------- piezas moviles
trig = m.bone("trigger", "body", pivot=(0, -3.0, 1.2))
trig.extrude("x", [(0.95, -3.0), (1.45, -3.0), (1.5, -3.6), (1.3, -4.25), (0.8, -4.55), (0.95, -4.15), (1.05, -3.6)],
             (-0.28, 0.28), "steel", tint="#5a5a5a")

sel = m.bone("selector", "body", pivot=(-1.5, -2.2, 4.6))
sel.cyl("x", (4.6, -2.2), 0.45, (-1.62, -1.4), AN, seg=12)
sel.box((-1.72, -2.42, 3.1), (-1.55, -1.98, 4.6), AN, bevel=0.08, axis="z")

bolt = m.bone("bolt", "body")
bolt.box((1.25, -0.25, -3.2), (1.3, 0.75, 0.8), "steel", axis="x", tint="#b0b0b0")
bolt.box((1.27, 0.0, -2.6), (1.31, 0.45, -1.2), "bore", axis="x")

ch = m.bone("charging_handle", "body")
ch.box((-0.5, 1.3, 9.2), (0.5, 1.85, 10.4), AN, bevel=0.1, axis="z")
ch.box((-1.95, 1.25, 9.95), (1.95, 1.85, 10.95), AN, bevel=0.22, axis="x")
ch.box((-1.95, 1.25, 9.6), (-1.2, 1.85, 10.0), AN, bevel=0.1, axis="x")

mag = m.bone("magazine", "body", pivot=(0, -1.5, -4.4))
mag_prof = [(-1.5, -1.3), (-1.5, -6.0), (-1.9, -10.0), (-2.7, -14.0), (-3.8, -17.6),
            (-9.6, -17.6), (-8.5, -14.0), (-7.6, -10.0), (-7.1, -6.0), (-7.0, -1.3)]
mag.extrude("x", mag_prof, (-1.12, 1.12), "polymer", tint="#d8d8d8", smooth=25)
mag.extrude("x", [(-9.95, -17.45), (-3.45, -17.45), (-3.3, -18.65), (-10.1, -18.65)], (-1.32, 1.32), "polymer",
            tint="#c8c8c8")
for k in range(5):
    y = -12.4 - k * 0.95
    zf = -8.0 - (k * 0.95 + 0.6) * 0.3
    zb = -2.4 - (k * 0.95 + 0.6) * 0.3
    mag.box((1.1, y, zf), (1.2, y + 0.38, zb), "polymer", bevel=0.05, axis="z", tint="#bdbdbd")
    mag.box((-1.2, y, zf), (-1.1, y + 0.38, zb), "polymer", bevel=0.05, axis="z", tint="#bdbdbd")
mag.cyl("z", (0, -1.0), 0.29, (-3.8, -6.5), "brass", seg=10)
mag.cyl("z", (0, -1.0), 0.29, (-6.5, -7.5), "copper", r2=0.06, seg=10)

# ---------------------------------------------------------------- mira de punto rojo
opt = m.bone("optic", "body")
opt.box((-1.25, 2.8, -2.0), (1.25, 4.3, 3.0), AN, bevel=0.3, axis="z")
opt.box((-1.0, 4.2, -1.3), (1.0, 5.3, 2.5), AN, bevel=0.3, axis="z")
opt.cyl("x", (0.5, 3.45), 0.55, (1.25, 1.95), "steel", seg=12, tint="#4a4a4a")
opt.box((1.75, 3.2, 0.1), (1.95, 3.7, 2.4), "steel", bevel=0.08, axis="z", tint="#4a4a4a")
opt.cyl("z", (0, 6.5), 1.55, (-2.6, 3.4), AN, seg=24, inner=1.25)
opt.cyl("z", (0, 6.5), 1.62, (-3.5, -2.6), AN, seg=24, inner=1.36)
opt.cyl("z", (0, 6.5), 1.62, (3.4, 3.9), AN, seg=24, inner=1.36)
opt.cyl("z", (0, 6.5), 1.27, (-2.0, -1.96), "glass", seg=24)
opt.cyl("z", (0, 6.5), 1.27, (3.0, 3.04), "glass", seg=24)
opt.cyl("y", (0, 0.4), 0.75, (7.8, 8.7), AN, seg=16)
opt.cyl("y", (0, 0.4), 0.8, (8.7, 9.05), AN, seg=20, tint="#bbbbbb")
opt.cyl("x", (0.4, 6.5), 0.75, (1.5, 2.4), AN, seg=16)
opt.cyl("x", (0.4, 6.5), 0.8, (2.4, 2.75), AN, seg=20, tint="#bbbbbb")
opt.cyl("x", (1.4, 6.5), 0.85, (-2.6, -1.5), AN, seg=18)
opt.decal([(-0.45, 6.05, -1.9), (0.45, 6.05, -1.9), (0.45, 6.95, -1.9), (-0.45, 6.95, -1.9)], "reticle_dot")

# ---------------------------------------------------------------- localizadores
m.locator("aim", "body", (0, 6.5, 3.9))
m.locator("muzzle", "body", (0, 0, -50.7))
m.locator("eject", "body", (1.4, 0.3, -1.0))
m.locator("rh", "body", (0.0, -6.6, 6.6))
m.locator("lh", "body", (-0.4, -2.9, -25.0))
m.locator("lh_mag", "magazine", (-0.3, -15.0, -6.2))
m.locator("rh_charge", "charging_handle", (1.4, 1.6, 10.7))
m.locator("pivot", "body", (0, -2.0, 4.0))


m.extra["empty_pose"] = {"bolt": [0, 0, 3.2]}
m.extra["flash"] = {"size": 5.5}
m.extra["view"] = {
    "hip": {"pos": [0.17, -0.115, -0.30], "rot": [0.0, 2.0, -4.0]},
    "sprint": {"pos": [0.06, -0.20, -0.20], "rot": [-12.0, 38.0, 18.0]},
    "eye_relief": 0.085,
    "arms": {"scale_w": 0.30, "scale_l": 1.05,
             "right": {"anchor": [0.30, -0.46, 0.30], "twist": 0.0},
             "left": {"anchor": [-0.06, -0.58, -0.12], "twist": 0.0}},
}
save(m)
