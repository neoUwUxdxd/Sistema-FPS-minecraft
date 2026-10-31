package com.fpsrealista.server;

import com.fpsrealista.Config;
import com.fpsrealista.FpsRealista;
import com.fpsrealista.ModRegistry;
import com.fpsrealista.gun.Ballistics;
import com.fpsrealista.gun.GunItem;
import com.fpsrealista.gun.GunType;
import com.fpsrealista.gun.GunTypes;
import com.fpsrealista.network.FireModePayload;
import com.fpsrealista.network.HitMarkerPayload;
import com.fpsrealista.network.ReloadPayload;
import com.fpsrealista.network.ShootPayload;
import com.fpsrealista.network.ShotFxPayload;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.phys.Vec3;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;

/**
 * Logica autoritativa del servidor: cadencia, municion, recargas, balistica y dano.
 */
public final class GunServerLogic {
    public static final ResourceKey<DamageType> BULLET = ResourceKey.create(Registries.DAMAGE_TYPE, FpsRealista.id("bullet"));
    public static final ResourceKey<DamageType> BULLET_HEADSHOT = ResourceKey.create(Registries.DAMAGE_TYPE, FpsRealista.id("bullet_headshot"));

    private static final Map<UUID, State> STATES = new ConcurrentHashMap<>();

    private static final class State {
        long lastShotTick = -1000;
        double tokens = 2;
        // recarga
        boolean reloading;
        int reloadSlot;
        long reloadEnd;
        long nextShell;
        boolean shellMode;
        int capacity;
        Item reloadItem;
    }

    public static void init(IEventBus bus) {
        bus.addListener(PlayerTickEvent.Post.class, e -> {
            if (e.getEntity() instanceof ServerPlayer sp) {
                tick(sp);
            }
        });
        bus.addListener(PlayerEvent.PlayerLoggedOutEvent.class, e -> STATES.remove(e.getEntity().getUUID()));
    }

    private static State state(Player p) {
        return STATES.computeIfAbsent(p.getUUID(), u -> new State());
    }

    private static boolean infinite(Player p) {
        return p.getAbilities().instabuild && Config.INFINITE_AMMO_CREATIVE.get();
    }

    // ------------------------------------------------------------------ disparo
    public static void onShoot(Player player, ShootPayload p) {
        if (!(player instanceof ServerPlayer sp) || sp.isSpectator()) {
            return;
        }
        if (p.slot() != sp.getInventory().selected) {
            return;
        }
        ItemStack stack = sp.getMainHandItem();
        GunType type = GunItem.typeOf(stack);
        if (type == null) {
            return;
        }
        State st = state(sp);
        long now = sp.serverLevel().getGameTime();

        if (st.reloading) {
            if (st.shellMode) {
                st.reloading = false; // una recarga cartucho a cartucho se puede interrumpir disparando
            } else {
                return;
            }
        }
        // cadencia (cubo de fichas con tolerancia de latencia)
        double intervalTicks = type.shotInterval() * 20.0;
        st.tokens = Math.min(2.0, st.tokens + (now - st.lastShotTick) / intervalTicks);
        if (st.tokens < 0.85) {
            return;
        }
        st.tokens -= 1.0;
        st.lastShotTick = now;

        int ammo = GunItem.getAmmo(stack);
        if (ammo <= 0) {
            return;
        }
        if (!infinite(sp)) {
            GunItem.setAmmo(stack, ammo - 1);
        }

        // direccion: se acepta la del cliente si esta cerca de la del servidor
        float yaw = p.yaw();
        float pitch = p.pitch();
        if (Math.abs(Mth.wrapDegrees(yaw - sp.getYRot())) > 20 || Math.abs(pitch - sp.getXRot()) > 20) {
            yaw = sp.getYRot();
            pitch = sp.getXRot();
        }
        float minSpread = p.aiming() ? type.adsSpread : type.hipSpread * 0.5f;
        float spread = Mth.clamp(p.spread(), minSpread * 0.9f, type.hipSpread + type.moveSpread + type.maxBloom + 2f);

        ServerLevel level = sp.serverLevel();
        Vec3 eye = sp.getEyePosition();
        Vec3 fwd = Ballistics.viewVector(yaw, pitch);
        Random rnd = new Random(p.seed());
        boolean glass = Config.BREAK_GLASS.get();
        boolean foliage = Config.PENETRATE_FOLIAGE.get();
        List<ShotFxPayload.FxHit> fx = new ArrayList<>();
        boolean anyHit = false;
        boolean anyHead = false;
        boolean anyKill = false;

        for (int i = 0; i < type.pellets; i++) {
            Vec3 dir = Ballistics.spread(fwd, spread, rnd);
            List<Ballistics.Hit> hits = Ballistics.trace(level, sp, eye, dir, type.range, type.penetration, true, foliage);
            float energy = 1f;
            for (Ballistics.Hit h : hits) {
                switch (h.type) {
                    case GLASS -> {
                        if (glass) {
                            level.destroyBlock(h.blockPos, false, sp);
                        }
                        energy *= 0.85f;
                    }
                    case FOLIAGE -> energy *= 0.9f;
                    case ENTITY -> {
                        int r = damage(sp, type, h, dir, energy);
                        if (r > 0) {
                            anyHit = true;
                            anyHead |= h.headshot;
                            anyKill |= r == 2;
                        }
                        energy *= 0.55f;
                    }
                    default -> {}
                }
                int face = h.face == null ? -1 : h.face.ordinal();
                int bs = h.blockPos != null ? Block.getId(level.getBlockState(h.blockPos)) : 0;
                fx.add(new ShotFxPayload.FxHit(h.pos.x, h.pos.y, h.pos.z, h.type.ordinal(), face, bs));
            }
            whizz(level, sp, eye, hits.isEmpty() ? eye.add(dir.scale(type.range)) : hits.get(hits.size() - 1).pos);
        }

        // sonido del disparo para todos excepto el tirador (que lo reproduce localmente sin latencia)
        float range = type.scope ? 256f : type.pellets > 1 ? 150f : 160f;
        level.playSound(sp, sp.getX(), sp.getEyeY(), sp.getZ(), ModRegistry.sound(type.shootSound), SoundSource.PLAYERS,
                range / 16f, 0.95f + rnd.nextFloat() * 0.1f);
        PacketDistributor.sendToPlayersTrackingEntity(sp, new ShotFxPayload(sp.getId(), GunTypes.indexOf(type), fx));
        if (anyHit) {
            PacketDistributor.sendToPlayer(sp, new HitMarkerPayload(anyHead, anyKill));
        }
        sp.causeFoodExhaustion(0.005f);
    }

