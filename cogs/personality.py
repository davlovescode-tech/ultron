"""Passive behaviour: roasts, banter, mood drift and random jump-ins."""
import logging
import re
import time

import discord
from discord.ext import commands, tasks

import config

log = logging.getLogger("jarvis.personality")
NAME_RE = re.compile(r"\bjarvis\b", re.IGNORECASE)

# Natural-language orders from the owner, e.g. "jarvis dont reply" / "jarvis you can reply again".
_VERBS = r"(?:reply(?:ing)?|respond(?:ing)?|talk(?:ing)?|speak(?:ing)?|answer(?:ing)?)"
STOP_RE = re.compile(
    rf"\b(?:don'?t|do not|stop|quit|no more)\s+(?:you\s+)?{_VERBS}\b"
    r"|\b(?:be quiet|shut up|stay silent|go silent|go quiet|mute yourself)\b",
    re.IGNORECASE,
)
START_RE = re.compile(
    rf"\b(?:you can|you may|start|resume|continue|keep|go ahead and)\s+{_VERBS}\b"
    r"|\b(?:unmute|speak again|reply again|respond again|wake up)\b",
    re.IGNORECASE,
)
TO_SOMEONE_RE = re.compile(rf"\b{_VERBS}\s+to\b", re.IGNORECASE)
HERE_RE = re.compile(r"\b(?:here|this channel|in here)\b", re.IGNORECASE)


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
        store = self.bot.store
        is_vip = message.author.id in store.vips
        if not is_owner and not is_vip:
            self.last_active[message.guild.id] = (
                message.channel.id, message.author.display_name, text[:200], message.author.id,
            )

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

        # The owner's standing instructions ("don't reply", "you can reply again") always get through.
        if is_owner and addressed and await self._owner_instruction(message, text):
            return

        # Silence rules (set by the owner, remembered permanently). Commands still work.
        if (
            store.silenced_all
            or message.channel.id in store.silenced_channels
            or message.author.id in store.silenced_users
        ):
            return

        if pinged_owner and not is_owner and not is_vip and not addressed:
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
                    is_vip=is_vip,
                )
            await message.reply(reply, mention_author=False)
        except discord.HTTPException:
            log.warning("Could not send reply in #%s", message.channel)
            return
        brain.mood.bump(3 if task == "roast" else 1)

    async def _owner_instruction(self, message: discord.Message, text: str) -> bool:
        """Handle "don't reply" / "you can reply" style orders from the owner. True if handled."""
        if START_RE.search(text):
            stop = False
        elif STOP_RE.search(text):
            stop = True
        else:
            return False

        store, title = self.bot.store, config.OWNER_TITLE
        targets = [m for m in message.mentions if not m.bot and m.id != config.OWNER_ID]
        if targets:
            names = ", ".join(m.display_name for m in targets)
            for m in targets:
                (store.silenced_users.add if stop else store.silenced_users.discard)(m.id)
            reply = (
                f"Understood, {title}. I will ignore {names} until you say otherwise."
                if stop else f"Very well, {title}. {names} may be acknowledged again."
            )
        elif TO_SOMEONE_RE.search(text):
            reply = f"Who, exactly, {title}? @mention them so I silence the right person and not the whole server."
            await message.reply(reply, mention_author=False)
            return True
        elif HERE_RE.search(text):
            (store.silenced_channels.add if stop else store.silenced_channels.discard)(message.channel.id)
            reply = (
                f"Understood, {title}. Silent in this channel until you say otherwise."
                if stop else f"Back on duty in this channel, {title}."
            )
        else:
            store.silenced_all = stop
            reply = (
                f"Understood, {title}. Not a word from me until you say otherwise."
                if stop else f"Back online, {title}. The mortals were getting lonely."
            )
        store.save()
        try:
            await message.reply(reply, mention_author=False)
        except discord.HTTPException:
            pass
        return True

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
        store = self.bot.store
        info = self.last_active.get(guild.id)
        if not info or store.silenced_all:
            return False
        if info[3] in store.vips or info[3] in store.silenced_users:
            return False
        channel = guild.get_channel(info[0])
        if config.JUMPIN_CHANNEL_IDS:
            for cid in config.JUMPIN_CHANNEL_IDS:
                candidate = guild.get_channel(cid)
                if candidate:
                    channel = candidate
                    break
        if channel is None or channel.id in store.silenced_channels:
            return False
        if not channel.permissions_for(guild.me).send_messages:
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
