"""Central configuration. Everything comes from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _id_set(name: str) -> set:
    return {int(x) for x in os.getenv(name, "").replace(" ", "").split(",") if x.isdigit()}


# --- Discord -----------------------------------------------------------------
TOKEN = os.getenv("DISCORD_TOKEN", "")
OWNER_ID = _int("OWNER_ID")                 # YOUR Discord user ID
OWNER_TITLE = os.getenv("OWNER_TITLE", "sir")
DEV_GUILD_ID = _int("DEV_GUILD_ID")         # optional: instant slash-command sync in one server

# --- LLM (any OpenAI-compatible endpoint; defaults to Groq's free tier) -------
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip().strip("\"\x27")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# --- Behaviour ---------------------------------------------------------------
JUMPIN_HOURS = _float("JUMPIN_HOURS", 5.0)              # random jump-in interval
JUMPIN_CHANNEL_IDS = _id_set("JUMPIN_CHANNEL_IDS")      # optional: restrict jump-ins
BOOT_CHANNEL_ID = _int("BOOT_CHANNEL_ID")               # optional: post a boot sequence here

# --- Hosting -----------------------------------------------------------------
PORT = _int("PORT", 8080)                               # Render injects PORT automatically
