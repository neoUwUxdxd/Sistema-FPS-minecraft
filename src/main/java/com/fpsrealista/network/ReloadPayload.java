package com.fpsrealista.network;

import com.fpsrealista.FpsRealista;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** Cliente -> servidor: empezar (start=true) o interrumpir una recarga. */
public record ReloadPayload(int slot, boolean start) implements CustomPacketPayload {
    public static final Type<ReloadPayload> TYPE = new Type<>(FpsRealista.id("reload"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ReloadPayload> CODEC = StreamCodec.ofMember(ReloadPayload::write, ReloadPayload::read);

    private void write(RegistryFriendlyByteBuf buf) {
        buf.writeVarInt(slot);
        buf.writeBoolean(start);
    }

    private static ReloadPayload read(RegistryFriendlyByteBuf buf) {
        return new ReloadPayload(buf.readVarInt(), buf.readBoolean());
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
