package com.fpsrealista.client.render;

import com.fpsrealista.FpsRealista;
import com.fpsrealista.client.GunClient;
import com.fpsrealista.client.fx.ClientFx;
import com.fpsrealista.client.model.GunModel;
import com.fpsrealista.client.model.Pose;
import com.fpsrealista.gun.GunItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.resources.PlayerSkin;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.PlayerModelPart;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.client.event.RenderHandEvent;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * Render del arma en primera persona: pose de cadera/ADS/carrera, balanceo, retroceso,
 * animacion por fotogramas clave, brazos del jugador con IK sobre los localizadores y fogonazo.
 */
public final class FirstPersonRenderer {
    private static final ResourceLocation[] FLASH = {
            FpsRealista.id("textures/effect/muzzle_flash_0.png"), FpsRealista.id("textures/effect/muzzle_flash_1.png"),
            FpsRealista.id("textures/effect/muzzle_flash_2.png"), FpsRealista.id("textures/effect/muzzle_flash_3.png")};
    private static final ResourceLocation FLASH_SIDE = FpsRealista.id("textures/effect/muzzle_flash_side.png");

    private FirstPersonRenderer() {}

    /** Aplica las mismas operaciones a una PoseStack (opcional) y a una matriz JOML. */
    static final class Xf {
        final PoseStack ps;
        final Matrix4f m = new Matrix4f();

        Xf(PoseStack ps) {
            this.ps = ps;
        }

        void t(float x, float y, float z) {
            if (ps != null) {
                ps.translate(x, y, z);
            }
            m.translate(x, y, z);
        }

        void t(Vector3f v) {
            t(v.x, v.y, v.z);
        }

        void r(float rx, float ry, float rz) {
            Quaternionf q = new Quaternionf().rotationZYX(rz * Mth.DEG_TO_RAD, ry * Mth.DEG_TO_RAD, rx * Mth.DEG_TO_RAD);
            if (ps != null) {
                ps.mulPose(q);
            }
            m.rotate(q);
        }

        void s(float f) {
            if (ps != null) {
                ps.scale(f, f, f);
            }
            m.scale(f);
        }
    }

    static float smooth(float t) {
        t = Mth.clamp(t, 0, 1);
        return t * t * (3 - 2 * t);
    }

    static Vector3f lerp(Vector3f a, Vector3f b, float t) {
        return new Vector3f(a).lerp(b, t);
    }

    public static void onRenderHand(RenderHandEvent e) {
        GunClient g = GunClient.I;
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer p = mc.player;
        if (p == null || !g.active()) {
            ClientFx.viewValid = false;
            return;
        }
        ItemStack stack = p.getMainHandItem();
        if (GunItem.typeOf(stack) == null) {
            return;
        }
        e.setCanceled(true);
        if (e.getHand() == InteractionHand.OFF_HAND || g.isScoped()) {
            if (g.isScoped()) {
                ClientFx.viewValid = false;
            }
            return;
        }
        float pt = e.getPartialTick();
        PoseStack ps = e.getPoseStack();
        MultiBufferSource buf = e.getMultiBufferSource();
        int light = e.getPackedLight();
        double now = GunClient.now();
        boolean flash = now - g.flashTime < 0.05;
        if (flash) {
            light = LightTexture.pack(15, LightTexture.sky(light));
        }
        GunModel m = g.model;
        Pose pose = g.currentPose(stack);
        Matrix4f base = new Matrix4f(ps.last().pose());

        ps.pushPose();
        Xf xf = new Xf(ps);
        applyGunTransform(xf, m, g, pose, p, pt, (float) now);
        Matrix4f[] mats = GunMeshRenderer.render(m, pose, ps, buf, light, OverlayTexture.NO_OVERLAY);

        // localizadores en espacio de vista para efectos
        Matrix4f full = new Matrix4f(base).mul(xf.m);
        Vector3f mz = m.locator("muzzle", mats);
        Vector3f ej = m.locator("eject", mats);
        if (mz != null) {
            full.transformPosition(mz, ClientFx.MUZZLE_VIEW);
        }
        if (ej != null) {
            full.transformPosition(ej, ClientFx.EJECT_VIEW);
        }
        ClientFx.viewValid = true;

        if (flash && mz != null) {
            renderFlash(ps, buf, mz, m.flashSize, g);
        }
        ps.popPose();

        renderArms(ps, buf, light, p, m, g, xf.m, mats, pose);
    }

