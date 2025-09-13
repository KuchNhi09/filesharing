import os
from pyrogram import Client

# Environment se values lo
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Yaha apna channel id daalo (private wale ka, -100 ke sath)
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or -1002909767501)

app = Client(
    "test_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

with app:
    try:
        chat = app.get_chat(CHANNEL_ID)
        print(f"✅ Bot is inside channel: {chat.title}")
    except Exception as e:
        print(f"❌ Error: {e}")
