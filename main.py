import discord
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
load_dotenv()

# API keys
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

# Setup OpenAI client (versi terbaru)
client_ai = OpenAI(api_key=OPENAI_API_KEY)

# Setup Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Riwayat chat & pesan terakhir per user
chat_histories = {}
last_messages = {}

async def get_gpt_response(user_id, user_message, username):
    history = chat_histories.get(user_id, [])

    # Deteksi pesan berulang
    if last_messages.get(user_id) == user_message.lower():
        history.append({"role": "user", "content": "Aku ulangin pesan yang sama terus, coba kasih respon unik."})
    else:
        history.append({"role": "user", "content": user_message})

    system_prompt = f"""
Kamu adalah chatbot Discord dengan gaya santai dan gaul.
Gunakan bahasa sehari-hari, hangat, suka becanda, dan sok akrab.
Anggap user sebagai teman ngobrol. Nama user: {username}
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
    print(f"✅ Bot {client.user} aktif dan siap ngobrol!")

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
