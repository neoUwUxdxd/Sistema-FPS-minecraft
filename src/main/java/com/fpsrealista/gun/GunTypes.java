package com.fpsrealista.gun;

import com.fpsrealista.ModRegistry;
import java.util.List;

/** Catalogo de armas. Los tiempos coinciden con la duracion de los clips de animacion. */
public final class GunTypes {
    public static final GunType PISTOL_9MM = GunType.builder("pistol_9mm")
            .ammo(() -> ModRegistry.AMMO_9MM.get()).mag(15, true).modes(FireMode.SEMI).rpm(450)
            .damage(6.0f, 2.0f).range(120, 15, 50, 0.55f)
            .spread(1.6f, 0.25f, 1.0f).bloom(0.5f, 2.5f)
            .recoil(2.2f, 0.7f, 0.75f, 1.0f).ads(0.16f, 0.88f)
            .reload(1.6f, 1.95f).draw(0.45f).casing(CasingType.PISTOL).adsMove(0.8f)
            .velocity(360).knockback(0.04f).build();

    public static final GunType CARBINE_556 = GunType.builder("carbine_556")
            .ammo(() -> ModRegistry.AMMO_556.get()).mag(30, true).modes(FireMode.AUTO, FireMode.BURST, FireMode.SEMI)
            .rpm(800).burst(3)
            .damage(6.5f, 2.0f).range(250, 40, 140, 0.6f)
            .spread(2.6f, 0.08f, 1.8f).bloom(0.25f, 2.2f)
            .recoil(0.85f, 0.45f, 0.65f, 1.0f).ads(0.24f, 0.78f)
            .reload(2.2f, 2.75f).draw(0.6f).casing(CasingType.RIFLE).adsMove(0.6f)
            .penetration(2).velocity(880).build();

    public static final GunType RIFLE_762 = GunType.builder("rifle_762")
            .ammo(() -> ModRegistry.AMMO_762.get()).mag(30, true).modes(FireMode.AUTO, FireMode.SEMI).rpm(600)
            .damage(8.0f, 2.0f).range(250, 30, 120, 0.55f)
            .spread(3.0f, 0.12f, 2.0f).bloom(0.35f, 2.8f)
            .recoil(1.35f, 0.7f, 0.7f, 1.25f).ads(0.27f, 0.82f)
            .reload(2.4f, 3.05f).draw(0.65f).casing(CasingType.RIFLE).adsMove(0.6f)
            .penetration(2).velocity(715).knockback(0.07f).build();

    public static final GunType SHOTGUN_12G = GunType.builder("shotgun_12g")
            .ammo(() -> ModRegistry.AMMO_12G.get()).mag(6, true).modes(FireMode.SEMI).rpm(70)
            .damage(3.2f, 1.5f).range(60, 8, 30, 0.2f).pellets(9)
            .spread(4.5f, 3.2f, 1.0f).bloom(0f, 0f)
            .recoil(5.5f, 1.2f, 0.85f, 2.4f).ads(0.26f, 0.88f)
            .shellReload(0.45f, 0.55f, 0.5f).cycle("pump", 0.62f).draw(0.7f).casing(CasingType.SHELL)
            .adsMove(0.65f).velocity(400).knockback(0.12f).build();

    public static final GunType SNIPER_308 = GunType.builder("sniper_308")
            .ammo(() -> ModRegistry.AMMO_308.get()).mag(5, true).modes(FireMode.SEMI).rpm(60)
            .damage(26.0f, 2.5f).range(400, 120, 350, 0.7f)
            .spread(6.0f, 0.0f, 4.0f).bloom(0f, 0f)
            .recoil(6.0f, 0.9f, 0.6f, 2.8f).ads(0.38f, 0.16f).scope()
            .reload(2.6f, 3.45f).cycle("bolt", 1.15f).draw(0.8f).casing(CasingType.RIFLE)
            .adsMove(0.45f).penetration(3).velocity(850).knockback(0.15f).build();

    public static final List<GunType> ALL = List.of(PISTOL_9MM, CARBINE_556, RIFLE_762, SHOTGUN_12G, SNIPER_308);

    public static GunType byIndex(int i) {
        return i >= 0 && i < ALL.size() ? ALL.get(i) : null;
    }

    public static int indexOf(GunType t) {
        return ALL.indexOf(t);
    }

    private GunTypes() {}
}
