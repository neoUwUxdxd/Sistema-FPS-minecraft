package com.fpsrealista.gun;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.Tags;

/**
 * Balistica hitscan compartida por cliente (prediccion de efectos) y servidor (dano).
 * La dispersion usa una semilla para que ambos lados calculen los mismos perdigones.
 */
public final class Ballistics {
    public enum HitType { MISS, BLOCK, ENTITY, GLASS, FOLIAGE }

    public static final class Hit {
        public final HitType type;
        public final Vec3 pos;
        public final double distance;
        public final Entity entity;
        public final BlockPos blockPos;
        public final Direction face;
        public final boolean headshot;

        Hit(HitType type, Vec3 pos, double distance, Entity entity, BlockPos blockPos, Direction face, boolean headshot) {
            this.type = type;
            this.pos = pos;
            this.distance = distance;
            this.entity = entity;
            this.blockPos = blockPos;
            this.face = face;
            this.headshot = headshot;
        }
    }

    /** Direccion de mirada a partir de yaw/pitch en grados (convencion de Minecraft). */
    public static Vec3 viewVector(float yaw, float pitch) {
        float f = pitch * Mth.DEG_TO_RAD;
        float g = -yaw * Mth.DEG_TO_RAD;
        float h = Mth.cos(g);
        float i = Mth.sin(g);
        float j = Mth.cos(f);
        float k = Mth.sin(f);
        return new Vec3(i * j, -k, h * j);
    }

    /** Desvia "forward" dentro de un cono de semiangulo spreadDeg (distribucion concentrada en el centro). */
    public static Vec3 spread(Vec3 forward, float spreadDeg, Random rnd) {
        if (spreadDeg <= 0.0001f) {
            return forward;
        }
        double r = Math.sqrt(rnd.nextDouble()) * 0.65 + rnd.nextGaussian() * 0.12;
        r = Mth.clamp(Math.abs(r), 0, 1);
        double ang = Math.toRadians(spreadDeg) * r;
        double theta = rnd.nextDouble() * Math.PI * 2;
        Vec3 up = Math.abs(forward.y) > 0.99 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
        Vec3 right = forward.cross(up).normalize();
        Vec3 up2 = right.cross(forward).normalize();
        double t = Math.tan(ang);
        return forward.add(right.scale(Math.cos(theta) * t)).add(up2.scale(Math.sin(theta) * t)).normalize();
    }

    public static boolean isGlass(BlockState s) {
        return s.is(Tags.Blocks.GLASS_BLOCKS) || s.is(Tags.Blocks.GLASS_PANES);
    }

    public static boolean isFoliage(BlockState s) {
        return s.is(BlockTags.LEAVES);
    }

    /**
     * Traza una bala. Devuelve los impactos ordenados por distancia: cristales/hojas atravesados,
     * entidades alcanzadas (hasta maxEntities) y el impacto final en bloque o un MISS al alcance maximo.
     */
    public static List<Hit> trace(Level level, Entity shooter, Vec3 start, Vec3 dir, double range, int maxEntities,
                                  boolean passGlass, boolean passFoliage) {
        List<Hit> hits = new ArrayList<>();
        Vec3 end = start.add(dir.scale(range));
        Vec3 cur = start;
        Hit terminal = null;
        for (int iter = 0; iter < 12; iter++) {
            BlockHitResult bh = level.clip(new ClipContext(cur, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, shooter));
            if (bh.getType() == HitResult.Type.MISS) {
                break;
            }
            BlockState state = level.getBlockState(bh.getBlockPos());
            boolean glass = passGlass && isGlass(state);
            boolean foliage = passFoliage && isFoliage(state);
            double d = bh.getLocation().distanceTo(start);
            if (glass || foliage) {
                hits.add(new Hit(glass ? HitType.GLASS : HitType.FOLIAGE, bh.getLocation(), d, null, bh.getBlockPos(),
                        bh.getDirection(), false));
                // avanzar hasta salir del bloque atravesado
                BlockPos bp = bh.getBlockPos();
                Vec3 p = bh.getLocation();
                for (int s = 0; s < 40 && BlockPos.containing(p).equals(bp); s++) {
                    p = p.add(dir.scale(0.05));
                }
                cur = p;
                continue;
            }
            terminal = new Hit(HitType.BLOCK, bh.getLocation(), d, null, bh.getBlockPos(), bh.getDirection(), false);
            break;
        }
        Vec3 segEnd = terminal != null ? terminal.pos : end;

        List<Hit> ents = new ArrayList<>();
        AABB box = new AABB(start, segEnd).inflate(1.0);
        for (Entity e : level.getEntities(shooter, box, e -> e.isPickable() && e.isAlive() && !e.isSpectator())) {
            if (shooter != null && shooter.isPassengerOfSameVehicle(e)) {
                continue;
            }
            AABB bb = e.getBoundingBox().inflate(0.08);
            var o = bb.clip(start, segEnd);
            if (o.isEmpty() && !bb.contains(start)) {
                continue;
            }
            Vec3 hp = o.orElse(start);
            boolean head = false;
            if (e instanceof LivingEntity && e.getBbHeight() > 1.0f) {
                double eye = e.getEyeY();
                head = hp.y >= eye - 0.27 && hp.y <= e.getBoundingBox().maxY + 0.1;
            }
            ents.add(new Hit(HitType.ENTITY, hp, hp.distanceTo(start), e, null, null, head));
        }
        ents.sort(Comparator.comparingDouble(h -> h.distance));
        int n = Math.min(maxEntities, ents.size());
        hits.addAll(ents.subList(0, n));
        // si la bala se detiene en la ultima entidad posible, no hay impacto final mas alla
        if (n >= maxEntities && n > 0) {
            Hit last = ents.get(n - 1);
            hits.removeIf(h -> (h.type == HitType.GLASS || h.type == HitType.FOLIAGE) && h.distance > last.distance);
            terminal = null;
        }
        if (terminal != null) {
            hits.add(terminal);
        } else if (n < maxEntities) {
            hits.add(new Hit(HitType.MISS, end, range, null, null, null, false));
        }
        hits.sort(Comparator.comparingDouble(h -> h.distance));
        return hits;
    }

    /** Factor de dano por distancia (lineal entre falloffStart y falloffEnd). */
    public static float falloff(GunType t, double dist) {
        if (dist <= t.falloffStart) {
            return 1f;
        }
        if (dist >= t.falloffEnd) {
            return t.minDamageFactor;
        }
        double f = (dist - t.falloffStart) / (t.falloffEnd - t.falloffStart);
        return (float) Mth.lerp(f, 1.0, t.minDamageFactor);
    }

    private Ballistics() {}
}
