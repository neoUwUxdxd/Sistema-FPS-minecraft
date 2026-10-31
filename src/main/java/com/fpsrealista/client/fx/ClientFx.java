package com.fpsrealista.client.fx;

import com.fpsrealista.ModRegistry;
import com.fpsrealista.client.GunClient;
import com.fpsrealista.gun.Ballistics;
import com.fpsrealista.gun.CasingType;
import com.fpsrealista.gun.GunType;
import com.fpsrealista.gun.GunTypes;
import com.fpsrealista.network.ShotFxPayload;
import java.util.List;
import java.util.Random;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.ParticleEngine;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.client.event.RegisterParticleProvidersEvent;
import org.joml.Vector3f;

/** Efectos visuales del cliente: trazadoras, impactos, vainas, humo. */
public final class ClientFx {
    private static SpriteSet tracer, hole, casing, shotshell, smoke;
    private static final RandomSource RNG = RandomSource.create();

    /** Posiciones del canon y la ventana de expulsion en espacio de vista (las fija el render en 1a persona). */
    public static final Vector3f MUZZLE_VIEW = new Vector3f(0.15f, -0.08f, -0.8f);
    public static final Vector3f EJECT_VIEW = new Vector3f(0.18f, -0.08f, -0.3f);
    public static boolean viewValid;

    private ClientFx() {}

    public static void registerProviders(RegisterParticleProvidersEvent e) {
        e.registerSpriteSet(ModRegistry.TRACER.get(), s -> provider(() -> tracer = s, s));
        e.registerSpriteSet(ModRegistry.BULLET_HOLE.get(), s -> provider(() -> hole = s, s));
        e.registerSpriteSet(ModRegistry.CASING.get(), s -> provider(() -> casing = s, s));
        e.registerSpriteSet(ModRegistry.SHOTSHELL.get(), s -> provider(() -> shotshell = s, s));
        e.registerSpriteSet(ModRegistry.GUN_SMOKE.get(), s -> provider(() -> smoke = s, s));
    }

    private static ParticleProvider<SimpleParticleType> provider(Runnable capture, SpriteSet s) {
        capture.run();
        return (type, level, x, y, z, dx, dy, dz) -> new GunSmokeParticle(level, x, y, z, dx, dy, dz, s.get(RNG), 0.1f, 0.4f, 0.8f, 0.8f, 0.8f);
    }

    private static TextureAtlasSprite sprite(SpriteSet s) {
        return s == null ? null : s.get(RNG);
    }

    private static ParticleEngine engine() {
        return Minecraft.getInstance().particleEngine;
    }

    /** Convierte un punto del espacio de vista (1a persona) a coordenadas de mundo. */
    public static Vec3 viewToWorld(Vector3f v) {
        Camera cam = Minecraft.getInstance().gameRenderer.getMainCamera();
        Vector3f w = cam.rotation().transform(new Vector3f(v));
        return cam.getPosition().add(w.x, w.y, w.z);
    }

    private static Vec3 muzzleWorld(Player p) {
        Minecraft mc = Minecraft.getInstance();
        if (viewValid && mc.options.getCameraType().isFirstPerson() && p == mc.player) {
            return viewToWorld(MUZZLE_VIEW);
        }
        return approxMuzzle(p, 0.9);
    }

    private static Vec3 approxMuzzle(Entity p, double fwd) {
        Vec3 look = p.getLookAngle();
        Vec3 right = look.cross(new Vec3(0, 1, 0)).normalize();
        return p.getEyePosition().add(look.scale(fwd)).add(right.scale(0.25)).add(0, -0.18, 0);
    }

    // ------------------------------------------------------------------ disparo propio (prediccion)
    public static void localShot(Player player, GunType type, int seed, float yaw, float pitch, float spread) {
        ClientLevel level = Minecraft.getInstance().level;
        if (level == null) {
            return;
        }
        Vec3 eye = player.getEyePosition();
        Vec3 fwd = Ballistics.viewVector(yaw, pitch);
        Random rnd = new Random(seed);
        Vec3 muzzle = muzzleWorld(player);
        for (int i = 0; i < type.pellets; i++) {
            Vec3 dir = Ballistics.spread(fwd, spread, rnd);
            List<Ballistics.Hit> hits = Ballistics.trace(level, player, eye, dir, type.range, type.penetration, true, true);
            Vec3 end = hits.isEmpty() ? eye.add(dir.scale(type.range)) : hits.get(hits.size() - 1).pos;
            if (i == 0 || RNG.nextFloat() < 0.5f) {
                tracer(level, muzzle, end, type);
            }
            for (Ballistics.Hit h : hits) {
                BlockState st = h.blockPos != null ? level.getBlockState(h.blockPos) : null;
                impact(level, h.type, h.pos, h.face, h.blockPos, st, dir);
            }
        }
        muzzleSmoke(level, muzzle, fwd, type);
    }

