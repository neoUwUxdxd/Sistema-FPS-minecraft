package com.fpsrealista;

import com.fpsrealista.network.Network;
import com.fpsrealista.server.GunServerLogic;
import com.mojang.logging.LogUtils;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;

/**
 * FPS Realista - sistema de armas de fuego hiperrealista para Minecraft (NeoForge 1.21.1).
 */
@Mod(FpsRealista.MODID)
public final class FpsRealista {
    public static final String MODID = "fpsrealista";
    public static final Logger LOGGER = LogUtils.getLogger();

    public FpsRealista(IEventBus modBus, ModContainer container) {
        ModRegistry.register(modBus);
        modBus.addListener(Network::register);
        container.registerConfig(ModConfig.Type.SERVER, Config.SPEC);
        GunServerLogic.init(NeoForge.EVENT_BUS);
    }

    public static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(MODID, path);
    }
}
