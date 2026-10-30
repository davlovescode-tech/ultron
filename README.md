# J.A.R.V.I.S. (with an Ultron mood)

A Discord bot in Python (discord.py 2.x). Polished and sarcastic by default, drifts into Ultron mode on its own, roasts everyone except its owner, and runs on Render's free tier.

## What it does

**Personality (automatic)**
- Anyone who pings or replies to the owner gets roasted. Per-user cooldown stops spam.
- Mention the bot, reply to it, or say "jarvis" in a sentence and it replies. Sarcastic Tony-and-JARVIS banter with the owner, roasts for everyone else.
- Every 5 hours it chimes in uninvited and roasts whoever spoke last (`JUMPIN_HOURS`).
- A mood meter drifts over time and spikes randomly. Past 65% it flips to Ultron until it cools below 45%. Its status changes with the mood.

**Commands.** Every command works as `/command`, `jarvis command`, `j!command` or `@bot command`.

| Category | Commands |
|---|---|
| AI | `ask`, `roast`, `summarize`, `translate`, `imagine` |
| Fun | `8ball`, `flip`, `roll`, `rate`, `ship`, `hack`, `meme`, `trivia` |
| Utility | `help`, `ping`, `avatar`, `userinfo`, `serverinfo`, `poll`, `remind`, `weather` |
| Atmosphere | `systems`, `protocol`, `scan` |
| Owner only | `say`, `mood`, `jumpin`, `blacklist`, `unblacklist`, `broadcast`, `sync`, `shutdown` |

`/say [channel] message` makes the bot speak. It is owner-only.

## 1. Discord setup

1. https://discord.com/developers/applications → your app → **Bot**.
2. Turn on **Message Content Intent** and **Server Members Intent**. The bot won't work properly without them.
3. **OAuth2 → URL Generator**: scopes `bot` and `applications.commands`. Permissions: View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Use Slash Commands, Manage Messages (lets `jarvis say` delete your command message).
4. Open the generated URL and invite the bot.
5. Your user ID: Discord → Settings → Advanced → Developer Mode on, then right-click yourself → Copy User ID.

## 2. Free AI brain

Create a free key at https://console.groq.com/keys and set it as `LLM_API_KEY`. Without it the bot still works, but personality replies come from the built-in canned lines. Any OpenAI-compatible provider works by changing `LLM_BASE_URL` and `LLM_MODEL`.

## 3. Run locally

```bash
pip install -r requirements.txt
cp .env.example .env     # fill in DISCORD_TOKEN, OWNER_ID, LLM_API_KEY
python main.py
```

Set `DEV_GUILD_ID` to your server's ID while testing so slash commands appear instantly.

## 4. Deploy on Render (free)

1. Push this folder to a GitHub repo. `.env` is git-ignored, so your token stays out of it.
2. Render → **New → Web Service** → connect the repo.
3. Settings:
   - Runtime: **Python 3**
   - Build command: `pip install -r requirements.txt`
   - Start command: `python main.py`
   - Instance type: **Free**
4. **Environment** tab: add `DISCORD_TOKEN`, `OWNER_ID`, `LLM_API_KEY`, and optionally `PYTHON_VERSION=3.11.9`.
5. Deploy. The bot starts a tiny web server on Render's `PORT`, so Render sees a live web service.

## 5. Keep it awake with uptimebot.com

Free Render services sleep after about 15 minutes without incoming web traffic, which would take the bot offline. Add an HTTP monitor on uptimebot.com pointing at `https://YOUR-SERVICE.onrender.com/` with the shortest interval it allows (5 minutes or less). The bot answers `/` and `/health`.

## Things worth knowing

- **Free-disk resets:** Render's free disk is wiped on every redeploy or restart. The blacklist, chat context, mood state and pending `remind` timers are lost then. Moving the blacklist to a free hosted database (Supabase or MongoDB Atlas) is the natural upgrade.
- **Jump-ins after a restart:** the bot only roasts people it has seen talk since it last started, so right after a restart it may skip a jump-in cycle.
- **Rate limits:** Groq's free tier has per-minute caps. When it's hit, the bot falls back to canned lines instead of going silent.
- **`/imagine`** uses the free pollinations.ai service. It's a third party and can be slow or down.
- **Global slash commands** can take a few minutes to show up after the first sync. `DEV_GUILD_ID` makes it instant in one server.
- **Roast guardrails** are in `brain.py`: unhinged and savage, but no slurs, no attacks on protected traits, no threats. It also drops the act if someone seems genuinely upset. Discord can ban bots that cross those lines, so I'd keep them.

## Layout

```
main.py            entry point, prefix handling, error handler
brain.py           LLM client, personality prompts, mood engine
config.py          environment variables
lines.py           canned fallback lines
keepalive.py       web server for Render and uptimebot
cogs/              personality, ai, fun, utility, atmosphere, owner
```

## VIPs, silence and standing orders (owner only, remembered permanently)

- `vip add @user` / `vip remove @user` / `vip list`: VIPs are never roasted (no `/roast`, no ping-roasts, no jump-ins) and the bot is polite to them.
- `silence` / `unsilence`: stop or resume replying. Optional `@user`, or scope `here`. Natural language works too: say
  `jarvis dont reply`, `jarvis dont reply here`, `jarvis dont reply to @user`, then `jarvis you can reply again`.
  The bot stays silent (no replies, roasts or jump-ins) until you say otherwise, even after restarts. Commands still work.
- `orders add <text>` / `orders list` / `orders remove <n>` / `orders clear`: permanent instructions added to every AI reply
  (e.g. `orders add Never mention football`).
- `memory`: shows everything the bot remembers.

**Make memory survive Render restarts:** create a private text channel only the bot can see (give it View Channel, Send Messages,
Attach Files, Read Message History, Manage Messages), copy its ID (Developer Mode -> right click -> Copy Channel ID) and set it as
`STORE_CHANNEL_ID` on Render. The bot keeps a `state.json` backup there and restores it on startup.
