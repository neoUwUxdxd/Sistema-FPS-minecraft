"""
Sintetiza todos los sonidos del mod (OGG Vorbis mono, 44.1 kHz) y escribe sounds.json.

Disparos = chasquido supersonico + rafaga de boca (ruido filtrado) + golpe grave
           + mecanismo + reverberacion exterior con ecos (slapback).
Mecanica = impactos metalicos (ruido + modos resonantes amortiguados).
Requiere: numpy, scipy, soundfile, ffmpeg (libvorbis).
"""
import json
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
ROOT = os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "assets", "fpsrealista")
SND = os.path.join(ROOT, "sounds")
rng = np.random.default_rng(42)


def env_exp(n, tau):
    t = np.arange(n) / SR
    return np.exp(-t / tau)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def place(buf, x, t):
    i = int(t * SR)
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[:j - i]


def reverb(x, length=1.4, decay=0.35, echoes=((0.09, 0.30), (0.21, 0.18), (0.42, 0.10)), mix=0.35):
    n = int(length * SR)
    ir = rng.standard_normal(n) * env_exp(n, decay) * 0.02
    ir = lp(ir, 3500)
    for (d, g) in echoes:
        i = int(d * SR)
        if i < n:
            ir[i] += g
    ir[0] = 0
    wet = np.zeros(len(x) + n)
    c = signal.fftconvolve(x, ir)[:len(x) + n]
    wet[:len(c)] = c
    out = np.zeros(len(x) + n)
    out[:len(x)] += x
    out += wet * mix / (np.abs(wet).max() + 1e-9) * np.abs(x).max()
    return out


def metal_click(dur=0.08, modes=(2400, 3900, 6100), tau=0.012, noise=0.6, nf=(1500, 9000), gain=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), *nf) * env_exp(n, tau * 0.35) * noise
    for f in modes:
        f2 = f * rng.uniform(0.97, 1.03)
        x += np.sin(2 * np.pi * f2 * t + rng.uniform(0, 6)) * env_exp(n, tau * rng.uniform(0.6, 1.4)) * 0.35
    return x * gain


def thud(dur=0.12, f=140, tau=0.03, gain=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * env_exp(n, tau)
    x += lp(rng.standard_normal(n), 900) * env_exp(n, tau * 0.4) * 0.5
    return x * gain


def slide(dur=0.12, lo=1200, hi=6000, gain=0.5):
    n = int(dur * SR)
    e = np.sin(np.linspace(0, np.pi, n)) ** 0.6
    return bp(rng.standard_normal(n), lo, hi) * e * gain


def gunshot(body_tau=0.06, crack=1.0, thump_f=70, thump=0.8, bright=7000, mech=None, length=1.6,
            tail=1.4, tail_decay=0.4, low_body=0.6):
    n = int(length * SR)
    buf = np.zeros(n)
    # chasquido supersonico (onda N)
    if crack > 0:
        m = int(0.0012 * SR)
        nw = np.linspace(1, -1, m)
        place(buf, hp(nw, 800) * crack * 1.2, 0.0)
    # rafaga de boca
    m = int(0.35 * SR)
    blast = rng.standard_normal(m)
    attack = np.minimum(1, np.arange(m) / (0.0008 * SR))
    e = attack * (env_exp(m, body_tau) * 0.85 + env_exp(m, body_tau * 4) * 0.15)
    hi_part = lp(hp(blast, 300), bright) * e
    lo_part = lp(blast, 600, order=4) * env_exp(m, body_tau * 1.6) * attack * 3.0 * low_body
    place(buf, hi_part + lo_part, 0.0005)
    # golpe grave
    m = int(0.4 * SR)
    t = np.arange(m) / SR
    sweep = np.sin(2 * np.pi * (thump_f * t + 30 * (1 - np.exp(-t / 0.02)) * 0.02))
    place(buf, sweep * env_exp(m, 0.07) * thump, 0.0)
    if mech is not None:
        for (tt, g) in mech:
            place(buf, metal_click(0.06, (2800, 4500, 7000), 0.01, gain=g), tt)
    out = reverb(buf, length=tail, decay=tail_decay)
    # saturacion suave
    out = np.tanh(out / (np.abs(out).max() + 1e-9) * 2.2)
    return out


def norm(x, peak=0.95):
    x = x - np.mean(x)
    fade = int(0.01 * SR)
    if len(x) > fade * 2:
        x[-fade:] *= np.linspace(1, 0, fade)
    return x / (np.abs(x).max() + 1e-9) * peak


def write(name, x):
    os.makedirs(SND, exist_ok=True)
    x = norm(x)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    sf.write(tmp, x.astype(np.float32), SR, subtype="PCM_16")
    out = os.path.join(SND, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-ac", "1", "-c:a", "libvorbis", "-q:a", "5",
                    out], check=True)
    os.unlink(tmp)


