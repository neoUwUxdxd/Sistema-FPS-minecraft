package com.fpsrealista.client;

import com.fpsrealista.ModRegistry;
import com.fpsrealista.client.anim.AnimationClip;
import com.fpsrealista.client.anim.AnimationSet;
import com.fpsrealista.client.fx.ClientFx;
import com.fpsrealista.client.model.GunAssets;
import com.fpsrealista.client.model.GunModel;
import com.fpsrealista.client.model.Pose;
import com.fpsrealista.gun.FireMode;
import com.fpsrealista.gun.GunItem;
import com.fpsrealista.gun.GunType;
import com.fpsrealista.network.FireModePayload;
import com.fpsrealista.network.ReloadPayload;
import com.fpsrealista.network.ShootPayload;
import java.util.Random;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.network.PacketDistributor;

/**
 * Estado del arma en el cliente: entrada, cadencia, apuntado, recargas, ciclado,
 * retroceso fisico (muelles), balanceo y reproduccion de animaciones.
 */
public final class GunClient {
    public static final GunClient I = new GunClient();

    public enum Action { NONE, DRAW, RELOAD, SHELL_START, SHELL_LOOP, SHELL_END, CYCLE, INSPECT }

    private final Random rnd = new Random();

    // ---------------------------------------------------------------- arma equipada
    public GunType type;
    public GunModel model;
    public AnimationSet anims = AnimationSet.EMPTY;
    private int slot = -1;
    private Item lastItem;

    // ---------------------------------------------------------------- animacion
    private AnimationClip baseClip;
    private double baseStart;
    private float baseSpeed = 1;
    private float baseLastT;
    private AnimationClip fireClip;
    private double fireStart;
    private float fireLastT;

    public Action action = Action.NONE;
    private double actionEnd;
    private int shellsToLoad;
    private boolean shellFromEmpty;
    private boolean pendingCycle;
    private double cycleAt;

    // ---------------------------------------------------------------- apuntado / movimiento
    public float ads;
    public float sprint;
    private boolean adsHeld;

    // ---------------------------------------------------------------- disparo
    private boolean triggerWasDown;
    private boolean semiQueued;
    private double semiQueuedAt;
    private double nextShot;
    private int burstLeft;
    private boolean dryClicked;
    public float bloom;
    public double lastShotTime = -10;

    // ---------------------------------------------------------------- retroceso y balanceo
    public final Spring kickBack = new Spring(260f, 0.55f);
    public final Spring kickPitch = new Spring(220f, 0.45f);
    public final Spring kickYaw = new Spring(200f, 0.5f);
    public final Spring kickRoll = new Spring(180f, 0.4f);
    public final Spring camRoll = new Spring(160f, 0.45f);
    public final Spring swayYaw = new Spring(90f, 0.75f);
    public final Spring swayPitch = new Spring(90f, 0.75f);
    public final Spring fallOffset = new Spring(70f, 0.6f);
    public final Spring selector = new Spring(300f, 0.7f);
    private float camPitchPending, camYawPending, recoveryDebt;
    private float lastYaw, lastPitch;
    private boolean haveLast;

    // ---------------------------------------------------------------- efectos
    public double flashTime = -10;
    public int flashVariant;
    public float flashRot;
    public double hitTime = -10;
    public boolean hitHead, hitKill;
    private double lastFrame = -1;

    private GunClient() {}

    public static double now() {
        return System.nanoTime() / 1.0e9;
    }

    public boolean active() {
        return type != null && model != null;
    }

    public boolean isScoped() {
        return active() && type.scope && ads > 0.92f;
    }

