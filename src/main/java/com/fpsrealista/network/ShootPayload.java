package com.fpsrealista.network;

import com.fpsrealista.FpsRealista;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** Cliente -> servidor: un disparo (todos los perdigones comparten la semilla). */
public record ShootPayload(int slot, int seed, float yaw, float pitch, float spread, boolean aiming) implements CustomPacketPayload {
    public static final Type<ShootPayload> TYPE = new Type<>(FpsRealista.id("shoot"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ShootPayload> CODEC = StreamCodec.ofMember(ShootPayload::write, ShootPayload::read);

    private void write(RegistryFriendlyByteBuf buf) {
        buf.writeVarInt(slot);
        buf.writeInt(seed);
        buf.writeFloat(yaw);
        buf.writeFloat(pitch);
        buf.writeFloat(spread);
        buf.writeBoolean(aiming);
    }

    private static ShootPayload read(RegistryFriendlyByteBuf buf) {
        return new ShootPayload(buf.readVarInt(), buf.readInt(), buf.readFloat(), buf.readFloat(), buf.readFloat(), buf.readBoolean());
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
