"""Piezas reutilizables para los modelos de armas."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gunlib import Model, bezier, round_rect, circle, rect_profile  # noqa: E402,F401

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "main", "resources", "assets", "fpsrealista", "gunmodels")


def picatinny(b, z0, z1, y0, hw, mat="anodized", tint=None, pitch=1.0):
    """Riel picatinny a lo largo de Z: base y dientes (y0 = cara inferior)."""
    b.box((-hw, y0, z0), (hw, y0 + 0.35, z1), mat, bevel=0.08, axis="z", tint=tint)
    # flancos en cola de milano
    b.box((-hw - 0.12, y0 + 0.35, z0), (hw + 0.12, y0 + 0.55, z1), mat, bevel=0.1, axis="z", tint=tint)
    n = int((z1 - z0) / pitch)
    off = ((z1 - z0) - n * pitch) / 2
    for k in range(n):
        za = z0 + off + k * pitch + 0.18
        b.box((-hw, y0 + 0.55, za), (hw, y0 + 0.85, za + pitch - 0.36), mat, bevel=0.07, axis="x", tint=tint)


def mlok_slots(b, z0, z1, x, y, h, n, side=1, length=2.8, tint="#151517"):
    """Ranuras M-LOK (rebajes oscuros) sobre una cara lateral."""
    step = (z1 - z0) / n
    for k in range(n):
        zc = z0 + step * (k + 0.5)
        if side > 0:
            b.box((x - 0.05, y - h / 2, zc - length / 2), (x + 0.02, y + h / 2, zc + length / 2), "polymer",
                  bevel=0.2, axis="x", tint=tint)
        else:
            b.box((x - 0.02, y - h / 2, zc - length / 2), (x + 0.05, y + h / 2, zc + length / 2), "polymer",
                  bevel=0.2, axis="x", tint=tint)


def screw(b, x, y, z, axis="x", r=0.18, mat="steel", tint="#9a9a9a"):
    if axis == "x":
        b.cyl("x", (z, y), r, (x - 0.05, x + 0.05), mat, seg=8, tint=tint)
    elif axis == "z":
        b.cyl("z", (x, y), r, (z - 0.05, z + 0.05), mat, seg=8, tint=tint)
    else:
        b.cyl("y", (x, z), r, (y - 0.05, y + 0.05), mat, seg=8, tint=tint)


def save(m):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, m.name + ".json")
    m.save(p)
    return p
