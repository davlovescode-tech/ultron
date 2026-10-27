"""AI extras: ask, roast, summarize, imagine, translate."""
import asyncio
import io
import random
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

import config


class AI(commands.Cog):
    """AI-powered commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ask", description="Ask J.A.R.V.I.S. anything.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ask(self, ctx, *, question: str):
        brain = self.bot.brain
        async with ctx.typing():
            system = brain.system_prompt(
                "Answer the question accurately and helpfully in under 150 words, with light sarcastic flair. Accuracy first, jokes second."
            )
            answer = await brain.complete(system, question[:1500], max_tokens=450, temperature=0.8)
        await ctx.send(answer or brain.fallback("reply", ctx.author.display_name, ctx.author.id == config.OWNER_ID))

    @commands.hybrid_command(name="roast", description="Roast someone with zero mercy.")
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def roast(self, ctx, member: discord.Member):
        brain = self.bot.brain
        target = member
        reason = "No reason needed. Just roast them."
        if member.id == config.OWNER_ID:
            if ctx.author.id == config.OWNER_ID:
                return await ctx.send(f"Roast you, {config.OWNER_TITLE}? I'd need a week and a much bigger server. Respectfully declining.")
            target = ctx.author
            reason = f"{ctx.author.display_name} asked you to roast your owner, who is untouchable. Roast them for the audacity instead."
        elif member.id == self.bot.user.id:
            target = ctx.author
            reason = "They tried to make you roast yourself. Roast them for it."
        async with ctx.typing():
            user = (
                f"Recent chat:\n{brain.context_block(ctx.channel.id)}\n\n"
                f"Task: roast {target.display_name}. {reason} Maximum 3 sentences."
            )
            text = await brain.complete(brain.system_prompt(), user)
        text = text or brain.fallback("roast", target.display_name, False)
        await ctx.send(f"{target.mention} {text}")
        brain.mood.bump(3)

    @commands.hybrid_command(name="summarize", description="Summarize the recent messages in this channel.")
    @commands.cooldown(1, 15, commands.BucketType.channel)
    async def summarize(self, ctx, count: commands.Range[int, 10, 100] = 50):
        brain = self.bot.brain
        async with ctx.typing():
            msgs = [m async for m in ctx.channel.history(limit=count)]
            msgs.reverse()
            transcript = "\n".join(
                f"{m.author.display_name}: {m.clean_content[:300]}" for m in msgs if not m.author.bot and m.clean_content.strip()
            )[-6000:]
            if not transcript:
                return await ctx.send("Nothing worth summarizing. A remarkably quiet channel.")
            system = brain.system_prompt(
                "Summarize the conversation as 3-6 short bullet points, accurate first, with one dry joke at the end."
            )
            summary = await brain.complete(system, transcript, max_tokens=500, temperature=0.6)
        await ctx.send(summary or "My summarizer is offline. Try again shortly.")

    @commands.hybrid_command(name="translate", description="Translate text into another language.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def translate(self, ctx, language: str, *, text: str):
        brain = self.bot.brain
        async with ctx.typing():
            system = "You are a precise translator. Output only the translation, nothing else."
            out = await brain.complete(system, f"Translate into {language}:\n{text[:1500]}", max_tokens=500, temperature=0.2)
        await ctx.send(out or "Translation matrix offline. Try again shortly.")

    @commands.hybrid_command(name="imagine", description="Generate an image from a prompt.")
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def imagine(self, ctx, *, prompt: str):
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt[:400])}"
            f"?width=1024&height=1024&nologo=true&seed={random.randint(1, 1_000_000)}"
        )
        async with ctx.typing():
            try:
                async with self.bot.brain.session.get(url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                    ctype = resp.headers.get("Content-Type", "")
                    if resp.status != 200 or "image" not in ctype:
                        raise RuntimeError(f"bad response {resp.status}")
                    data = await resp.read()
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError):
                return await ctx.send("The image forge is down or overloaded. Try again in a minute.")
        ext = "png" if "png" in ctype else "jpg"
        filename = f"jarvis_imagine.{ext}"
        embed = discord.Embed(title="Render complete", description=prompt[:200], color=self.bot.brain.color)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed, file=discord.File(io.BytesIO(data), filename=filename))


async def setup(bot):
    await bot.add_cog(AI(bot))
