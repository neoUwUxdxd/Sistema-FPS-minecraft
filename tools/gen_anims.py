"""
Genera las animaciones por fotogramas clave de todas las armas
(assets/fpsrealista/gunanims/<arma>.json).

Convenciones del hueso "gun" (todo el arma, alrededor del localizador "pivot"):
  rot x > 0  -> boca hacia arriba      rot y > 0 -> boca hacia la izquierda
  rot z < 0  -> el arma rueda a la derecha (lomo hacia la derecha)
Posiciones en cm del modelo. Los eventos que empiezan por "!" no son sonidos:
  !eject  -> expulsa una vaina      !mag_drop -> (reservado)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from animlib import Clip, save_clips  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "assets", "fpsrealista", "gunanims")
Z3 = (0.0, 0.0, 0.0)


def k(t, x, y, z, e=None):
    return (t, x, y, z) if e is None else (t, x, y, z, e)


def draw_clip(length, lift=12.0, spin=25.0):
    c = Clip(length)
    c.pos("gun", k(0, 0, -lift, 6), k(length * 0.7, 0, 0.6, -0.5, "ease_out"), k(length, 0, 0, 0))
    c.rot("gun", k(0, -40, 12, spin), k(length * 0.7, 2.5, -0.5, -1.5, "ease_out"), k(length, 0, 0, 0))
    c.rot("camera", k(0, 0, 0, 0), k(length * 0.5, 0.4, 0, -0.3), k(length, 0, 0, 0))
    c.sound(0.0, "gun_draw")
    return c


def inspect_clip(length, extra=None):
    c = Clip(length)
    L = length
    c.pos("gun", k(0, 0, 0, 0), k(0.12 * L, -2, 3.5, 2, "ease_in_out"), k(0.42 * L, -2.5, 3.8, 2.2),
          k(0.55 * L, -1.5, 4.5, 1.5, "ease_in_out"), k(0.82 * L, -1.8, 4.2, 1.8), k(L, 0, 0, 0, "ease_in_out"))
    c.rot("gun", k(0, 0, 0, 0), k(0.12 * L, 6, -38, 28, "ease_in_out"), k(0.42 * L, 4, -42, 32),
          k(0.55 * L, 18, 22, -42, "ease_in_out"), k(0.82 * L, 15, 25, -45), k(L, 0, 0, 0, "ease_in_out"))
    c.sound(0.05, "gun_handle")
    c.sound(0.5 * L, "gun_handle")
    if extra:
        extra(c)
    return c


def mag_reload(length, mag_out_t, mag_gone_t, mag_back_t, mag_in_t, drop, hook=None, tilt=(12, -10, -20),
               gun_off=(-4.0, 7.0, -12.0), hand="lh_mag"):
    """Recarga generica de cargador. drop: posicion del cargador fuera de pantalla."""
    c = Clip(length)
    L = length
    end = mag_in_t + 0.35
    c.rot("gun", k(0, 0, 0, 0), k(mag_out_t - 0.05, *tilt, "ease_in_out"),
          k(mag_in_t - 0.02, tilt[0] * 0.8, tilt[1] * 0.8, tilt[2] * 0.85),
          k(mag_in_t + 0.06, tilt[0] * 0.8 - 4, tilt[1] * 0.8, tilt[2] * 0.85 - 2, "ease_out"),
          k(end + 0.15, tilt[0] * 0.3, tilt[1] * 0.3, tilt[2] * 0.3), k(L, 0, 0, 0, "ease_in_out"))
    c.pos("gun", k(0, 0, 0, 0), k(mag_out_t - 0.05, *gun_off, "ease_in_out"),
          k(mag_in_t - 0.02, *gun_off), k(mag_in_t + 0.06, gun_off[0], gun_off[1] + 0.9, gun_off[2], "ease_out"),
          k(L, 0, 0, 0, "ease_in_out"))
    if hook is None:
        c.pos("magazine", k(0, 0, 0, 0), k(mag_out_t, 0, 0, 0), k(mag_out_t + 0.12, drop[0] * 0.1, drop[1] * 0.1,
                                                                    drop[2] * 0.1, "ease_in"),
              k(mag_gone_t, *drop, "ease_in"), k(mag_back_t, *drop, "step"),
              k(mag_in_t - 0.14, drop[0] * 0.08, drop[1] * 0.12, drop[2] * 0.12, "ease_out"),
              k(mag_in_t, 0, 0, 0, "ease_in"))
        c.rot("magazine", k(0, 0, 0, 0), k(mag_out_t + 0.12, 0, 0, 0), k(mag_gone_t, -20, 10, 25, "ease_in"),
              k(mag_back_t, 15, -10, -20, "step"), k(mag_in_t - 0.14, 2, 0, 0, "ease_out"), k(mag_in_t, 0, 0, 0))
    else:
        hook(c)
    c.ik("left_hand", hand, (0, 0.0), (mag_out_t - 0.12, 1.0, "ease_in_out"), (mag_in_t + 0.05, 1.0),
         (end, 0.0, "ease_in_out"))
    c.rot("camera", k(0, 0, 0, 0), k(mag_out_t, 0.6, 0, -0.4), k(mag_out_t + 0.2, 0, 0, 0),
          k(mag_in_t, 0, 0, 0), k(mag_in_t + 0.05, 1.2, 0.2, 0.6), k(mag_in_t + 0.3, 0, 0, 0))
    c.sound(mag_out_t, "mag_out")
    c.sound(mag_in_t - 0.02, "mag_in")
    c.sound(0.05, "gun_handle")
    return c


# =============================================================================
def pistol():
    clips = {}
    clips["draw"] = draw_clip(0.45, lift=10, spin=15)
    c = Clip(0.08)
    c.pos("slide", k(0, 0, 0, 0), k(0.022, 0, 0, 2.8, "ease_out"), k(0.075, 0, 0, 0, "ease_in"))
    c.rot("trigger", k(0, -14, 0, 0), k(0.05, -14, 0, 0), k(0.08, 0, 0, 0))
    c.sound(0.02, "!eject")
    clips["fire"] = c
    drop = (0.0, -32.0, 10.5)
    clips["reload"] = mag_reload(1.6, 0.28, 0.6, 0.85, 1.2, drop, tilt=(18, 6, -18), gun_off=(-3.0, 5.0, 2.0))
    ce = mag_reload(1.95, 0.28, 0.6, 0.85, 1.2, drop, tilt=(18, 6, -18), gun_off=(-3.0, 5.0, 2.0))
    ce.pos("slide", k(0, 0, 0, 2.6), k(1.5, 0, 0, 2.6), k(1.56, 0, 0, 0, "ease_in"))
    ce.sound(1.52, "slide_release")
    clips["reload_empty"] = ce

    def press_check(c):
        c.pos("slide", k(0, 0, 0, 0), k(0.25 * 2.6, 0, 0, 0), k(0.32 * 2.6, 0, 0, 1.3, "ease_out"),
              k(0.42 * 2.6, 0, 0, 1.3), k(0.47 * 2.6, 0, 0, 0, "ease_in"))
        c.ik("left_hand", "lh_slide", (0, 0.0), (0.22 * 2.6, 1.0), (0.48 * 2.6, 1.0), (0.56 * 2.6, 0.0))
        c.sound(0.32 * 2.6, "slide_back")
        c.sound(0.47 * 2.6, "slide_release")
    clips["inspect"] = inspect_clip(2.6, press_check)
    return clips


def carbine():
    clips = {}
    clips["draw"] = draw_clip(0.6)
    c = Clip(0.07)
    c.pos("bolt", k(0, 0, 0, 0), k(0.02, 0, 0, 3.2, "ease_out"), k(0.065, 0, 0, 0, "ease_in"))
    c.rot("trigger", k(0, -12, 0, 0), k(0.045, -12, 0, 0), k(0.07, 0, 0, 0))
    c.sound(0.02, "!eject")
    clips["fire"] = c
    drop = (-4.0, -34.0, 6.0)
    clips["reload"] = mag_reload(2.2, 0.42, 0.75, 1.05, 1.5, drop)
    ce = mag_reload(2.75, 0.42, 0.75, 1.05, 1.5, drop)
    ce.ik("left_hand", "lh_mag", (0, 0.0), (0.3, 1.0, "ease_in_out"), (1.55, 1.0), (1.75, 0.0, "ease_in_out"))
    ce.ik("right_hand", "rh_charge", (0, 0.0), (1.7, 0.0), (1.92, 1.0, "ease_in_out"), (2.22, 1.0),
          (2.5, 0.0, "ease_in_out"))
    ce.pos("charging_handle", k(0, 0, 0, 0), k(1.95, 0, 0, 0), k(2.1, 0, 0, 6.5, "ease_out"), k(2.16, 0, 0, 6.5),
           k(2.2, 0, 0, 0, "ease_in"))
    ce.pos("bolt", k(0, 0, 0, 3.2), k(1.95, 0, 0, 3.2), k(2.1, 0, 0, 7.5, "ease_out"), k(2.16, 0, 0, 7.5),
           k(2.2, 0, 0, 0, "ease_in"))
    ce.rot("gun", k(0, 0, 0, 0), k(0.37, 10, -8, -28, "ease_in_out"), k(1.48, 8, -6.4, -24),
           k(1.56, 4, -6.4, -26, "ease_out"), k(1.9, 14, -4, -6, "ease_in_out"), k(2.1, 16, -4, -5),
           k(2.22, 12, -3, -8, "ease_out"), k(2.75, 0, 0, 0, "ease_in_out"))
    ce.sound(2.0, "charge_back")
    ce.sound(2.18, "charge_release")
    clips["reload_empty"] = ce
    clips["inspect"] = inspect_clip(3.2)
    return clips


def rifle():
    clips = {}
    clips["draw"] = draw_clip(0.65)
    c = Clip(0.09)
    c.pos("bolt", k(0, 0, 0, 0), k(0.03, 0, 0, 9.0, "ease_out"), k(0.085, 0, 0, 0, "ease_in"))
    c.rot("trigger", k(0, -12, 0, 0), k(0.05, -12, 0, 0), k(0.09, 0, 0, 0))
    c.sound(0.03, "!eject")
    clips["fire"] = c

    def rock(t_out, t_gone, t_back, t_in):
        def f(c):
            c.pos("magazine", k(0, 0, 0, 0), k(t_out, 0, 0, 0), k(t_out + 0.15, 0, -1.0, 0, "ease_out"),
                  k(t_gone, -6, -34, -8, "ease_in"), k(t_back, -6, -34, -8, "step"),
                  k(t_in - 0.22, 0, -1.6, 0, "ease_out"), k(t_in, 0, 0, 0, "ease_in"))
            c.rot("magazine", k(0, 0, 0, 0), k(t_out, 0, 0, 0), k(t_out + 0.15, 24, 0, 0, "ease_out"),
                  k(t_gone, 45, 10, 20, "ease_in"), k(t_back, 40, -10, -10, "step"),
                  k(t_in - 0.22, 22, 0, 0, "ease_out"), k(t_in, 0, 0, 0, "ease_in"))
        return f

    clips["reload"] = mag_reload(2.4, 0.5, 0.85, 1.15, 1.72, None, hook=rock(0.5, 0.85, 1.15, 1.72),
                                 tilt=(10, -8, -22))
    ce = mag_reload(3.05, 0.5, 0.85, 1.15, 1.72, None, hook=rock(0.5, 0.85, 1.15, 1.72), tilt=(10, -8, -22))
    ce.ik("right_hand", "rh_bolt", (0, 0.0), (1.95, 0.0), (2.18, 1.0, "ease_in_out"), (2.5, 1.0),
          (2.8, 0.0, "ease_in_out"))
    ce.pos("bolt", k(0, 0, 0, 0), k(2.2, 0, 0, 0), k(2.38, 0, 0, 9.0, "ease_out"), k(2.44, 0, 0, 9.0),
           k(2.5, 0, 0, 0, "ease_in"))
    ce.rot("gun", k(0, 0, 0, 0), k(0.45, 8, -6, -30, "ease_in_out"), k(1.7, 6.4, -4.8, -25.5),
           k(1.78, 2.4, -4.8, -27.5, "ease_out"), k(2.15, 6, 4, 18, "ease_in_out"), k(2.4, 8, 4, 20),
           k(2.52, 5, 3, 16, "ease_out"), k(3.05, 0, 0, 0, "ease_in_out"))
    ce.sound(2.3, "charge_back")
    ce.sound(2.48, "charge_release")
    clips["reload_empty"] = ce
    clips["inspect"] = inspect_clip(3.2)
    return clips


def shotgun():
    clips = {}
    clips["draw"] = draw_clip(0.7)
    c = Clip(0.1)
    c.rot("trigger", k(0, -14, 0, 0), k(0.06, -14, 0, 0), k(0.1, 0, 0, 0))
    clips["fire"] = c
    p = Clip(0.62)
    p.pos("pump", k(0, 0, 0, 0), k(0.06, 0, 0, 0), k(0.22, 0, 0, 8.6, "ease_out"), k(0.27, 0, 0, 8.6),
          k(0.42, 0, 0, 0, "ease_in"))
    p.rot("gun", k(0, 0, 0, 0), k(0.22, -2.5, -2, -3, "ease_out"), k(0.42, 1.5, 0, 0, "ease_in"),
          k(0.62, 0, 0, 0, "ease_in_out"))
    p.pos("gun", k(0, 0, 0, 0), k(0.22, 0, -0.4, 0.8, "ease_out"), k(0.42, 0, 0.2, -0.3, "ease_in"),
          k(0.62, 0, 0, 0))
    p.rot("camera", k(0, 0, 0, 0), k(0.24, 0.3, 0, 0.2), k(0.44, -0.2, 0, -0.1), k(0.62, 0, 0, 0))
    p.sound(0.1, "pump_back")
    p.sound(0.22, "!eject")
    p.sound(0.36, "pump_forward")
    clips["pump"] = p
    tilt = (10, -6, -38)
    s = Clip(0.45)
    s.rot("gun", k(0, 0, 0, 0), k(0.45, *tilt, "ease_in_out"))
    s.pos("gun", k(0, 0, 0, 0), k(0.45, -2.5, 1.5, 1.0, "ease_in_out"))
    s.ik("left_hand", "lh_shell", (0, 0.0), (0.4, 1.0, "ease_in_out"))
    s.vis("shell", (0, 0), (0.2, 1))
    s.pos("shell", k(0, -7, -16, 5), k(0.45, -7, -16, 5))
    s.sound(0.05, "gun_handle")
    clips["reload_start"] = s
    lp = Clip(0.55)
    lp.rot("gun", k(0, *tilt), k(0.36, *tilt), k(0.4, tilt[0] - 2, tilt[1], tilt[2] - 1.5, "ease_out"),
           k(0.55, *tilt, "ease_in_out"))
    lp.pos("gun", k(0, -2.5, 1.5, 1.0), k(0.55, -2.5, 1.5, 1.0))
    lp.pos("shell", k(0, -7, -16, 5), k(0.22, 0, -0.5, 0.5, "ease_out"), k(0.3, 0, 3.0, 0.0, "ease_in"),
           k(0.4, 0, 3.0, -7.0, "ease_in"), k(0.41, -7, -16, 5, "step"), k(0.55, -7, -16, 5))
    lp.vis("shell", (0, 1), (0.4, 0), (0.46, 1))
    lp.ik("left_hand", "lh_shell", (0, 1.0), (0.55, 1.0))
    lp.sound(0.36, "shell_insert")
    lp.rot("camera", k(0, 0, 0, 0), k(0.38, 0, 0, 0), k(0.42, 0.5, 0, 0.3), k(0.55, 0, 0, 0))
    clips["reload_loop"] = lp
    e = Clip(0.5)
    e.rot("gun", k(0, *tilt), k(0.5, 0, 0, 0, "ease_in_out"))
    e.pos("gun", k(0, -2.5, 1.5, 1.0), k(0.5, 0, 0, 0, "ease_in_out"))
    e.ik("left_hand", "lh_shell", (0, 1.0), (0.4, 0.0, "ease_in_out"))
    e.vis("shell", (0, 0))
    clips["reload_end"] = e
    clips["inspect"] = inspect_clip(3.0)
    return clips


def sniper():
    clips = {}
    clips["draw"] = draw_clip(0.8)
    c = Clip(0.1)
    c.rot("trigger", k(0, -12, 0, 0), k(0.06, -12, 0, 0), k(0.1, 0, 0, 0))
    clips["fire"] = c

    def bolt(c, t0):
        c.ik("right_hand", "rh_bolt", (t0, 0.0), (t0 + 0.18, 1.0, "ease_in_out"), (t0 + 0.88, 1.0),
             (t0 + 1.08, 0.0, "ease_in_out"))
        c.rot("bolt", k(0, 0, 0, 0), k(t0 + 0.18, 0, 0, 0), k(t0 + 0.3, 0, 0, 62, "ease_out"),
              k(t0 + 0.76, 0, 0, 62), k(t0 + 0.86, 0, 0, 0, "ease_in"))
        c.pos("bolt", k(0, 0, 0, 0), k(t0 + 0.3, 0, 0, 0), k(t0 + 0.5, 0, 0, 9.5, "ease_out"),
              k(t0 + 0.56, 0, 0, 9.5), k(t0 + 0.74, 0, 0, 0, "ease_in"))
        c.sound(t0 + 0.24, "bolt_up")
        c.sound(t0 + 0.44, "bolt_back")
        c.sound(t0 + 0.5, "!eject")
        c.sound(t0 + 0.7, "bolt_forward")
        c.sound(t0 + 0.84, "bolt_down")

    b = Clip(1.15)
    bolt(b, 0.0)
    b.rot("gun", k(0, 0, 0, 0), k(0.3, 1.5, 1, 6, "ease_in_out"), k(0.5, -1.5, 1.5, 7), k(0.74, 1.0, 1, 6),
          k(1.15, 0, 0, 0, "ease_in_out"))
    b.pos("gun", k(0, 0, 0, 0), k(0.5, 0, 0, 0.8), k(1.15, 0, 0, 0, "ease_in_out"))
    clips["bolt"] = b
    drop = (0.0, -32.0, 2.0)
    clips["reload"] = mag_reload(2.6, 0.5, 0.85, 1.2, 1.65, drop, tilt=(8, -6, -22))
    ce = mag_reload(3.45, 0.5, 0.85, 1.2, 1.65, drop, tilt=(8, -6, -22))
    bolt(ce, 2.2)
    ce.rot("gun", k(0, 0, 0, 0), k(0.45, 8, -6, -22, "ease_in_out"), k(1.63, 6.4, -4.8, -18.7),
           k(1.71, 2.4, -4.8, -20.7, "ease_out"), k(2.2, 2, 1, 6, "ease_in_out"), k(2.7, -1.5, 1.5, 7),
           k(3.0, 1.0, 1, 6), k(3.45, 0, 0, 0, "ease_in_out"))
    clips["reload_empty"] = ce
    clips["inspect"] = inspect_clip(3.0)
    return clips


GUNS = {"pistol_9mm": pistol, "carbine_556": carbine, "rifle_762": rifle, "shotgun_12g": shotgun,
        "sniper_308": sniper}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in GUNS.items():
        save_clips(os.path.join(OUT, name + ".json"), fn())
        print("ok", name)
