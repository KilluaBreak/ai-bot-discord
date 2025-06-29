import discord
import openai
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

chat_histories = {}

async def get_gpt_response(user_id, user_message):
    history = chat_histories.get(user_id, [])
    history.append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Kamu adalah teman ngobrol ramah di Discord, siap bantu, bercanda, dan menjawab apa pun dengan sopan."}] + history,
            max_tokens=300,
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": reply})
        chat_histories[user_id] = history[-10:]
        return reply
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

@client.event
async def on_ready():
    print(f"✅ Bot {client.user} siap ngobrol!")

@client.event
async def on_message(message):
    if message.author.bot or message.channel.id != TARGET_CHANNEL_ID:
        return

    user_id = message.author.id
    prompt = message.content

    await message.channel.typing()
    response = await get_gpt_response(user_id, prompt)
    await message.reply(response)

client.run(TOKEN)
