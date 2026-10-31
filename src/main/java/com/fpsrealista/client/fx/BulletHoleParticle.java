package com.fpsrealista.client.fx;

import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

/** Agujero de bala pegado a la cara de un bloque; se desvanece y desaparece si el bloque cambia. */
public class BulletHoleParticle extends TextureSheetParticle {
    private final Vector3f n;
    private final Vector3f t1;
    private final Vector3f t2;
    private final BlockPos pos;
    private final float size;

    public BulletHoleParticle(ClientLevel level, Vec3 hit, Direction face, BlockPos pos, TextureAtlasSprite sprite, float size, float angle) {
        super(level, hit.x + face.getStepX() * 0.004, hit.y + face.getStepY() * 0.004, hit.z + face.getStepZ() * 0.004);
        this.setSprite(sprite);
        this.pos = pos;
        this.size = size;
        this.lifetime = 900 + level.random.nextInt(200);
        this.hasPhysics = false;
        this.gravity = 0;
        this.n = new Vector3f(face.getStepX(), face.getStepY(), face.getStepZ());
        Vector3f up = Math.abs(n.y) > 0.5f ? new Vector3f(1, 0, 0) : new Vector3f(0, 1, 0);
        Vector3f a = new Vector3f(up).cross(n).normalize();
        Vector3f b = new Vector3f(n).cross(a).normalize();
        float c = (float) Math.cos(angle), s = (float) Math.sin(angle);
        this.t1 = new Vector3f(a).mul(c).add(new Vector3f(b).mul(s));
        this.t2 = new Vector3f(b).mul(c).sub(new Vector3f(a).mul(s));
    }

    @Override
    public void tick() {
        this.xo = this.x;
        this.yo = this.y;
        this.zo = this.z;
        if (this.age++ >= this.lifetime) {
            this.remove();
            return;
        }
        if ((age & 15) == 0 && level.getBlockState(pos).isAir()) {
            this.remove();
        }
        int left = lifetime - age;
        this.alpha = left < 80 ? left / 80f : 1f;
    }

    @Override
    public void render(VertexConsumer buffer, Camera camera, float partialTicks) {
        Vec3 cam = camera.getPosition();
        float cx = (float) (x - cam.x), cy = (float) (y - cam.y), cz = (float) (z - cam.z);
        int light = getLightColor(partialTicks);
        float u0 = getU0(), u1 = getU1(), v0 = getV0(), v1 = getV1();
        float[][] corners = {{-1, -1, u0, v1}, {1, -1, u1, v1}, {1, 1, u1, v0}, {-1, 1, u0, v0}};
        for (float[] c : corners) {
            float px = cx + (t1.x * c[0] + t2.x * c[1]) * size;
            float py = cy + (t1.y * c[0] + t2.y * c[1]) * size;
            float pz = cz + (t1.z * c[0] + t2.z * c[1]) * size;
            buffer.addVertex(px, py, pz).setUv(c[2], c[3]).setColor(1f, 1f, 1f, alpha).setLight(light);
        }
    }

    @Override
    public ParticleRenderType getRenderType() {
        return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT;
    }
}
