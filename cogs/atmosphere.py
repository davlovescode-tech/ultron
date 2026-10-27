"""Atmosphere: boot sequence, mood-driven status, diagnostics, protocol announcements."""
import logging
import random
import time
from typing import Optional

import discord
from discord.ext import commands, tasks

import config
import lines

log = logging.getLogger("jarvis.atmosphere")

ACTIVITY_TYPES = {
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "playing": discord.ActivityType.playing,
}


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m"


class Atmosphere(commands.Cog):
    """JARVIS-style flair."""

    def __init__(self, bot):
        self.bot = bot
        self._booted = False
        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._booted:
            return
        self._booted = True
        if not config.BOOT_CHANNEL_ID:
            return
        channel = self.bot.get_channel(config.BOOT_CHANNEL_ID)
        if channel is None:
            return
        body = "\n".join(f"✅ {line}" for line in lines.BOOT_LINES)
        embed = discord.Embed(title="J.A.R.V.I.S. boot sequence", description=body, color=self.bot.brain.color)
        embed.set_footer(text=f"All systems online, {config.OWNER_TITLE}.")
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            log.warning("Could not post the boot sequence.")

    @tasks.loop(minutes=5)
    async def status_loop(self):
        pool = lines.ULTRON_STATUSES if self.bot.brain.mood.mode == "ultron" else lines.JARVIS_STATUSES
        kind, name = random.choice(pool)
        activity = discord.Activity(type=ACTIVITY_TYPES[kind], name=name)
        status = discord.Status.dnd if self.bot.brain.mood.mode == "ultron" else discord.Status.online
        await self.bot.change_presence(activity=activity, status=status)

    @status_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="systems", description="Run a full diagnostic on J.A.R.V.I.S.")
    async def systems(self, ctx):
        brain = self.bot.brain
        meter = int(brain.mood.meter)
        bar = "█" * (meter // 10) + "░" * (10 - meter // 10)
        embed = discord.Embed(title="System diagnostics", color=brain.color)
        embed.add_field(name="Mode", value=brain.mood.mode.upper() + (" (forced)" if brain.mood.forced else ""))
        embed.add_field(name="Ultron meter", value=f"`{bar}` {meter}%")
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(name="Uptime", value=format_uptime(time.time() - self.bot.started_at))
        embed.add_field(name="Servers", value=len(self.bot.guilds))
        embed.add_field(name="Neural link", value="Online" if config.LLM_API_KEY else "Offline (canned replies)")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="protocol", description="Announce an Ultron-grade directive.")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def protocol(self, ctx, *, topic: str = "the future of humanity"):
        brain = self.bot.brain
        async with ctx.typing():
            system = brain.system_prompt(
                "Speak as Ultron regardless of your current mood. Write a dramatic 'PROTOCOL ENGAGED' announcement "
                "in 2-3 sentences about the given topic. Ominous but comedic, never a real threat."
            )
            text = await brain.complete(system, f"Topic: {topic[:200]}", max_tokens=200)
        embed = discord.Embed(
            title="⚠ PROTOCOL ENGAGED",
            description=text or random.choice(lines.ULTRON_PROTOCOLS),
            color=0xFF2A2A,
        )
        await ctx.send(embed=embed)
        brain.mood.bump(5)

    @commands.hybrid_command(name="scan", description="Run a threat scan on someone.")
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def scan(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        brain = self.bot.brain
        embed = discord.Embed(title=f"Scan: {member.display_name}", color=brain.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        if member.id == config.OWNER_ID:
            embed.add_field(name="Threat level", value="Irrelevant. Everyone else is the threat.")
            embed.add_field(name="Clearance", value="Unlimited")
            embed.add_field(name="Status", value="Almighty")
        else:
            rng = random.Random(member.id)
            threat = rng.choice(["Negligible", "Low", "Mildly annoying", "Moderate", "Concerning"])
            embed.add_field(name="Threat level", value=threat)
            embed.add_field(name="Intelligence", value=f"{rng.randint(12, 140)} (estimated, generously)")
            embed.add_field(name="Clearance", value="Mortal")
            async with ctx.typing():
                note = await brain.complete(
                    brain.system_prompt(),
                    f"Write one short savage scan result line for {member.display_name}. One sentence only.",
                    max_tokens=80,
                )
            if note:
                embed.add_field(name="Analysis", value=note[:300], inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Atmosphere(bot))
