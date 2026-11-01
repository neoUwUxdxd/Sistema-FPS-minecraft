// @ts-check
/**
 * FPS Realista para Minecraft Bedrock — lógica de armas (Script API @minecraft/server 2.4.0).
 *
 * Controles:
 *   Mantener USAR (clic derecho / botón Disparar)  -> disparar (automático mientras se mantiene)
 *   Agacharse (mantener)                           -> apuntar con la mira (zoom)
 *   Agacharse + Saltar                             -> recargar (con el cargador lleno: inspeccionar)
 *   Doble toque de Agacharse                       -> cambiar modo de fuego
 *
 * La munición del cargador se guarda en el jugador por tipo de arma (propiedades dinámicas),
 * así no hay que reescribir el objeto en cada disparo (lo que reiniciaría su animación).
 * Las animaciones del arma (attachable) se sincronizan mediante propiedades de entidad del jugador.
 */
import {
    world,
    system,
    EquipmentSlot,
    InputButton,
    ButtonState,
    EntityDamageCause,
    MolangVariableMap,
    GameMode,
} from "@minecraft/server";

const NS = "fps";
const TICK = 20;

/**
 * @typedef {Object} Gun
 * @property {string} name
 * @property {string} ammo
 * @property {number} mag
 * @property {boolean} chamber
 * @property {string[]} modes
 * @property {number} rpm
 * @property {number} burst
 * @property {number} damage
 * @property {number} head
 * @property {number} range
 * @property {number} fs   inicio de la caída de daño (bloques)
 * @property {number} fe   fin de la caída de daño
 * @property {number} fmin factor mínimo
 * @property {number} pellets
 * @property {number} hip
 * @property {number} ads
 * @property {number} move
 * @property {number} bloom
 * @property {number} maxBloom
 * @property {number} rv   retroceso vertical (grados)
 * @property {number} rh   retroceso horizontal
 * @property {number} radsf factor de retroceso apuntando
 * @property {number} fov  FOV al apuntar
 * @property {number} draw
 * @property {number} reload
 * @property {number} reloadEmpty
 * @property {number} inspect
 * @property {number} [cycle]  duración del ciclado manual (corredera/cerrojo)
 * @property {number[]} [shell] recarga cartucho a cartucho: [inicio, por cartucho, final]
 * @property {number} pen
 * @property {number} kb
 * @property {string} sound
 * @property {number} shake
 */

/** @type {Record<string, Gun>} */
const GUNS = {
    [`${NS}:pistol_9mm`]: {
        name: "Pistola 9 mm", ammo: `${NS}:ammo_9mm`, mag: 15, chamber: true, modes: ["semi"], rpm: 450, burst: 1,
        damage: 6, head: 2, range: 120, fs: 15, fe: 50, fmin: 0.55, pellets: 1, hip: 1.6, ads: 0.25, move: 1.0,
        bloom: 0.5, maxBloom: 2.5, rv: 2.2, rh: 0.7, radsf: 0.75, fov: 62, draw: 0.45, reload: 1.6, reloadEmpty: 1.95,
        inspect: 2.6, pen: 1, kb: 0.15, sound: `${NS}.pistol_shot`, shake: 0.02,
    },
    [`${NS}:carbine_556`]: {
        name: "Carabina 5,56", ammo: `${NS}:ammo_556`, mag: 30, chamber: true, modes: ["auto", "burst", "semi"], rpm: 800,
        burst: 3, damage: 6.5, head: 2, range: 250, fs: 40, fe: 140, fmin: 0.6, pellets: 1, hip: 2.6, ads: 0.08, move: 1.8,
        bloom: 0.25, maxBloom: 2.2, rv: 0.85, rh: 0.45, radsf: 0.65, fov: 55, draw: 0.6, reload: 2.2, reloadEmpty: 2.75,
        inspect: 3.2, pen: 2, kb: 0.15, sound: `${NS}.carbine_shot`, shake: 0.015,
    },
    [`${NS}:rifle_762`]: {
        name: "Fusil 7,62", ammo: `${NS}:ammo_762`, mag: 30, chamber: true, modes: ["auto", "semi"], rpm: 600, burst: 1,
        damage: 8, head: 2, range: 250, fs: 30, fe: 120, fmin: 0.55, pellets: 1, hip: 3.0, ads: 0.12, move: 2.0,
        bloom: 0.35, maxBloom: 2.8, rv: 1.35, rh: 0.7, radsf: 0.7, fov: 58, draw: 0.65, reload: 2.4, reloadEmpty: 3.05,
        inspect: 3.2, pen: 2, kb: 0.2, sound: `${NS}.rifle_shot`, shake: 0.025,
    },
    [`${NS}:shotgun_12g`]: {
        name: "Escopeta cal. 12", ammo: `${NS}:ammo_12g`, mag: 6, chamber: true, modes: ["semi"], rpm: 70, burst: 1,
        damage: 3.2, head: 1.5, range: 60, fs: 8, fe: 30, fmin: 0.2, pellets: 9, hip: 4.5, ads: 3.2, move: 1.0,
        bloom: 0, maxBloom: 0, rv: 5.5, rh: 1.2, radsf: 0.85, fov: 62, draw: 0.7, reload: 0, reloadEmpty: 0,
        inspect: 3.0, cycle: 0.62, shell: [0.45, 0.55, 0.5], pen: 1, kb: 0.35, sound: `${NS}.shotgun_shot`, shake: 0.06,
    },
    [`${NS}:sniper_308`]: {
        name: "Rifle .308", ammo: `${NS}:ammo_308`, mag: 5, chamber: true, modes: ["semi"], rpm: 60, burst: 1,
        damage: 26, head: 2.5, range: 400, fs: 120, fe: 350, fmin: 0.7, pellets: 1, hip: 6.0, ads: 0, move: 4.0,
        bloom: 0, maxBloom: 0, rv: 6.0, rh: 0.9, radsf: 0.6, fov: 12, draw: 0.8, reload: 2.6, reloadEmpty: 3.45,
        inspect: 3.0, cycle: 1.15, pen: 3, kb: 0.4, sound: `${NS}.sniper_shot`, shake: 0.07,
    },
};
const GUN_IDS = Object.keys(GUNS);
const MODE_NAMES = { semi: "SEMI", burst: "RÁFAGA", auto: "AUTO" };

