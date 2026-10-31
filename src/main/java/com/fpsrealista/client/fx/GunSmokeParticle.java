package com.fpsrealista.client.fx;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;

/** Humo de disparo / polvo de impacto que se expande y se desvanece. */
public class GunSmokeParticle extends TextureSheetParticle {
    private final float startSize;
    private final float growth;
    private final float startAlpha;

    public GunSmokeParticle(ClientLevel level, double x, double y, double z, double vx, double vy, double vz,
                            TextureAtlasSprite sprite, float size, float alpha, float r, float g, float b) {
        super(level, x, y, z);
        this.xd = vx;
        this.yd = vy;
        this.zd = vz;
        this.setSprite(sprite);
        this.startSize = size;
        this.quadSize = size;
        this.growth = 2.5f + level.random.nextFloat() * 1.5f;
        this.startAlpha = alpha;
        this.alpha = alpha;
        this.rCol = r;
        this.gCol = g;
        this.bCol = b;
        this.gravity = -0.015f;
        this.friction = 0.9f;
        this.hasPhysics = false;
        this.lifetime = 25 + level.random.nextInt(25);
        this.roll = level.random.nextFloat() * 6.28f;
        this.oRoll = roll;
    }

    @Override
    public void tick() {
        super.tick();
        float f = age / (float) lifetime;
        this.quadSize = startSize * (1f + f * growth);
        this.alpha = startAlpha * (1f - f) * (1f - f);
        this.oRoll = roll;
        this.roll += 0.01f;
    }

    @Override
    public ParticleRenderType getRenderType() {
        return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT;
    }
}
