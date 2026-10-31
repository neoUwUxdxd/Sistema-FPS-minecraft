package com.fpsrealista.network;

import com.fpsrealista.FpsRealista;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** Cliente -> servidor: seleccionar modo de fuego. */
public record FireModePayload(int slot, int mode) implements CustomPacketPayload {
    public static final Type<FireModePayload> TYPE = new Type<>(FpsRealista.id("fire_mode"));
    public static final StreamCodec<RegistryFriendlyByteBuf, FireModePayload> CODEC = StreamCodec.ofMember(FireModePayload::write, FireModePayload::read);

    private void write(RegistryFriendlyByteBuf buf) {
        buf.writeVarInt(slot);
        buf.writeVarInt(mode);
    }

    private static FireModePayload read(RegistryFriendlyByteBuf buf) {
        return new FireModePayload(buf.readVarInt(), buf.readVarInt());
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