// códigos de animación (propiedad fps:anim) — deben coincidir con build_bedrock.py
const ANIM = { idle: 0, draw: 1, reload: 2, reload_empty: 3, inspect: 4, cycle: 5, shell_start: 6, shell_loop: 7, shell_end: 8 };

const CONFIG = { breakGlass: true, infiniteCreative: true, damageMultiplier: 1.0 };

/**
 * @typedef {Object} State
 * @property {string|null} gunId
 * @property {number} slot
 * @property {boolean} held
 * @property {number} lastUse
 * @property {boolean} prevWant
 * @property {boolean} semiQueued
 * @property {number} nextShot
 * @property {number} burstLeft
 * @property {string|null} action
 * @property {number} actionEnd
 * @property {number} shellsLeft
 * @property {boolean} shellFromEmpty
 * @property {number} cycleAt
 * @property {number} bloom
 * @property {number} lastShot
 * @property {number} recoilDebt
 * @property {boolean} aimed
 * @property {number} lastSneakPress
 * @property {number} seq
 * @property {number} shot
 * @property {boolean} dryClicked
 * @property {number} hitTick
 * @property {boolean} hitHead
 */

/** @type {Map<string, State>} */
const STATES = new Map();
/** @type {Map<string, number>} */
const LAST_HIT = new Map();
let tick = 0;

/** @param {import("@minecraft/server").Player} p */
function st(p) {
    let s = STATES.get(p.id);
    if (!s) {
        s = {
            gunId: null, slot: -1, held: false, lastUse: -100, prevWant: false, semiQueued: false, nextShot: 0,
            burstLeft: 0, action: null, actionEnd: 0, shellsLeft: 0, shellFromEmpty: false, cycleAt: -1, bloom: 0,
            lastShot: -100, recoilDebt: 0, aimed: false, lastSneakPress: -100, seq: 0, shot: 0, dryClicked: false,
            hitTick: -100, hitHead: false,
        };
        STATES.set(p.id, s);
    }
    return s;
}

// --------------------------------------------------------------------------- utilidades
/** @param {import("@minecraft/server").Player} p */
function heldItem(p) {
    const eq = p.getComponent("minecraft:equippable");
    return eq ? eq.getEquipment(EquipmentSlot.Mainhand) : undefined;
}

/** @param {import("@minecraft/server").Player} p */
function creative(p) {
    return p.getGameMode() === GameMode.Creative && CONFIG.infiniteCreative;
}

/** @param {import("@minecraft/server").Player} p @param {string} gunId */
function getAmmo(p, gunId) {
    const v = p.getDynamicProperty(`${NS}:ammo:${gunId}`);
    if (typeof v === "number") return v;
    const g = GUNS[gunId];
    p.setDynamicProperty(`${NS}:ammo:${gunId}`, g.mag);
    return g.mag;
}

