package com.fpsrealista;

import com.fpsrealista.gun.GunItem;
import com.fpsrealista.gun.GunType;
import com.fpsrealista.gun.GunTypes;
import com.mojang.serialization.Codec;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

public final class ModRegistry {
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(FpsRealista.MODID);
    public static final DeferredRegister<SoundEvent> SOUNDS = DeferredRegister.create(Registries.SOUND_EVENT, FpsRealista.MODID);
    public static final DeferredRegister<DataComponentType<?>> COMPONENTS =
            DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, FpsRealista.MODID);
    public static final DeferredRegister<ParticleType<?>> PARTICLES = DeferredRegister.create(Registries.PARTICLE_TYPE, FpsRealista.MODID);
    public static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, FpsRealista.MODID);

    // ------------------------------------------------------------------ componentes de datos
    /** Cartuchos en el cargador (incluida la recamara). */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> AMMO = COMPONENTS.register("ammo",
            () -> DataComponentType.<Integer>builder().persistent(Codec.INT).networkSynchronized(ByteBufCodecs.VAR_INT).build());
    /** Indice del modo de fuego seleccionado. */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> FIRE_MODE = COMPONENTS.register("fire_mode",
            () -> DataComponentType.<Integer>builder().persistent(Codec.INT).networkSynchronized(ByteBufCodecs.VAR_INT).build());

    // ------------------------------------------------------------------ municion
    public static final DeferredItem<Item> AMMO_9MM = ITEMS.registerSimpleItem("ammo_9mm", new Item.Properties().stacksTo(64));
    public static final DeferredItem<Item> AMMO_556 = ITEMS.registerSimpleItem("ammo_556", new Item.Properties().stacksTo(64));
    public static final DeferredItem<Item> AMMO_762 = ITEMS.registerSimpleItem("ammo_762", new Item.Properties().stacksTo(64));
    public static final DeferredItem<Item> AMMO_12G = ITEMS.registerSimpleItem("ammo_12g", new Item.Properties().stacksTo(32));
    public static final DeferredItem<Item> AMMO_308 = ITEMS.registerSimpleItem("ammo_308", new Item.Properties().stacksTo(32));
    public static final DeferredItem<Item> GUN_PARTS = ITEMS.registerSimpleItem("gun_parts", new Item.Properties().stacksTo(64));

    // ------------------------------------------------------------------ armas
    public static final Map<GunType, DeferredItem<GunItem>> GUNS = new LinkedHashMap<>();

    static {
        for (GunType type : GunTypes.ALL) {
            GUNS.put(type, ITEMS.register(type.id(), () -> new GunItem(type, new Item.Properties().stacksTo(1))));
        }
    }

    // ------------------------------------------------------------------ sonidos
    public static final String[] SOUND_NAMES = {
            "pistol_shot", "carbine_shot", "rifle_shot", "shotgun_shot", "sniper_shot", "dry_fire", "fire_select",
            "mag_out", "mag_in", "slide_back", "slide_release", "charge_back", "charge_release", "pump_back",
            "pump_forward", "shell_insert", "bolt_up", "bolt_back", "bolt_forward", "bolt_down", "gun_draw",
            "gun_handle", "casing", "shell_drop", "hitmarker", "headshot", "impact_flesh", "impact_block", "whizz",
            "glass_hit"};
    private static final Map<String, DeferredHolder<SoundEvent, SoundEvent>> SOUND_MAP = new HashMap<>();

    static {
        for (String name : SOUND_NAMES) {
            SOUND_MAP.put(name, SOUNDS.register(name, () -> SoundEvent.createVariableRangeEvent(FpsRealista.id(name))));
        }
    }

    public static SoundEvent sound(String name) {
        DeferredHolder<SoundEvent, SoundEvent> h = SOUND_MAP.get(name);
        if (h == null) {
            throw new IllegalArgumentException("Sonido desconocido: " + name);
        }
        return h.get();
    }

    public static boolean hasSound(String name) {
        return SOUND_MAP.containsKey(name);
    }

    // ------------------------------------------------------------------ particulas
    public static final DeferredHolder<ParticleType<?>, SimpleParticleType> TRACER = PARTICLES.register("tracer", () -> new SimpleParticleType(true));
    public static final DeferredHolder<ParticleType<?>, SimpleParticleType> BULLET_HOLE = PARTICLES.register("bullet_hole", () -> new SimpleParticleType(true));
    public static final DeferredHolder<ParticleType<?>, SimpleParticleType> CASING = PARTICLES.register("casing", () -> new SimpleParticleType(true));
    public static final DeferredHolder<ParticleType<?>, SimpleParticleType> SHOTSHELL = PARTICLES.register("shotshell", () -> new SimpleParticleType(true));
    public static final DeferredHolder<ParticleType<?>, SimpleParticleType> GUN_SMOKE = PARTICLES.register("gun_smoke", () -> new SimpleParticleType(true));

    // ------------------------------------------------------------------ pestana creativa
    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> TAB = TABS.register("armas", () -> CreativeModeTab.builder()
            .title(Component.translatable("itemGroup.fpsrealista"))
            .icon(() -> new ItemStack(GUNS.get(GunTypes.CARBINE_556).get()))
            .displayItems((params, out) -> {
                for (DeferredItem<GunItem> gun : GUNS.values()) {
                    out.accept(GunItem.loaded(gun.get()));
                }
                out.accept(AMMO_9MM.get());
                out.accept(AMMO_556.get());
                out.accept(AMMO_762.get());
                out.accept(AMMO_12G.get());
                out.accept(AMMO_308.get());
                out.accept(GUN_PARTS.get());
            })
            .build());

    public static void register(IEventBus bus) {
        COMPONENTS.register(bus);
        ITEMS.register(bus);
        SOUNDS.register(bus);
        PARTICLES.register(bus);
        TABS.register(bus);
    }

    private ModRegistry() {}
}
