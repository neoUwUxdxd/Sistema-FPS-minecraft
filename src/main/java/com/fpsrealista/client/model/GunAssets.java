package com.fpsrealista.client.model;

import com.fpsrealista.FpsRealista;
import com.fpsrealista.client.anim.AnimationSet;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.Reader;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.SimplePreparableReloadListener;
import net.minecraft.util.profiling.ProfilerFiller;

/**
 * Carga (y recarga con F3+T) modelos, materiales y animaciones de las armas desde los recursos,
 * de modo que pueden editarse mediante paquetes de recursos.
 */
public final class GunAssets extends SimplePreparableReloadListener<GunAssets.Loaded> {
    public static final GunAssets INSTANCE = new GunAssets();

    public record Loaded(Map<String, GunModel> models, Map<String, AnimationSet> anims) {}

    private volatile Loaded current = new Loaded(Map.of(), Map.of());

    public static GunModel model(String id) {
        return INSTANCE.current.models().get(id);
    }

    public static AnimationSet anims(String id) {
        return INSTANCE.current.anims().getOrDefault(id, AnimationSet.EMPTY);
    }

    private static JsonObject read(Resource r) throws Exception {
        try (Reader reader = r.openAsReader()) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        }
    }

    private static String baseName(ResourceLocation rl) {
        String p = rl.getPath();
        return p.substring(p.lastIndexOf('/') + 1, p.length() - ".json".length());
    }

    @Override
    protected Loaded prepare(ResourceManager rm, ProfilerFiller profiler) {
        Map<String, Material> materials = new HashMap<>();
        Map<String, GunModel> models = new HashMap<>();
        Map<String, AnimationSet> anims = new HashMap<>();
        try {
            var res = rm.getResource(FpsRealista.id("gunmodels/materials.json"));
            if (res.isPresent()) {
                for (Map.Entry<String, JsonElement> e : read(res.get()).entrySet()) {
                    JsonObject o = e.getValue().getAsJsonObject();
                    materials.put(e.getKey(), new Material(e.getKey(), ResourceLocation.parse(o.get("texture").getAsString()),
                            o.get("scale").getAsFloat(), Material.Kind.parse(o.get("type").getAsString())));
                }
            }
        } catch (Exception ex) {
            FpsRealista.LOGGER.error("Error cargando materiales de armas", ex);
        }
        for (Map.Entry<ResourceLocation, Resource> e : rm.listResources("gunmodels", rl -> rl.getPath().endsWith(".json")).entrySet()) {
            String name = baseName(e.getKey());
            if (!e.getKey().getNamespace().equals(FpsRealista.MODID) || name.equals("materials")) {
                continue;
            }
            try {
                models.put(name, GunModel.parse(name, read(e.getValue()), materials));
            } catch (Exception ex) {
                FpsRealista.LOGGER.error("Error cargando modelo de arma {}", e.getKey(), ex);
            }
        }
        for (Map.Entry<ResourceLocation, Resource> e : rm.listResources("gunanims", rl -> rl.getPath().endsWith(".json")).entrySet()) {
            try {
                anims.put(baseName(e.getKey()), AnimationSet.parse(read(e.getValue())));
            } catch (Exception ex) {
                FpsRealista.LOGGER.error("Error cargando animaciones {}", e.getKey(), ex);
            }
        }
        FpsRealista.LOGGER.info("FPS Realista: {} modelos de armas y {} juegos de animaciones cargados", models.size(), anims.size());
        return new Loaded(models, anims);
    }

    @Override
    protected void apply(Loaded loaded, ResourceManager rm, ProfilerFiller profiler) {
        current = loaded;
    }
}
