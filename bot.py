import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- CONFIG ----------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))   # channel id (-100 से शुरू)
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)

ADMINS = {8324187938, 603360648}  # तुम और तुम्हारी दूसरी ID
USERS = set()
# ----------------------------------------

app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ----------- Start Command -----------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    USERS.add(message.from_user.id)

    if len(message.command) > 1:
        code = message.command[1]
        try:
            msg_id = int(code)
            file = await client.get_messages(FILE_CHANNEL, msg_id)
            sent = await file.copy(message.chat.id)
            if AUTO_DELETE_MINUTES > 0:
                await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
                await sent.delete()
        except Exception as e:
            await message.reply(f"❌ File not found!\n\nDebug: {e}")
    else:
        if message.from_user.id in ADMINS:
            await message.reply("👋 Welcome Admin!\nUse /panel to manage settings.")
        else:
            await message.reply(
                f"Hello {message.from_user.first_name} ✨\n\n"
                "Send me any file and I’ll give you a sharable link 📂\n\n"
                "Users can access stored messages by clicking those links.\n\n"
                "To know more, click the Help button 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📖 Help", callback_data="help")]]
                ),
            )

# ----------- Help Button -----------
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "help":
        await callback_query.message.reply_text(
            "📖 **Help & Feedback**\n\n"
            "Got any request or feedback?\n"
            "👉 Just type your message here and I’ll deliver it to the admin!"
        )
    elif callback_query.data.startswith("getfile_"):
        payload = callback_query.data.split("_", 1)[1]
        await send_stored_file(client, callback_query.message, payload)

# ----------- Send File Function -----------
async def send_stored_file(client, message, payload):
    try:
        msg_id = int(payload)
        sent = await client.copy_message(
            message.chat.id,
            FILE_CHANNEL,
            msg_id
        )

        await message.reply_text(
            f"⚠️ **Important:**\n\n"
            f"All messages will be deleted after {AUTO_DELETE_MINUTES} minutes.\n"
            "Please **save or forward** them to your personal Saved Messages!"
        )

        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, payload, message.chat.id))

    except Exception as e:
        await message.reply_text(f"❌ File not found!\n\nDebug: {e}")

# ----------- Auto Delete + Notify -----------
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)

        await app.send_message(
            user_id,
            "ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\n"
            "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again!", callback_data=f"getfile_{payload}")]]
            )
        )

    except:
        pass

if __name__ == "__main__":
    app.run()
