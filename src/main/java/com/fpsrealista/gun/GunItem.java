package com.fpsrealista.gun;

import com.fpsrealista.ModRegistry;
import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.UseAnim;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

public class GunItem extends Item {
    private final GunType type;

    public GunItem(GunType type, Properties props) {
        super(props);
        this.type = type;
    }

    public GunType type() {
        return type;
    }

    public static ItemStack loaded(GunItem item) {
        ItemStack s = new ItemStack(item);
        setAmmo(s, item.type.magSize);
        return s;
    }

    public static GunType typeOf(ItemStack stack) {
        return stack.getItem() instanceof GunItem g ? g.type : null;
    }

    public static int getAmmo(ItemStack stack) {
        return stack.getOrDefault(ModRegistry.AMMO.get(), 0);
    }

    public static void setAmmo(ItemStack stack, int ammo) {
        stack.set(ModRegistry.AMMO.get(), Math.max(0, ammo));
    }

    public static FireMode getFireMode(ItemStack stack) {
        GunType t = typeOf(stack);
        if (t == null) {
            return FireMode.SEMI;
        }
        int i = stack.getOrDefault(ModRegistry.FIRE_MODE.get(), 0);
        return t.fireModes.get(Math.floorMod(i, t.fireModes.size()));
    }

    public static void setFireModeIndex(ItemStack stack, int index) {
        stack.set(ModRegistry.FIRE_MODE.get(), index);
    }

    public static int getFireModeIndex(ItemStack stack) {
        return stack.getOrDefault(ModRegistry.FIRE_MODE.get(), 0);
    }

    @Override
    public ItemStack getDefaultInstance() {
        ItemStack s = super.getDefaultInstance();
        setAmmo(s, type.magSize);
        return s;
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        // El clic derecho (apuntar) se gestiona en el cliente.
        return InteractionResultHolder.fail(player.getItemInHand(hand));
    }

    @Override
    public UseAnim getUseAnimation(ItemStack stack) {
        return UseAnim.NONE;
    }

    @Override
    public boolean canAttackBlock(BlockState state, Level level, BlockPos pos, Player player) {
        return false;
    }

    @Override
    public boolean onEntitySwing(ItemStack stack, LivingEntity entity) {
        return true;
    }

    @Override
    public boolean shouldCauseReequipAnimation(ItemStack oldStack, ItemStack newStack, boolean slotChanged) {
        return slotChanged || oldStack.getItem() != newStack.getItem();
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext ctx, List<Component> tip, TooltipFlag flag) {
        tip.add(Component.translatable("tooltip.fpsrealista.ammo", getAmmo(stack), type.magSize)
                .withStyle(ChatFormatting.GOLD));
        tip.add(Component.translatable("tooltip.fpsrealista.caliber", Component.translatable(type.ammo.get().getDescriptionId()))
                .withStyle(ChatFormatting.GRAY));
        String dmg = type.pellets > 1 ? String.format("%.1f x%d", type.damage, type.pellets) : String.format("%.1f", type.damage);
        tip.add(Component.translatable("tooltip.fpsrealista.damage", dmg).withStyle(ChatFormatting.GRAY));
        tip.add(Component.translatable("tooltip.fpsrealista.rpm", Math.round(type.rpm)).withStyle(ChatFormatting.GRAY));
        tip.add(Component.translatable("tooltip.fpsrealista.mode", Component.translatable(getFireMode(stack).translationKey()))
                .withStyle(ChatFormatting.GRAY));
        tip.add(Component.translatable("tooltip.fpsrealista.controls").withStyle(ChatFormatting.DARK_GRAY));
    }
}
