package com.fpsrealista.client.fx;

import com.fpsrealista.ModRegistry;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.sounds.SoundSource;

/** Vaina expulsada con fisica, giro y rebotes con sonido metalico. */
public class CasingParticle extends TextureSheetParticle {
    private final float spin;
    private int bounces;
    private final boolean shell;

    public CasingParticle(ClientLevel level, double x, double y, double z, double vx, double vy, double vz,
                          TextureAtlasSprite sprite, float size, boolean shell) {
        super(level, x, y, z);
        this.xd = vx;
        this.yd = vy;
        this.zd = vz;
        this.setSprite(sprite);
        this.quadSize = size;
        this.gravity = 1.0f;
        this.friction = 0.985f;
        this.hasPhysics = true;
        this.lifetime = 120 + level.random.nextInt(60);
        this.spin = (level.random.nextFloat() - 0.5f) * 1.6f;
        this.shell = shell;
    }

    @Override
    public void tick() {
        double vyBefore = this.yd;
        this.oRoll = this.roll;
        super.tick();
        if (!onGround) {
            this.roll += spin;
        } else if (bounces < 3 && vyBefore < -0.06) {
            bounces++;
            this.yd = -vyBefore * 0.38;
            this.xd *= 0.55;
            this.zd *= 0.55;
            this.roll += spin * 0.5f;
            float vol = Math.min(0.6f, (float) -vyBefore * 1.6f);
            level.playLocalSound(x, y, z, ModRegistry.sound(shell ? "shell_drop" : "casing"), SoundSource.PLAYERS,
                    vol, 0.9f + level.random.nextFloat() * 0.25f, false);
        }
        int left = lifetime - age;
        this.alpha = left < 20 ? left / 20f : 1f;
    }

    @Override
    public ParticleRenderType getRenderType() {
        return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT;
    }
}
