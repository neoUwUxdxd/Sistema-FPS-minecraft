package com.fpsrealista.network;

import com.fpsrealista.FpsRealista;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** Servidor -> tirador: confirmacion de impacto. */
public record HitMarkerPayload(boolean headshot, boolean kill) implements CustomPacketPayload {
    public static final Type<HitMarkerPayload> TYPE = new Type<>(FpsRealista.id("hit_marker"));
    public static final StreamCodec<RegistryFriendlyByteBuf, HitMarkerPayload> CODEC = StreamCodec.ofMember(HitMarkerPayload::write, HitMarkerPayload::read);

    private void write(RegistryFriendlyByteBuf buf) {
        buf.writeBoolean(headshot);
        buf.writeBoolean(kill);
    }

    private static HitMarkerPayload read(RegistryFriendlyByteBuf buf) {
        return new HitMarkerPayload(buf.readBoolean(), buf.readBoolean());
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
