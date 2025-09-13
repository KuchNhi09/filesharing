import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # without @
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)

app = Client("file_store_bot", bot_token=BOT_TOKEN)


# Start command handler
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    # अगर user ने सिर्फ /start लिखा
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
        # /start के साथ payload आया (जैसे /start file123)
        payload = message.command[1]
        await send_stored_file(client, message, payload)


# Callback query handler (Help button)
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "help":
        await callback_query.message.reply_text(
            "📖 **How to use me?**\n\n"
            "1. Click on buttons/links from channels.\n"
            "2. I will send you the requested file with a shareable link.\n"
            f"3. Files auto-delete after {AUTO_DELETE_MINUTES} minutes ⏳."
        )


# Function: Send stored file by payload
async def send_stored_file(client, message, payload):
    try:
        # payload = channel message_id मान लो
        msg_id = int(payload)
        # channel से copy करो
        sent = await client.copy_message(message.chat.id, f"@{CHANNEL_USERNAME}", msg_id)

        # नीचे warning msg
        await message.reply_text(
            f"⚠️ **Important:**\n\n"
            f"All messages will be deleted after {AUTO_DELETE_MINUTES} minutes.\n"
            "Please **save or forward** them to your personal Saved Messages!"
        )

        # schedule delete
        asyncio.create_task(delete_after(sent.chat.id, sent.message_id))

    except Exception as e:
        await message.reply_text("❌ File not found or expired!")


async def delete_after(chat_id, msg_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
    except:
        pass


if __name__ == "__main__":
    app.run()
