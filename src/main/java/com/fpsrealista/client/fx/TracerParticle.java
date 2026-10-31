package com.fpsrealista.client.fx;

import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

/** Trazadora: segmento luminoso que viaja del canon al impacto. */
public class TracerParticle extends TextureSheetParticle {
    private final Vec3 start;
    private final Vec3 dir;
    private final double length;
    private final double speed;
    private final double segment;
    private final float width;
    private double head;
    private double headO;

    public TracerParticle(ClientLevel level, Vec3 start, Vec3 end, TextureAtlasSprite sprite, double speedPerTick, float width) {
        super(level, start.x, start.y, start.z);
        this.start = start;
        Vec3 d = end.subtract(start);
        this.length = d.length();
        this.dir = length > 1e-6 ? d.scale(1 / length) : new Vec3(0, 0, 1);
        this.speed = speedPerTick;
        this.segment = Math.min(5.0, speedPerTick * 0.6);
        this.width = width;
        this.lifetime = (int) Math.ceil((length + segment) / speed) + 1;
        this.hasPhysics = false;
        this.gravity = 0;
        this.setSprite(sprite);
        this.head = Math.min(length, speed * 0.35);
        this.headO = 0;
    }

    @Override
    public void tick() {
        this.xo = this.x;
        this.yo = this.y;
        this.zo = this.z;
        if (this.age++ >= this.lifetime || headO - segment > length) {
            this.remove();
            return;
        }
        headO = head;
        head += speed;
        Vec3 p = start.add(dir.scale(Math.min(head, length)));
        this.setPos(p.x, p.y, p.z);
    }

    @Override
    public void render(VertexConsumer buffer, Camera camera, float partialTicks) {
        double h = headO + (head - headO) * partialTicks;
        double a = Math.max(0, h - segment);
        double b = Math.min(length, h);
        if (b <= a) {
            return;
        }
        Vec3 cam = camera.getPosition();
        Vec3 pa = start.add(dir.scale(a)).subtract(cam);
        Vec3 pb = start.add(dir.scale(b)).subtract(cam);
        Vec3 mid = pa.add(pb).scale(0.5);
        Vec3 side = dir.cross(mid).normalize();
        double dist = mid.length();
        float w = (float) (width * Math.max(1.0, dist * 0.06));
        Vector3f s = new Vector3f((float) side.x * w, (float) side.y * w, (float) side.z * w);
        float u0 = getU0(), u1 = getU1(), v0 = getV0(), v1 = getV1();
        int light = 0xF000F0;
        float alpha = 0.9f;
        quad(buffer, pa, pb, s, u0, u1, v0, v1, light, alpha);
    }

    private static void quad(VertexConsumer b, Vec3 pa, Vec3 pb, Vector3f s, float u0, float u1, float v0, float v1, int light, float alpha) {
        // cola (u0) -> cabeza (u1); doble cara
        vtx(b, pa.x - s.x, pa.y - s.y, pa.z - s.z, u0, v1, light, alpha);
        vtx(b, pa.x + s.x, pa.y + s.y, pa.z + s.z, u0, v0, light, alpha);
        vtx(b, pb.x + s.x, pb.y + s.y, pb.z + s.z, u1, v0, light, alpha);
        vtx(b, pb.x - s.x, pb.y - s.y, pb.z - s.z, u1, v1, light, alpha);
        vtx(b, pb.x - s.x, pb.y - s.y, pb.z - s.z, u1, v1, light, alpha);
        vtx(b, pb.x + s.x, pb.y + s.y, pb.z + s.z, u1, v0, light, alpha);
        vtx(b, pa.x + s.x, pa.y + s.y, pa.z + s.z, u0, v0, light, alpha);
        vtx(b, pa.x - s.x, pa.y - s.y, pa.z - s.z, u0, v1, light, alpha);
    }

    private static void vtx(VertexConsumer b, double x, double y, double z, float u, float v, int light, float alpha) {
        b.addVertex((float) x, (float) y, (float) z).setUv(u, v).setColor(1f, 0.92f, 0.7f, alpha).setLight(light);
    }

    @Override
    public ParticleRenderType getRenderType() {
        return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT;
    }

    @Override
    protected int getLightColor(float partialTick) {
        return 0xF000F0;
    }
}
