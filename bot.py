import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Example: -1002909767501
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)

# Bot client
app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# ✅ Test command to check channel access
@app.on_message(filters.private & filters.command("test"))
async def test_cmd(client, message):
    try:
        chat = await client.get_chat(CHANNEL_ID)
        await message.reply_text(
            f"✅ Bot को channel access है!\n\n"
            f"📌 Channel Title: {chat.title}\n"
            f"🆔 Channel ID: `{chat.id}`"
        )
    except Exception as e:
        await message.reply_text(f"❌ Bot channel तक पहुँच नहीं पा रहा:\n\n`{e}`")


# Start command handler
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            f"Hello {message.from_user.first_name} ✨\n\n"
            "I am a **permanent file store bot** 📂\n\n"
            "Users can access stored messages by using a **shareable link** given by me.\n\n"
            "To know more, click the **Help** button 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📖 Help", callback_data="help")]]
            ),
        )
    else:
        payload = message.command[1]
        await send_stored_file(client, message, payload)


# Help button callback
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "help":
        await callback_query.message.reply_text(
            "📖 **How to use me?**\n\n"
            "1. Click on buttons/links from channels.\n"
            "2. I will send you the requested file with a shareable link.\n"
            f"3. Files auto-delete after {AUTO_DELETE_MINUTES} minutes ⏳."
        )
    elif callback_query.data.startswith("getfile_"):
        payload = callback_query.data.split("_", 1)[1]
        await send_stored_file(client, callback_query.message, payload)


# Function: Send stored file
async def send_stored_file(client, message, payload):
    try:
        msg_id = int(payload)
        sent = await client.copy_message(
            message.chat.id,
            CHANNEL_ID,
            msg_id
        )

        await message.reply_text(
            f"⚠️ **Important:**\n\n"
            f"All messages will be deleted after {AUTO_DELETE_MINUTES} minutes.\n"
            "Please **save or forward** them to your personal Saved Messages!"
        )

        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, payload, message.chat.id))

    except Exception as e:
        await message.reply_text(f"❌ File not found or expired!\n\nDebug: `{e}`")


# Auto delete function + notify user
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)

        await app.send_message(
            user_id,
            "ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\n"
            "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again!", callback_data=f"getfile_{payload}")]]
            )
        )

    except:
        pass


if __name__ == "__main__":
    app.run()