    /** @return 0 sin dano, 1 dano, 2 muerte */
    private static int damage(ServerPlayer sp, GunType type, Ballistics.Hit h, Vec3 dir, float energy) {
        Entity target = h.entity;
        if (target == null) {
            return 0;
        }
        if (Config.FRIENDLY_PETS.get() && target instanceof OwnableEntity own && sp.getUUID().equals(own.getOwnerUUID())) {
            return 0;
        }
        float dmg = type.damage * Ballistics.falloff(type, h.distance) * energy * Config.DAMAGE_MULTIPLIER.get().floatValue();
        if (h.headshot) {
            dmg *= type.headshotMultiplier;
        }
        Holder<DamageType> dt = sp.serverLevel().registryAccess().registryOrThrow(Registries.DAMAGE_TYPE)
                .getHolderOrThrow(h.headshot ? BULLET_HEADSHOT : BULLET);
        DamageSource src = new DamageSource(dt, sp, sp);
        target.invulnerableTime = 0;
        boolean wasAlive = target.isAlive();
        boolean ok = target.hurt(src, dmg);
        if (ok && target instanceof LivingEntity le) {
            le.knockback(type.knockback * energy, -dir.x, -dir.z);
            le.invulnerableTime = 0;
        }
        sp.serverLevel().playSound(null, h.pos.x, h.pos.y, h.pos.z, ModRegistry.sound("impact_flesh"), SoundSource.PLAYERS, 0.7f, 1f);
        if (!ok) {
            return 0;
        }
        return wasAlive && !target.isAlive() ? 2 : 1;
    }

    /** Silbido de bala para jugadores cerca de la trayectoria. */
    private static void whizz(ServerLevel level, ServerPlayer shooter, Vec3 a, Vec3 b) {
        Vec3 ab = b.subtract(a);
        double len2 = ab.lengthSqr();
        if (len2 < 4) {
            return;
        }
        for (ServerPlayer other : level.players()) {
            if (other == shooter) {
                continue;
            }
            Vec3 p = other.getEyePosition();
            double t = Mth.clamp(p.subtract(a).dot(ab) / len2, 0, 1);
            Vec3 c = a.add(ab.scale(t));
            double d = c.distanceTo(p);
            if (d < 3.0 && c.distanceTo(a) > 6) {
                level.playSound(null, c.x, c.y, c.z, ModRegistry.sound("whizz"), SoundSource.PLAYERS, 1.0f, 0.9f + level.random.nextFloat() * 0.2f);
            }
        }
    }

