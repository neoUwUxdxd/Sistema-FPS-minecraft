package com.fpsrealista.network;

import com.fpsrealista.server.GunServerLogic;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public final class Network {
    /** Manejadores de paquetes del cliente; los instala el lado cliente para no cargar clases de cliente en el servidor. */
    public static ClientHandlers client = new ClientHandlers() {};

    public interface ClientHandlers {
        default void onShotFx(ShotFxPayload p) {}
        default void onHitMarker(HitMarkerPayload p) {}
    }

    public static void register(RegisterPayloadHandlersEvent event) {
        PayloadRegistrar r = event.registrar("1");
        r.playToServer(ShootPayload.TYPE, ShootPayload.CODEC, (p, ctx) -> GunServerLogic.onShoot(ctx.player(), p));
        r.playToServer(ReloadPayload.TYPE, ReloadPayload.CODEC, (p, ctx) -> GunServerLogic.onReload(ctx.player(), p));
        r.playToServer(FireModePayload.TYPE, FireModePayload.CODEC, (p, ctx) -> GunServerLogic.onFireMode(ctx.player(), p));
        r.playToClient(ShotFxPayload.TYPE, ShotFxPayload.CODEC, (p, ctx) -> client.onShotFx(p));
        r.playToClient(HitMarkerPayload.TYPE, HitMarkerPayload.CODEC, (p, ctx) -> client.onHitMarker(p));
    }

    private Network() {}
}
