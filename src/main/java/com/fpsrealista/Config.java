package com.fpsrealista;

import net.neoforged.neoforge.common.ModConfigSpec;

/** Configuracion del servidor (config/fpsrealista-server.toml dentro del mundo). */
public final class Config {
    private static final ModConfigSpec.Builder B = new ModConfigSpec.Builder();

    public static final ModConfigSpec.DoubleValue DAMAGE_MULTIPLIER = B
            .comment("Multiplicador global del dano de las armas")
            .defineInRange("damageMultiplier", 1.0, 0.0, 100.0);
    public static final ModConfigSpec.BooleanValue BREAK_GLASS = B
            .comment("Las balas rompen cristales y paneles de cristal")
            .define("breakGlass", true);
    public static final ModConfigSpec.BooleanValue PENETRATE_FOLIAGE = B
            .comment("Las balas atraviesan hojas y vegetacion")
            .define("penetrateFoliage", true);
    public static final ModConfigSpec.BooleanValue INFINITE_AMMO_CREATIVE = B
            .comment("Municion infinita en modo creativo")
            .define("infiniteAmmoCreative", true);
    public static final ModConfigSpec.BooleanValue FRIENDLY_PETS = B
            .comment("No danar a las mascotas propias")
            .define("protectOwnPets", true);

    public static final ModConfigSpec SPEC = B.build();

    private Config() {}
}
