package com.fpsrealista.gun;

import java.util.List;
import java.util.function.Supplier;
import net.minecraft.world.item.Item;

/**
 * Estadisticas de un arma. Distancias en bloques (1 bloque = 1 m), tiempos en segundos,
 * dispersion y retroceso en grados, dano en puntos de vida (2 = un corazon).
 */
public final class GunType {
    private final String id;
    public final Supplier<Item> ammo;
    public final int magSize;
    public final boolean chamber;
    public final List<FireMode> fireModes;
    public final float rpm;
    public final int burstCount;
    public final float damage;
    public final float headshotMultiplier;
    public final float range;
    public final float falloffStart;
    public final float falloffEnd;
    public final float minDamageFactor;
    public final int pellets;
    public final float hipSpread;
    public final float adsSpread;
    public final float moveSpread;
    public final float bloomPerShot;
    public final float maxBloom;
    public final float recoilVertical;
    public final float recoilHorizontal;
    public final float recoilAdsFactor;
    public final float visualKick;
    public final float adsTime;
    public final float adsFov;
    public final boolean scope;
    public final float reloadTime;
    public final float reloadEmptyTime;
    public final boolean shellReload;
    public final float shellStart;
    public final float shellTime;
    public final float shellEnd;
    /** Clip de ciclado manual tras cada disparo ("pump", "bolt") o null. */
    public final String cycleClip;
    public final float cycleTime;
    public final float drawTime;
    public final String shootSound;
    public final CasingType casing;
    public final float adsMoveFactor;
    public final int penetration;
    public final float knockback;
    public final float muzzleVelocity;

    private GunType(Builder b) {
        this.id = b.id;
        this.ammo = b.ammo;
        this.magSize = b.magSize;
        this.chamber = b.chamber;
        this.fireModes = List.copyOf(b.fireModes);
        this.rpm = b.rpm;
        this.burstCount = b.burstCount;
        this.damage = b.damage;
        this.headshotMultiplier = b.headshotMultiplier;
        this.range = b.range;
        this.falloffStart = b.falloffStart;
        this.falloffEnd = b.falloffEnd;
        this.minDamageFactor = b.minDamageFactor;
        this.pellets = b.pellets;
        this.hipSpread = b.hipSpread;
        this.adsSpread = b.adsSpread;
        this.moveSpread = b.moveSpread;
        this.bloomPerShot = b.bloomPerShot;
        this.maxBloom = b.maxBloom;
        this.recoilVertical = b.recoilVertical;
        this.recoilHorizontal = b.recoilHorizontal;
        this.recoilAdsFactor = b.recoilAdsFactor;
        this.visualKick = b.visualKick;
        this.adsTime = b.adsTime;
        this.adsFov = b.adsFov;
        this.scope = b.scope;
        this.reloadTime = b.reloadTime;
        this.reloadEmptyTime = b.reloadEmptyTime;
        this.shellReload = b.shellReload;
        this.shellStart = b.shellStart;
        this.shellTime = b.shellTime;
        this.shellEnd = b.shellEnd;
        this.cycleClip = b.cycleClip;
        this.cycleTime = b.cycleTime;
        this.drawTime = b.drawTime;
        this.shootSound = b.shootSound;
        this.casing = b.casing;
        this.adsMoveFactor = b.adsMoveFactor;
        this.penetration = b.penetration;
        this.knockback = b.knockback;
        this.muzzleVelocity = b.muzzleVelocity;
    }

    public String id() {
        return id;
    }

    /** Capacidad maxima contando el cartucho en la recamara (recarga tactica). */
    public int capacity(boolean tactical) {
        return magSize + (chamber && tactical ? 1 : 0);
    }

    /** Segundos minimos entre disparos. */
    public float shotInterval() {
        float base = 60f / rpm;
        return cycleClip != null ? Math.max(base, cycleTime) : base;
    }

    public static Builder builder(String id) {
        return new Builder(id);
    }

    public static final class Builder {
        private final String id;
        private Supplier<Item> ammo;
        private int magSize = 30;
        private boolean chamber = true;
        private List<FireMode> fireModes = List.of(FireMode.SEMI);
        private float rpm = 600;
        private int burstCount = 3;
        private float damage = 6;
        private float headshotMultiplier = 2f;
        private float range = 200;
        private float falloffStart = 40;
        private float falloffEnd = 120;
        private float minDamageFactor = 0.5f;
        private int pellets = 1;
        private float hipSpread = 2.5f;
        private float adsSpread = 0.15f;
        private float moveSpread = 1.5f;
        private float bloomPerShot = 0.4f;
        private float maxBloom = 3f;
        private float recoilVertical = 1f;
        private float recoilHorizontal = 0.4f;
        private float recoilAdsFactor = 0.7f;
        private float visualKick = 1f;
        private float adsTime = 0.25f;
        private float adsFov = 0.8f;
        private boolean scope;
        private float reloadTime = 2f;
        private float reloadEmptyTime = 2.5f;
        private boolean shellReload;
        private float shellStart, shellTime, shellEnd;
        private String cycleClip;
        private float cycleTime;
        private float drawTime = 0.5f;
        private String shootSound;
        private CasingType casing = CasingType.RIFLE;
        private float adsMoveFactor = 0.6f;
        private int penetration = 1;
        private float knockback = 0.05f;
        private float muzzleVelocity = 400f;

        private Builder(String id) {
            this.id = id;
            this.shootSound = id + "_shot";
        }

        public Builder ammo(Supplier<Item> v) { ammo = v; return this; }
        public Builder mag(int size, boolean chamber) { magSize = size; this.chamber = chamber; return this; }
        public Builder modes(FireMode... v) { fireModes = List.of(v); return this; }
        public Builder rpm(float v) { rpm = v; return this; }
        public Builder burst(int v) { burstCount = v; return this; }
        public Builder damage(float dmg, float head) { damage = dmg; headshotMultiplier = head; return this; }
        public Builder range(float range, float fs, float fe, float min) { this.range = range; falloffStart = fs; falloffEnd = fe; minDamageFactor = min; return this; }
        public Builder pellets(int v) { pellets = v; return this; }
        public Builder spread(float hip, float ads, float move) { hipSpread = hip; adsSpread = ads; moveSpread = move; return this; }
        public Builder bloom(float perShot, float max) { bloomPerShot = perShot; maxBloom = max; return this; }
        public Builder recoil(float v, float h, float adsFactor, float kick) { recoilVertical = v; recoilHorizontal = h; recoilAdsFactor = adsFactor; visualKick = kick; return this; }
        public Builder ads(float time, float fov) { adsTime = time; adsFov = fov; return this; }
        public Builder scope() { scope = true; return this; }
        public Builder reload(float tactical, float empty) { reloadTime = tactical; reloadEmptyTime = empty; return this; }
        public Builder shellReload(float start, float perShell, float end) { shellReload = true; shellStart = start; shellTime = perShell; shellEnd = end; return this; }
        public Builder cycle(String clip, float time) { cycleClip = clip; cycleTime = time; return this; }
        public Builder draw(float v) { drawTime = v; return this; }
        public Builder casing(CasingType v) { casing = v; return this; }
        public Builder adsMove(float v) { adsMoveFactor = v; return this; }
        public Builder penetration(int v) { penetration = v; return this; }
        public Builder knockback(float v) { knockback = v; return this; }
        public Builder velocity(float v) { muzzleVelocity = v; return this; }

        public GunType build() {
            if (ammo == null) {
                throw new IllegalStateException("El arma " + id + " no tiene municion");
            }
            return new GunType(this);
        }
    }
}
