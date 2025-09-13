import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== Config from env ======
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID") or 0)  # optional, used by /test
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None

DATA_FILE = "MOVIES.json"   # stores code -> file_id

# ====== Helpers to load/save ======
def load_movies():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_movies(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

MOVIES = load_movies()
PENDING = {}  # user_id -> file_id (waiting for code)

# ====== Client ======
app = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ====== Test command (keeps same behavior) ======
@app.on_message(filters.private & filters.command("test"))
async def test_cmd(client, message):
    if CHANNEL_ID == 0:
        await message.reply_text("⚠️ CHANNEL_ID env variable not set.")
        return
    try:
        chat = await client.get_chat(CHANNEL_ID)
        await message.reply_text(
            f"✅ Bot को channel access है!\n\n📌 Channel Title: {chat.title}\n🆔 Channel ID: `{chat.id}`"
        )
    except Exception as e:
        await message.reply_text(f"❌ Bot channel तक पहुँच नहीं पा रहा:\n\n`{e}`")

# ====== Start handler (deep-link support) ======
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    if len(message.command) == 1:
        await message.reply_text(
            f"Hello {message.from_user.first_name} ✨\n\n"
            "I am a **permanent file store bot** 📂\n\n"
            "Send me any file and I'll save it with a custom code.\n"
            "Or click a deep-link from channel to get files.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📖 Help", callback_data="help")]])
        )
        return

    payload = message.command[1]
    if payload in MOVIES:
        await send_stored_file(client, message, payload, MOVIES[payload])
    else:
        await message.reply_text("❌ File not found ya invalid link!")

# ====== Callback handler (help + getfile) ======
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data or ""
    if data == "help":
        await callback_query.message.reply_text(
            "📖 How to use:\n\n"
            "1. Send me a file (photo/video/document) in private chat.\n"
            "2. I'll ask for a unique code (e.g. ep2_720) and give you a deep-link.\n"
            "3. Put that link in your channel button: https://t.me/YourBot?start=ep2_720\n"
            f"Files auto-delete after {AUTO_DELETE_MINUTES} minutes."
        )
    elif data.startswith("getfile_"):
        payload = data.split("_", 1)[1]
        if payload in MOVIES:
            await send_stored_file(client, callback_query.message, payload, MOVIES[payload])
        else:
            await callback_query.message.reply_text("❌ File not found or expired.")

# ====== Receive file & ask for code ======
@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_file_handler(client, message):
    # optional: restrict who can save files
    if OWNER_ID and message.from_user.id != OWNER_ID:
        await message.reply_text("❌ You are not allowed to add files to this bot.")
        return

    # get file_id (handle photo specially)
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.audio:
        file_id = message.audio.file_id
    else:
        await message.reply_text("Unsupported file type.")
        return

    user_id = message.from_user.id
    PENDING[user_id] = file_id

    # Ask for code
    await message.reply_text(
        "✅ File received!\n\nSend me a unique code to save this file (e.g. `ep2_720`).\n"
        "Or send /cancel to abort. (Timeout 120s)"
    )

    # start timeout to clear pending
    async def pending_timeout(uid, timeout=120):
        await asyncio.sleep(timeout)
        if uid in PENDING:
            PENDING.pop(uid, None)
            try:
                await app.send_message(uid, "⌛ Time out — please send the file again if you still want to save it.")
            except:
                pass

    asyncio.create_task(pending_timeout(user_id, 120))

# ====== Handler to receive the code text ======
@app.on_message(filters.private & filters.text & ~filters.command)
async def receive_code_handler(client, message):
    user_id = message.from_user.id
    if user_id not in PENDING:
        # not waiting for code
        return

    code = message.text.strip()
    if not code:
        await message.reply_text("⚠️ Empty code. Send a valid code like `ep2_720`.")
        return

    if code in MOVIES:
        await message.reply_text("⚠️ Ye code already exist karta hai. Choose a different code.")
        return

    # save mapping
    file_id = PENDING.pop(user_id)
    MOVIES[code] = file_id
    save_movies(MOVIES)

    username = (await client.get_me()).username
    deep_link = f"https://t.me/{username}?start={code}"

    await message.reply_text(f"✅ File saved with code `{code}`\n\n🔗 Deep Link:\n{deep_link}")

# ====== Cancel (optional) ======
@app.on_message(filters.private & filters.command("cancel"))
async def cancel_save(client, message):
    uid = message.from_user.id
    if uid in PENDING:
        PENDING.pop(uid, None)
        await message.reply_text("✅ Saved process cancelled.")
    else:
        await message.reply_text("Nothing to cancel.")

# ====== Send stored file (unified, works for any media type) ======
async def send_stored_file(client, message, payload, file_id):
    try:
        # reply_cached_media will send correct media type based on file_id
        sent = await message.reply_cached_media(file_id)

        await message.reply_text(
            f"⚠️ Important:\nFiles will be auto-deleted after {AUTO_DELETE_MINUTES} minutes.\n"
            "Save or forward them to your Saved Messages!"
        )

        asyncio.create_task(delete_after(sent.chat.id, sent.id, payload, message.chat.id))
    except Exception as e:
        await message.reply_text(f"❌ Error sending file:\n`{e}`")

# ====== Auto delete + notify ======
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 30)
    try:
        await app.delete_messages(chat_id, msg_id)
        await app.send_message(
            user_id,
            "🗑️ Your file has been auto-deleted!\n\nClick below to get it again:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again", callback_data=f"getfile_{payload}")]]
            )
        )
    except:
        pass

if __name__ == "__main__":
    app.run()
