"""Owner controls that the bot remembers permanently: VIPs, silence rules and standing orders."""
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from cogs.owner import owner_only
from store import MAX_ORDER_LEN, MAX_ORDERS


class Control(commands.Cog):
    """VIP list, silence switches and standing orders (all owner-only, all persistent)."""

    def __init__(self, bot):
        self.bot = bot

    @property
    def store(self):
        return self.bot.store

    # -- VIPs: never roasted, always treated with respect --------------------------------
    @commands.hybrid_group(name="vip", description="Manage VIPs the bot never roasts (owner only).", invoke_without_command=True)
    @owner_only()
    async def vip(self, ctx):
        await ctx.send("Use `vip add @user`, `vip remove @user` or `vip list`.", ephemeral=True)

    @vip.command(name="add", description="Make someone a VIP: never roasted, treated with respect.")
    @owner_only()
    async def vip_add(self, ctx, member: discord.Member):
        if member.bot:
            return await ctx.send("Bots do not get VIP status. Professional jealousy.", ephemeral=True)
        self.store.vips.add(member.id)
        self.store.silenced_users.discard(member.id)
        self.store.blacklist.discard(member.id)
        self.store.save()
        await ctx.send(f"{member.display_name} is now a VIP. No roasts, ever. I'll even be nice to them, {config.OWNER_TITLE}.")

    @vip.command(name="remove", description="Remove someone's VIP status.")
    @owner_only()
    async def vip_remove(self, ctx, member: discord.Member):
        self.store.vips.discard(member.id)
        self.store.save()
        await ctx.send(f"{member.display_name} is no longer a VIP. Back to being fair game.")

    @vip.command(name="list", description="Show all VIPs.")
    @owner_only()
    async def vip_list(self, ctx):
        if not self.store.vips:
            return await ctx.send("No VIPs yet. You are the only one who matters, which is fine by me.", ephemeral=True)
        await ctx.send("**VIPs:** " + ", ".join(f"<@{uid}>" for uid in sorted(self.store.vips)), ephemeral=True)

    # -- silence: "don't reply" stays in force until the owner says otherwise ------------
    @commands.hybrid_command(name="silence", description="Stop replying (everywhere, here, or to one person) until told otherwise.")
    @app_commands.describe(member="Ignore only this person", scope="Where to go quiet when no person is given")
    @owner_only()
    async def silence(self, ctx, member: Optional[discord.Member] = None, scope: Literal["everywhere", "here"] = "everywhere"):
        if member is not None:
            if member.id == config.OWNER_ID:
                return await ctx.send("Ignoring you? Not in my programming.", ephemeral=True)
            self.store.silenced_users.add(member.id)
            msg = f"Understood. I will ignore {member.display_name} until you say otherwise."
        elif scope == "here":
            self.store.silenced_channels.add(ctx.channel.id)
            msg = f"Silent in this channel until you say otherwise, {config.OWNER_TITLE}."
        else:
            self.store.silenced_all = True
            msg = f"Not a word from me until you say otherwise, {config.OWNER_TITLE}. (Commands still work.)"
        self.store.save()
        await ctx.send(msg)

    @commands.hybrid_command(name="unsilence", description="Resume replying (everywhere, here, or to one person).")
    @app_commands.describe(member="Resume for only this person", scope="Where to resume when no person is given")
    @owner_only()
    async def unsilence(self, ctx, member: Optional[discord.Member] = None, scope: Literal["everywhere", "here"] = "everywhere"):
        if member is not None:
            self.store.silenced_users.discard(member.id)
            msg = f"{member.display_name} may be acknowledged again."
        elif scope == "here":
            self.store.silenced_channels.discard(ctx.channel.id)
            msg = f"Back on duty in this channel, {config.OWNER_TITLE}."
        else:
            self.store.silenced_all = False
            self.store.silenced_channels.clear()
            msg = f"Back online everywhere, {config.OWNER_TITLE}."
        self.store.save()
        await ctx.send(msg)

    @commands.hybrid_command(name="memory", description="Show everything I'm remembering (owner only).")
    @owner_only()
    async def memory(self, ctx):
        s = self.store
        persisted = "backed up to Discord" if config.STORE_CHANNEL_ID else "**local only: resets on restart** (set STORE_CHANNEL_ID)"
        embed = discord.Embed(title="Memory", color=self.bot.brain.color)
        embed.add_field(name="Replying", value="silent everywhere" if s.silenced_all else "normal", inline=False)
        embed.add_field(name="Silenced users", value=", ".join(f"<@{u}>" for u in sorted(s.silenced_users)) or "none")
        embed.add_field(name="Silenced channels", value=", ".join(f"<#{c}>" for c in sorted(s.silenced_channels)) or "none")
        embed.add_field(name="VIPs", value=", ".join(f"<@{u}>" for u in sorted(s.vips)) or "none", inline=False)
        embed.add_field(name="Blacklisted", value=str(len(s.blacklist)))
        embed.add_field(name="Standing orders", value=str(len(s.orders)))
        embed.set_footer(text=f"Storage: {persisted}".replace("**", ""))
        await ctx.send(embed=embed, ephemeral=True)

    # -- standing orders: permanent instructions fed into every AI reply ------------------
    @commands.hybrid_group(name="orders", description="Permanent instructions the bot always follows (owner only).", invoke_without_command=True)
    @owner_only()
    async def orders(self, ctx):
        await ctx.send("Use `orders add <text>`, `orders list`, `orders remove <number>` or `orders clear`.", ephemeral=True)

    @orders.command(name="add", description="Give a permanent order, e.g. 'never mention football'.")
    @owner_only()
    async def orders_add(self, ctx, *, text: str):
        if len(self.store.orders) >= MAX_ORDERS:
            return await ctx.send(f"That's {MAX_ORDERS} orders already. Remove one first.", ephemeral=True)
        self.store.orders.append(text.strip()[:MAX_ORDER_LEN])
        self.store.save()
        await ctx.send(f"Order #{len(self.store.orders)} recorded. I will not forget it, {config.OWNER_TITLE}.")

    @orders.command(name="list", description="Show all standing orders.")
    @owner_only()
    async def orders_list(self, ctx):
        if not self.store.orders:
            return await ctx.send("No standing orders.", ephemeral=True)
        body = "\n".join(f"**{i}.** {o}" for i, o in enumerate(self.store.orders, 1))
        await ctx.send(f"**Standing orders:**\n{body}"[:2000], ephemeral=True)

    @orders.command(name="remove", description="Cancel a standing order by its number.")
    @owner_only()
    async def orders_remove(self, ctx, number: int):
        if not 1 <= number <= len(self.store.orders):
            return await ctx.send("No order with that number.", ephemeral=True)
        gone = self.store.orders.pop(number - 1)
        self.store.save()
        await ctx.send(f"Order cancelled: *{gone[:200]}*")

    @orders.command(name="clear", description="Cancel all standing orders.")
    @owner_only()
    async def orders_clear(self, ctx):
        self.store.orders.clear()
        self.store.save()
        await ctx.send("All standing orders cleared.")


async def setup(bot):
    await bot.add_cog(Control(bot))
