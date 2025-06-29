import discord
import openai
import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simpan riwayat percakapan dan pesan terakhir user
chat_histories = {}
last_messages = {}

async def get_gpt_response(user_id, user_message, username):
    history = chat_histories.get(user_id, [])

    # Deteksi kalau user kirim pesan yang sama berulang
    if last_messages.get(user_id) == user_message.lower():
        history.append({"role": "user", "content": "Aku ulangin pesan yang sama terus, coba kasih respon unik."})
    else:
        history.append({"role": "user", "content": user_message})

    # Tambah karakter santai/gaul
    system_prompt = f"""
Kamu adalah chatbot Discord yang punya kepribadian santai, gaul, dan suka becanda.
Jawaban kamu ramah, akrab, dan pakai bahasa sehari-hari.
Nama user: {username}
"""

try:
    response = client_ai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt}] + history,
        temperature=0.85,
        max_tokens=300
    )
    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})
    chat_histories[user_id] = history[-10:]
    last_messages[user_id] = user_message.lower()
    return reply

except Exception as e:
    return f"⚠️ Error: {str(e)}"

@client.event
async def on_ready():
    print(f"✅ Bot {client.user} siap ngobrol kayak temen!")

@client.event
async def on_message(message):
    if message.author.bot or message.channel.id != TARGET_CHANNEL_ID:
        return

    user_id = message.author.id
    username = message.author.display_name
    prompt = message.content

    await message.channel.typing()
    response = await get_gpt_response(user_id, prompt, username)
    await message.reply(response)

client.run(TOKEN)