def seq(parts, length):
    buf = np.zeros(int(length * SR))
    for (t, x) in parts:
        place(buf, x, t)
    return buf


SOUNDS = {}


def snd(name, variants=1, dist=16, subtitle=None):
    def deco(fn):
        SOUNDS[name] = (fn, variants, dist, subtitle)
        return fn
    return deco


# ---------------------------------------------------------------- disparos
@snd("pistol_shot", 3, 96, "subtitles.fpsrealista.shot")
def s_pistol(v):
    return gunshot(body_tau=0.035, crack=0.4, thump_f=95, thump=0.5, bright=8000, mech=[(0.012, 0.25)],
                   tail=1.0, tail_decay=0.25, low_body=0.4)


@snd("carbine_shot", 3, 160, "subtitles.fpsrealista.shot")
def s_carbine(v):
    return gunshot(body_tau=0.05, crack=1.0, thump_f=75, thump=0.7, bright=9500, mech=[(0.018, 0.2)],
                   tail=1.5, tail_decay=0.38)


@snd("rifle_shot", 3, 170, "subtitles.fpsrealista.shot")
def s_rifle(v):
    return gunshot(body_tau=0.065, crack=0.9, thump_f=62, thump=0.95, bright=7500, mech=[(0.02, 0.3)],
                   tail=1.6, tail_decay=0.42, low_body=0.8)


@snd("shotgun_shot", 2, 150, "subtitles.fpsrealista.shot")
def s_shotgun(v):
    return gunshot(body_tau=0.09, crack=0.0, thump_f=48, thump=1.2, bright=5500, tail=1.7, tail_decay=0.45,
                   low_body=1.2)


@snd("sniper_shot", 2, 256, "subtitles.fpsrealista.shot")
def s_sniper(v):
    return gunshot(body_tau=0.085, crack=1.4, thump_f=52, thump=1.1, bright=9000, tail=2.4, tail_decay=0.65,
                   low_body=1.0)


@snd("dry_fire", 1, 8, "subtitles.fpsrealista.dry_fire")
def s_dry(v):
    return seq([(0.0, metal_click(0.05, (3200, 5200), 0.006, gain=0.8))], 0.12)


@snd("fire_select", 1, 8, "subtitles.fpsrealista.fire_select")
def s_select(v):
    return seq([(0.0, metal_click(0.04, (2600, 4100), 0.005, gain=0.6)),
                (0.03, metal_click(0.04, (3000, 4700), 0.004, gain=0.4))], 0.12)


# ---------------------------------------------------------------- mecanica
@snd("mag_out", 2, 12, "subtitles.fpsrealista.mag_out")
def s_mag_out(v):
    return seq([(0.0, metal_click(0.06, (1900, 3300), 0.01, gain=0.9)), (0.02, slide(0.14, 900, 4500, 0.35)),
                (0.12, thud(0.1, 220, 0.02, 0.3))], 0.32)


@snd("mag_in", 2, 12, "subtitles.fpsrealista.mag_in")
def s_mag_in(v):
    return seq([(0.0, slide(0.08, 900, 4500, 0.3)), (0.07, thud(0.12, 180, 0.025, 0.9)),
                (0.075, metal_click(0.07, (2100, 3500, 5200), 0.014, gain=1.0))], 0.3)


@snd("slide_back", 1, 12, "subtitles.fpsrealista.slide")
def s_slide_back(v):
    return seq([(0.0, metal_click(0.04, (2500, 4300), 0.006, gain=0.5)), (0.0, slide(0.09, 1500, 7000, 0.5)),
                (0.09, metal_click(0.05, (2200, 3800), 0.01, gain=0.7))], 0.22)


