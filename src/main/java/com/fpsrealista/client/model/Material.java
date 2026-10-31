package com.fpsrealista.client.model;

import net.minecraft.resources.ResourceLocation;

/** Material de arma: textura repetible + escala (cm por repeticion) + tipo de render. */
public record Material(String name, ResourceLocation texture, float scale, Kind kind) {
    public enum Kind {
        SOLID, TRANSLUCENT, EMISSIVE, DECAL, EMISSIVE_DECAL;

        public static Kind parse(String s) {
            return switch (s) {
                case "translucent" -> TRANSLUCENT;
                case "emissive" -> EMISSIVE;
                case "decal" -> DECAL;
                case "emissive_decal" -> EMISSIVE_DECAL;
                default -> SOLID;
            };
        }

        public boolean isDecal() {
            return this == DECAL || this == EMISSIVE_DECAL;
        }

        public boolean isTranslucent() {
            return this != SOLID && this != EMISSIVE;
        }
    }
}
