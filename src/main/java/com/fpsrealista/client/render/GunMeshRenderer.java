package com.fpsrealista.client.render;

import com.fpsrealista.client.model.GunModel;
import com.fpsrealista.client.model.Material;
import com.fpsrealista.client.model.MeshBuilder;
import com.fpsrealista.client.model.Pose;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/** Dibuja la malla de un {@link GunModel} con una pose de animacion. Coordenadas del modelo en cm. */
public final class GunMeshRenderer {
    private GunMeshRenderer() {}

    public static RenderType renderType(Material m) {
        return switch (m.kind()) {
            case TRANSLUCENT, DECAL -> RenderType.entityTranslucent(m.texture());
            case EMISSIVE_DECAL -> RenderType.eyes(m.texture());
            default -> RenderType.entityCutoutNoCull(m.texture());
        };
    }

    /**
     * @param pose pose de animacion (puede ser null)
     * @param overlay overlay de entidad (OverlayTexture.NO_OVERLAY normalmente)
     * @return las matrices de hueso usadas (espacio modelo)
     */
    public static Matrix4f[] render(GunModel model, Pose pose, PoseStack ps, MultiBufferSource buffers, int light, int overlay) {
        Matrix4f[] mats = model.boneMatrices(pose);
        for (Material mat : model.materialOrder) {
            VertexConsumer vc = null;
            for (GunModel.Bone bone : model.bones) {
                boolean visible = pose != null ? pose.isVisible(bone.name, !model.hidden.contains(bone.name))
                        : !model.hidden.contains(bone.name);
                if (!visible || !parentsVisible(model, bone, pose)) {
                    continue;
                }
                for (GunModel.Part part : bone.parts) {
                    if (part.material != mat) {
                        continue;
                    }
                    if (vc == null) {
                        vc = buffers.getBuffer(renderType(mat));
                    }
                    ps.pushPose();
                    ps.last().pose().mul(mats[bone.index]);
                    ps.last().normal().mul(new Matrix3f(mats[bone.index]));
                    int l = mat.kind() == Material.Kind.EMISSIVE || mat.kind() == Material.Kind.EMISSIVE_DECAL
                            ? LightTexture.FULL_BRIGHT : light;
                    emit(vc, ps.last(), part, l, overlay, mat.kind().isDecal());
                    ps.popPose();
                }
            }
        }
        return mats;
    }

    private static boolean parentsVisible(GunModel model, GunModel.Bone bone, Pose pose) {
        int p = bone.parent;
        while (p >= 0) {
            GunModel.Bone b = model.bones.get(p);
            boolean v = pose != null ? pose.isVisible(b.name, !model.hidden.contains(b.name)) : !model.hidden.contains(b.name);
            if (!v) {
                return false;
            }
            p = b.parent;
        }
        return true;
    }

    private static void emit(VertexConsumer vc, PoseStack.Pose pose, GunModel.Part part, int light, int overlay, boolean twoSided) {
        float[] d = part.data;
        int color = part.color;
        int S = MeshBuilder.STRIDE;
        for (int q = 0; q < d.length; q += 4 * S) {
            for (int k = 0; k < 4; k++) {
                vertex(vc, pose, d, q + k * S, color, light, overlay, 1f);
            }
            if (twoSided) {
                for (int k = 3; k >= 0; k--) {
                    vertex(vc, pose, d, q + k * S, color, light, overlay, -1f);
                }
            }
        }
    }

    private static void vertex(VertexConsumer vc, PoseStack.Pose pose, float[] d, int o, int color, int light, int overlay, float ns) {
        vc.addVertex(pose, d[o], d[o + 1], d[o + 2])
                .setColor(color)
                .setUv(d[o + 3], d[o + 4])
                .setOverlay(overlay)
                .setLight(light)
                .setNormal(pose, d[o + 5] * ns, d[o + 6] * ns, d[o + 7] * ns);
    }
}