    static void applyGunTransform(Xf xf, GunModel m, GunClient g, Pose pose, LocalPlayer p, float pt, float time) {
        GunModel.View v = m.view;
        Matrix4f[] rest = m.restMatrices();
        Vector3f aim = m.hasLocator("aim") ? m.locator("aim", rest) : new Vector3f();
        Vector3f piv = m.hasLocator("pivot") ? m.locator("pivot", rest) : new Vector3f();
        float adsE = smooth(g.ads);
        float spE = smooth(g.sprint);

        Vector3f adsPos = new Vector3f(0, 0, -v.eyeRelief).sub(new Vector3f(aim).mul(0.01f));
        Vector3f pos = lerp(v.hipPos, adsPos, adsE);
        Vector3f rot = lerp(v.hipRot, new Vector3f(), adsE);
        pos = lerp(pos, v.sprintPos, spE);
        rot = lerp(rot, v.sprintRot, spE);

        // balanceo al caminar (figura en 8), respiracion, inclinacion lateral
        float wd = Mth.lerp(pt, p.walkDistO, p.walkDist);
        float b = Mth.lerp(pt, p.oBob, p.bob);
        float k = (1f - 0.85f * adsE) * (1f + 1.6f * spE);
        float s = Mth.sin(wd * Mth.PI);
        float c = Math.abs(Mth.cos(wd * Mth.PI));
        float bx = s * b * 0.10f * k;
        float by = -c * b * 0.12f * k;
        float broll = s * b * 14f * k;
        float bpitch = -c * b * 10f * k;
        float br = 1f - 0.7f * adsE;
        bx += Mth.sin(time * 1.1f) * 0.0016f * br;
        by += Mth.sin(time * 2.2f) * 0.0011f * br;
        Vec3 vel = p.getDeltaMovement();
        float yawR = p.getYRot() * Mth.DEG_TO_RAD;
        double lateral = vel.x * -Mth.cos(yawR) + vel.z * -Mth.sin(yawR);
        float strafe = (float) Mth.clamp(lateral * 28.0, -6, 6) * (1f - 0.6f * adsE);
        by += g.fallOffset.x * 0.05f * (1f - 0.5f * adsE);
        float crouchRoll = 0;
        if (p.isCrouching()) {
            by -= 0.01f * (1f - adsE);
            crouchRoll = 4f * (1f - adsE);
        }

        Vector3f procPos = new Vector3f(bx + g.swayYaw.x * 0.0015f, by + g.swayPitch.x * 0.0015f, g.kickBack.x * 0.6f);
        float prx = g.kickPitch.x + g.swayPitch.x + bpitch;
        float pry = g.kickYaw.x + g.swayYaw.x;
        float prz = g.kickRoll.x + broll + strafe + crouchRoll;

        Pose.Channel gc = pose.get("gun");
        xf.t(new Vector3f(pos).add(procPos));
        xf.r(rot.x, rot.y, rot.z);
        xf.s(0.01f);
        xf.t(piv);
        xf.r(prx, pry, prz);
        if (gc != null) {
            xf.t(gc.pos[0], gc.pos[1], gc.pos[2]);
            xf.r(gc.rot[0], gc.rot[1], gc.rot[2]);
        }
        xf.t(-piv.x, -piv.y, -piv.z);
    }

    // ------------------------------------------------------------------ fogonazo
    private static void renderFlash(PoseStack ps, MultiBufferSource buf, Vector3f mz, float size, GunClient g) {
        ps.pushPose();
        ps.translate(mz.x, mz.y, mz.z);
        float r = size * (0.85f + (g.flashVariant % 2) * 0.3f);
        PoseStack.Pose pose = ps.last();
        // estrella frontal
        VertexConsumer vc = buf.getBuffer(RenderType.eyes(FLASH[g.flashVariant & 3]));
        float a = g.flashRot * Mth.DEG_TO_RAD;
        float ca = Mth.cos(a) * r, sa = Mth.sin(a) * r;
        float[][] q = {{-ca + sa, -sa - ca}, {ca + sa, sa - ca}, {ca - sa, sa + ca}, {-ca - sa, -sa + ca}};
        float[][] uv = {{0, 1}, {1, 1}, {1, 0}, {0, 0}};
        for (int side = 0; side < 2; side++) {
            for (int i = 0; i < 4; i++) {
                int j = side == 0 ? i : 3 - i;
                fv(vc, pose, q[j][0], q[j][1], -r * 0.2f, uv[j][0], uv[j][1]);
            }
        }
        // conos laterales
        vc = buf.getBuffer(RenderType.eyes(FLASH_SIDE));
        float len = r * 2.6f, w = r * 0.75f;
        for (int plane = 0; plane < 2; plane++) {
            float[][] pts = new float[4][];
            for (int i = 0; i < 4; i++) {
                float along = (i == 0 || i == 3) ? 0 : -len;
                float across = (i < 2) ? -w : w;
                pts[i] = plane == 0 ? new float[] {across, 0, along} : new float[] {0, across, along};
            }
            float[][] uvs = {{0, 0}, {1, 0}, {1, 1}, {0, 1}};
            for (int side = 0; side < 2; side++) {
                for (int i = 0; i < 4; i++) {
                    int j = side == 0 ? i : 3 - i;
                    fv(vc, pose, pts[j][0], pts[j][1], pts[j][2], uvs[j][0], uvs[j][1]);
                }
            }
        }
        ps.popPose();
    }