@snd("slide_release", 1, 14, "subtitles.fpsrealista.slide")
def s_slide_rel(v):
    return seq([(0.0, slide(0.04, 1500, 7000, 0.4)), (0.04, metal_click(0.09, (1800, 3100, 5200), 0.018, gain=1.0)),
                (0.04, thud(0.1, 160, 0.02, 0.5))], 0.25)


@snd("charge_back", 1, 12, "subtitles.fpsrealista.charge")
def s_charge_back(v):
    return seq([(0.0, metal_click(0.04, (2000, 3600), 0.006, gain=0.5)), (0.01, slide(0.15, 900, 6000, 0.55)),
                (0.15, metal_click(0.06, (1700, 2900), 0.012, gain=0.8))], 0.3)


@snd("charge_release", 1, 16, "subtitles.fpsrealista.charge")
def s_charge_rel(v):
    return seq([(0.0, slide(0.05, 1200, 7000, 0.4)), (0.05, metal_click(0.12, (1500, 2600, 4400), 0.025, gain=1.0)),
                (0.05, thud(0.12, 130, 0.025, 0.7))], 0.3)


@snd("pump_back", 1, 16, "subtitles.fpsrealista.pump")
def s_pump_back(v):
    return seq([(0.0, metal_click(0.05, (1400, 2500), 0.01, gain=0.6)), (0.0, slide(0.13, 600, 4500, 0.6)),
                (0.12, metal_click(0.08, (1200, 2200, 3600), 0.02, gain=1.0)), (0.12, thud(0.1, 110, 0.03, 0.6))],
               0.3)


@snd("pump_forward", 1, 16, "subtitles.fpsrealista.pump")
def s_pump_fwd(v):
    return seq([(0.0, slide(0.11, 600, 4500, 0.5)), (0.1, metal_click(0.1, (1300, 2400, 3900), 0.02, gain=1.0)),
                (0.1, thud(0.1, 120, 0.03, 0.7))], 0.3)


@snd("shell_insert", 2, 10, "subtitles.fpsrealista.shell_insert")
def s_shell(v):
    return seq([(0.0, slide(0.06, 700, 3500, 0.35)), (0.05, thud(0.08, 260, 0.015, 0.7)),
                (0.05, metal_click(0.05, (2500, 4200), 0.008, gain=0.6))], 0.18)


@snd("bolt_up", 1, 10, "subtitles.fpsrealista.bolt")
def s_bolt_up(v):
    return seq([(0.0, metal_click(0.06, (1800, 3000), 0.012, gain=0.8))], 0.12)


@snd("bolt_back", 1, 12, "subtitles.fpsrealista.bolt")
def s_bolt_back(v):
    return seq([(0.0, slide(0.12, 800, 5500, 0.6)), (0.11, metal_click(0.07, (1600, 2700, 4300), 0.015, gain=0.9))],
               0.25)


@snd("bolt_forward", 1, 12, "subtitles.fpsrealista.bolt")
def s_bolt_fwd(v):
    return seq([(0.0, slide(0.1, 800, 5500, 0.5)), (0.09, metal_click(0.07, (1700, 2900, 4600), 0.015, gain=0.9))],
               0.22)


@snd("bolt_down", 1, 10, "subtitles.fpsrealista.bolt")
def s_bolt_down(v):
    return seq([(0.0, metal_click(0.08, (1500, 2600, 4100), 0.016, gain=1.0)), (0.0, thud(0.08, 170, 0.02, 0.5))],
               0.15)


@snd("gun_draw", 2, 8, "subtitles.fpsrealista.draw")
def s_draw(v):
    n = int(0.35 * SR)
    cloth = lp(hp(rng.standard_normal(n), 400), 3000) * np.sin(np.linspace(0, np.pi, n)) ** 1.5 * 0.4
    return seq([(0.0, cloth), (0.22, metal_click(0.06, (1800, 3200), 0.01, gain=0.5))], 0.4)


