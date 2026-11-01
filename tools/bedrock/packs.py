"""
Partes comunes del add-on de Bedrock: manifiestos, items, recetas, player.json, partículas,
sonidos, idiomas, controlador de render y empaquetado .mcaddon.
"""
import json
import os
import shutil
import uuid
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def u(name):
    """UUID estable a partir de un nombre (para que las actualizaciones reemplacen el pack)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "fpsrealista/" + name))


def build_all(B):
    write = B.write_json
    NS = B.NS
    BP, RP, REPO = B.BP, B.RP, B.REPO
    JA = B.JAVA_ASSETS

    # ------------------------------------------------------------------ manifiestos
    write(os.path.join(BP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": u("bp"),
                   "version": B.VERSION, "min_engine_version": B.MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": u("bp-data"), "version": B.VERSION},
            {"type": "script", "language": "javascript", "uuid": u("bp-script"), "version": B.VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": B.SCRIPT_API},
            {"uuid": u("rp"), "version": B.VERSION},
        ],
        "metadata": {"authors": ["neoUwUxdxd"], "license": "MIT", "url": "https://github.com/neoUwUxdxd/Sistema-FPS-minecraft"},
    })
    write(os.path.join(RP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": u("rp"),
                   "version": B.VERSION, "min_engine_version": B.MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": u("rp-res"), "version": B.VERSION}],
        "dependencies": [{"uuid": u("bp"), "version": B.VERSION}],
    })
    logo = Image.open(os.path.join(REPO, "src", "main", "resources", "logo.png")).convert("RGBA").resize((256, 256))
    logo.save(os.path.join(BP, "pack_icon.png"))
    logo.save(os.path.join(RP, "pack_icon.png"))

    # ------------------------------------------------------------------ items
    texture_data = {}
    for g in B.GUNS:
        write(os.path.join(BP, "items", f"{g}.json"), {
            "format_version": "1.21.60",
            "minecraft:item": {
                "description": {"identifier": f"{NS}:{g}", "menu_category": {"category": "equipment"}},
                "components": {
                    "minecraft:icon": {"textures": {"default": f"{NS}_{g}"}},
                    "minecraft:display_name": {"value": f"item.{NS}:{g}.name"},
                    "minecraft:max_stack_size": 1,
                    "minecraft:hand_equipped": {"value": True},
                    "minecraft:allow_off_hand": {"value": False},
                    "minecraft:can_destroy_in_creative": {"value": False},
                    # mantener pulsado "usar" = apretar el gatillo (fuego automatico)
                    "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.85, "emit_vibrations": False},
                    "minecraft:food": {"nutrition": 0, "saturation_modifier": 0, "can_always_eat": True},
                    "minecraft:tags": {"tags": [f"{NS}:gun"]},
                    "minecraft:interact_button": "Disparar",
                },
            },
        })
        texture_data[f"{NS}_{g}"] = {"textures": f"textures/{NS}/items/{g}"}
    for a in B.AMMO:
        write(os.path.join(BP, "items", f"{a}.json"), {
            "format_version": "1.21.60",
            "minecraft:item": {
                "description": {"identifier": f"{NS}:{a}", "menu_category": {"category": "items"}},
                "components": {
                    "minecraft:icon": {"textures": {"default": f"{NS}_{a}"}},
                    "minecraft:display_name": {"value": f"item.{NS}:{a}.name"},
                    "minecraft:max_stack_size": 64,
                },
            },
        })
        src = os.path.join(JA, "textures", "item", f"{a}.png")
        dst = os.path.join(RP, "textures", NS, "items", f"{a}.png")
        Image.open(src).convert("RGBA").resize((32, 32), Image.NEAREST).save(dst)
        texture_data[f"{NS}_{a}"] = {"textures": f"textures/{NS}/items/{a}"}
    build_probes(B)
    for nm in ("sonda_a", "sonda_b"):
        texture_data[f"{NS}_{nm}"] = {"textures": f"textures/{NS}/items/{nm}"}
    write(os.path.join(RP, "textures", "item_texture.json"),
          {"resource_pack_name": "fps_realista", "texture_name": "atlas.items", "texture_data": texture_data})

    # ------------------------------------------------------------------ recetas (desde las de Java)
    rdir = os.path.join(REPO, "src", "main", "resources", "data", "fpsrealista", "recipe")
    for fn in sorted(os.listdir(rdir)):
        with open(os.path.join(rdir, fn)) as f:
            r = json.load(f)
        name = fn[:-5]

        def conv(i):
            return i.replace("fpsrealista:", f"{NS}:")
        res = {"item": conv(r["result"]["id"]), "count": r["result"].get("count", 1)}
        if r["type"] == "minecraft:crafting_shaped":
            body = {"description": {"identifier": f"{NS}:{name}"}, "tags": ["crafting_table"],
                    "pattern": r["pattern"], "key": {k: {"item": conv(v["item"])} for k, v in r["key"].items()},
                    "result": res}
            write(os.path.join(BP, "recipes", fn), {"format_version": "1.20.10", "minecraft:recipe_shaped": body})
        else:
            body = {"description": {"identifier": f"{NS}:{name}"}, "tags": ["crafting_table"],
                    "ingredients": [{"item": conv(i["item"])} for i in r["ingredients"]], "result": res}
            write(os.path.join(BP, "recipes", fn), {"format_version": "1.20.10", "minecraft:recipe_shapeless": body})

    # ------------------------------------------------------------------ player.json con propiedades sincronizadas
    with open(os.path.join(HERE, "vanilla", "player.json")) as f:
        player = json.load(f)
    player["minecraft:entity"]["description"]["properties"] = {
        f"{NS}:anim": {"type": "int", "range": [0, 15], "default": 0, "client_sync": True},
        f"{NS}:seq": {"type": "int", "range": [0, 1000], "default": 0, "client_sync": True},
        f"{NS}:shot": {"type": "int", "range": [0, 1], "default": 0, "client_sync": True},
        f"{NS}:empty": {"type": "bool", "default": False, "client_sync": True},
        f"{NS}:mode": {"type": "int", "range": [0, 3], "default": 0, "client_sync": True},
    }
    write(os.path.join(BP, "entities", "player.json"), player)

    # ------------------------------------------------------------------ script
    sdir = os.path.join(BP, "scripts")
    os.makedirs(sdir, exist_ok=True)
    shutil.copy(os.path.join(HERE, "scripts", "main.js"), os.path.join(sdir, "main.js"))

    # ------------------------------------------------------------------ render controller y pose del jugador
    write(os.path.join(RP, "render_controllers", f"{NS}.render_controllers.json"), {
        "format_version": "1.8.0",
        "render_controllers": {f"controller.render.{NS}.gun": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}, {"glass_*": "Material.glass"}],
            "textures": ["Texture.default"],
        }},
    })
    names = ", ".join(f"'{NS}:{g}'" for g in B.GUNS)
    aim = "(1 - variable.is_first_person)"
    write(os.path.join(RP, "animations", f"{NS}_player.animation.json"), {
        "format_version": "1.8.0",
        "animations": {f"animation.{NS}.player.aim": {
            "loop": True,
            "override_previous_animation": False,
            "bones": {
                "rightarm": {"rotation": [f"{aim} * (-90 + q.target_x_rotation) ", f"{aim} * (q.target_y_rotation - 5)", 0]},
                "leftarm": {"rotation": [f"{aim} * (-90 + q.target_x_rotation)", f"{aim} * (q.target_y_rotation + 38)", 0]},
            },
        }},
    })

    # ------------------------------------------------------------------ sonidos
    sdst = os.path.join(RP, "sounds", NS)
    os.makedirs(sdst, exist_ok=True)
    with open(os.path.join(JA, "sounds.json")) as f:
        java_sounds = json.load(f)
    defs = {}
    for ev, d in java_sounds.items():
        files = []
        dist = 16
        for s in d["sounds"]:
            nm = s["name"].split(":", 1)[1]
            dist = s.get("attenuation_distance", dist)
            shutil.copy(os.path.join(JA, "sounds", nm + ".ogg"), os.path.join(sdst, nm + ".ogg"))
            files.append({"name": f"sounds/{NS}/{nm}", "load_on_low_memory": True})
        defs[f"{NS}.{ev}"] = {"category": "player", "min_distance": 1.0, "max_distance": float(dist), "sounds": files}
    write(os.path.join(RP, "sounds", "sound_definitions.json"), {"format_version": "1.20.20", "sound_definitions": defs})

    # ------------------------------------------------------------------ particulas
    pdst = os.path.join(RP, "textures", NS, "particle")
    os.makedirs(pdst, exist_ok=True)
    tex = os.path.join(JA, "textures")
    shutil.copy(os.path.join(tex, "particle", "tracer.png"), os.path.join(pdst, "tracer.png"))
    shutil.copy(os.path.join(tex, "particle", "bullet_hole_0.png"), os.path.join(pdst, "bullet_hole.png"))
    shutil.copy(os.path.join(tex, "particle", "casing.png"), os.path.join(pdst, "casing.png"))
    shutil.copy(os.path.join(tex, "particle", "shotshell.png"), os.path.join(pdst, "shotshell.png"))
    shutil.copy(os.path.join(tex, "particle", "gun_smoke_0.png"), os.path.join(pdst, "smoke.png"))
    Image.open(os.path.join(tex, "effect", "muzzle_flash_0.png")).resize((64, 64), Image.LANCZOS).save(os.path.join(pdst, "muzzle_flash.png"))
    for nm, p in particles(NS).items():
        write(os.path.join(RP, "particles", nm + ".json"), p)

    # ------------------------------------------------------------------ idiomas
    lang_es = ["pack.name=FPS Realista", "pack.description=Armas de fuego hiperrealistas: modelos 3D detallados, animaciones con manos, retroceso, apuntado y balística."]
    lang_en = ["pack.name=Realistic FPS", "pack.description=Hyperrealistic firearms: detailed 3D models, animated hands, recoil, ADS and ballistics."]
    for g, (es, en) in list(B.NAMES.items()) + list(B.AMMO.items()):
        lang_es.append(f"item.{NS}:{g}.name={es}")
        lang_en.append(f"item.{NS}:{g}.name={en}")
    lang_es += [f"item.{NS}:sonda_a.name=Sonda de calibración A", f"item.{NS}:sonda_b.name=Sonda de calibración B"]
    lang_en += [f"item.{NS}:sonda_a.name=Calibration probe A", f"item.{NS}:sonda_b.name=Calibration probe B"]
    texts = {
        "es_ES": lang_es + [
            "fps.hud.reload=§c[Agacharse + Saltar] RECARGAR",
            "fps.hud.noammo=§cSIN MUNICIÓN",
            "death.attack.fps.bullet=%1$s fue abatido por %2$s",
        ],
        "en_US": lang_en + [
            "fps.hud.reload=§c[Sneak + Jump] RELOAD",
            "fps.hud.noammo=§cNO AMMO",
            "death.attack.fps.bullet=%1$s was shot by %2$s",
        ],
    }
    for lang, lines in texts.items():
        p = os.path.join(RP, "texts", lang + ".lang")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        bp = os.path.join(BP, "texts", lang + ".lang")
        os.makedirs(os.path.dirname(bp), exist_ok=True)
        with open(bp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines[:2]) + "\n")
    write(os.path.join(RP, "texts", "languages.json"), list(texts.keys()))
    write(os.path.join(BP, "texts", "languages.json"), list(texts.keys()))

    # ------------------------------------------------------------------ empaquetado
    os.makedirs(B.DIST, exist_ok=True)
    out = os.path.join(B.DIST, "FPS_Realista.mcaddon")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root_dir in (BP, RP):
            base = os.path.dirname(root_dir)
            for dp, _, fns in os.walk(root_dir):
                for fn in fns:
                    full = os.path.join(dp, fn)
                    z.write(full, os.path.relpath(full, base))
    print("add-on:", out, f"({os.path.getsize(out) // 1024} KB)")


def particles(NS):
    def base(ident, texture, material="particles_alpha"):
        return {"format_version": "1.10.0", "particle_effect": {
            "description": {"identifier": f"{NS}:{ident}",
                            "basic_render_parameters": {"material": material, "texture": f"textures/{NS}/particle/{texture}"}},
            "components": {}}}

    full_uv = {"texture_width": 1, "texture_height": 1, "uv": [0, 0], "uv_size": [1, 1]}
    P = {}

    p = base("muzzle_flash", "muzzle_flash", "particles_add")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_local_space": {"position": True, "rotation": True},
        "minecraft:emitter_rate_instant": {"num_particles": 2},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.06},
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)"},
        "minecraft:particle_appearance_billboard": {"size": ["0.09 + v.particle_random_1 * 0.06", "0.09 + v.particle_random_1 * 0.06"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": full_uv},
    }
    P["muzzle_flash"] = p

    p = base("muzzle_smoke", "smoke", "particles_blend")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_rate_instant": {"num_particles": 3},
        "minecraft:emitter_lifetime_once": {"active_time": 0.1},
        "minecraft:emitter_shape_sphere": {"radius": 0.02, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.25,
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.35, 0], "linear_drag_coefficient": 2.5},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "1.2 + v.particle_random_1"},
        "minecraft:particle_appearance_billboard": {"size": ["0.06 + v.particle_age * 0.25", "0.06 + v.particle_age * 0.25"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": full_uv},
        "minecraft:particle_appearance_tinting": {"color": [0.85, 0.85, 0.85, "0.35 * (1 - v.particle_age / v.particle_lifetime)"]},
        "minecraft:particle_appearance_lighting": {},
    }
    P["muzzle_smoke"] = p

    for nm, texf, size in (("casing_rifle", "casing", 0.05), ("casing_pistol", "casing", 0.035), ("casing_shell", "shotshell", 0.08)):
        p = base(nm, texf)
        p["particle_effect"]["components"] = {
            "minecraft:emitter_rate_instant": {"num_particles": 1},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_point": {"direction": ["math.random(-1, 1)", "1.4", "math.random(-1, 1)"]},
            "minecraft:particle_initial_speed": "2.2 + v.particle_random_1",
            "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-900, 900)"},
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -18, 0], "linear_drag_coefficient": 0.3,
                                                  "rotation_drag_coefficient": 1.2},
            "minecraft:particle_motion_collision": {"collision_drag": 6, "coefficient_of_restitution": 0.35,
                                                    "collision_radius": 0.02},
            "minecraft:particle_lifetime_expression": {"max_lifetime": 4},
            "minecraft:particle_appearance_billboard": {"size": [size, size], "facing_camera_mode": "rotate_xyz", "uv": full_uv},
            "minecraft:particle_appearance_lighting": {},
        }
        P[nm] = p

    p = base("tracer", "tracer", "particles_add")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.01},
        "minecraft:emitter_shape_point": {"direction": ["v.dir.direction_x", "v.dir.direction_y", "v.dir.direction_z"]},
        "minecraft:particle_initial_speed": "v.dir.speed",
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "v.life"},
        "minecraft:particle_appearance_billboard": {"size": [1.8, 0.018], "facing_camera_mode": "lookat_direction",
                                                    "uv": full_uv},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.9, 0.65, 0.9]},
    }
    P["tracer"] = p

    p = base("bullet_hole", "bullet_hole")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.01},
        "minecraft:emitter_shape_point": {"offset": [0, 0, 0]},
        "minecraft:particle_motion_parametric": {"direction": ["v.dir.direction_x", "v.dir.direction_y", "v.dir.direction_z"]},
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 40},
        "minecraft:particle_appearance_billboard": {"size": [0.07, 0.07], "facing_camera_mode": "direction_z", "uv": full_uv},
        "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "math.clamp((v.particle_lifetime - v.particle_age) / 4, 0, 1)"]},
        "minecraft:particle_appearance_lighting": {},
    }
    P["bullet_hole"] = p

    p = base("impact_dust", "smoke", "particles_blend")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_rate_instant": {"num_particles": 6},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"direction": ["v.dir.direction_x + math.random(-0.6, 0.6)", "v.dir.direction_y + math.random(-0.6, 0.6)",
                                                        "v.dir.direction_z + math.random(-0.6, 0.6)"]},
        "minecraft:particle_initial_speed": "1.2 + v.particle_random_1 * 2",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -4, 0], "linear_drag_coefficient": 3},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.6 + v.particle_random_2 * 0.8"},
        "minecraft:particle_appearance_billboard": {"size": ["0.04 + v.particle_age * 0.12", "0.04 + v.particle_age * 0.12"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": full_uv},
        "minecraft:particle_appearance_tinting": {"color": [0.62, 0.58, 0.52, "0.7 * (1 - v.particle_age / v.particle_lifetime)"]},
        "minecraft:particle_appearance_lighting": {},
    }
    P["impact_dust"] = p

    p = base("blood", "smoke", "particles_alpha")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_rate_instant": {"num_particles": 10},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 0.05, "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.5 + v.particle_random_1 * 2",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -12, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_motion_collision": {"collision_drag": 10, "coefficient_of_restitution": 0, "collision_radius": 0.01},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.5 + v.particle_random_2"},
        "minecraft:particle_appearance_billboard": {"size": [0.045, 0.045], "facing_camera_mode": "rotate_xyz", "uv": full_uv},
        "minecraft:particle_appearance_tinting": {"color": [0.45, 0.02, 0.02, 1.0]},
        "minecraft:particle_appearance_lighting": {},
    }
    P["blood"] = p

    p = base("sparks", "tracer", "particles_add")
    p["particle_effect"]["components"] = {
        "minecraft:emitter_rate_instant": {"num_particles": 5},
        "minecraft:emitter_lifetime_once": {"active_time": 0.02},
        "minecraft:emitter_shape_point": {"direction": ["v.dir.direction_x + math.random(-0.8, 0.8)", "v.dir.direction_y + math.random(-0.5, 0.9)",
                                                        "v.dir.direction_z + math.random(-0.8, 0.8)"]},
        "minecraft:particle_initial_speed": "4 + v.particle_random_1 * 4",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -14, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.12 + v.particle_random_2 * 0.2"},
        "minecraft:particle_appearance_billboard": {"size": [0.12, 0.012], "facing_camera_mode": "lookat_direction", "uv": full_uv},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.75, 0.35, 1.0]},
    }
    P["sparks"] = p
    return P


def build_probes(B):
    """Objetos de calibracion: ejes de colores unidos a la mano (A estatica, B con rotacion conocida)."""
    NS, BP, RP, write = B.NS, B.BP, B.RP, B.write_json
    tex = Image.new("RGBA", (16, 16))
    cols = [(255, 255, 255), (230, 30, 30), (30, 200, 30), (40, 80, 255), (255, 220, 0), (255, 0, 255)]
    for i, c in enumerate(cols):
        for y in range(4):
            for x in range(4):
                tex.putpixel(((i % 4) * 4 + x, (i // 4) * 4 + y), c + (255,))
    os.makedirs(os.path.join(RP, "textures", NS, "probe"), exist_ok=True)
    tex.save(os.path.join(RP, "textures", NS, "probe", "axes.png"))

    def cube(origin, size, ci):
        u, v = (ci % 4) * 4 + 1, (ci // 4) * 4 + 1
        f = {"uv": [u, v], "uv_size": [2, 2]}
        return {"origin": origin, "size": size, "uv": {k: f for k in ("north", "south", "east", "west", "up", "down")}}

    cubes = [
        cube([-0.75, -0.75, -0.75], [1.5, 1.5, 1.5], 0),      # centro blanco
        cube([0.75, -0.3, -0.3], [8, 0.6, 0.6], 1),           # +X rojo
        cube([-0.3, 0.75, -0.3], [0.6, 8, 0.6], 2),           # +Y verde
        cube([-0.3, -0.3, 0.75], [0.6, 0.6, 8], 3),           # +Z azul
        cube([-0.6, -0.6, -6.0], [1.2, 1.2, 1.2], 4),         # -Z amarillo
        cube([7.0, -0.8, -0.8], [1.6, 1.6, 1.6], 1),          # punta +X
        cube([-0.8, 7.0, -0.8], [1.6, 1.6, 1.6], 2),          # punta +Y
        cube([-0.8, -0.8, 7.0], [1.6, 1.6, 1.6], 3),          # punta +Z
    ]
    write(os.path.join(RP, "models", "entity", "probe.geo.json"), {"format_version": "1.16.0", "minecraft:geometry": [{
        "description": {"identifier": f"geometry.{NS}.probe", "texture_width": 16, "texture_height": 16,
                        "visible_bounds_width": 4, "visible_bounds_height": 4, "visible_bounds_offset": [0, 1, 0]},
        "bones": [{"name": "root", "pivot": [0, 0, 0], "binding": "q.item_slot_to_bone_name(c.item_slot)", "cubes": cubes}]}]})
    write(os.path.join(RP, "animations", f"{NS}_probe.animation.json"), {"format_version": "1.8.0", "animations": {
        f"animation.{NS}.probe.test": {"loop": True, "bones": {"root": {
            "rotation": [90, 0, 0], "position": [0, "c.is_first_person ? 4 : 0", 0]}}}}})
    for name, animated in (("sonda_a", False), ("sonda_b", True)):
        desc = {
            "identifier": f"{NS}:{name}",
            "item": {f"{NS}:{name}": "query.is_owner_identifier_any('minecraft:player')"},
            "materials": {"default": "entity_alphatest"},
            "textures": {"default": f"textures/{NS}/probe/axes"},
            "geometry": {"default": f"geometry.{NS}.probe"},
            "render_controllers": [f"controller.render.{NS}.gun"],
        }
        if animated:
            desc["animations"] = {"test": f"animation.{NS}.probe.test"}
            desc["scripts"] = {"animate": ["test"]}
        write(os.path.join(RP, "attachables", f"{name}.json"), {"format_version": "1.10.0", "minecraft:attachable": {"description": desc}})
        write(os.path.join(BP, "items", f"{name}.json"), {"format_version": "1.21.60", "minecraft:item": {
            "description": {"identifier": f"{NS}:{name}", "menu_category": {"category": "equipment"}},
            "components": {"minecraft:icon": {"textures": {"default": f"{NS}_{name}"}},
                           "minecraft:display_name": {"value": f"item.{NS}:{name}.name"},
                           "minecraft:max_stack_size": 1, "minecraft:hand_equipped": {"value": True}}}})
        icon = tex.resize((32, 32), Image.NEAREST)
        icon.save(os.path.join(RP, "textures", NS, "items", f"{name}.png"))
