import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_1 = os.getenv("CHANNEL_1")   # -100 से शुरू होने वाला ID या @username
CHANNEL_2 = os.getenv("CHANNEL_2")   # -100 से शुरू होने वाला ID या @username
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # जिस channel में files पड़ी हैं (-100 से शुरू)

AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)

# Bot client
app = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# 🔹 Helper: check channel join
async def is_user_joined(client, user_id, channel):
    try:
        member = await client.get_chat_member(channel, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False


# 🔹 Start command
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id

    # अगर सिर्फ /start भेजा
    if len(message.command) == 1:
        await message.reply_text(
            "👋 Hello!\n\n"
            "मैं सिर्फ **sharable links** से files देता हूँ।\n"
            "कृपया किसी channel post के बटन पर क्लिक करके आएं।"
        )
        return

    # Payload निकाला (message id)
    payload = message.command[1]

    # पहले check करो channel join
    joined1 = await is_user_joined(client, user_id, CHANNEL_1)
    joined2 = await is_user_joined(client, user_id, CHANNEL_2)

    if not joined1 or not joined2:
        # कौन सा बाकी है ये दिखाओ
        buttons = []
        if not joined1:
            buttons.append([InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1.strip('@')}")])
        if not joined2:
            buttons.append([InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2.strip('@')}")])
        buttons.append([InlineKeyboardButton("✅ Try Again", callback_data=f"retry_{payload}")])

        await message.reply_text(
            "⚠️ पहले हमारे दोनों channels join करें, तभी file मिलेगी।",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # अगर joined है दोनों → file भेजो
    await send_stored_file(client, message.chat.id, payload)


# 🔹 Callback handler (Try Again)
@app.on_callback_query()
async def callback_handler(client, query):
    data = query.data

    if data.startswith("retry_"):
        payload = data.split("_", 1)[1]
        user_id = query.from_user.id

        joined1 = await is_user_joined(client, user_id, CHANNEL_1)
        joined2 = await is_user_joined(client, user_id, CHANNEL_2)

        if joined1 and joined2:
            await query.message.delete()
            await send_stored_file(client, user_id, payload)
        else:
            await query.answer("❌ अभी भी सभी channels join नहीं किए!", show_alert=True)


# 🔹 Function: send file
async def send_stored_file(client, user_id, payload):
    try:
        msg_id = int(payload)

        sent = await client.copy_message(
            user_id,
            FILE_CHANNEL,
            msg_id
        )

        await client.send_message(
            user_id,
            f"⚠️ **Important:**\n\n"
            f"ये file {AUTO_DELETE_MINUTES} मिनट में delete हो जाएगी ⏳.\n"
            "कृपया इसे save/forward कर लें!"
        )

        # schedule delete
        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, payload, user_id))

    except Exception as e:
        await client.send_message(user_id, f"❌ File not found or expired!\n\nDebug: {e}")


# 🔹 Delete + notify
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)

        # Notify user
        await app.send_message(
            user_id,
            "🗑 ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ᴅᴇʟᴇᴛᴇᴅ !!\n\n"
            "🔁 नीचे बटन से file फिर से पा सकते हो 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Get File Again 🔁", callback_data=f"retry_{payload}")]]
            )
        )
    except:
        pass


if __name__ == "__main__":
    app.run()
