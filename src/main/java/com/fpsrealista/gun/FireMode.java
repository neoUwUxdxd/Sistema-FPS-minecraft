package com.fpsrealista.gun;

public enum FireMode {
    SEMI("semi"), BURST("burst"), AUTO("auto");

    private final String key;

    FireMode(String key) {
        this.key = key;
    }

    public String translationKey() {
        return "firemode.fpsrealista." + key;
    }
}
