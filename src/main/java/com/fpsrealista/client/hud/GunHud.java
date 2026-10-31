package com.fpsrealista.client.hud;

import com.fpsrealista.FpsRealista;
import com.fpsrealista.client.GunClient;
import com.fpsrealista.gun.GunItem;
import com.fpsrealista.gun.GunType;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.client.event.RenderGuiLayerEvent;
import net.neoforged.neoforge.client.gui.VanillaGuiLayers;

/** HUD del arma: mira dinamica, marcador de impactos, municion, modo de fuego y mira telescopica. */
public final class GunHud {
    public static final ResourceLocation ID = FpsRealista.id("gun_hud");
    private static final ResourceLocation SCOPE = FpsRealista.id("textures/gui/scope_overlay.png");
    private static final ResourceLocation HIT = FpsRealista.id("textures/gui/hitmarker.png");

    private GunHud() {}

    public static void onLayerPre(RenderGuiLayerEvent.Pre e) {
        if (!GunClient.I.active()) {
            return;
        }
        if (e.getName().equals(VanillaGuiLayers.CROSSHAIR)) {
            e.setCanceled(true);
        }
    }

    public static void render(GuiGraphics g, DeltaTracker delta) {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer p = mc.player;
        GunClient gc = GunClient.I;
        if (p == null || !gc.active() || mc.options.hideGui) {
            return;
        }
        int w = g.guiWidth();
        int h = g.guiHeight();
        if (gc.isScoped()) {
            drawScope(g, w, h, gc);
        } else if (mc.options.getCameraType().isFirstPerson()) {
            drawCrosshair(g, w, h, gc, p);
        }
        drawHitMarker(g, w, h, gc);
        drawAmmo(g, w, h, gc, p, mc.font);
    }

    private static void drawScope(GuiGraphics g, int w, int h, GunClient gc) {
        RenderSystem.enableBlend();
        int size = h;
        // balanceo de la imagen de la mira con la respiracion/retroceso
        int ox = (int) (gc.swayYaw.x * 3 + gc.kickYaw.x * 2);
        int oy = (int) (-gc.swayPitch.x * 3 - gc.kickPitch.x * 2);
        int x0 = (w - size) / 2 + ox;
        int y0 = oy;
        g.blit(SCOPE, x0, y0, 0, 0, size, size, size, size);
        g.fill(0, 0, Math.max(0, x0), h, 0xFF000000);
        g.fill(Math.min(w, x0 + size), 0, w, h, 0xFF000000);
        if (y0 > 0) {
            g.fill(0, 0, w, y0, 0xFF000000);
        }
        if (y0 + size < h) {
            g.fill(0, y0 + size, w, h, 0xFF000000);
        }
        RenderSystem.disableBlend();
    }

    private static void drawCrosshair(GuiGraphics g, int w, int h, GunClient gc, LocalPlayer p) {
        float vis = 1f - Math.max(Mth.clamp(gc.ads * 2.5f, 0, 1), gc.sprint);
        if (gc.action == GunClient.Action.RELOAD || gc.action == GunClient.Action.INSPECT) {
            vis *= 0.35f;
        }
        if (vis <= 0.02f) {
            return;
        }
        float spread = gc.currentSpread(p);
        // conversion aproximada grados -> pixeles de GUI
        Minecraft mc = Minecraft.getInstance();
        double fov = mc.options.fov().get();
        float pxPerDeg = h / (float) fov;
        int gap = (int) Math.max(3, spread * pxPerDeg);
        int a = (int) (vis * 220) << 24;
        int col = a | 0xFFFFFF;
        int shadow = (int) (vis * 120) << 24;
        int cx = w / 2, cy = h / 2, len = 5;
        int[][] seg = {{cx - gap - len, cy, cx - gap, cy + 1}, {cx + gap + 1, cy, cx + gap + len + 1, cy + 1},
                {cx, cy - gap - len, cx + 1, cy - gap}, {cx, cy + gap + 1, cx + 1, cy + gap + len + 1}};
        for (int[] s : seg) {
            g.fill(s[0] - 1, s[1] - 1, s[2] + 1, s[3] + 1, shadow);
            g.fill(s[0], s[1], s[2], s[3], col);
        }
        g.fill(cx, cy, cx + 1, cy + 1, col);
    }

