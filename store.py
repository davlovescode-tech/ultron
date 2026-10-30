"""Persistent bot memory: VIPs, silence rules, standing orders and the blacklist.

Saved to data/state.json. Render's free disk is wiped on every restart/redeploy, so if
STORE_CHANNEL_ID is set the state is also backed up as a `state.json` attachment in that
(private) Discord channel and restored from it on startup. That keeps the bot's memory
forever without any extra service or signup.
"""
import asyncio
import io
import json
import logging
from pathlib import Path

import discord

import config

log = logging.getLogger("jarvis.store")
FILE = Path("data/state.json")
BACKUP_NAME = "state.json"
MAX_ORDERS = 25
MAX_ORDER_LEN = 300


class Store:
    def __init__(self):
        self.vips = set()               # user ids that are never roasted
        self.blacklist = set()          # user ids banned from the bot
        self.silenced_users = set()     # bot ignores these users completely
        self.silenced_channels = set()  # bot stays quiet in these channels
        self.silenced_all = False       # bot stays quiet everywhere (chat only)
        self.orders = []                # standing orders from the owner, fed to the AI
        self._bot = None
        self._backup_msg_id = None
        self._push_lock = asyncio.Lock()
        self._push_pending = False
        self._load_local()

    # -- (de)serialisation ----------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "vips": sorted(self.vips),
            "blacklist": sorted(self.blacklist),
            "silenced_users": sorted(self.silenced_users),
            "silenced_channels": sorted(self.silenced_channels),
            "silenced_all": self.silenced_all,
            "orders": list(self.orders),
        }

    def _apply(self, data: dict):
        # Mutate in place so references held elsewhere (bot.blacklist) stay valid.
        def fill(target: set, values):
            target.clear()
            target.update(int(v) for v in values or [])

        fill(self.vips, data.get("vips"))
        fill(self.blacklist, data.get("blacklist"))
        fill(self.silenced_users, data.get("silenced_users"))
        fill(self.silenced_channels, data.get("silenced_channels"))
        self.silenced_all = bool(data.get("silenced_all", False))
        self.orders = [str(o)[:MAX_ORDER_LEN] for o in (data.get("orders") or [])][:MAX_ORDERS]

    def _load_local(self):
        try:
            self._apply(json.loads(FILE.read_text()))
        except (OSError, ValueError, TypeError):
            pass
        legacy = Path("data/blacklist.json")  # older versions kept the blacklist here
        if not self.blacklist and legacy.exists():
            try:
                self.blacklist.update(int(x) for x in json.loads(legacy.read_text()))
            except (OSError, ValueError, TypeError):
                pass

    # -- saving ---------------------------------------------------------------------
    def save(self):
        """Write locally right away and queue a Discord backup."""
        try:
            FILE.parent.mkdir(parents=True, exist_ok=True)
            FILE.write_text(json.dumps(self.to_dict(), indent=1))
        except OSError:
            log.warning("Could not write %s", FILE)
        if self._bot and config.STORE_CHANNEL_ID:
            self._push_pending = True
            self._bot.loop.create_task(self._push())

    def _channel(self):
        return self._bot.get_channel(config.STORE_CHANNEL_ID) if self._bot else None

    async def _push(self):
        async with self._push_lock:
            if not self._push_pending:  # an earlier task already pushed the latest state
                return
            self._push_pending = False
            channel = self._channel()
            if channel is None:
                return
            payload = json.dumps(self.to_dict(), indent=1).encode()
            try:
                new = await channel.send(
                    "State backup. Do not delete the newest one.",
                    file=discord.File(io.BytesIO(payload), filename=BACKUP_NAME),
                )
                old_id, self._backup_msg_id = self._backup_msg_id, new.id
                if old_id:
                    try:
                        await channel.get_partial_message(old_id).delete()
                    except discord.HTTPException:
                        pass
            except discord.HTTPException:
                log.warning("Could not back up state to channel %s", config.STORE_CHANNEL_ID)

    # -- restore on startup ---------------------------------------------------------
    async def attach(self, bot):
        """Bind to the bot and restore the newest Discord backup (if configured)."""
        self._bot = bot
        if not config.STORE_CHANNEL_ID:
            log.warning("STORE_CHANNEL_ID not set: memory resets whenever Render restarts the bot.")
            return
        channel = bot.get_channel(config.STORE_CHANNEL_ID)
        if channel is None:
            log.warning("STORE_CHANNEL_ID %s not found or not visible to the bot.", config.STORE_CHANNEL_ID)
            return
        try:
            async for msg in channel.history(limit=50):
                if msg.author.id != bot.user.id:
                    continue
                att = next((a for a in msg.attachments if a.filename == BACKUP_NAME), None)
                if att is None:
                    continue
                self._apply(json.loads(await att.read()))
                self._backup_msg_id = msg.id
                log.info("Restored state from Discord backup: %d VIPs, %d orders, %d blacklisted.",
                         len(self.vips), len(self.orders), len(self.blacklist))
                FILE.parent.mkdir(parents=True, exist_ok=True)
                FILE.write_text(json.dumps(self.to_dict(), indent=1))
                return
            log.info("No state backup found in the store channel yet; creating one.")
            self.save()
        except (discord.HTTPException, ValueError, TypeError):
            log.warning("Could not restore state from the store channel.", exc_info=True)