    private static void fv(VertexConsumer vc, PoseStack.Pose pose, float x, float y, float z, float u, float v) {
        vc.addVertex(pose, x, y, z).setColor(0xFFFFFFFF).setUv(u, v).setOverlay(OverlayTexture.NO_OVERLAY)
                .setLight(LightTexture.FULL_BRIGHT).setNormal(pose, 0, 0, 1);
    }

    // ------------------------------------------------------------------ brazos
    private static Vector3f handTarget(GunModel m, Matrix4f gun, Matrix4f[] mats, Pose pose, String rest, String ikKey) {
        Vector3f lp = m.locator(rest, mats);
        if (lp == null) {
            return null;
        }
        Vector3f p = gun.transformPosition(new Vector3f(lp));
        Pose.Ik ik = pose.ik.get(ikKey);
        if (ik != null && ik.weight() > 0.001f && m.hasLocator(ik.target())) {
            Vector3f t = gun.transformPosition(m.locator(ik.target(), mats));
            p.lerp(t, ik.weight());
        }
        return p;
    }

    private static void renderArms(PoseStack ps, MultiBufferSource buf, int light, LocalPlayer p, GunModel m, GunClient g,
                                   Matrix4f gun, Matrix4f[] mats, Pose pose) {
        if (p.isInvisible()) {
            return;
        }
        EntityRenderer<? super LocalPlayer> er = Minecraft.getInstance().getEntityRenderDispatcher().getRenderer(p);
        if (!(er instanceof PlayerRenderer pr)) {
            return;
        }
        PlayerModel<AbstractClientPlayer> pm = pr.getModel();
        PlayerSkin skin = p.getSkin();
        boolean slim = skin.model() == PlayerSkin.Model.SLIM;
        float adsE = smooth(g.ads);
        GunModel.View v = m.view;
        for (int side = 0; side < 2; side++) {
            boolean right = side == 0;
            Vector3f hand = handTarget(m, gun, mats, pose, right ? "rh" : "lh", right ? "right_hand" : "left_hand");
            if (hand == null) {
                continue;
            }
            GunModel.Arm arm = right ? v.right : v.left;
            Vector3f anchor = lerp(arm.anchor(), arm.anchorAds(), adsE);
            Vector3f dir = new Vector3f(hand).sub(anchor);
            if (dir.lengthSquared() < 1e-6f) {
                continue;
            }
            dir.normalize();
            Quaternionf q = new Quaternionf().rotationTo(new Vector3f(0, 1, 0), dir);
            if (arm.twist() != 0) {
                q = new Quaternionf().rotationAxis(arm.twist() * Mth.DEG_TO_RAD, dir).mul(q);
            }
            float cx = (right ? -1f : 1f) * (slim ? 0.5f : 1f) / 16f;
            ps.pushPose();
            ps.translate(hand.x, hand.y, hand.z);
            ps.mulPose(q);
            ps.scale(v.armScaleW, v.armScaleL, v.armScaleW);
            ps.translate(-cx, -10f / 16f, 0);
            ModelPart a = right ? pm.rightArm : pm.leftArm;
            ModelPart sl = right ? pm.rightSleeve : pm.leftSleeve;
            resetPart(a);
            resetPart(sl);
            a.visible = true;
            sl.visible = p.isModelPartShown(right ? PlayerModelPart.RIGHT_SLEEVE : PlayerModelPart.LEFT_SLEEVE);
            a.render(ps, buf.getBuffer(RenderType.entitySolid(skin.texture())), light, OverlayTexture.NO_OVERLAY);
            if (sl.visible) {
                sl.render(ps, buf.getBuffer(RenderType.entityTranslucent(skin.texture())), light, OverlayTexture.NO_OVERLAY);
            }
            ps.popPose();
        }
    }

    private static void resetPart(ModelPart part) {
        part.x = 0;
        part.y = 0;
        part.z = 0;
        part.xRot = 0;
        part.yRot = 0;
        part.zRot = 0;
    }
}
