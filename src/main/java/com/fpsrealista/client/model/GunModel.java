package com.fpsrealista.client.model;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** Modelo de arma cargado desde assets/fpsrealista/gunmodels/<id>.json con la malla ya generada. */
public final class GunModel {
    public static final class Part {
        public final Material material;
        public final int color;
        /** Quads concatenados: 4 vertices x (x,y,z,u,v,nx,ny,nz). */
        public final float[] data;

        Part(Material material, int color, float[] data) {
            this.material = material;
            this.color = color;
            this.data = data;
        }
    }

    public static final class Bone {
        public final String name;
        public final int index;
        public int parent = -1;
        public final Vector3f pivot;
        public final Vector3f rotation;
        public final List<Part> parts = new ArrayList<>();

        Bone(String name, int index, Vector3f pivot, Vector3f rotation) {
            this.name = name;
            this.index = index;
            this.pivot = pivot;
            this.rotation = rotation;
        }
    }

    public record Locator(int bone, Vector3f pos) {}

    public record Arm(Vector3f anchor, Vector3f anchorAds, float twist) {}

    public static final class View {
        public Vector3f hipPos = new Vector3f(0.15f, -0.12f, -0.3f);
        public Vector3f hipRot = new Vector3f();
        public Vector3f sprintPos = new Vector3f(0.06f, -0.2f, -0.2f);
        public Vector3f sprintRot = new Vector3f(-12, 38, 18);
        public float eyeRelief = 0.1f;
        public float armScaleW = 0.3f;
        public float armScaleL = 1.05f;
        public Arm right = new Arm(new Vector3f(0.3f, -0.46f, 0.3f), new Vector3f(0.3f, -0.46f, 0.3f), 0);
        public Arm left = new Arm(new Vector3f(-0.06f, -0.58f, -0.12f), new Vector3f(-0.06f, -0.58f, -0.12f), 0);
    }

    public final String name;
    public final List<Bone> bones = new ArrayList<>();
    public final Map<String, Integer> boneIndex = new HashMap<>();
    public final Map<String, Locator> locators = new HashMap<>();
    public final Set<String> hidden = new HashSet<>();
    /** Desplazamientos aplicados cuando el arma esta vacia (corredera/cerrojo abiertos). */
    public final Map<String, float[]> emptyPose = new HashMap<>();
    public float flashSize = 5f;
    public final View view = new View();
    public final Vector3f boundsMin = new Vector3f(Float.MAX_VALUE);
    public final Vector3f boundsMax = new Vector3f(-Float.MAX_VALUE);
    public final List<Material> materialOrder = new ArrayList<>();

    private GunModel(String name) {
        this.name = name;
    }

    private static Vector3f v3(JsonElement e) {
        JsonArray a = e.getAsJsonArray();
        return new Vector3f(a.get(0).getAsFloat(), a.get(1).getAsFloat(), a.get(2).getAsFloat());
    }

    private static int parseColor(String hex) {
        String h = hex.startsWith("#") ? hex.substring(1) : hex;
        long v = Long.parseLong(h, 16);
        if (h.length() <= 6) {
            v |= 0xFF000000L;
        } else {
            // formato RRGGBBAA -> ARGB
            v = ((v & 0xFF) << 24) | (v >>> 8);
        }
        return (int) v;
    }