    // ------------------------------------------------------------------ recarga
    public static void onReload(Player player, ReloadPayload p) {
        if (!(player instanceof ServerPlayer sp)) {
            return;
        }
        State st = state(sp);
        if (!p.start()) {
            st.reloading = false;
            return;
        }
        if (st.reloading || p.slot() != sp.getInventory().selected) {
            return;
        }
        ItemStack stack = sp.getMainHandItem();
        GunType type = GunItem.typeOf(stack);
        if (type == null) {
            return;
        }
        int ammo = GunItem.getAmmo(stack);
        int cap = type.capacity(ammo > 0);
        Item ammoItem = type.ammo.get();
        if (ammo >= cap || (!infinite(sp) && countAmmo(sp, ammoItem) <= 0)) {
            return;
        }
        long now = sp.serverLevel().getGameTime();
        st.reloading = true;
        st.reloadSlot = sp.getInventory().selected;
        st.capacity = cap;
        st.reloadItem = stack.getItem();
        st.shellMode = type.shellReload;
        if (type.shellReload) {
            st.nextShell = now + Math.round((type.shellStart + type.shellTime * 0.7f) * 20);
        } else {
            // el cargador queda insertado ~80% de la animacion; se acredita al final
            st.reloadEnd = now + Math.round((ammo == 0 ? type.reloadEmptyTime : type.reloadTime) * 20 * 0.9f);
        }
    }

    private static void tick(ServerPlayer sp) {
        State st = STATES.get(sp.getUUID());
        if (st == null || !st.reloading) {
            return;
        }
        ItemStack stack = sp.getMainHandItem();
        GunType type = GunItem.typeOf(stack);
        if (type == null || sp.getInventory().selected != st.reloadSlot || stack.getItem() != st.reloadItem) {
            st.reloading = false;
            return;
        }
        long now = sp.serverLevel().getGameTime();
        int ammo = GunItem.getAmmo(stack);
        Item ammoItem = type.ammo.get();
        if (st.shellMode) {
            if (now >= st.nextShell) {
                if (ammo < st.capacity && (infinite(sp) || takeAmmo(sp, ammoItem, 1) == 1)) {
                    GunItem.setAmmo(stack, ammo + 1);
                    st.nextShell = now + Math.round(type.shellTime * 20);
                    if (ammo + 1 >= st.capacity) {
                        st.reloading = false;
                    }
                } else {
                    st.reloading = false;
                }
            }
        } else if (now >= st.reloadEnd) {
            int need = st.capacity - ammo;
            int got = infinite(sp) ? need : takeAmmo(sp, ammoItem, need);
            GunItem.setAmmo(stack, ammo + got);
            st.reloading = false;
        }
    }

    public static int countAmmo(Player p, Item item) {
        int n = 0;
        for (ItemStack s : p.getInventory().items) {
            if (s.is(item)) {
                n += s.getCount();
            }
        }
        for (ItemStack s : p.getInventory().offhand) {
            if (s.is(item)) {
                n += s.getCount();
            }
        }
        return n;
    }

    private static int takeAmmo(Player p, Item item, int want) {
        int got = 0;
        List<ItemStack> all = new ArrayList<>(p.getInventory().items);
        all.addAll(p.getInventory().offhand);
        for (ItemStack s : all) {
            if (got >= want) {
                break;
            }
            if (s.is(item)) {
                int t = Math.min(want - got, s.getCount());
                s.shrink(t);
                got += t;
            }
        }
        if (got > 0) {
            p.getInventory().setChanged();
        }
        return got;
    }

    // ------------------------------------------------------------------ modo de fuego
    public static void onFireMode(Player player, FireModePayload p) {
        if (p.slot() != player.getInventory().selected) {
            return;
        }
        ItemStack stack = player.getMainHandItem();
        GunType type = GunItem.typeOf(stack);
        if (type == null) {
            return;
        }
        GunItem.setFireModeIndex(stack, Math.floorMod(p.mode(), type.fireModes.size()));
        player.level().playSound(player, player.getX(), player.getY(), player.getZ(), ModRegistry.sound("fire_select"),
                SoundSource.PLAYERS, 0.5f, 1f);
    }

    private GunServerLogic() {}
}
