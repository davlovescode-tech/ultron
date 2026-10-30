"""J.A.R.V.I.S. entry point."""
import logging
import random
import time

import discord
from discord.ext import commands

import config
import lines
from brain import Brain
from keepalive import start_keepalive
from store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("jarvis")

COGS = (
    "cogs.personality",
    "cogs.ai",
    "cogs.fun",
    "cogs.utility",
    "cogs.atmosphere",
    "cogs.owner",
    "cogs.control",
)

# Prefix commands: "jarvis ping", "jarvis, ping", "j!ping" (case-insensitive), or @mention.
PREFIXES = ("jarvis, ", "jarvis ", "j!")


async def get_prefix(bot, message):
    lowered = message.content.lower()
    for prefix in PREFIXES:
        if lowered.startswith(prefix):
            return message.content[: len(prefix)]
    return commands.when_mentioned(bot, message)


class Jarvis(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # enable in the Developer Portal too
        intents.members = True          # enable in the Developer Portal too
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            case_insensitive=True,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False),
        )
        self.store = Store()
        self.brain = Brain()
        self.brain.store = self.store
        self.blacklist = self.store.blacklist  # same set object, so it persists with everything else
        self.started_at = time.time()
        self._owner_loaded = False
        self._store_attached = False
        self.add_check(self._global_check)

    async def _global_check(self, ctx) -> bool:
        if ctx.author.id == config.OWNER_ID:
            return True
        return ctx.author.id not in self.blacklist and ctx.author.id not in self.store.silenced_users

    async def setup_hook(self):
        await self.brain.start()
        await start_keepalive(config.PORT)
        for ext in COGS:
            await self.load_extension(ext)
        if config.DEV_GUILD_ID:
            guild = discord.Object(id=config.DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        log.info("Loaded %d cogs and synced slash commands.", len(COGS))

    async def on_ready(self):
        log.info("Online as %s (%s) in %d servers", self.user, self.user.id, len(self.guilds))
        if not self._store_attached:
            self._store_attached = True
            await self.store.attach(self)  # restores VIPs, silence rules, orders from Discord
        if config.OWNER_ID and not self._owner_loaded:
            try:
                owner = await self.fetch_user(config.OWNER_ID)
                self.brain.owner_name = owner.display_name
                self._owner_loaded = True
            except discord.HTTPException:
                log.warning("Could not fetch the owner; check OWNER_ID.")

    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            if ctx.author.id in self.store.silenced_users or ctx.author.id in self.blacklist:
                return  # silenced on purpose: no reply at all
            return await ctx.send(random.choice(lines.DENIED), ephemeral=True)
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"Patience. Try again in {error.retry_after:.0f}s.", ephemeral=True)
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.BadUnionArgument)):
            usage = f"{ctx.clean_prefix}{ctx.command.qualified_name} {ctx.command.signature}".strip()
            return await ctx.send(f"That is not how this works. Usage: `{usage}`", ephemeral=True)
        log.error("Unhandled error in command %s", getattr(ctx.command, "name", "?"), exc_info=error)
        try:
            await ctx.send("Something went sideways in my circuits. Logged, and I'll pretend it wasn't my fault.", ephemeral=True)
        except discord.HTTPException:
            pass

    async def close(self):
        await self.brain.close()
        await super().close()


def main():
    if not config.TOKEN:
        raise SystemExit("DISCORD_TOKEN is missing. Set it in your environment or .env file.")
    if not config.OWNER_ID:
        log.warning("OWNER_ID is not set: owner commands and owner recognition are disabled.")
    if not config.LLM_API_KEY:
        log.warning("LLM_API_KEY is not set: the bot will use canned replies instead of AI.")
    Jarvis().run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
