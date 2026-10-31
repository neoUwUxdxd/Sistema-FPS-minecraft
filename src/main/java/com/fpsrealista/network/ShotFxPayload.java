package com.fpsrealista.network;

import com.fpsrealista.FpsRealista;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/** Servidor -> jugadores cercanos: efectos visuales del disparo de otro jugador. */
public record ShotFxPayload(int shooterId, int gun, List<FxHit> hits) implements CustomPacketPayload {
    public static final Type<ShotFxPayload> TYPE = new Type<>(FpsRealista.id("shot_fx"));
    public static final StreamCodec<RegistryFriendlyByteBuf, ShotFxPayload> CODEC = StreamCodec.ofMember(ShotFxPayload::write, ShotFxPayload::read);

    /** type: ordinal de Ballistics.HitType; face: ordinal de Direction o -1. */
    public record FxHit(double x, double y, double z, int type, int face, int blockState) {}

    private void write(RegistryFriendlyByteBuf buf) {
        buf.writeVarInt(shooterId);
        buf.writeVarInt(gun);
        buf.writeVarInt(hits.size());
        for (FxHit h : hits) {
            buf.writeDouble(h.x());
            buf.writeDouble(h.y());
            buf.writeDouble(h.z());
            buf.writeByte(h.type());
            buf.writeByte(h.face());
            buf.writeVarInt(h.blockState());
        }
    }

    private static ShotFxPayload read(RegistryFriendlyByteBuf buf) {
        int id = buf.readVarInt();
        int gun = buf.readVarInt();
        int n = Math.min(buf.readVarInt(), 256);
        List<FxHit> hits = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            hits.add(new FxHit(buf.readDouble(), buf.readDouble(), buf.readDouble(), buf.readByte(), buf.readByte(), buf.readVarInt()));
        }
        return new ShotFxPayload(id, gun, hits);
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
