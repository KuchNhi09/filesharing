import os
import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Env vars
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # -100 से शुरू वाला channel id
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)

# Bot client
app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# Encode/Decode helpers
def encode_id(msg_id: int) -> str:
    return base64.urlsafe_b64encode(str(msg_id).encode()).decode()

def decode_id(payload: str) -> int:
    return int(base64.urlsafe_b64decode(payload.encode()).decode())


# /start handler
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            f"Hello {message.from_user.first_name} ✨\n\n"
            "Send me any file and I’ll give you a sharable link 📂\n\n"
            "Users can access stored messages by clicking those links.\n\n"
            "To know more, click the **Help** button 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📖 Help", callback_data="help")]]
            ),
        )
    else:
        try:
            payload = message.command[1]
            msg_id = decode_id(payload)
            await send_stored_file(client, message, msg_id)
        except Exception as e:
            await message.reply_text("❌ Invalid or expired link!")


# Help button
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "help":
        await callback_query.message.reply_text(
            "📖 **How to use me?**\n\n"
            "1. Send me any file.\n"
            "2. I’ll give you a sharable link.\n"
            f"3. Files auto-delete after {AUTO_DELETE_MINUTES} minutes ⏳."
        )
    elif callback_query.data.startswith("getfile_"):
        payload = callback_query.data.split("_", 1)[1]
        msg_id = decode_id(payload)
        await send_stored_file(client, callback_query.message, msg_id)


# Handle file upload by admin
@app.on_message(filters.private & (filters.document | filters.video | filters.photo | filters.audio))
async def handle_file(client, message):
    try:
        # save to file channel
        sent = await client.copy_message(
            FILE_CHANNEL,
            message.chat.id,
            message.id
        )

        # generate sharable link
        encoded = encode_id(sent.id)
        bot_username = (await client.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={encoded}"

        await message.reply_text(
            f"✅ File stored!\n\n"
            f"🔗 **Sharable Link:**\n{share_link}\n\n"
            f"⚠️ File will auto-delete after {AUTO_DELETE_MINUTES} minutes.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("➡️ Open Link", url=share_link)]]
            ),
        )

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# Send stored file by id
async def send_stored_file(client, message, msg_id: int):
    try:
        sent = await client.copy_message(message.chat.id, FILE_CHANNEL, msg_id)

        await message.reply_text(
            f"⚠️ **Important:**\n\n"
            f"All messages will be deleted after {AUTO_DELETE_MINUTES} minutes.\n"
            "Please **save or forward** them to your personal Saved Messages!"
        )

        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, msg_id, message.chat.id))

    except Exception as e:
        await message.reply_text("❌ File not found or expired!")


# Auto delete + notify
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
        await app.send_message(
            user_id,
            "ʏᴏᴜʀ ꜰɪʟᴇ ᴡᴀꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\n"
            "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪᴛ ᴀɢᴀɪɴ 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again!", callback_data=f"getfile_{encode_id(payload)}")]]
            )
        )
    except:
        pass


if __name__ == "__main__":
    app.run()