    // ================================================================ ciclo por fotograma
    public void frame() {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer player = mc.player;
        double now = now();
        float dt = lastFrame < 0 ? 0 : (float) Mth.clamp(now - lastFrame, 0, 0.1);
        lastFrame = now;
        if (player == null || mc.level == null) {
            unequip();
            return;
        }
        if (mc.isPaused()) {
            dt = 0;
        }
        ItemStack stack = player.getMainHandItem();
        GunType t = GunItem.typeOf(stack);
        int sel = player.getInventory().selected;
        if (t != type || sel != slot || stack.getItem() != lastItem) {
            equip(t, sel, stack.getItem());
        } else if (t != null && model == null) {
            // los recursos aun no estaban cargados al equipar
            model = GunAssets.model(t.id());
            anims = GunAssets.anims(t.id());
        }
        if (!active()) {
            return;
        }

        processEvents(now);
        updateAction(now, stack, player);

        boolean ui = mc.screen == null && mc.mouseHandler.isMouseGrabbed();
        boolean attack = ui && mc.options.keyAttack.isDown();
        adsHeld = ui && mc.options.keyUse.isDown();

        // ---------------- apuntado
        boolean canAds = action == Action.NONE || action == Action.CYCLE && !"pump".equals(type.cycleClip);
        boolean wantAds = adsHeld && canAds && !player.isSpectator();
        if (wantAds && player.isSprinting()) {
            player.setSprinting(false);
        }
        if (wantAds && action == Action.INSPECT) {
            stopBase();
        }
        float adsStep = dt / Math.max(0.05f, type.adsTime);
        ads = Mth.clamp(ads + (wantAds ? adsStep : -adsStep * 1.3f), 0f, 1f);

        // ---------------- carrera
        boolean running = player.isSprinting() && ads < 0.1f && action != Action.RELOAD;
        sprint = Mth.clamp(sprint + (running ? dt * 5f : -dt * 6f), 0f, 1f);

        // ---------------- disparo
        handleFire(now, attack, stack, player);
        if (pendingCycle && now >= cycleAt && (action == Action.NONE || action == Action.INSPECT)) {
            pendingCycle = false;
            play(type.cycleClip, type.cycleTime, Action.CYCLE);
        }

        // ---------------- retroceso de camara
        float ap = 1f - (float) Math.exp(-dt * 30f);
        float dp = camPitchPending * ap;
        float dy = camYawPending * ap;
        camPitchPending -= dp;
        camYawPending -= dy;
        float rec = 0;
        if (now - lastShotTime > 0.14) {
            rec = recoveryDebt * (1f - (float) Math.exp(-dt * 6.5f));
            recoveryDebt -= rec;
        }
        if (dp != 0 || dy != 0 || rec != 0) {
            player.turn(dy / 0.15, (dp + rec) / 0.15);
        }

        // ---------------- balanceo por movimiento de raton
        float yaw = player.getYRot();
        float pitch = player.getXRot();
        if (!haveLast) {
            lastYaw = yaw;
            lastPitch = pitch;
            haveLast = true;
        }
        if (dt > 0) {
            float dYaw = Mth.wrapDegrees(yaw - lastYaw) / dt;
            float dPitch = (pitch - lastPitch) / dt;
            float k = 1f - 0.75f * ads;
            swayYaw.update(dt, Mth.clamp(-dYaw * 0.012f, -6f, 6f) * k);
            swayPitch.update(dt, Mth.clamp(-dPitch * 0.012f, -5f, 5f) * k);
            float vy = (float) player.getDeltaMovement().y;
            fallOffset.update(dt, player.onGround() ? 0f : Mth.clamp(-vy * 1.4f, -0.6f, 0.6f));
        }
        lastYaw = yaw;
        lastPitch = pitch;

        kickBack.update(dt, 0);
        kickPitch.update(dt, 0);
        kickYaw.update(dt, 0);
        kickRoll.update(dt, 0);
        camRoll.update(dt, 0);
        selector.update(dt, GunItem.getFireModeIndex(stack) * -40f);
        if (now - lastShotTime > 0.12) {
            bloom = Math.max(0, bloom - dt * Math.max(1.5f, type.maxBloom * 2.2f));
        }
    }

