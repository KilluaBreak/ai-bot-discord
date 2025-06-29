import discord
import os
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

chat_histories = {}
last_messages = {}

async def get_response(user_id, user_message, username):
    history = chat_histories.get(user_id, [])

    # Deteksi pesan yang diulang
    if last_messages.get(user_id) == user_message.lower():
        history.append({"role": "user", "content": "Aku ulangin pesan yang sama terus, coba kasih respon unik."})
    else:
        history.append({"role": "user", "content": user_message})

    system_prompt = f"""
Kamu adalah bot Discord dengan gaya santai, gaul, dan lucu. Kamu suka jawab dengan cara yang asik dan kayak ngobrol sama temen. Nama user: {username}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "openchat/openchat-3.5",  # gratis dan bagus
        "messages": [{"role": "system", "content": system_prompt}] + history,
        "temperature": 0.85,
        "max_tokens": 300
    }

    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
        data = res.json()

        if 'choices' in data:
            reply = data['choices'][0]['message']['content'].strip()
            history.append({"role": "assistant", "content": reply})
            chat_histories[user_id] = history[-10:]
            last_messages[user_id] = user_message.lower()
            return reply
        else:
            return f"⚠️ Error dari API: {data.get('error', {}).get('message', 'Gagal menerima respon')}"

    except Exception as e:
        return f"⚠️ Error: {str(e)}"

@client.event
async def on_ready():
    print(f"✅ Bot {client.user} sudah online dan siap ngobrol!")

@client.event
async def on_message(message):
    if message.author.bot or message.channel.id != TARGET_CHANNEL_ID:
        return

    user_id = message.author.id
    username = message.author.display_name
    prompt = message.content

    await message.channel.typing()
    response = await get_response(user_id, prompt, username)
    await message.reply(response)

client.run(DISCORD_TOKEN)
