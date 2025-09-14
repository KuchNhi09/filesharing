import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= ENV VARIABLES =========
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # -100 से शुरू होने वाला Channel ID
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 15)

# ========= ADMINS =========
ADMINS = [8324187938, 603360648]

# ========= BOT INIT =========
app = Client(
    "file_store_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ========= STORAGE =========
users_db = set()
files_db = {}
waiting_for_file = {}  # track कौन admin अभी file bhejne wala hai

# ========= START HANDLER =========
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    users_db.add(message.from_user.id)

    if len(message.command) == 1:
        # Normal start (Welcome msg)
        if message.from_user.id in ADMINS:
            await message.reply_text("👋 Welcome Admin!\nSend /panel to open admin panel.")
        else:
            await message.reply_text(
                f"Hello {message.from_user.first_name} ✨\n\n"
                "Send me any file and I’ll give you a sharable link 📂\n\n"
                "Users can access stored messages by clicking those links.\n\n"
                "To know more, click the Help button 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("📖 Help", callback_data="help"),
                        InlineKeyboardButton("📝 Request/Feedback", callback_data="feedback")
                    ]]
                ),
            )
    else:
        # Payload (Sharable link)
        payload = message.command[1]
        if payload in files_db:
            msg_id = files_db[payload]
            await send_stored_file(client, message, msg_id, payload)
        else:
            await message.reply_text("❌ Invalid or expired sharable link!")

# ========= CALLBACKS =========
@app.on_callback_query()
async def callback_handler(client, cq):
    data = cq.data
    await cq.answer()  # IMPORTANT: respond to button click

    if data == "help":
        await cq.message.reply_text(
            "📖 **How to use me?**\n\n"
            "1. Click on valid sharable links.\n"
            "2. I will send you the requested file.\n"
            f"3. Files auto-delete after {AUTO_DELETE_MINUTES} minutes ⏳."
        )

    elif data == "feedback":
        await cq.message.reply_text(
            "💌 Please type your request/feedback and send it.\n\n(Admins will receive it directly)"
        )

    elif data == "genlink":
        if cq.from_user.id not in ADMINS:
            return
        waiting_for_file[cq.from_user.id] = True
        await cq.message.reply_text("📂 Send me the file from your channel (forward as admin).")

    elif data == "stats":
        if cq.from_user.id not in ADMINS:
            return
        total = len(users_db)
        await cq.message.reply_text(
            f"📊 **Bot Stats:**\n\n"
            f"👥 Total Users: {total}\n"
            f"⏳ Auto Delete: {AUTO_DELETE_MINUTES} min"
        )

    elif data.startswith("getfile_"):
        payload = data.split("_", 1)[1]
        if payload in files_db:
            msg_id = files_db[payload]
            await send_stored_file(client, cq.message, msg_id, payload)

# ========= FEEDBACK HANDLER =========
@app.on_message(filters.private & ~filters.command(["start", "panel"]))
async def feedback_handler(client, message):
    # If admin is sending file for link generation
    if message.from_user.id in ADMINS and message.from_user.id in waiting_for_file:
        if message.forward_from_chat and message.forward_from_chat.id == FILE_CHANNEL:
            msg_id = message.forward_from_message_id
            payload = str(msg_id)
            files_db[payload] = msg_id
            link = f"https://t.me/{client.me.username}?start={payload}"
            await message.reply_text(f"✅ Sharable Link Generated:\n\n{link}")
            waiting_for_file.pop(message.from_user.id, None)
            return

    # Otherwise, it's user feedback
    if message.text and message.from_user.id not in ADMINS:
        for admin in ADMINS:
            try:
                await client.send_message(
                    admin,
                    f"📩 **Feedback from {message.from_user.mention}:**\n\n{message.text}"
                )
            except:
                pass

# ========= FILE SENDER =========
async def send_stored_file(client, message, msg_id, payload):
    try:
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
        await message.reply_text("❌ File not found or expired!")

# ========= AUTO DELETE =========
async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
        await app.send_message(
            user_id,
            "🗑️ Your file has been deleted!\n\nClick below to get it again 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again!", callback_data=f"getfile_{payload}")]]
            )
        )
    except:
        pass

# ========= ADMIN PANEL =========
@app.on_message(filters.private & filters.command("panel"))
async def admin_panel(client, message):
    if message.from_user.id not in ADMINS:
        return
    await message.reply_text(
        "⚙️ **Admin Panel**\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Generate Sharable Link", callback_data="genlink")],
            [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
        ])
    )

# ========= RUN =========
if __name__ == "__main__":
    app.run()