    public static GunModel parse(String name, JsonObject json, Map<String, Material> materials) {
        GunModel m = new GunModel(name);
        JsonArray bones = json.getAsJsonArray("bones");
        for (JsonElement be : bones) {
            JsonObject b = be.getAsJsonObject();
            String bn = b.get("name").getAsString();
            Vector3f rot = b.has("rotation") ? v3(b.get("rotation")) : new Vector3f();
            Bone bone = new Bone(bn, m.bones.size(), v3(b.get("pivot")), rot);
            m.boneIndex.put(bn, bone.index);
            m.bones.add(bone);
        }
        for (int bi = 0; bi < bones.size(); bi++) {
            JsonObject b = bones.get(bi).getAsJsonObject();
            Bone bone = m.bones.get(bi);
            if (b.has("parent") && !b.get("parent").isJsonNull()) {
                bone.parent = m.boneIndex.getOrDefault(b.get("parent").getAsString(), -1);
            }
            JsonArray parts = b.getAsJsonArray("parts");
            Map<String, List<float[]>> byKey = new HashMap<>();
            List<String> keyOrder = new ArrayList<>();
            for (int pi = 0; pi < parts.size(); pi++) {
                JsonObject p = parts.get(pi).getAsJsonObject();
                Material mat = materials.get(p.get("mat").getAsString());
                if (mat == null) {
                    continue;
                }
                int color = p.has("tint") ? parseColor(p.get("tint").getAsString()) : 0xFFFFFFFF;
                MeshBuilder.Quads q = MeshBuilder.build(p);
                float ou = (float) ((pi * 0.618034) % 1.0);
                float ov = (float) ((pi * 0.414214) % 1.0);
                for (float[] quad : q.quads) {
                    for (int k = 0; k < 4; k++) {
                        int o = k * MeshBuilder.STRIDE;
                        if (!mat.kind().isDecal()) {
                            quad[o + 3] = quad[o + 3] / mat.scale() + ou;
                            quad[o + 4] = -(quad[o + 4] / mat.scale() + ov);
                        }
                    }
                }
                String key = mat.name() + "|" + color;
                if (!byKey.containsKey(key)) {
                    byKey.put(key, new ArrayList<>());
                    keyOrder.add(key);
                }
                byKey.get(key).addAll(q.quads);
            }
            for (String key : keyOrder) {
                String[] s = key.split("\\|");
                Material mat = materials.get(s[0]);
                List<float[]> qs = byKey.get(key);
                float[] data = new float[qs.size() * 4 * MeshBuilder.STRIDE];
                int o = 0;
                for (float[] qd : qs) {
                    System.arraycopy(qd, 0, data, o, qd.length);
                    o += qd.length;
                }
                bone.parts.add(new Part(mat, Integer.parseInt(s[1]), data));
                if (!m.materialOrder.contains(mat)) {
                    m.materialOrder.add(mat);
                }
            }
        }
        // los materiales translucidos se dibujan al final
        m.materialOrder.sort((a, b) -> Boolean.compare(a.kind().isTranslucent(), b.kind().isTranslucent()));

        if (json.has("locators")) {
            for (Map.Entry<String, JsonElement> e : json.getAsJsonObject("locators").entrySet()) {
                JsonObject l = e.getValue().getAsJsonObject();
                Integer bi = m.boneIndex.get(l.get("bone").getAsString());
                if (bi != null) {
                    m.locators.put(e.getKey(), new Locator(bi, v3(l.get("pos"))));
                }
            }
        }
        if (json.has("hidden")) {
            for (JsonElement e : json.getAsJsonArray("hidden")) {
                m.hidden.add(e.getAsString());
            }
        }
        if (json.has("empty_pose")) {
            for (Map.Entry<String, JsonElement> e : json.getAsJsonObject("empty_pose").entrySet()) {
                Vector3f p = v3(e.getValue());
                m.emptyPose.put(e.getKey(), new float[] {p.x, p.y, p.z});
            }
        }
        if (json.has("flash")) {
            m.flashSize = json.getAsJsonObject("flash").get("size").getAsFloat();
        }
        if (json.has("view")) {
            JsonObject v = json.getAsJsonObject("view");
            JsonObject hip = v.getAsJsonObject("hip");
            m.view.hipPos = v3(hip.get("pos"));
            m.view.hipRot = v3(hip.get("rot"));
            JsonObject sp = v.getAsJsonObject("sprint");
            m.view.sprintPos = v3(sp.get("pos"));
            m.view.sprintRot = v3(sp.get("rot"));
            m.view.eyeRelief = v.get("eye_relief").getAsFloat();
            JsonObject arms = v.getAsJsonObject("arms");
            m.view.armScaleW = arms.get("scale_w").getAsFloat();
            m.view.armScaleL = arms.get("scale_l").getAsFloat();
            m.view.right = arm(arms.getAsJsonObject("right"));
            m.view.left = arm(arms.getAsJsonObject("left"));
        }
        // limites en pose de reposo
        Matrix4f[] mats = m.restMatrices();
        Vector3f tmp = new Vector3f();
        for (Bone b : m.bones) {
            if (m.hidden.contains(b.name)) {
                continue;
            }
            for (Part p : b.parts) {
                for (int o = 0; o < p.data.length; o += MeshBuilder.STRIDE) {
                    mats[b.index].transformPosition(p.data[o], p.data[o + 1], p.data[o + 2], tmp);
                    m.boundsMin.min(tmp);
                    m.boundsMax.max(tmp);
                }
            }
        }
        return m;
    }

    private static Arm arm(JsonObject o) {
        Vector3f a = v3(o.get("anchor"));
        Vector3f ads = o.has("anchor_ads") ? v3(o.get("anchor_ads")) : new Vector3f(a);
        return new Arm(a, ads, o.has("twist") ? o.get("twist").getAsFloat() : 0f);
    }

    /** Matrices de los huesos (espacio modelo, cm) con desplazamientos de animacion opcionales. */
    public Matrix4f[] boneMatrices(Pose pose) {
        Matrix4f[] out = new Matrix4f[bones.size()];
        for (Bone b : bones) {
            compute(b, pose, out);
        }
        return out;
    }

    public Matrix4f[] restMatrices() {
        return boneMatrices(null);
    }

    private Matrix4f compute(Bone b, Pose pose, Matrix4f[] out) {
        if (out[b.index] != null) {
            return out[b.index];
        }
        Matrix4f m = b.parent >= 0 ? new Matrix4f(compute(bones.get(b.parent), pose, out)) : new Matrix4f();
        float px = 0, py = 0, pz = 0, rx = b.rotation.x, ry = b.rotation.y, rz = b.rotation.z;
        if (pose != null) {
            Pose.Channel c = pose.get(b.name);
            if (c != null) {
                px = c.pos[0];
                py = c.pos[1];
                pz = c.pos[2];
                rx += c.rot[0];
                ry += c.rot[1];
                rz += c.rot[2];
            }
        }
        m.translate(b.pivot.x + px, b.pivot.y + py, b.pivot.z + pz);
        m.rotateZ((float) Math.toRadians(rz)).rotateY((float) Math.toRadians(ry)).rotateX((float) Math.toRadians(rx));
        m.translate(-b.pivot.x, -b.pivot.y, -b.pivot.z);
        out[b.index] = m;
        return m;
    }

    /** Posicion de un localizador en espacio modelo (cm). */
    public Vector3f locator(String name, Matrix4f[] mats) {
        Locator l = locators.get(name);
        if (l == null) {
            return null;
        }
        return mats[l.bone()].transformPosition(new Vector3f(l.pos()));
    }

    public boolean hasLocator(String name) {
        return locators.containsKey(name);
    }
}
