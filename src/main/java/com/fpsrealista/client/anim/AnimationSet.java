package com.fpsrealista.client.anim;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.HashMap;
import java.util.Map;

/** Todos los clips de un arma. */
public final class AnimationSet {
    public static final AnimationSet EMPTY = new AnimationSet();
    private final Map<String, AnimationClip> clips = new HashMap<>();

    public static AnimationSet parse(JsonObject json) {
        AnimationSet s = new AnimationSet();
        JsonObject clips = json.getAsJsonObject("clips");
        for (Map.Entry<String, JsonElement> e : clips.entrySet()) {
            s.clips.put(e.getKey(), AnimationClip.parse(e.getKey(), e.getValue().getAsJsonObject()));
        }
        return s;
    }

    public AnimationClip get(String name) {
        return clips.get(name);
    }
}
