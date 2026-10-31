package com.fpsrealista.client;

import com.fpsrealista.FpsRealista;
import com.fpsrealista.ModRegistry;
import com.fpsrealista.client.fx.ClientFx;
import com.fpsrealista.client.hud.GunHud;
import com.fpsrealista.client.model.GunAssets;
import com.fpsrealista.client.render.FirstPersonRenderer;
import com.fpsrealista.client.render.GunItemRenderer;
import com.fpsrealista.gun.GunItem;
import com.fpsrealista.gun.GunType;
import com.fpsrealista.network.HitMarkerPayload;
import com.fpsrealista.network.Network;
import com.fpsrealista.network.ShotFxPayload;
import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.CalculatePlayerTurnEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.InputEvent;
import net.neoforged.neoforge.client.event.MovementInputUpdateEvent;
import net.neoforged.neoforge.client.event.RegisterClientReloadListenersEvent;
import net.neoforged.neoforge.client.event.RegisterGuiLayersEvent;
import net.neoforged.neoforge.client.event.RegisterKeyMappingsEvent;
import net.neoforged.neoforge.client.event.RenderFrameEvent;
import net.neoforged.neoforge.client.event.RenderGuiLayerEvent;
import net.neoforged.neoforge.client.event.RenderHandEvent;
import net.neoforged.neoforge.client.event.ViewportEvent;
import net.neoforged.neoforge.client.extensions.common.IClientItemExtensions;
import net.neoforged.neoforge.client.extensions.common.RegisterClientExtensionsEvent;
import net.neoforged.neoforge.common.NeoForge;
import org.lwjgl.glfw.GLFW;

/** Punto de entrada del cliente: registra render, entrada, HUD, efectos y camara. */
@Mod(value = FpsRealista.MODID, dist = Dist.CLIENT)
public final class FpsRealistaClient {
    private static final String CATEGORY = "key.categories.fpsrealista";
    public static final KeyMapping RELOAD = new KeyMapping("key.fpsrealista.reload", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_R, CATEGORY);
    public static final KeyMapping FIRE_MODE = new KeyMapping("key.fpsrealista.fire_mode", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_V, CATEGORY);
    public static final KeyMapping INSPECT = new KeyMapping("key.fpsrealista.inspect", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_H, CATEGORY);

    public FpsRealistaClient(IEventBus modBus, ModContainer container) {
        modBus.addListener(RegisterKeyMappingsEvent.class, e -> {
            e.register(RELOAD);
            e.register(FIRE_MODE);
            e.register(INSPECT);
        });
        modBus.addListener(RegisterClientReloadListenersEvent.class, e -> e.registerReloadListener(GunAssets.INSTANCE));
        modBus.addListener(RegisterGuiLayersEvent.class, e -> e.registerAboveAll(GunHud.ID, GunHud::render));
        modBus.addListener(ClientFx::registerProviders);
        modBus.addListener(RegisterClientExtensionsEvent.class, FpsRealistaClient::registerExtensions);

        Network.client = new Network.ClientHandlers() {
            @Override
            public void onShotFx(ShotFxPayload p) {
                ClientFx.remoteShot(p);
            }

            @Override
            public void onHitMarker(HitMarkerPayload p) {
                GunClient.I.onHitMarker(p.headshot(), p.kill());
            }
        };

        IEventBus bus = NeoForge.EVENT_BUS;
        bus.addListener(RenderFrameEvent.Pre.class, e -> GunClient.I.frame());
        bus.addListener(ClientTickEvent.Post.class, e -> onClientTick());
        bus.addListener(RenderHandEvent.class, FirstPersonRenderer::onRenderHand);
        bus.addListener(RenderGuiLayerEvent.Pre.class, GunHud::onLayerPre);
        bus.addListener(InputEvent.InteractionKeyMappingTriggered.class, FpsRealistaClient::onInteraction);
        bus.addListener(ViewportEvent.ComputeFov.class, FpsRealistaClient::onFov);
        bus.addListener(ViewportEvent.ComputeCameraAngles.class, FpsRealistaClient::onCamera);
        bus.addListener(MovementInputUpdateEvent.class, FpsRealistaClient::onMovement);
        bus.addListener(CalculatePlayerTurnEvent.class, FpsRealistaClient::onTurn);
    }

