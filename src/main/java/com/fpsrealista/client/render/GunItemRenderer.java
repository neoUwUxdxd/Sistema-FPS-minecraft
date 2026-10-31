package com.fpsrealista.client.render;

import com.fpsrealista.client.model.GunAssets;
import com.fpsrealista.client.model.GunModel;
import com.fpsrealista.gun.GunItem;
import com.fpsrealista.gun.GunType;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import org.joml.Vector3f;

/** Render del arma en inventario, suelo, marcos y en la mano en tercera persona. */
public final class GunItemRenderer extends BlockEntityWithoutLevelRenderer {
    public static GunItemRenderer INSTANCE;

    public GunItemRenderer() {
        super(Minecraft.getInstance().getBlockEntityRenderDispatcher(), Minecraft.getInstance().getEntityModels());
    }

    public static GunItemRenderer get() {
        if (INSTANCE == null) {
            INSTANCE = new GunItemRenderer();
        }
        return INSTANCE;
    }

    @Override
    public void renderByItem(ItemStack stack, ItemDisplayContext ctx, PoseStack ps, MultiBufferSource buffers, int light, int overlay) {
        GunType type = GunItem.typeOf(stack);
        if (type == null) {
            return;
        }
        GunModel m = GunAssets.model(type.id());
        if (m == null) {
            return;
        }
        Vector3f mn = m.boundsMin, mx = m.boundsMax;
        Vector3f center = new Vector3f(mn).add(mx).mul(0.5f);
        float length = Math.max(1f, Math.max(mx.z - mn.z, Math.max(mx.y - mn.y, mx.x - mn.x)));
        ps.pushPose();
        ps.translate(0.5f, 0.5f, 0.5f);
        switch (ctx) {
            case GUI -> {
                ps.mulPose(Axis.YP.rotationDegrees(-90f));
                ps.mulPose(Axis.XP.rotationDegrees(-8f));
                float s = 0.98f / length;
                ps.scale(s, s, s);
                ps.translate(-center.x, -center.y, -center.z);
            }
            case FIXED -> {
                ps.mulPose(Axis.YP.rotationDegrees(90f));
                float s = 0.9f / length;
                ps.scale(s, s, s);
                ps.translate(-center.x, -center.y, -center.z);
            }
            case GROUND -> {
                float s = 0.75f / length * Math.min(1.6f, length / 40f);
                ps.scale(s, s, s);
                ps.translate(-center.x, -center.y, -center.z);
            }
            case HEAD -> {
                ps.mulPose(Axis.YP.rotationDegrees(-90f));
                float s = 0.8f / length;
                ps.scale(s, s, s);
                ps.translate(-center.x, -center.y, -center.z);
            }
            default -> {
                // tercera persona (y primera persona si otro mod desactiva nuestro render)
                float s = 0.01f * 0.72f;
                ps.translate(0, 0.02f, 0.06f);
                ps.scale(s, s, s);
                Vector3f rh = m.hasLocator("rh") ? m.locator("rh", m.restMatrices()) : new Vector3f();
                ps.translate(-rh.x, -rh.y, -rh.z);
            }
        }
        GunMeshRenderer.render(m, null, ps, buffers, light, overlay);
        ps.popPose();
    }
}
