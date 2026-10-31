package com.fpsrealista.client.anim;

import com.fpsrealista.client.model.Pose;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Clip de animacion por fotogramas clave (gunanims/<arma>.json). Espejo de tools/animlib.py.
 * Interpolacion por fotograma de destino: catmull (defecto), linear, step, ease_in, ease_out, ease_in_out.
 */
public final class AnimationClip {
    enum Ease { CATMULL, LINEAR, STEP, EASE_IN, EASE_OUT, EASE_IN_OUT }

    static final class Key {
        final float t;
        final float[] v;
        final Ease ease;

        Key(float t, float[] v, Ease ease) {
            this.t = t;
            this.v = v;
            this.ease = ease;
        }
    }

    static final class Track {
        final List<Key> keys = new ArrayList<>();
        final int dim;

        Track(int dim) {
            this.dim = dim;
        }

        float[] sample(float t) {
            float[] out = new float[dim];
            if (keys.isEmpty()) {
                return out;
            }
            Key first = keys.get(0);
            Key last = keys.get(keys.size() - 1);
            if (t <= first.t) {
                return first.v.clone();
            }
            if (t >= last.t) {
                return last.v.clone();
            }
            for (int i = 0; i < keys.size() - 1; i++) {
                Key k0 = keys.get(i), k1 = keys.get(i + 1);
                if (t >= k0.t && t <= k1.t) {
                    float span = k1.t - k0.t;
                    float f = span <= 0 ? 0 : (t - k0.t) / span;
                    if (k1.ease == Ease.CATMULL) {
                        Key km = i > 0 ? keys.get(i - 1) : k0;
                        Key kp = i + 2 < keys.size() ? keys.get(i + 2) : k1;
                        float f2 = f * f, f3 = f2 * f;
                        for (int d = 0; d < dim; d++) {
                            float p0 = km.v[d], p1 = k0.v[d], p2 = k1.v[d], p3 = kp.v[d];
                            out[d] = 0.5f * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * f3);
                        }
                        return out;
                    }
                    float g = ease(k1.ease, f);
                    for (int d = 0; d < dim; d++) {
                        out[d] = k0.v[d] + (k1.v[d] - k0.v[d]) * g;
                    }
                    return out;
                }
            }
            return last.v.clone();
        }
    }

    static float ease(Ease e, float t) {
        return switch (e) {
            case LINEAR -> t;
            case STEP -> 0f;
            case EASE_IN -> t * t * t;
            case EASE_OUT -> {
                float u = 1 - t;
                yield 1 - u * u * u;
            }
            case EASE_IN_OUT -> t * t * (3 - 2 * t);
            default -> t;
        };
    }

    record BoneTracks(String bone, Track pos, Track rot) {}

    record IkTrack(String hand, String target, Track weight) {}

    record VisTrack(String bone, List<float[]> keys) {}

    public record Event(float time, String name) {}

    public final String name;
    public final float length;
    final List<BoneTracks> bones = new ArrayList<>();
    final List<IkTrack> ik = new ArrayList<>();
    final List<VisTrack> vis = new ArrayList<>();
    public final List<Event> events = new ArrayList<>();

    private AnimationClip(String name, float length) {
        this.name = name;
        this.length = length;
    }

    private static Ease parseEase(String s) {
        return switch (s) {
            case "linear" -> Ease.LINEAR;
            case "step" -> Ease.STEP;
            case "ease_in" -> Ease.EASE_IN;
            case "ease_out" -> Ease.EASE_OUT;
            case "ease_in_out" -> Ease.EASE_IN_OUT;
            default -> Ease.CATMULL;
        };
    }

    private static Track track(JsonArray arr, int dim) {
        Track tr = new Track(dim);
        if (arr == null) {
            return tr;
        }
        for (JsonElement e : arr) {
            JsonArray k = e.getAsJsonArray();
            float t = k.get(0).getAsFloat();
            float[] v = new float[dim];
            for (int d = 0; d < dim; d++) {
                v[d] = k.get(1 + d).getAsFloat();
            }
            Ease ease = k.size() > 1 + dim ? parseEase(k.get(1 + dim).getAsString()) : Ease.CATMULL;
            tr.keys.add(new Key(t, v, ease));
        }
        return tr;
    }

    public static AnimationClip parse(String name, JsonObject o) {
        AnimationClip c = new AnimationClip(name, o.get("length").getAsFloat());
        if (o.has("bones")) {
            for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("bones").entrySet()) {
                JsonObject b = e.getValue().getAsJsonObject();
                c.bones.add(new BoneTracks(e.getKey(), track(b.getAsJsonArray("pos"), 3), track(b.getAsJsonArray("rot"), 3)));
            }
        }
        if (o.has("ik")) {
            for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("ik").entrySet()) {
                JsonObject b = e.getValue().getAsJsonObject();
                c.ik.add(new IkTrack(e.getKey(), b.get("target").getAsString(), track(b.getAsJsonArray("keys"), 1)));
            }
        }
        if (o.has("vis")) {
            for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("vis").entrySet()) {
                List<float[]> keys = new ArrayList<>();
                for (JsonElement k : e.getValue().getAsJsonArray()) {
                    JsonArray a = k.getAsJsonArray();
                    keys.add(new float[] {a.get(0).getAsFloat(), a.get(1).getAsFloat()});
                }
                c.vis.add(new VisTrack(e.getKey(), keys));
            }
        }
        if (o.has("sounds")) {
            for (JsonElement e : o.getAsJsonArray("sounds")) {
                JsonArray a = e.getAsJsonArray();
                c.events.add(new Event(a.get(0).getAsFloat(), a.get(1).getAsString()));
            }
            c.events.sort((a, b) -> Float.compare(a.time(), b.time()));
        }
        return c;
    }

    /** Suma la pose del clip en el instante t (segundos) con peso w. */
    public void apply(Pose pose, float t, float w) {
        for (BoneTracks b : bones) {
            pose.add(b.bone(), b.pos().sample(t), b.rot().sample(t), w);
        }
        for (IkTrack k : ik) {
            float wt = Math.max(0, Math.min(1, k.weight().sample(t)[0])) * w;
            pose.setIk(k.hand(), k.target(), wt);
        }
        for (VisTrack v : vis) {
            float val = 1;
            for (float[] k : v.keys()) {
                if (k[0] <= t) {
                    val = k[1];
                }
            }
            pose.visibility.put(v.bone(), val > 0.5f);
        }
    }
}
