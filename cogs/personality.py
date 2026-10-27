"""Passive behaviour: roasts, banter, mood drift and random jump-ins."""
import logging
import re
import time

import discord
from discord.ext import commands, tasks

import config

log = logging.getLogger("jarvis.personality")
NAME_RE = re.compile(r"\bjarvis\b", re.IGNORECASE)


class Personality(commands.Cog):
    """Roasts, banter and the Ultron mood engine."""

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.last_active = {}  # guild_id -> (channel_id, author_name, text)
        self._first_jump_skipped = False
        self.mood_tick.start()
        self.jump_in_loop.start()

    def cog_unload(self):
        self.mood_tick.cancel()
        self.jump_in_loop.cancel()

    def _ready(self, user_id: int, kind: str, seconds: float) -> bool:
        now = time.monotonic()
        key = (user_id, kind)
        if now - self.cooldowns.get(key, 0) < seconds:
            return False
        self.cooldowns[key] = now
        return True

    # -- reactive behaviour -------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.author.id in self.bot.blacklist:
            return
        text = message.clean_content.strip()
        if not text:
            return

        brain = self.bot.brain
        is_owner = message.author.id == config.OWNER_ID
        brain.remember(message.channel.id, message.author.display_name, text)
        if not is_owner:
            self.last_active[message.guild.id] = (message.channel.id, message.author.display_name, text[:200])

        # Real commands are handled by the command system, not by chat.
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        ref = message.reference.resolved if message.reference else None
        ref_author_id = ref.author.id if isinstance(ref, discord.Message) else None
        mentioned = {m.id for m in message.mentions}

        pinged_owner = bool(config.OWNER_ID) and (config.OWNER_ID in mentioned or ref_author_id == config.OWNER_ID)
        addressed = (
            self.bot.user.id in mentioned
            or ref_author_id == self.bot.user.id
            or bool(NAME_RE.search(text))
        )

        if pinged_owner and not is_owner and not addressed:
            task, cooldown = "roast", 15
        elif addressed:
            task, cooldown = "reply", 6
        else:
            return
        if not self._ready(message.author.id, task, cooldown):
            return

        try:
            async with message.channel.typing():
                reply = await brain.respond(
                    channel_id=message.channel.id,
                    author=message.author.display_name,
                    text=text[:300],
                    is_owner=is_owner,
                    task=task,
                )
            await message.reply(reply, mention_author=False)
        except discord.HTTPException:
            log.warning("Could not send reply in #%s", message.channel)
            return
        brain.mood.bump(3 if task == "roast" else 1)

    # -- background loops ---------------------------------------------------------
    @tasks.loop(minutes=10)
    async def mood_tick(self):
        self.bot.brain.mood.tick()

    @tasks.loop(hours=config.JUMPIN_HOURS)
    async def jump_in_loop(self):
        if not self._first_jump_skipped:  # loops fire once immediately on start
            self._first_jump_skipped = True
            return
        for guild in self.bot.guilds:
            try:
                await self.jump_in_guild(guild)
            except discord.HTTPException:
                log.warning("Jump-in failed in %s", guild.name)

    @mood_tick.before_loop
    @jump_in_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

    async def jump_in_guild(self, guild: discord.Guild) -> bool:
        """Chime in uninvited with a roast aimed at whoever spoke last. Returns True if sent."""
        info = self.last_active.get(guild.id)
        if not info:
            return False
        channel = guild.get_channel(info[0])
        if config.JUMPIN_CHANNEL_IDS:
            for cid in config.JUMPIN_CHANNEL_IDS:
                candidate = guild.get_channel(cid)
                if candidate:
                    channel = candidate
                    break
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            return False
        brain = self.bot.brain
        reply = await brain.respond(
            channel_id=channel.id,
            author=info[1],
            text=info[2],
            is_owner=False,
            task="jumpin",
        )
        await channel.send(reply)
        brain.mood.bump(2)
        return True


async def setup(bot):
    await bot.add_cog(Personality(bot))
