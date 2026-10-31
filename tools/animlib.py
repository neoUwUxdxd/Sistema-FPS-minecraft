"""
Formato de animacion por fotogramas clave (gunanims/<arma>.json) y muestreador
de referencia. com.fpsrealista.client.anim.AnimationClip implementa lo mismo.

{
 "clips": {
  "reload": {
    "length": 2.3,
    "bones":  {"magazine": {"pos": [[t, x, y, z, "ease"], ...], "rot": [[t, rx, ry, rz, "ease"], ...]},
               "gun":      {...},     # transformacion de todo el arma alrededor del localizador "pivot"
               "camera":   {"rot": [...]}},   # sacudida de camara (grados)
    "ik":     {"left_hand": {"target": "lh_mag", "keys": [[t, peso, "ease"], ...]},
               "right_hand": {...}},
    "vis":    {"shell": [[t, 0|1], ...]},
    "sounds": [[t, "fpsrealista:mag_out"], ...]
  }
 }
}
Interpolacion (se indica en el fotograma de destino):
  "catmull" (por defecto) | "linear" | "step" | "ease_in" | "ease_out" | "ease_in_out"
Unidades: posicion en cm del modelo, rotacion en grados, tiempo en segundos.
"""
import json


def _ease(kind, t):
    if kind == "linear":
        return t
    if kind == "step":
        return 0.0
    if kind == "ease_in":
        return t * t * t
    if kind == "ease_out":
        u = 1 - t
        return 1 - u * u * u
    if kind == "ease_in_out":
        return t * t * (3 - 2 * t)
    return t


def sample_track(keys, t, dim):
    """keys: lista [t, v1..vdim, (ease)]."""
    if not keys:
        return [0.0] * dim
    if t <= keys[0][0]:
        return list(keys[0][1:1 + dim])
    if t >= keys[-1][0]:
        return list(keys[-1][1:1 + dim])
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        if k0[0] <= t <= k1[0]:
            span = k1[0] - k0[0]
            f = 0.0 if span <= 0 else (t - k0[0]) / span
            ease = k1[1 + dim] if len(k1) > 1 + dim else "catmull"
            if ease == "catmull":
                km = keys[i - 1] if i > 0 else k0
                kp = keys[i + 2] if i + 2 < len(keys) else k1
                out = []
                for d in range(dim):
                    p0, p1, p2, p3 = km[1 + d], k0[1 + d], k1[1 + d], kp[1 + d]
                    f2, f3 = f * f, f * f * f
                    out.append(0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2
                                      + (-p0 + 3 * p1 - 3 * p2 + p3) * f3))
                return out
            g = _ease(ease, f)
            return [k0[1 + d] + (k1[1 + d] - k0[1 + d]) * g for d in range(dim)]
    return list(keys[-1][1:1 + dim])


def sample_clip(clip, t):
    """Devuelve (pose{bone:(pos,rot)}, ik{hand:(target, w)}, vis{bone:bool})."""
    pose = {}
    for bone, ch in clip.get("bones", {}).items():
        p = sample_track(ch.get("pos", []), t, 3)
        r = sample_track(ch.get("rot", []), t, 3)
        pose[bone] = (p, r)
    ik = {}
    for hand, d in clip.get("ik", {}).items():
        w = sample_track(d["keys"], t, 1)[0]
        ik[hand] = (d["target"], max(0.0, min(1.0, w)))
    vis = {}
    for bone, keys in clip.get("vis", {}).items():
        v = 1
        for k in keys:
            if k[0] <= t:
                v = k[1]
        vis[bone] = bool(v)
    return pose, ik, vis


class Clip:
    """Ayudante para escribir clips en Python."""

    def __init__(self, length):
        self.d = {"length": length, "bones": {}, "ik": {}, "vis": {}, "sounds": []}

    def pos(self, bone, *keys):
        self.d["bones"].setdefault(bone, {})["pos"] = [list(k) for k in keys]
        return self

    def rot(self, bone, *keys):
        self.d["bones"].setdefault(bone, {})["rot"] = [list(k) for k in keys]
        return self

    def ik(self, hand, target, *keys):
        self.d["ik"][hand] = {"target": target, "keys": [list(k) for k in keys]}
        return self

    def vis(self, bone, *keys):
        self.d["vis"][bone] = [list(k) for k in keys]
        return self

    def sound(self, t, name):
        self.d["sounds"].append([t, "fpsrealista:" + name])
        return self


def save_clips(path, clips):
    with open(path, "w") as f:
        json.dump({"clips": {k: (v.d if isinstance(v, Clip) else v) for k, v in clips.items()}}, f, indent=1)