@snd("gun_handle", 2, 6, "subtitles.fpsrealista.handle")
def s_handle(v):
    n = int(0.3 * SR)
    cloth = lp(hp(rng.standard_normal(n), 300), 2500) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.35
    return seq([(0.0, cloth), (0.15, metal_click(0.05, (1500, 2600), 0.008, gain=0.3))], 0.35)


@snd("casing", 6, 10, "subtitles.fpsrealista.casing")
def s_casing(v):
    parts = []
    t = 0.0
    g = 0.9
    for _ in range(int(rng.integers(3, 6))):
        f0 = rng.uniform(4800, 7800)
        parts.append((t, metal_click(0.12, (f0, f0 * 1.52, f0 * 2.1), 0.03, noise=0.2, gain=g)))
        t += rng.uniform(0.06, 0.16) * g
        g *= 0.55
    return seq(parts, t + 0.2)


@snd("shell_drop", 3, 10, "subtitles.fpsrealista.casing")
def s_shell_drop(v):
    return seq([(0.0, thud(0.08, 300, 0.012, 0.7)), (0.09, thud(0.06, 340, 0.01, 0.35)),
                (0.0, metal_click(0.06, (3000, 4600), 0.01, gain=0.25))], 0.25)


# ---------------------------------------------------------------- impactos / interfaz
@snd("hitmarker", 1, 4, None)
def s_hit(v):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * env_exp(n, 0.012) + metal_click(0.06, (3600,), 0.008, gain=0.4)[:n]


@snd("headshot", 1, 4, None)
def s_head(v):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 3100 * t) + 0.5 * np.sin(2 * np.pi * 4650 * t)) * env_exp(n, 0.06)
    return x + seq([(0.0, thud(0.1, 200, 0.02, 0.5))], 0.25)


@snd("impact_flesh", 3, 16, "subtitles.fpsrealista.impact")
def s_flesh(v):
    return seq([(0.0, thud(0.14, 95, 0.03, 1.0)), (0.0, lp(rng.standard_normal(int(0.08 * SR)), 1500)
                                                  * env_exp(int(0.08 * SR), 0.015) * 0.7)], 0.2)


@snd("impact_block", 4, 20, "subtitles.fpsrealista.impact")
def s_block(v):
    n = int(0.2 * SR)
    debris = bp(rng.standard_normal(n), 1500, 9000) * env_exp(n, 0.03)
    return seq([(0.0, thud(0.1, 180, 0.015, 0.8)), (0.0, debris * 0.8),
                (0.05, bp(rng.standard_normal(int(0.15 * SR)), 2500, 8000) * env_exp(int(0.15 * SR), 0.04) * 0.3)],
               0.3)


@snd("whizz", 3, 24, "subtitles.fpsrealista.whizz")
def s_whizz(v):
    n = int(0.35 * SR)
    t = np.linspace(-1, 1, n)
    e = np.exp(-(t * 3) ** 2)
    sweep = bp(rng.standard_normal(n), 1800, 7000) * e
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(1400, 700, n)) / SR) * e * 0.3
    return sweep + tone


@snd("glass_hit", 2, 20, "subtitles.fpsrealista.impact")
def s_glass(v):
    parts = [(0.0, thud(0.06, 400, 0.01, 0.5))]
    for k in range(10):
        f0 = rng.uniform(3000, 9000)
        parts.append((rng.uniform(0, 0.25), metal_click(0.15, (f0, f0 * 1.7), 0.04, noise=0.3, gain=rng.uniform(0.2, 0.6))))
    return seq(parts, 0.5)


def main():
    meta = {}
    for name, (fn, variants, dist, sub) in SOUNDS.items():
        files = []
        for v in range(variants):
            fname = name if variants == 1 else f"{name}_{v}"
            write(fname, fn(v))
            files.append({"name": f"fpsrealista:{fname}", "attenuation_distance": dist})
        entry = {"sounds": files}
        if sub:
            entry["subtitle"] = sub
        meta[name] = entry
    with open(os.path.join(ROOT, "sounds.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(len(SOUNDS), "sonidos ->", os.path.abspath(SND))
    print(json.dumps(sorted(SOUNDS.keys())))


if __name__ == "__main__":
    main()