    // ------------------------------------------------------------------ disparos de otros jugadores
    public static void remoteShot(ShotFxPayload p) {
        Minecraft mc = Minecraft.getInstance();
        ClientLevel level = mc.level;
        if (level == null) {
            return;
        }
        Entity shooter = level.getEntity(p.shooterId());
        GunType type = GunTypes.byIndex(p.gun());
        Vec3 muzzle = shooter != null ? approxMuzzle(shooter, 0.8) : null;
        int n = 0;
        for (ShotFxPayload.FxHit h : p.hits()) {
            Vec3 pos = new Vec3(h.x(), h.y(), h.z());
            Ballistics.HitType ht = Ballistics.HitType.values()[Math.floorMod(h.type(), Ballistics.HitType.values().length)];
            Direction face = h.face() >= 0 && h.face() < 6 ? Direction.values()[h.face()] : null;
            BlockPos bp = ht == Ballistics.HitType.ENTITY || ht == Ballistics.HitType.MISS ? null : BlockPos.containing(
                    face != null ? pos.subtract(face.getStepX() * 0.01, face.getStepY() * 0.01, face.getStepZ() * 0.01) : pos);
            BlockState st = h.blockState() != 0 ? Block.stateById(h.blockState()) : null;
            Vec3 dir = muzzle != null ? pos.subtract(muzzle).normalize() : new Vec3(0, 0, 1);
            boolean terminal = ht == Ballistics.HitType.BLOCK || ht == Ballistics.HitType.MISS;
            if (terminal && muzzle != null && type != null && n++ < 6) {
                tracer(level, muzzle, pos, type);
            }
            impact(level, ht, pos, face, bp, st, dir);
        }
        if (muzzle != null && type != null && shooter != null) {
            muzzleSmoke(level, muzzle, shooter.getLookAngle(), type);
        }
    }

    // ------------------------------------------------------------------ piezas
    private static void tracer(ClientLevel level, Vec3 from, Vec3 to, GunType type) {
        TextureAtlasSprite s = sprite(tracer);
        if (s == null || from.distanceToSqr(to) < 4) {
            return;
        }
        double speed = Math.min(40.0, type.muzzleVelocity / 20.0 * 0.12);
        float w = type.pellets > 1 ? 0.012f : 0.02f;
        engine().add(new TracerParticle(level, from, to, s, Math.max(12.0, speed), w));
    }