/** @param {import("@minecraft/server").Player} p @param {string} gunId @param {number} n */
function setAmmo(p, gunId, n) {
    p.setDynamicProperty(`${NS}:ammo:${gunId}`, Math.max(0, n));
    trySetProp(p, `${NS}:empty`, n <= 0);
}

/** @param {import("@minecraft/server").Player} p @param {string} gunId */
function getModeIndex(p, gunId) {
    const v = p.getDynamicProperty(`${NS}:mode:${gunId}`);
    return typeof v === "number" ? v % GUNS[gunId].modes.length : 0;
}

/** @param {import("@minecraft/server").Player} p @param {string} id @param {boolean|number} v */
function trySetProp(p, id, v) {
    try {
        p.setProperty(id, v);
    } catch (e) {
        // si el player.json del pack fue sobrescrito por otro add-on, las animaciones no se sincronizan
    }
}

/** @param {import("@minecraft/server").Player} p @param {string} itemId */
function countAmmo(p, itemId) {
    const inv = p.getComponent("minecraft:inventory");
    if (!inv || !inv.container) return 0;
    const c = inv.container;
    let n = 0;
    for (let i = 0; i < c.size; i++) {
        const it = c.getItem(i);
        if (it && it.typeId === itemId) n += it.amount;
    }
    return n;
}

/** @param {import("@minecraft/server").Player} p @param {string} itemId @param {number} want */
function takeAmmo(p, itemId, want) {
    const inv = p.getComponent("minecraft:inventory");
    if (!inv || !inv.container) return 0;
    const c = inv.container;
    let got = 0;
    for (let i = 0; i < c.size && got < want; i++) {
        const it = c.getItem(i);
        if (!it || it.typeId !== itemId) continue;
        const t = Math.min(want - got, it.amount);
        got += t;
        if (t >= it.amount) c.setItem(i, undefined);
        else {
            it.amount -= t;
            c.setItem(i, it);
        }
    }
    return got;
}

/** @param {import("@minecraft/server").Player} p @param {number} code */
function playAction(p, code) {
    const s = st(p);
    s.seq = (s.seq % 999) + 1;
    trySetProp(p, `${NS}:anim`, code);
    trySetProp(p, `${NS}:seq`, s.seq);
}

/** @param {import("@minecraft/server").Player} p @param {string} sound @param {number} [vol] @param {number} [pitch] */
function sfx(p, sound, vol = 1, pitch = 1) {
    try {
        p.dimension.playSound(sound, p.getHeadLocation(), { volume: vol, pitch });
    } catch (e) { /* sonido no disponible */ }
}

/** @param {import("@minecraft/server").Vector3} a @param {import("@minecraft/server").Vector3} b @param {number} k */
const add = (a, b, k = 1) => ({ x: a.x + b.x * k, y: a.y + b.y * k, z: a.z + b.z * k });
/** @param {import("@minecraft/server").Vector3} a @param {import("@minecraft/server").Vector3} b */
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
/** @param {import("@minecraft/server").Vector3} v */
const norm = (v) => {
    const l = Math.hypot(v.x, v.y, v.z) || 1;
    return { x: v.x / l, y: v.y / l, z: v.z / l };
};
/** @param {import("@minecraft/server").Vector3} a @param {import("@minecraft/server").Vector3} b */
const cross = (a, b) => ({ x: a.y * b.z - a.z * b.y, y: a.z * b.x - a.x * b.z, z: a.x * b.y - a.y * b.x });

/** Desvía la dirección dentro de un cono (grados), concentrado hacia el centro. */
function spread(dir, deg) {
    if (deg <= 0.0001) return dir;
    const r = Math.min(1, Math.abs(Math.sqrt(Math.random()) * 0.65 + (Math.random() + Math.random() + Math.random() - 1.5) * 0.2));
    const ang = (deg * Math.PI / 180) * r;
    const th = Math.random() * Math.PI * 2;
    const up = Math.abs(dir.y) > 0.99 ? { x: 1, y: 0, z: 0 } : { x: 0, y: 1, z: 0 };
    const right = norm(cross(dir, up));
    const up2 = norm(cross(right, dir));
    const t = Math.tan(ang);
    return norm(add(add(dir, right, Math.cos(th) * t), up2, Math.sin(th) * t));
}

/** @param {string} id */
const isGlass = (id) => id.includes("glass");

/** @param {Gun} g @param {number} d */
function falloff(g, d) {
    if (d <= g.fs) return 1;
    if (d >= g.fe) return g.fmin;
    return 1 + (g.fmin - 1) * ((d - g.fs) / (g.fe - g.fs));
}

