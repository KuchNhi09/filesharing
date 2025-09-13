import os
import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # Private channel ID (-100 से शुरू)
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)

# Bot client
app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ✅ Function: Shareable link generator
def generate_share_link(bot_username, message_id: int):
    encoded = base64.urlsafe_b64encode(str(message_id).encode()).decode()
    return f"https://t.me/{bot_username}?start={encoded}"

# ✅ Start command handler
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            f"Hello {message.from_user.first_name} ✨\n\n"
            "I am a **permanent file store bot** 📂\n\n"
            "You can only access files via my **special sharable links** 🔗.\n\n"
            "Click the **Help** button to know more 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📖 Help", callback_data="help")]]
            ),
        )
    else:
        try:
            # base64 decode
            payload = base64.urlsafe_b64decode(message.command[1].encode()).decode()
            await send_stored_file(client, message, payload)
        except Exception:
            await message.reply_text("❌ Invalid or expired link!")

# ✅ Help button callback
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "help":
        await callback_query.message.reply_text(
            "📖 **How to use me?**\n\n"
            "1. Get sharable links from channels.\n"
            "2. I will send you the requested file directly 📂.\n"
            f"3. Files auto-delete after {AUTO_DELETE_MINUTES} minutes ⏳."
        )
    elif callback_query.data.startswith("getfile_"):
        payload = callback_query.data.split("_", 1)[1]
        await send_stored_file(client, callback_query.message, payload)

# ✅ Function: Send stored file
async def send_stored_file(client, message, payload):
    try:
        msg_id = int(payload)
        sent = await client.copy_message(
            message.chat.id,
            FILE_CHANNEL,
            msg_id
        )

        await message.reply_text(
            f"⚠️ **Note:**\n\n"
            f"All files will auto-delete after {AUTO_DELETE_MINUTES} minutes.\n"
            "Please **save or forward** them now!"
        )

        # schedule delete with notify
        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, payload, message.chat.id))

    except Exception as e:
        await message.reply_text(f"❌ File not found or expired!\n\nDebug: {e}")

# ✅ Auto delete function + notify user
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
        await app.send_message(
            user_id,
            "⏳ Your file has been **auto-deleted**!\n\n"
            "Click below button to get it again 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again!", callback_data=f"getfile_{payload}")]]
            )
        )
    except:
        pass

if __name__ == "__main__":
    app.run()