    public static void impact(ClientLevel level, Ballistics.HitType type, Vec3 pos, Direction face, BlockPos bp, BlockState st, Vec3 dir) {
        switch (type) {
            case BLOCK -> {
                if (face == null || bp == null) {
                    return;
                }
                TextureAtlasSprite hs = sprite(hole);
                if (hs != null) {
                    engine().add(new BulletHoleParticle(level, pos, face, bp, hs, 0.055f + RNG.nextFloat() * 0.03f,
                            RNG.nextFloat() * 6.28f));
                }
                Vec3 n = new Vec3(face.getStepX(), face.getStepY(), face.getStepZ());
                if (st != null && !st.isAir()) {
                    BlockParticleOption opt = new BlockParticleOption(ParticleTypes.BLOCK, st);
                    for (int i = 0; i < 8; i++) {
                        Vec3 v = n.scale(0.12 + RNG.nextDouble() * 0.15).add(RNG.nextGaussian() * 0.06, RNG.nextDouble() * 0.1, RNG.nextGaussian() * 0.06);
                        level.addParticle(opt, pos.x, pos.y, pos.z, v.x, v.y, v.z);
                    }
                }
                TextureAtlasSprite sm = sprite(smoke);
                if (sm != null) {
                    float c = 0.55f + RNG.nextFloat() * 0.1f;
                    for (int i = 0; i < 2; i++) {
                        Vec3 v = n.scale(0.03 + RNG.nextDouble() * 0.03);
                        engine().add(new GunSmokeParticle(level, pos.x + n.x * 0.05, pos.y + n.y * 0.05, pos.z + n.z * 0.05,
                                v.x, v.y, v.z, sm, 0.08f, 0.55f, c, c * 0.95f, c * 0.9f));
                    }
                }
                level.playLocalSound(pos.x, pos.y, pos.z, ModRegistry.sound("impact_block"), SoundSource.BLOCKS, 0.6f,
                        0.9f + RNG.nextFloat() * 0.2f, false);
                if (st != null) {
                    var stp = st.getSoundType();
                    level.playLocalSound(pos.x, pos.y, pos.z, stp.getHitSound(), SoundSource.BLOCKS, 0.4f, stp.getPitch() * 1.2f, false);
                }
            }
            case GLASS -> {
                if (st != null) {
                    BlockParticleOption opt = new BlockParticleOption(ParticleTypes.BLOCK, st);
                    for (int i = 0; i < 14; i++) {
                        Vec3 v = dir.scale(0.15 + RNG.nextDouble() * 0.2).add(RNG.nextGaussian() * 0.08, RNG.nextGaussian() * 0.08, RNG.nextGaussian() * 0.08);
                        level.addParticle(opt, pos.x, pos.y, pos.z, v.x, v.y, v.z);
                    }
                }
                level.playLocalSound(pos.x, pos.y, pos.z, ModRegistry.sound("glass_hit"), SoundSource.BLOCKS, 0.8f, 1f, false);
            }
            case FOLIAGE -> {
                if (st != null) {
                    BlockParticleOption opt = new BlockParticleOption(ParticleTypes.BLOCK, st);
                    for (int i = 0; i < 4; i++) {
                        level.addParticle(opt, pos.x, pos.y, pos.z, RNG.nextGaussian() * 0.05, RNG.nextDouble() * 0.05, RNG.nextGaussian() * 0.05);
                    }
                }
            }
            case ENTITY -> {
                DustParticleOptions blood = new DustParticleOptions(new Vector3f(0.45f, 0.02f, 0.02f), 1.1f);
                for (int i = 0; i < 10; i++) {
                    Vec3 v = dir.scale(0.08 + RNG.nextDouble() * 0.12).add(RNG.nextGaussian() * 0.05, RNG.nextDouble() * 0.06, RNG.nextGaussian() * 0.05);
                    level.addParticle(blood, pos.x, pos.y, pos.z, v.x, v.y, v.z);
                }
                level.addParticle(ParticleTypes.DAMAGE_INDICATOR, pos.x, pos.y, pos.z, 0, 0.1, 0);
            }
            default -> {}
        }
    }

    private static void muzzleSmoke(ClientLevel level, Vec3 muzzle, Vec3 fwd, GunType type) {
        TextureAtlasSprite sm = sprite(smoke);
        if (sm == null) {
            return;
        }
        int n = type.pellets > 1 || type.scope ? 4 : 2;
        for (int i = 0; i < n; i++) {
            Vec3 v = fwd.scale(0.03 + RNG.nextDouble() * 0.05).add(RNG.nextGaussian() * 0.01, 0.01, RNG.nextGaussian() * 0.01);
            engine().add(new GunSmokeParticle(level, muzzle.x, muzzle.y, muzzle.z, v.x, v.y, v.z, sm, 0.05f, 0.28f, 0.85f, 0.85f, 0.85f));
        }
    }

    /** Expulsa una vaina desde la ventana de expulsion del arma en primera persona. */
    public static void ejectCasing(GunType type) {
        Minecraft mc = Minecraft.getInstance();
        ClientLevel level = mc.level;
        Player p = mc.player;
        if (level == null || p == null || type == null || type.casing == CasingType.NONE) {
            return;
        }
        boolean shell = type.casing == CasingType.SHELL;
        TextureAtlasSprite s = sprite(shell ? shotshell : casing);
        if (s == null) {
            return;
        }
        Vec3 pos = viewValid && mc.options.getCameraType().isFirstPerson() ? viewToWorld(EJECT_VIEW) : approxMuzzle(p, 0.3);
        Vec3 look = p.getLookAngle();
        Vec3 right = look.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 v = right.scale(0.12 + RNG.nextDouble() * 0.06).add(0, 0.12 + RNG.nextDouble() * 0.06, 0)
                .add(look.scale(-0.03)).add(p.getDeltaMovement());
        float size = shell ? 0.05f : type.casing == CasingType.PISTOL ? 0.022f : 0.03f;
        engine().add(new CasingParticle(level, pos.x, pos.y, pos.z, v.x, v.y, v.z, s, size, shell));
        if (GunClient.I.type != null && !shell) {
            // pequena voluta de humo por la ventana
            TextureAtlasSprite sm = sprite(smoke);
            if (sm != null) {
                engine().add(new GunSmokeParticle(level, pos.x, pos.y, pos.z, 0, 0.01, 0, sm, 0.025f, 0.2f, 0.85f, 0.85f, 0.85f));
            }
        }
    }
}