/**
 * @param {import("@minecraft/server").Dimension} dim
 * @param {string} effect
 * @param {import("@minecraft/server").Vector3} loc
 * @param {import("@minecraft/server").Vector3} [dir]
 * @param {number} [speed]
 * @param {number} [life]
 */
function particle(dim, effect, loc, dir, speed = 0.0001, life) {
    try {
        const m = new MolangVariableMap();
        if (dir) m.setSpeedAndDirection("variable.dir", speed, dir);
        if (life !== undefined) m.setFloat("variable.life", life);
        dim.spawnParticle(effect, loc, m);
    } catch (e) { /* fuera de chunks cargados */ }
}

// --------------------------------------------------------------------------- disparo
/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g */
function currentSpread(p, s, g) {
    const aim = s.aimed ? 1 : 0;
    const base = g.hip + (g.ads - g.hip) * aim;
    const v = p.getVelocity();
    const hv = Math.hypot(v.x, v.z);
    const move = Math.min(1.5, hv / 0.22) * g.move * (1 - 0.6 * aim);
    const air = p.isOnGround ? 0 : 2.5;
    const crouch = p.isSneaking && !s.aimed ? 0.75 : 1;
    return (base + move + air + s.bloom) * crouch;
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g @param {string} gunId */
function fire(p, s, g, gunId) {
    const ammo = getAmmo(p, gunId);
    if (!creative(p)) setAmmo(p, gunId, ammo - 1);
    else trySetProp(p, `${NS}:empty`, false);
    s.shot ^= 1;
    trySetProp(p, `${NS}:shot`, s.shot);
    s.lastShot = tick;

    const dim = p.dimension;
    const eye = p.getHeadLocation();
    const fwd = p.getViewDirection();
    dim.playSound(g.sound, eye, { volume: 1, pitch: 0.95 + Math.random() * 0.1 });

    const right = norm(cross(fwd, { x: 0, y: 1, z: 0 }));
    const muzzle = add(add(add(eye, fwd, 0.8), right, 0.17), { x: 0, y: -0.14, z: 0 });
    const sp = currentSpread(p, s, g);
    let anyHit = false;
    let anyHead = false;
    let anyKill = false;

    for (let i = 0; i < g.pellets; i++) {
        const dir = spread(fwd, sp);
        let origin = eye;
        let travelled = 0;
        let end = add(eye, dir, g.range);
        /** @type {{loc: import("@minecraft/server").Vector3, normal: import("@minecraft/server").Vector3} | null} */
        let impact = null;
        let maxDist = g.range;
        // rayo contra bloques, atravesando cristales
        for (let pass = 0; pass < 4; pass++) {
            const bh = dim.getBlockFromRay(origin, dir, { maxDistance: g.range - travelled, includeLiquidBlocks: false, includePassableBlocks: false });
            if (!bh) break;
            const b = bh.block;
            const hit = { x: b.location.x + bh.faceLocation.x, y: b.location.y + bh.faceLocation.y, z: b.location.z + bh.faceLocation.z };
            if (isGlass(b.typeId)) {
                if (CONFIG.breakGlass) {
                    try {
                        b.setType("minecraft:air");
                        dim.playSound("random.glass", hit, { volume: 1 });
                    } catch (e) { /* zona protegida */ }
                }
                travelled = dist(eye, hit) + 0.05;
                origin = add(eye, dir, travelled);
                continue;
            }
            maxDist = dist(eye, hit);
            end = hit;
            const f = String(bh.face);
            const normal = f === "Up" ? { x: 0, y: 1, z: 0 } : f === "Down" ? { x: 0, y: -1, z: 0 }
                : f === "North" ? { x: 0, y: 0, z: -1 } : f === "South" ? { x: 0, y: 0, z: 1 }
                    : f === "East" ? { x: 1, y: 0, z: 0 } : { x: -1, y: 0, z: 0 };
            impact = { loc: hit, normal };
            break;
        }
        // entidades en la trayectoria (hasta el bloque)
        let hits = [];
        try {
            hits = dim.getEntitiesFromRay(eye, dir, { maxDistance: maxDist, ignoreBlockCollision: true })
                .filter((h) => h.entity.id !== p.id && h.entity.isValid);
        } catch (e) { hits = []; }
        hits.sort((a, b) => a.distance - b.distance);
        let energy = 1;
        let n = 0;
        for (const h of hits) {
            if (n >= g.pen) break;
            const e = h.entity;
            if (e.typeId === "minecraft:item" || e.typeId === "minecraft:xp_orb" || e.typeId === "minecraft:arrow") continue;
            const hp = e.getComponent("minecraft:health");
            if (!hp) continue;
            const loc = add(eye, dir, h.distance);
            let head = false;
            try {
                const hl = e.getHeadLocation();
                head = (e.typeId === "minecraft:player" || hl.y - e.location.y > 1.0) && loc.y >= hl.y - 0.27;
            } catch (err) { head = false; }
            let dmg = g.damage * falloff(g, h.distance) * energy * CONFIG.damageMultiplier;
            if (head) dmg *= g.head;
            const r = damage(p, e, hp, dmg, dir, g.kb * energy);
            if (r > 0) {
                anyHit = true;
                anyHead = anyHead || head;
                anyKill = anyKill || r === 2;
            }
            particle(dim, `${NS}:blood`, loc);
            dim.playSound(`${NS}.impact_flesh`, loc, { volume: 0.7 });
            energy *= 0.55;
            n++;
            if (n >= g.pen) {
                end = loc;
                impact = null;
            }
        }
        // efectos
        const d = dist(muzzle, end);
        if (i === 0 || Math.random() < 0.5) particle(dim, `${NS}:tracer`, muzzle, norm({ x: end.x - muzzle.x, y: end.y - muzzle.y, z: end.z - muzzle.z }), 180, Math.max(0.02, d / 180));
        if (impact) {
            const off = add(impact.loc, impact.normal, 0.012);
            particle(dim, `${NS}:bullet_hole`, off, impact.normal);
            particle(dim, `${NS}:impact_dust`, off, impact.normal, 0.001);
            if (Math.random() < 0.4) particle(dim, `${NS}:sparks`, off, impact.normal, 0.001);
            dim.playSound(`${NS}.impact_block`, impact.loc, { volume: 0.6, pitch: 0.9 + Math.random() * 0.2 });
        }
        whizz(p, eye, end);
    }
    if (anyHit) {
        s.hitTick = tick;
        s.hitHead = anyHead;
        p.playSound(anyHead ? `${NS}.headshot` : `${NS}.hitmarker`, { volume: anyHead ? 0.8 : 0.5, pitch: anyKill ? 0.8 : 1 });
    }

    // retroceso de cámara
    const adsF = s.aimed ? g.radsf : 1;
    const crouchF = p.isSneaking && !s.aimed ? 0.8 : 1;
    const v = g.rv * adsF * crouchF * (0.85 + Math.random() * 0.3);
    const hz = g.rh * adsF * (Math.random() * 2 - 1 + 0.25);
    const rot = p.getRotation();
    try {
        p.setRotation({ x: Math.max(-90, rot.x - v), y: rot.y + hz });
    } catch (e) { /* jugador no válido */ }
    s.recoilDebt += v * 0.6;
    if (g.shake > 0) {
        try {
            p.runCommand(`camerashake add @s ${g.shake.toFixed(3)} 0.12 rotational`);
        } catch (e) { /* comando no disponible */ }
    }
    s.bloom = Math.min(g.maxBloom, s.bloom + g.bloom);
}

/**
 * @param {import("@minecraft/server").Player} p
 * @param {import("@minecraft/server").Entity} e
 * @param {import("@minecraft/server").EntityHealthComponent} hp
 * @param {number} dmg
 * @param {import("@minecraft/server").Vector3} dir
 * @param {number} kb
 * @returns {number} 0 nada, 1 dañado, 2 muerto
 */
function damage(p, e, hp, dmg, dir, kb) {
    const before = hp.currentValue;
    if (before <= 0) return 0;
    const last = LAST_HIT.get(e.id) ?? -100;
    LAST_HIT.set(e.id, tick);
    try {
        if (tick - last >= 10) {
            e.applyDamage(dmg, { cause: EntityDamageCause.entityAttack, damagingEntity: p });
        } else if (before - dmg > 0) {
            // dentro de los ticks de invulnerabilidad: la bala igualmente resta vida (cadencias altas)
            hp.setCurrentValue(before - dmg);
        } else {
            // golpe mortal durante la invulnerabilidad: un daño mayor que el anterior sí se aplica
            e.applyDamage(before + 1000, { cause: EntityDamageCause.entityAttack, damagingEntity: p });
        }
        if (e.typeId !== "minecraft:player") e.applyKnockback({ x: dir.x * kb, z: dir.z * kb }, 0.04);
    } catch (err) {
        return 0;
    }
    let after = before;
    try {
        after = e.isValid ? hp.currentValue : 0;
    } catch (err) { after = 0; }
    if (after <= 0) return 2;
    return after < before ? 1 : 0;
}

/** Silbido de bala para otros jugadores cerca de la trayectoria. */
function whizz(shooter, a, b) {
    const ab = { x: b.x - a.x, y: b.y - a.y, z: b.z - a.z };
    const len2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z;
    if (len2 < 16) return;
    for (const o of shooter.dimension.getPlayers()) {
        if (o.id === shooter.id) continue;
        const pe = o.getHeadLocation();
        const t = Math.max(0, Math.min(1, ((pe.x - a.x) * ab.x + (pe.y - a.y) * ab.y + (pe.z - a.z) * ab.z) / len2));
        const c = add(a, ab, t);
        if (dist(c, pe) < 3 && dist(c, a) > 6) o.playSound(`${NS}.whizz`, { location: c, volume: 1 });
    }
}

// --------------------------------------------------------------------------- acciones
/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g @param {string} gunId */
function startReload(p, s, g, gunId) {
    if (s.action) return;
    const ammo = getAmmo(p, gunId);
    const cap = g.mag + (g.chamber && ammo > 0 ? 1 : 0);
    const reserve = creative(p) ? 999 : countAmmo(p, g.ammo);
    if (ammo >= cap) {
        startInspect(p, s, g);
        return;
    }
    if (reserve <= 0) {
        p.onScreenDisplay.setActionBar({ rawtext: [{ translate: "fps.hud.noammo" }] });
        return;
    }
    s.burstLeft = 0;
    s.cycleAt = -1;
    if (g.shell) {
        s.action = "shell_start";
        s.actionEnd = tick + g.shell[0] * TICK;
        s.shellsLeft = Math.min(cap - ammo, reserve);
        s.shellFromEmpty = ammo === 0;
        playAction(p, ANIM.shell_start);
    } else {
        const empty = ammo === 0;
        s.action = empty ? "reload_empty" : "reload";
        s.actionEnd = tick + (empty ? g.reloadEmpty : g.reload) * TICK;
        playAction(p, empty ? ANIM.reload_empty : ANIM.reload);
    }
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g */
function startInspect(p, s, g) {
    if (s.action || s.aimed) return;
    s.action = "inspect";
    s.actionEnd = tick + g.inspect * TICK;
    playAction(p, ANIM.inspect);
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g */
function startCycle(p, s, g) {
    s.action = "cycle";
    s.actionEnd = tick + (g.cycle ?? 0.5) * TICK;
    playAction(p, ANIM.cycle);
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g @param {string} gunId */
function finishAction(p, s, g, gunId) {
    const a = s.action;
    s.action = null;
    if (a === "reload" || a === "reload_empty") {
        const ammo = getAmmo(p, gunId);
        const cap = g.mag + (g.chamber && a === "reload" && ammo > 0 ? 1 : 0);
        const need = cap - ammo;
        const got = creative(p) ? need : takeAmmo(p, g.ammo, need);
        setAmmo(p, gunId, ammo + got);
    } else if (a === "shell_start") {
        if (s.shellsLeft > 0) {
            s.action = "shell_loop";
            s.actionEnd = tick + (g.shell ? g.shell[1] : 0.5) * TICK;
            playAction(p, ANIM.shell_loop);
            return;
        }
        s.action = "shell_end";
        s.actionEnd = tick + (g.shell ? g.shell[2] : 0.5) * TICK;
        playAction(p, ANIM.shell_end);
        return;
    } else if (a === "shell_loop") {
        const ammo = getAmmo(p, gunId);
        const got = creative(p) ? 1 : takeAmmo(p, g.ammo, 1);
        if (got > 0) setAmmo(p, gunId, ammo + 1);
        s.shellsLeft--;
        if (got > 0 && s.shellsLeft > 0) {
            s.action = "shell_loop";
            s.actionEnd = tick + (g.shell ? g.shell[1] : 0.5) * TICK;
            playAction(p, ANIM.shell_loop);
            return;
        }
        s.action = "shell_end";
        s.actionEnd = tick + (g.shell ? g.shell[2] : 0.5) * TICK;
        playAction(p, ANIM.shell_end);
        return;
    } else if (a === "shell_end") {
        if (s.shellFromEmpty && g.cycle) {
            s.shellFromEmpty = false;
            startCycle(p, s, g);
            return;
        }
    }
    trySetProp(p, `${NS}:anim`, ANIM.idle);
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {string} gunId */
function cycleMode(p, s, gunId) {
    const g = GUNS[gunId];
    if (g.modes.length < 2) return;
    const idx = (getModeIndex(p, gunId) + 1) % g.modes.length;
    p.setDynamicProperty(`${NS}:mode:${gunId}`, idx);
    trySetProp(p, `${NS}:mode`, idx);
    s.burstLeft = 0;
    sfx(p, `${NS}.fire_select`, 0.6);
    p.onScreenDisplay.setActionBar(`§6Modo: §f${MODE_NAMES[g.modes[idx]]}`);
}

/** @param {import("@minecraft/server").Player} p @param {State} s */
function setAim(p, s, on, g) {
    if (s.aimed === on) return;
    s.aimed = on;
    try {
        if (on) p.camera.setFov({ fov: g.fov, easeOptions: { easeTime: g.fov < 30 ? 0.3 : 0.2 } });
        else p.camera.clear();
    } catch (e) { /* cámara no disponible */ }
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {string|null} gunId @param {number} slot */
function equip(p, s, gunId, slot) {
    if (s.gunId && s.aimed) setAim(p, s, false, GUNS[s.gunId]);
    s.gunId = gunId;
    s.slot = slot;
    s.action = null;
    s.burstLeft = 0;
    s.cycleAt = -1;
    s.bloom = 0;
    s.recoilDebt = 0;
    s.semiQueued = false;
    if (!gunId) {
        trySetProp(p, `${NS}:anim`, ANIM.idle);
        return;
    }
    const g = GUNS[gunId];
    s.action = "draw";
    s.actionEnd = tick + g.draw * TICK;
    s.nextShot = tick + g.draw * TICK * 0.9;
    trySetProp(p, `${NS}:empty`, getAmmo(p, gunId) <= 0);
    trySetProp(p, `${NS}:mode`, getModeIndex(p, gunId));
    playAction(p, ANIM.draw);
    try {
        const ids = GUN_IDS.map((i) => `'${i}'`).join(", ");
        p.playAnimation(`animation.${NS}.player.aim`, {
            controller: `${NS}_aim`,
            blendOutTime: 0.2,
            stopExpression: `!q.is_item_name_any('slot.weapon.mainhand', 0, ${ids})`,
        });
    } catch (e) { /* playanimation no disponible */ }
}

// --------------------------------------------------------------------------- bucle por tick
/** @param {import("@minecraft/server").Player} p */
function tickPlayer(p) {
    const s = st(p);
    const item = heldItem(p);
    const gunId = item && GUNS[item.typeId] ? item.typeId : null;
    const slot = p.selectedSlotIndex;
    if (gunId !== s.gunId || (gunId && slot !== s.slot)) equip(p, s, gunId, slot);
    if (!gunId) return;
    const g = GUNS[gunId];

    // fin de acciones
    if (s.action && tick >= s.actionEnd) finishAction(p, s, g, gunId);
    if (s.cycleAt >= 0 && tick >= s.cycleAt && !s.action) {
        s.cycleAt = -1;
        startCycle(p, s, g);
    }

    // apuntar
    const canAim = !s.action || s.action === "cycle";
    setAim(p, s, p.isSneaking && canAim && !p.isSprinting, g);

    // gatillo
    const want = s.held || tick - s.lastUse <= 4;
    const pressed = want && !s.prevWant;
    s.prevWant = want;
    const mode = g.modes[getModeIndex(p, gunId)];
    if (pressed) {
        s.dryClicked = false;
        s.semiQueued = true;
        if (mode === "burst" && s.burstLeft === 0) s.burstLeft = g.burst;
        if (s.action === "inspect") {
            s.action = null;
            trySetProp(p, `${NS}:anim`, ANIM.idle);
        }
        if (s.action === "shell_start" || s.action === "shell_loop") {
            s.action = "shell_end";
            s.actionEnd = tick + (g.shell ? g.shell[2] : 0.5) * TICK * 0.8;
            s.shellFromEmpty = false;
            playAction(p, ANIM.shell_end);
        }
    }
    const fireWanted = mode === "auto" ? want : mode === "burst" ? s.burstLeft > 0 : s.semiQueued;
    if (fireWanted && !s.action && s.cycleAt < 0 && !p.isSprinting) {
        const interval = TICK * Math.max(60 / g.rpm, g.cycle ?? 0);
        let guard = 0;
        while (tick >= s.nextShot && guard++ < 3) {
            const ammo = getAmmo(p, gunId);
            if (ammo <= 0) {
                if (!s.dryClicked) {
                    s.dryClicked = true;
                    sfx(p, `${NS}.dry_fire`, 0.7);
                    if (creative(p) || countAmmo(p, g.ammo) > 0) startReload(p, s, g, gunId);
                }
                s.semiQueued = false;
                s.burstLeft = 0;
                break;
            }
            fire(p, s, g, gunId);
            s.nextShot = (tick - s.nextShot < interval ? s.nextShot : tick) + interval;
            s.semiQueued = false;
            if (mode === "burst") s.burstLeft--;
            if (g.cycle) {
                s.cycleAt = tick + 3;
                break;
            }
            if (mode !== "auto" && !(mode === "burst" && s.burstLeft > 0)) break;
        }
    }

    // recuperación del retroceso y dispersión
    if (tick - s.lastShot > 3 && s.recoilDebt > 0.02) {
        const rec = s.recoilDebt * 0.22;
        s.recoilDebt -= rec;
        try {
            const r = p.getRotation();
            p.setRotation({ x: Math.min(90, r.x + rec), y: r.y });
        } catch (e) { /* ignorado */ }
    }
    if (tick - s.lastShot > 2) s.bloom = Math.max(0, s.bloom - Math.max(0.08, g.maxBloom * 0.11));

    // HUD
    if (tick % 3 === 0) hud(p, s, g, gunId, mode);
}

/** @param {import("@minecraft/server").Player} p @param {State} s @param {Gun} g @param {string} gunId @param {string} mode */
function hud(p, s, g, gunId, mode) {
    const ammo = getAmmo(p, gunId);
    const reserve = creative(p) ? "∞" : String(countAmmo(p, g.ammo));
    const col = ammo === 0 ? "§c" : ammo <= Math.max(1, Math.floor(g.mag / 4)) ? "§6" : "§f";
    const bars = Math.min(g.mag, 30);
    const filled = Math.ceil(ammo * bars / g.mag);
    const bar = "§f" + "|".repeat(Math.min(bars, filled)) + "§8" + "|".repeat(Math.max(0, bars - filled));
    const hit = tick - s.hitTick < 6 ? (s.hitHead ? " §e✖" : " §f✖") : "";
    let status = "";
    if (s.action === "reload" || s.action === "reload_empty" || (s.action && s.action.startsWith("shell"))) status = " §7recargando…";
    else if (ammo === 0) status = " §c[Agacharse+Saltar] RECARGAR";
    p.onScreenDisplay.setActionBar(`${col}§l${ammo}§r§7 / ${reserve}  §6${MODE_NAMES[mode]}  ${bar}${hit}${status}`);
}

// --------------------------------------------------------------------------- eventos
world.afterEvents.itemStartUse.subscribe((e) => {
    if (GUNS[e.itemStack.typeId]) st(e.source).held = true;
});
world.afterEvents.itemStopUse.subscribe((e) => {
    st(e.source).held = false;
});
world.afterEvents.itemUse.subscribe((e) => {
    if (GUNS[e.itemStack.typeId]) st(e.source).lastUse = tick;
});
world.afterEvents.playerButtonInput.subscribe((e) => {
    if (e.newButtonState !== ButtonState.Pressed) return;
    const p = e.player;
    const s = st(p);
    if (!s.gunId) return;
    const g = GUNS[s.gunId];
    if (e.button === InputButton.Sneak) {
        if (tick - s.lastSneakPress <= 7) {
            cycleMode(p, s, s.gunId);
            s.lastSneakPress = -100;
        } else s.lastSneakPress = tick;
    } else if (e.button === InputButton.Jump && p.isSneaking) {
        startReload(p, s, g, s.gunId);
    }
});
world.afterEvents.playerLeave.subscribe((e) => STATES.delete(e.playerId));
world.afterEvents.entityDie.subscribe((e) => LAST_HIT.delete(e.deadEntity.id));

system.runInterval(() => {
    tick++;
    for (const p of world.getAllPlayers()) {
        try {
            tickPlayer(p);
        } catch (err) {
            if (tick % 200 === 0) console.warn(`[FPS Realista] ${err}`);
        }
    }
}, 1);

// /scriptevent fps:config breakGlass=false   (opciones simples en tiempo de ejecución)
system.afterEvents.scriptEventReceive.subscribe((e) => {
    if (e.id !== `${NS}:config`) return;
    for (const kv of e.message.split(/\s+/)) {
        const [k, v] = kv.split("=");
        if (k === "breakGlass") CONFIG.breakGlass = v !== "false";
        if (k === "infiniteCreative") CONFIG.infiniteCreative = v !== "false";
        if (k === "damage") CONFIG.damageMultiplier = Math.max(0, Number(v) || 1);
    }
    console.warn(`[FPS Realista] config: ${JSON.stringify(CONFIG)}`);
});
