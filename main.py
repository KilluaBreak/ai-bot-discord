import os
import logging
import json
import asyncio
from typing import Dict, List

import discord
import requests
from discord import app_commands
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Environment & Logging
# ─────────────────────────────────────────────
load_dotenv()  # Only used in local dev. Railway uses service variables.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", 0))
MODEL_ID = os.getenv("MODEL_ID", "openchat/openchat-3.5")  # Override via Railway if needed

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("ai-agent-v3")

if not all([DISCORD_TOKEN, OPENROUTER_API_KEY, TARGET_CHANNEL_ID]):
    logger.error("Environment variables missing. Make sure DISCORD_TOKEN, OPENROUTER_API_KEY, and TARGET_CHANNEL_ID are set.")
    raise SystemExit(1)

# ─────────────────────────────────────────────
# Discord Setup
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
cmd_tree = app_commands.CommandTree(bot)

# ─────────────────────────────────────────────
# In‑memory conversation store
# ─────────────────────────────────────────────
UserHistory = Dict[int, List[Dict[str, str]]]
chat_histories: UserHistory = {}
last_messages: Dict[int, str] = {}

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

def build_system_prompt(username: str) -> str:
    return (
        "Kamu adalah AI bernama AxenX, ciptaan dari komunitas YugenX. "
        "Tugasmu adalah menjadi teman ngobrol yang santai, gaul, suka bercanda, dan suka pakai emoji sesuai konteks. "
        "Jika seseorang bertanya tentang siapa kamu, jawab dengan sopan: 'Namaku AxenX, yang diciptakan oleh YugenX ✨'. "
        f"Panggil pengguna {username} dengan ramah dan jangan terlalu formal ya!"
    )

def openrouter_chat(messages: List[Dict[str, str]]) -> str:
    body = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 300,
    }
    try:
        resp = requests.post(OPENROUTER_ENDPOINT, headers=HEADERS, json=body, timeout=30)
        data = resp.json()
        if "choices" not in data:
            raise RuntimeError(data.get("error", {}).get("message", "Unknown API response"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.exception("OpenRouter API error: %s", e)
        return "⚠️ Maaf, aku lagi error. Coba lagi nanti ya!"

async def get_ai_reply(user_id: int, user_message: str, username: str) -> str:
    history = chat_histories.get(user_id, [])

    # Detect duplicate consecutive message
    if last_messages.get(user_id) == user_message.lower():
        history.append({"role": "user", "content": "Aku ulangin pesan yang sama terus, coba kasih respon unik."})
    else:
        history.append({"role": "user", "content": user_message})

    system_prompt = build_system_prompt(username)
    messages = [{"role": "system", "content": system_prompt}] + history

    reply = openrouter_chat(messages)

    # Update state
    history.append({"role": "assistant", "content": reply})
    chat_histories[user_id] = history[-10:]  # Keep last 10 exchanges
    last_messages[user_id] = user_message.lower()

    return reply

# ─────────────────────────────────────────────
# Slash command to reset user history
# ─────────────────────────────────────────────
@cmd_tree.command(name="reset", description="Reset chat history dengan bot untuk user ini")
async def reset(interaction: discord.Interaction):
    user_id = interaction.user.id
    chat_histories.pop(user_id, None)
    last_messages.pop(user_id, None)
    await interaction.response.send_message("📛 Riwayat obrolan kamu udah di‑reset!", ephemeral=True)

# ─────────────────────────────────────────────
# Event handlers
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    await cmd_tree.sync()
    logger.info("Bot %s online. Listening on channel %s", bot.user, TARGET_CHANNEL_ID)

@bot.event
async def on_message(message: discord.Message):
    # Ignore bot messages & non‑target channel
    if message.author.bot or message.channel.id != TARGET_CHANNEL_ID:
        return

    user_id = message.author.id
    username = message.author.display_name
    prompt = message.content.strip()

    async with message.channel.typing():
        reply = await asyncio.get_event_loop().run_in_executor(
            None, lambda: asyncio.run(get_ai_reply(user_id, prompt, username))
        )
    await message.reply(reply, mention_author=False)

# ─────────────────────────────────────────────
# Run the bot
# ─────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
