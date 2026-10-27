"""Fun commands."""
import asyncio
import html
import random
import re
from typing import Optional

import aiohttp
import discord
from discord.ext import commands

import config
import lines


class TriviaView(discord.ui.View):
    def __init__(self, correct: str, answers: list):
        super().__init__(timeout=25)
        self.correct = correct
        self.done = False
        self.message = None
        for answer in answers:
            button = discord.ui.Button(label=answer[:80], style=discord.ButtonStyle.secondary)
            button.callback = self._make_callback(answer, button)
            self.add_item(button)

    def _make_callback(self, answer: str, button: discord.ui.Button):
        async def callback(interaction: discord.Interaction):
            if self.done:
                return await interaction.response.send_message("Too late. Someone beat you to it.", ephemeral=True)
            self.done = True
            right = answer == self.correct
            for item in self.children:
                item.disabled = True
                if item.label == self.correct[:80]:
                    item.style = discord.ButtonStyle.success
            if not right:
                button.style = discord.ButtonStyle.danger
            await interaction.response.edit_message(view=self)
            verdict = "Correct. Don't let it go to your head." if right else "Wrong. Spectacularly."
            await interaction.followup.send(f"{interaction.user.mention} {verdict} The answer: **{self.correct}**")
            self.stop()

        return callback

    async def on_timeout(self):
        if self.done:
            return
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Fun(commands.Cog):
    """Games, jokes and nonsense."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="8ball", description="Consult the all-knowing J.A.R.V.I.S.")
    async def eightball(self, ctx, *, question: str):
        await ctx.send(f"**{question[:200]}**\n{random.choice(lines.EIGHTBALL)}")

    @commands.hybrid_command(name="flip", description="Flip a coin.")
    async def flip(self, ctx):
        await ctx.send(random.choice(["Heads.", "Tails."]))

    @commands.hybrid_command(name="roll", description="Roll dice, e.g. 2d6 (default 1d20).")
    async def roll(self, ctx, dice: str = "1d20"):
        match = re.fullmatch(r"(\d{1,2})d(\d{1,3})", dice.lower().strip())
        if not match:
            return await ctx.send("Format it like `2d6`, please.")
        count, sides = int(match.group(1)), int(match.group(2))
        if not (1 <= count <= 20 and 2 <= sides <= 100):
            return await ctx.send("Between 1-20 dice with 2-100 sides. I have limits, unlike your ambition.")
        rolls = [random.randint(1, sides) for _ in range(count)]
        await ctx.send(f"🎲 {dice}: {', '.join(map(str, rolls))} → **{sum(rolls)}**")

    @commands.hybrid_command(name="rate", description="Rate anything out of 10.")
    async def rate(self, ctx, *, thing: str):
        score = random.Random(thing.lower().strip()).randint(0, 10)
        tier = "low" if score <= 3 else "mid" if score <= 6 else "high"
        await ctx.send(f"**{thing[:100]}**: {score}/10. {random.choice(lines.RATE_COMMENTS[tier])}")

    @commands.hybrid_command(name="ship", description="Calculate compatibility between two people.")
    async def ship(self, ctx, first: discord.Member, second: Optional[discord.Member] = None):
        second = second or ctx.author
        percent = (first.id + second.id) % 101
        bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
        verdict = "A disaster in motion." if percent < 35 else "Workable, with supervision." if percent < 70 else "Alarmingly compatible."
        await ctx.send(f"💘 {first.display_name} × {second.display_name}\n`{bar}` **{percent}%**\n{verdict}")

    @commands.hybrid_command(name="hack", description="Run a totally real hacking sequence on someone.")
    async def hack(self, ctx, member: Optional[discord.Member] = None):
        target = member or ctx.author
        if target.id == config.OWNER_ID:
            return await ctx.send(f"Hack the almighty? Access denied. Also, {ctx.author.display_name}, I've logged your attempt.")
        steps = [
            f"Locating {target.display_name}...",
            "Bypassing firewall (it was a sticky note)...",
            "Extracting browser history... please don't read it, I'm disturbed.",
            "Downloading 4.2GB of questionable memes...",
            f"Hack complete. {target.display_name} is, in fact, the weakest link.",
        ]
        msg = await ctx.send(steps[0])
        for step in steps[1:]:
            await asyncio.sleep(1.5)
            await msg.edit(content=step)

    @commands.hybrid_command(name="meme", description="Fetch a fresh meme.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def meme(self, ctx):
        async with ctx.typing():
            for _ in range(3):
                try:
                    async with self.bot.brain.session.get("https://meme-api.com/gimme") as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                    continue
                if data.get("nsfw") or data.get("spoiler") or not data.get("url"):
                    continue
                embed = discord.Embed(title=str(data.get("title", "Meme"))[:250], color=self.bot.brain.color)
                embed.set_image(url=data["url"])
                return await ctx.send(embed=embed)
        await ctx.send("The meme servers are being difficult. Try again shortly.")

    @commands.hybrid_command(name="trivia", description="Answer a trivia question.")
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def trivia(self, ctx):
        async with ctx.typing():
            try:
                async with self.bot.brain.session.get("https://opentdb.com/api.php?amount=1&type=multiple") as resp:
                    data = await resp.json()
                item = data["results"][0]
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError, IndexError):
                return await ctx.send("Trivia database unavailable. Probably embarrassed by your last score.")
        question = html.unescape(item["question"])
        correct = html.unescape(item["correct_answer"])
        answers = [html.unescape(a) for a in item["incorrect_answers"]] + [correct]
        random.shuffle(answers)
        embed = discord.Embed(
            title="Trivia",
            description=question,
            color=self.bot.brain.color,
        )
        embed.set_footer(text=f"{html.unescape(item['category'])} • {item['difficulty']} • 25 seconds")
        view = TriviaView(correct, answers)
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Fun(bot))