    private void equip(GunType t, int sel, Item item) {
        if (action == Action.SHELL_START || action == Action.SHELL_LOOP) {
            PacketDistributor.sendToServer(new ReloadPayload(slot, false));
        }
        type = t;
        slot = sel;
        lastItem = item;
        baseClip = null;
        fireClip = null;
        action = Action.NONE;
        pendingCycle = false;
        ads = 0;
        bloom = 0;
        burstLeft = 0;
        recoveryDebt = 0;
        camPitchPending = camYawPending = 0;
        kickBack.reset();
        kickPitch.reset();
        kickYaw.reset();
        kickRoll.reset();
        if (t == null) {
            model = null;
            anims = AnimationSet.EMPTY;
            return;
        }
        model = GunAssets.model(t.id());
        anims = GunAssets.anims(t.id());
        play("draw", t.drawTime, Action.DRAW);
        nextShot = now() + t.drawTime * 0.9;
    }

    private void unequip() {
        type = null;
        model = null;
        slot = -1;
        lastItem = null;
        haveLast = false;
    }

    // ================================================================ animacion
    private void play(String clip, float duration, Action a) {
        AnimationClip c = anims.get(clip);
        double now = now();
        baseClip = c;
        baseStart = now;
        baseLastT = -1e-4f;
        baseSpeed = c != null && duration > 0 ? c.length / duration : 1f;
        action = a;
        actionEnd = now + (c != null ? c.length / baseSpeed : duration);
    }

    private void stopBase() {
        baseClip = null;
        action = Action.NONE;
    }

    private void processEvents(double now) {
        if (baseClip != null) {
            float t = (float) ((now - baseStart) * baseSpeed);
            fireEvents(baseClip, baseLastT, t);
            baseLastT = t;
        }
        if (fireClip != null) {
            float t = (float) (now - fireStart);
            fireEvents(fireClip, fireLastT, t);
            fireLastT = t;
            if (t > fireClip.length) {
                fireClip = null;
            }
        }
    }

    private void fireEvents(AnimationClip c, float from, float to) {
        for (AnimationClip.Event e : c.events) {
            if (e.time() > from && e.time() <= to) {
                event(e.name());
            }
        }
    }

