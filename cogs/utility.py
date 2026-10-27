"""Utility commands."""
import asyncio
import re
from typing import Optional
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

import config

DURATION_RE = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


def parse_duration(text: str) -> int:
    return sum(int(n) * UNITS[u.lower()] for n, u in DURATION_RE.findall(text))


class Utility(commands.Cog):
    """Everyday tools."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="List everything J.A.R.V.I.S. can do.")
    async def help(self, ctx):
        is_owner = ctx.author.id == config.OWNER_ID
        embed = discord.Embed(
            title="J.A.R.V.I.S. command index",
            description="Use `/command`, `jarvis command` or `j!command`.",
            color=self.bot.brain.color,
        )
        for name, cog in self.bot.cogs.items():
            if name == "Owner" and not is_owner:
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue
            text = ", ".join(f"`{c.name}`" for c in sorted(cmds, key=lambda c: c.name))
            embed.add_field(name=name, value=text[:1000], inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Check latency.")
    async def ping(self, ctx):
        await ctx.send(f"Pong. {round(self.bot.latency * 1000)}ms. Faster than your reflexes, I'd wager.")

    @commands.hybrid_command(name="avatar", description="Show someone's avatar.")
    async def avatar(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"{member.display_name}'s avatar", color=self.bot.brain.color)
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Show info about a user.")
    @commands.guild_only()
    async def userinfo(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]
        embed = discord.Embed(title=str(member), color=self.bot.brain.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, "R"))
        if member.joined_at:
            embed.add_field(name="Joined server", value=discord.utils.format_dt(member.joined_at, "R"))
        embed.add_field(name="Roles", value=(" ".join(roles[:15]) or "None"), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Show info about this server.")
    @commands.guild_only()
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=g.name, color=self.bot.brain.color)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Channels", value=len(g.channels))
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Boosts", value=g.premium_subscription_count)
        embed.add_field(name="Created", value=discord.utils.format_dt(g.created_at, "R"))
        if g.owner:
            embed.add_field(name="Owner", value=g.owner.mention)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="poll", description="Create a poll. Separate options with |")
    @commands.guild_only()
    async def poll(self, ctx, question: str, options: str):
        choices = [o.strip() for o in options.split("|") if o.strip()]
        if not 2 <= len(choices) <= 9:
            return await ctx.send("Give me 2 to 9 options separated by `|`.", ephemeral=True)
        body = "\n".join(f"{NUMBER_EMOJIS[i]} {c[:100]}" for i, c in enumerate(choices))
        embed = discord.Embed(title=question[:250], description=body, color=self.bot.brain.color)
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        try:
            for i in range(len(choices)):
                await msg.add_reaction(NUMBER_EMOJIS[i])
        except discord.HTTPException:
            pass

    @commands.hybrid_command(name="remind", description="Set a reminder, e.g. 10m, 2h30m, 1d. Resets if the bot restarts.")
    async def remind(self, ctx, duration: str, *, what: str):
        seconds = parse_duration(duration)
        if seconds <= 0 or seconds > 7 * 86400:
            return await ctx.send("Pick a duration between 1 second and 7 days, like `10m` or `2h30m`.", ephemeral=True)
        await ctx.send(f"Noted. I'll remind you in {duration}. Reminders reset if I restart, so don't bet your life on it.")
        await asyncio.sleep(seconds)
        try:
            await ctx.channel.send(f"{ctx.author.mention} Reminder: {what[:500]}")
        except discord.HTTPException:
            pass

    @commands.hybrid_command(name="weather", description="Get the weather for a city.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def weather(self, ctx, *, city: str):
        async with ctx.typing():
            try:
                async with self.bot.brain.session.get(f"https://wttr.in/{quote(city[:80])}?format=j1") as resp:
                    if resp.status != 200:
                        raise ValueError("bad status")
                    data = await resp.json(content_type=None)
                cur = data["current_condition"][0]
                area = data["nearest_area"][0]["areaName"][0]["value"]
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError, IndexError):
                return await ctx.send("Couldn't reach the weather satellites for that location.")
        embed = discord.Embed(title=f"Weather in {area}", description=cur["weatherDesc"][0]["value"], color=self.bot.brain.color)
        embed.add_field(name="Temperature", value=f"{cur['temp_C']}°C (feels {cur['FeelsLikeC']}°C)")
        embed.add_field(name="Humidity", value=f"{cur['humidity']}%")
        embed.add_field(name="Wind", value=f"{cur['windspeedKmph']} km/h")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
