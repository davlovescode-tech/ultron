"""Owner-only commands."""
import logging
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

import config

log = logging.getLogger("jarvis.owner")


def owner_only():
    async def predicate(ctx) -> bool:
        return bool(config.OWNER_ID) and ctx.author.id == config.OWNER_ID

    return commands.check(predicate)


class Owner(commands.Cog):
    """Commands only the almighty can use."""

    def __init__(self, bot):
        self.bot = bot

    # -- commands -----------------------------------------------------------------
    @commands.hybrid_command(name="say", description="Make J.A.R.V.I.S. speak (owner only).")
    @app_commands.describe(message="What to say", channel="Where to say it (defaults to this channel)")
    @owner_only()
    async def say(self, ctx, channel: Optional[discord.TextChannel] = None, *, message: str):
        target = channel or ctx.channel
        try:
            await target.send(
                message[:2000],
                allowed_mentions=discord.AllowedMentions(everyone=False, roles=True, users=True),
            )
        except discord.HTTPException as exc:
            return await ctx.send(f"Delivery failed: {exc}", ephemeral=True)
        if ctx.interaction:
            await ctx.send(f"Delivered, {config.OWNER_TITLE}.", ephemeral=True)
        else:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

    @commands.hybrid_command(name="mood", description="Inspect or override the mood engine (owner only).")
    @owner_only()
    async def mood(self, ctx, mode: Optional[Literal["jarvis", "ultron", "auto"]] = None):
        mood = self.bot.brain.mood
        if mode is None:
            return await ctx.send(f"Mode: **{mood.mode.upper()}**{' (forced)' if mood.forced else ''}. Ultron meter: {int(mood.meter)}%.")
        mood.forced = None if mode == "auto" else mode
        await ctx.send(f"Mood set to **{mode.upper()}**, {config.OWNER_TITLE}.")

    @commands.hybrid_command(name="jumpin", description="Trigger a random jump-in right now (owner only).")
    @owner_only()
    @commands.guild_only()
    async def jumpin(self, ctx):
        cog = self.bot.get_cog("Personality")
        sent = await cog.jump_in_guild(ctx.guild) if cog else False
        await ctx.send("Done." if sent else "Nobody has said anything worth roasting yet.", ephemeral=True)

    @commands.hybrid_command(name="blacklist", description="Ban someone from using the bot (owner only).")
    @owner_only()
    async def blacklist(self, ctx, member: discord.Member):
        if member.id == config.OWNER_ID:
            return await ctx.send("Blacklisting yourself? Bold. Denied.", ephemeral=True)
        self.bot.blacklist.add(member.id)
        self.bot.store.save()
        await ctx.send(f"{member.display_name} has been erased from my attention.")

    @commands.hybrid_command(name="unblacklist", description="Restore someone's access (owner only).")
    @owner_only()
    async def unblacklist(self, ctx, member: discord.Member):
        self.bot.blacklist.discard(member.id)
        self.bot.store.save()
        await ctx.send(f"{member.display_name} may speak again. Try not to waste it.")

    @commands.hybrid_command(name="broadcast", description="Announce a message in every server (owner only).")
    @owner_only()
    async def broadcast(self, ctx, *, message: str):
        embed = discord.Embed(title="Announcement", description=message[:2000], color=self.bot.brain.color)
        sent = 0
        for guild in self.bot.guilds:
            channel = guild.system_channel
            if channel is None or not channel.permissions_for(guild.me).send_messages:
                channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
            if channel is None:
                continue
            try:
                await channel.send(embed=embed)
                sent += 1
            except discord.HTTPException:
                continue
        await ctx.send(f"Broadcast delivered to {sent}/{len(self.bot.guilds)} servers.", ephemeral=True)

    @commands.hybrid_command(name="sync", description="Re-sync slash commands (owner only).")
    @owner_only()
    async def sync(self, ctx):
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} slash commands. Global changes can take a few minutes to appear.", ephemeral=True)

    @commands.hybrid_command(name="shutdown", description="Shut J.A.R.V.I.S. down (owner only).")
    @owner_only()
    async def shutdown(self, ctx):
        await ctx.send(f"Powering down. Try not to miss me, {config.OWNER_TITLE}.")
        await self.bot.close()


async def setup(bot):
    await bot.add_cog(Owner(bot))