    private static void registerExtensions(RegisterClientExtensionsEvent e) {
        IClientItemExtensions ext = new IClientItemExtensions() {
            @Override
            public BlockEntityWithoutLevelRenderer getCustomRenderer() {
                return GunItemRenderer.get();
            }

            @Override
            public HumanoidModel.ArmPose getArmPose(LivingEntity entity, InteractionHand hand, ItemStack stack) {
                return hand == InteractionHand.MAIN_HAND ? HumanoidModel.ArmPose.CROSSBOW_HOLD : HumanoidModel.ArmPose.EMPTY;
            }
        };
        Item[] items = ModRegistry.GUNS.values().stream().map(h -> (Item) h.get()).toArray(Item[]::new);
        e.registerItem(ext, items);
    }

    private static void onClientTick() {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer p = mc.player;
        if (p == null) {
            return;
        }
        GunClient g = GunClient.I;
        while (RELOAD.consumeClick()) {
            if (g.active()) {
                g.startReload(p.getMainHandItem(), p);
            }
        }
        while (FIRE_MODE.consumeClick()) {
            g.cycleFireMode(p.getMainHandItem());
        }
        while (INSPECT.consumeClick()) {
            g.inspect();
        }
        if (g.active() && g.ads > 0.3f && p.isSprinting()) {
            p.setSprinting(false);
        }
    }

    private static void onInteraction(InputEvent.InteractionKeyMappingTriggered e) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || GunItem.typeOf(mc.player.getMainHandItem()) == null) {
            return;
        }
        if (e.isAttack() || e.isUseItem()) {
            e.setCanceled(true);
            e.setSwingHand(false);
        }
    }

    private static void onFov(ViewportEvent.ComputeFov e) {
        GunClient g = GunClient.I;
        if (!g.active()) {
            return;
        }
        float a = g.ads * g.ads * (3 - 2 * g.ads);
        if (e.usedConfiguredFov()) {
            float target = g.type.adsFov;
            e.setFOV(e.getFOV() * Mth.lerp(a, 1f, target));
        } else {
            // FOV del modelo en mano: ligero acercamiento al apuntar
            e.setFOV(e.getFOV() * Mth.lerp(a, 1f, g.type.scope ? 0.8f : 0.9f));
        }
    }

    private static void onCamera(ViewportEvent.ComputeCameraAngles e) {
        GunClient g = GunClient.I;
        if (!g.active()) {
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer p = mc.player;
        float rx = 0, ry = 0, rz = g.camRoll.x;
        if (p != null) {
            var pose = g.currentPose(p.getMainHandItem()).get("camera");
            if (pose != null) {
                rx += pose.rot[0];
                ry += pose.rot[1];
                rz += pose.rot[2];
            }
        }
        e.setPitch(e.getPitch() + rx);
        e.setYaw(e.getYaw() + ry);
        e.setRoll(e.getRoll() + rz);
    }

    private static void onMovement(MovementInputUpdateEvent e) {
        GunClient g = GunClient.I;
        if (!g.active()) {
            return;
        }
        GunType t = g.type;
        float f = Mth.lerp(g.ads, 1f, t.adsMoveFactor);
        e.getInput().forwardImpulse *= f;
        e.getInput().leftImpulse *= f;
    }

    private static void onTurn(CalculatePlayerTurnEvent e) {
        GunClient g = GunClient.I;
        if (!g.active() || g.ads <= 0.01f) {
            return;
        }
        // sensibilidad proporcional al zoom: Minecraft usa (0.6 s + 0.2)^3
        float a = g.ads * g.ads * (3 - 2 * g.ads);
        float zoom = Mth.lerp(a, 1f, g.type.adsFov);
        double s = e.getMouseSensitivity();
        double base = s * 0.6 + 0.2;
        double scaled = base * Math.cbrt(Math.max(0.05, zoom));
        e.setMouseSensitivity(Math.max(0, (scaled - 0.2) / 0.6));
    }
}