    private static void drawHitMarker(GuiGraphics g, int w, int h, GunClient gc) {
        double age = GunClient.now() - gc.hitTime;
        if (age > 0.35) {
            return;
        }
        float a = (float) (1 - age / 0.35);
        int s = (int) (16 + (gc.hitHead ? 6 : 0) + age * 10);
        RenderSystem.enableBlend();
        if (gc.hitKill) {
            RenderSystem.setShaderColor(1f, 0.2f, 0.15f, a);
        } else if (gc.hitHead) {
            RenderSystem.setShaderColor(1f, 0.85f, 0.2f, a);
        } else {
            RenderSystem.setShaderColor(1f, 1f, 1f, a);
        }
        g.blit(HIT, w / 2 - s / 2, h / 2 - s / 2, 0, 0, s, s, s, s);
        RenderSystem.setShaderColor(1f, 1f, 1f, 1f);
        RenderSystem.disableBlend();
    }

    private static void drawAmmo(GuiGraphics g, int w, int h, GunClient gc, LocalPlayer p, Font font) {
        ItemStack stack = p.getMainHandItem();
        GunType t = GunItem.typeOf(stack);
        if (t == null) {
            return;
        }
        int ammo = GunItem.getAmmo(stack);
        boolean creative = p.getAbilities().instabuild;
        int reserve = GunClient.reserve(p);
        int x1 = w - 8;
        int y1 = h - 8;
        int bw = 118, bh = 38;
        int x0 = x1 - bw, y0 = y1 - bh;
        g.fill(x0, y0, x1, y1, 0x66000000);
        g.fill(x0, y1 - 2, x1, y1, 0xAAFFB040);
        String a = String.valueOf(ammo);
        int ammoCol = ammo == 0 ? 0xFFFF4040 : ammo <= Math.max(1, t.magSize / 4) ? 0xFFFFB040 : 0xFFFFFFFF;
        g.pose().pushPose();
        g.pose().translate(x0 + 8, y0 + 7, 0);
        g.pose().scale(2f, 2f, 1f);
        g.drawString(font, a, 0, 0, ammoCol, true);
        g.pose().popPose();
        int ax = x0 + 8 + font.width(a) * 2 + 4;
        g.drawString(font, "/ " + (creative ? "∞" : String.valueOf(reserve)), ax, y0 + 15, 0xFFBBBBBB, true);
        Component name = stack.getHoverName();
        g.drawString(font, name, x1 - font.width(name) - 4, y0 - 11, 0xFFE0E0E0, true);
        Component mode = Component.translatable(GunItem.getFireMode(stack).translationKey());
        g.drawString(font, mode, x1 - font.width(mode) - 6, y0 + 6, 0xFFFFB040, true);
        // barra de cartuchos
        int n = Math.min(t.magSize, 30);
        int cell = Math.max(1, (bw - 16) / n);
        int filled = (int) Math.ceil(ammo * n / (float) t.magSize);
        for (int i = 0; i < n; i++) {
            int cx = x0 + 8 + i * cell;
            g.fill(cx, y1 - 9, cx + Math.max(1, cell - 1), y1 - 5, i < filled ? 0xDDFFFFFF : 0x44FFFFFF);
        }
        if (ammo == 0 && (creative || reserve > 0) && gc.action != GunClient.Action.RELOAD) {
            Component r = Component.translatable("hud.fpsrealista.reload");
            g.drawCenteredString(font, r, w / 2, h / 2 + 18, 0xFFFF5050);
        } else if (ammo == 0 && reserve == 0 && !creative) {
            Component r = Component.translatable("hud.fpsrealista.no_ammo");
            g.drawCenteredString(font, r, w / 2, h / 2 + 18, 0xFFFF5050);
        }
    }
}