    private void event(String name) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) {
            return;
        }
        if (name.equals("!eject")) {
            ClientFx.ejectCasing(type);
            return;
        }
        if (name.startsWith("!")) {
            return;
        }
        String s = name.contains(":") ? name.substring(name.indexOf(':') + 1) : name;
        if (ModRegistry.hasSound(s)) {
            playLocal(ModRegistry.sound(s), 0.8f, 0.95f + rnd.nextFloat() * 0.1f);
        }
    }

    public static void playLocal(SoundEvent sound, float volume, float pitch) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player != null && mc.level != null) {
            mc.level.playLocalSound(mc.player.getX(), mc.player.getEyeY(), mc.player.getZ(), sound, SoundSource.PLAYERS,
                    volume, pitch, false);
        }
    }

    /** Pose actual (clip base + disparo + pose de arma vacia + selector). */
    public Pose currentPose(ItemStack stack) {
        Pose pose = new Pose();
        double now = now();
        if (baseClip != null) {
            float t = (float) Math.min((now - baseStart) * baseSpeed, baseClip.length);
            baseClip.apply(pose, t, 1f);
        }
        if (fireClip != null) {
            float t = (float) Math.min(now - fireStart, fireClip.length);
            fireClip.apply(pose, t, 1f);
        }
        if (model != null && GunItem.getAmmo(stack) == 0 && action != Action.RELOAD) {
            for (var e : model.emptyPose.entrySet()) {
                pose.add(e.getKey(), e.getValue(), new float[3], 1f);
            }
        }
        pose.add("selector", new float[3], new float[] {selector.x, 0, 0}, 1f);
        return pose;
    }

    // ================================================================ maquina de estados
    private void updateAction(double now, ItemStack stack, LocalPlayer player) {
        if (action == Action.NONE || now < actionEnd) {
            return;
        }
        switch (action) {
            case SHELL_START -> {
                if (shellsToLoad > 0) {
                    play("reload_loop", type.shellTime, Action.SHELL_LOOP);
                } else {
                    play("reload_end", type.shellEnd, Action.SHELL_END);
                }
            }
            case SHELL_LOOP -> {
                shellsToLoad--;
                if (shellsToLoad > 0 && (player.getAbilities().instabuild || reserve(player) > 0)) {
                    play("reload_loop", type.shellTime, Action.SHELL_LOOP);
                } else {
                    play("reload_end", type.shellEnd, Action.SHELL_END);
                }
            }
            case SHELL_END -> {
                baseClip = null;
                action = Action.NONE;
                if (shellFromEmpty && type.cycleClip != null) {
                    play(type.cycleClip, type.cycleTime, Action.CYCLE);
                    shellFromEmpty = false;
                }
            }
            default -> {
                baseClip = null;
                action = Action.NONE;
            }
        }
    }

    public static int reserve(LocalPlayer p) {
        GunType t = GunItem.typeOf(p.getMainHandItem());
        if (t == null) {
            return 0;
        }
        Item ammo = t.ammo.get();
        int n = 0;
        for (ItemStack s : p.getInventory().items) {
            if (s.is(ammo)) {
                n += s.getCount();
            }
        }
        for (ItemStack s : p.getInventory().offhand) {
            if (s.is(ammo)) {
                n += s.getCount();
            }
        }
        return n;
    }

    // ================================================================ disparo
    private void handleFire(double now, boolean down, ItemStack stack, LocalPlayer player) {
        FireMode mode = GunItem.getFireMode(stack);
        boolean pressed = down && !triggerWasDown;
        triggerWasDown = down;
        if (pressed) {
            dryClicked = false;
            semiQueued = true;
            semiQueuedAt = now;
            if (mode == FireMode.BURST && burstLeft == 0) {
                burstLeft = type.burstCount;
            }
            if (action == Action.INSPECT) {
                stopBase();
            }
            if (action == Action.SHELL_START || action == Action.SHELL_LOOP) {
                PacketDistributor.sendToServer(new ReloadPayload(slot, false));
                play("reload_end", type.shellEnd * 0.8f, Action.SHELL_END);
                shellFromEmpty = false;
                return;
            }
        }
        if (semiQueued && now - semiQueuedAt > 0.3) {
            semiQueued = false;
        }
        boolean want = switch (mode) {
            case AUTO -> down;
            case SEMI -> semiQueued;
            case BURST -> burstLeft > 0;
        };
        if (!want) {
            return;
        }
        if (player.isSprinting()) {
            player.setSprinting(false);
        }
        if (sprint > 0.35f || action != Action.NONE || pendingCycle || player.isSpectator()) {
            return;
        }
        float interval = type.shotInterval();
        for (int guard = 0; guard < 4 && now >= nextShot; guard++) {
            int ammo = GunItem.getAmmo(stack);
            if (ammo <= 0) {
                if (!dryClicked) {
                    dryClicked = true;
                    playLocal(ModRegistry.sound("dry_fire"), 0.7f, 1f);
                    if (player.getAbilities().instabuild || reserve(player) > 0) {
                        startReload(stack, player);
                    }
                }
                semiQueued = false;
                burstLeft = 0;
                return;
            }
            shoot(now, stack, player, ammo);
            nextShot = (now - nextShot < interval ? nextShot : now) + interval;
            semiQueued = false;
            if (mode == FireMode.BURST) {
                burstLeft--;
            }
            if (type.cycleClip != null) {
                pendingCycle = true;
                cycleAt = now + 0.14;
                break;
            }
            if (mode != FireMode.AUTO && (mode != FireMode.BURST || burstLeft <= 0)) {
                break;
            }
        }
    }

    public float currentSpread(LocalPlayer p) {
        float base = Mth.lerp(ads, type.hipSpread, type.adsSpread);
        double hv = p.getDeltaMovement().horizontalDistance();
        float move = (float) Mth.clamp(hv / 0.22, 0, 1.5) * type.moveSpread * (1f - 0.6f * ads);
        float air = p.onGround() ? 0f : 2.5f;
        float crouch = p.isCrouching() ? 0.75f : 1f;
        return (base + move + air + bloom) * crouch;
    }

    private void shoot(double now, ItemStack stack, LocalPlayer player, int ammo) {
        int seed = rnd.nextInt();
        float spread = currentSpread(player);
        float yaw = player.getYRot();
        float pitch = player.getXRot();
        PacketDistributor.sendToServer(new ShootPayload(slot, seed, yaw, pitch, spread, ads > 0.5f));
        if (!player.getAbilities().instabuild) {
            GunItem.setAmmo(stack, ammo - 1);
        }
        playLocal(ModRegistry.sound(type.shootSound), 1.0f, 0.96f + rnd.nextFloat() * 0.08f);

        // retroceso: patron vertical con deriva horizontal aleatoria (ligero sesgo a la derecha)
        float adsF = Mth.lerp(ads, 1f, type.recoilAdsFactor);
        float crouchF = player.isCrouching() ? 0.8f : 1f;
        float v = type.recoilVertical * adsF * crouchF * (0.85f + rnd.nextFloat() * 0.3f);
        float h = type.recoilHorizontal * adsF * ((rnd.nextFloat() * 2f - 1f) + 0.25f);
        camPitchPending -= v;
        camYawPending += h;
        recoveryDebt += v * 0.6f;
        float k = type.visualKick * Mth.lerp(ads, 1f, 0.55f);
        kickBack.impulse(1.1f * k);
        kickPitch.impulse(70f * k * (0.8f + rnd.nextFloat() * 0.4f));
        kickYaw.impulse((rnd.nextFloat() * 2f - 1f) * 25f * k);
        kickRoll.impulse((rnd.nextFloat() * 2f - 1f) * 45f * k);
        camRoll.impulse((rnd.nextFloat() * 2f - 1f) * 10f * type.visualKick);
        bloom = Math.min(type.maxBloom, bloom + type.bloomPerShot);

        flashTime = now;
        flashVariant = rnd.nextInt(4);
        flashRot = rnd.nextFloat() * 360f;
        lastShotTime = now;

        AnimationClip fc = anims.get("fire");
        if (fc != null) {
            fireClip = fc;
            fireStart = now;
            fireLastT = -1e-4f;
        }
        ClientFx.localShot(player, type, seed, yaw, pitch, spread);
    }

    // ================================================================ acciones de teclado
    public void startReload(ItemStack stack, LocalPlayer player) {
        if (!active() || action == Action.RELOAD || action == Action.DRAW || action == Action.SHELL_START
                || action == Action.SHELL_LOOP || action == Action.SHELL_END || pendingCycle) {
            return;
        }
        int ammo = GunItem.getAmmo(stack);
        int cap = type.capacity(ammo > 0);
        boolean creative = player.getAbilities().instabuild;
        int reserve = creative ? 999 : reserve(player);
        if (ammo >= cap || reserve <= 0) {
            return;
        }
        PacketDistributor.sendToServer(new ReloadPayload(slot, true));
        burstLeft = 0;
        if (type.shellReload) {
            shellsToLoad = Math.min(cap - ammo, reserve);
            shellFromEmpty = ammo == 0;
            play("reload_start", type.shellStart, Action.SHELL_START);
        } else {
            boolean empty = ammo == 0;
            play(empty ? "reload_empty" : "reload", empty ? type.reloadEmptyTime : type.reloadTime, Action.RELOAD);
        }
    }

    public void cycleFireMode(ItemStack stack) {
        if (!active() || type.fireModes.size() < 2) {
            return;
        }
        int idx = Math.floorMod(GunItem.getFireModeIndex(stack) + 1, type.fireModes.size());
        GunItem.setFireModeIndex(stack, idx);
        PacketDistributor.sendToServer(new FireModePayload(slot, idx));
        playLocal(ModRegistry.sound("fire_select"), 0.6f, 1f);
        burstLeft = 0;
    }

    public void inspect() {
        if (active() && action == Action.NONE && ads < 0.1f && !pendingCycle) {
            AnimationClip c = anims.get("inspect");
            if (c != null) {
                play("inspect", c.length, Action.INSPECT);
            }
        }
    }

    public void onHitMarker(boolean head, boolean kill) {
        hitTime = now();
        hitHead = head;
        hitKill = kill;
        playLocal(ModRegistry.sound(head ? "headshot" : "hitmarker"), head ? 0.8f : 0.5f, kill ? 0.8f : 1f);
    }

    public boolean adsHeld() {
        return adsHeld;
    }
}
