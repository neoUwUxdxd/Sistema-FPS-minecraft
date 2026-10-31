package com.fpsrealista.client.model;

import java.util.HashMap;
import java.util.Map;

/** Pose de animacion: desplazamientos por hueso, pesos de IK de manos y visibilidad. */
public final class Pose {
    public static final class Channel {
        public final float[] pos = new float[3];
        public final float[] rot = new float[3];
    }

    public record Ik(String target, float weight) {}

    private final Map<String, Channel> channels = new HashMap<>();
    public final Map<String, Ik> ik = new HashMap<>();
    public final Map<String, Boolean> visibility = new HashMap<>();

    public Channel get(String bone) {
        return channels.get(bone);
    }

    public Channel getOrCreate(String bone) {
        return channels.computeIfAbsent(bone, k -> new Channel());
    }

    public void add(String bone, float[] pos, float[] rot, float w) {
        Channel c = getOrCreate(bone);
        for (int i = 0; i < 3; i++) {
            c.pos[i] += pos[i] * w;
            c.rot[i] += rot[i] * w;
        }
    }

    public void setIk(String hand, String target, float weight) {
        Ik cur = ik.get(hand);
        if (cur == null || weight > cur.weight()) {
            ik.put(hand, new Ik(target, weight));
        }
    }

    public boolean isVisible(String bone, boolean def) {
        Boolean v = visibility.get(bone);
        return v == null ? def : v;
    }
}
