import os
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- CONFIG ----------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMINS = [8324187938, 603360648]  # 👈 तुम्हारे admin IDs
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # -100 से शुरू होने वाला channel id

# Default settings (Panel से बदले जा सकते हैं)
AUTO_DELETE_MINUTES = 15
THANK_YOU_MSG = "✅ Thank you for using our bot! Share our channel with friends 🎉"
FORCE_CHANNELS = []  # यहां channel IDs की list रहेगी

# ---------------- CLIENT ----------------
app = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Users data
users_db = {}
today_users = set()


# ---------------- HELPERS ----------------
def is_admin(user_id):
    return user_id in ADMINS


def user_stats():
    return {
        "total": len(users_db),
        "today": len(today_users),
        "active": sum(1 for u in users_db.values() if datetime.now() - u < timedelta(days=7))
    }


async def check_force_join(user_id):
    """Check if user joined all required channels"""
    if not FORCE_CHANNELS:
        return True, []
    not_joined = []
    for ch in FORCE_CHANNELS:
        try:
            member = await app.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return (len(not_joined) == 0), not_joined


# ---------------- HANDLERS ----------------
@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    users_db[user_id] = datetime.now()
    today_users.add(user_id)

    if len(message.command) == 1:
        # Normal start
        if is_admin(user_id):
            await message.reply_text(
                "👋 Welcome Admin!\nUse /panel to manage the bot.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Open Panel", callback_data="open_panel")]])
            )
        else:
            await message.reply_text(
                f"Hello {message.from_user.first_name} ✨\n\n"
                "Send me any sharable link and I’ll give you the file 📂\n\n"
                "To know more, click below 👇",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("📖 Help", callback_data="help")],
                        [InlineKeyboardButton("📩 Request/Feedback", callback_data="request")]
                    ]
                )
            )
    else:
        # Start with payload (sharable link)
        payload = message.command[1]
        await send_stored_file(client, message, payload)


@app.on_callback_query()
async def callback_handler(client, cq):
    user_id = cq.from_user.id

    if cq.data == "help":
        await cq.message.reply_text(
            "📖 **How to use me?**\n\n"
            "• Files are only available through sharable links.\n"
            f"• Files auto-delete after {AUTO_DELETE_MINUTES} minutes ⏳.\n"
            "• Save/forward them immediately!"
        )

    elif cq.data == "request":
        await cq.message.reply_text("✍️ Please type your request. It will be forwarded to admin.")

    elif cq.data == "open_panel" and is_admin(user_id):
        await show_admin_panel(cq.message)

    elif cq.data.startswith("genlink_") and is_admin(user_id):
        msg_id = cq.data.split("_", 1)[1]
        link = f"https://t.me/{(await app.get_me()).username}?start={msg_id}"
        await cq.message.reply_text(f"✅ Sharable Link Generated:\n{link}")

    elif cq.data == "view_stats" and is_admin(user_id):
        stats = user_stats()
        await cq.message.reply_text(
            f"📊 **Bot Stats**:\n\n"
            f"👥 Total Users: {stats['total']}\n"
            f"📅 Today: {stats['today']}\n"
            f"🔥 Active (7d): {stats['active']}"
        )

    elif cq.data.startswith("set_timer_") and is_admin(user_id):
        global AUTO_DELETE_MINUTES
        AUTO_DELETE_MINUTES = int(cq.data.split("_", 2)[2])
        await cq.message.reply_text(f"⏳ Auto-delete timer updated: {AUTO_DELETE_MINUTES} minutes")

    elif cq.data == "view_settings" and is_admin(user_id):
        await cq.message.reply_text(
            f"⚙️ **Current Settings**:\n\n"
            f"⏳ Auto-delete: {AUTO_DELETE_MINUTES} min\n"
            f"🙏 Thank you msg: {THANK_YOU_MSG}\n"
            f"📌 Force Channels: {FORCE_CHANNELS or 'None'}"
        )


# ---------------- FILE HANDLING ----------------
async def send_stored_file(client, message, payload):
    user_id = message.from_user.id
    ok, not_joined = await check_force_join(user_id)
    if not ok:
        buttons = [[InlineKeyboardButton(f"Join Channel", url=f"https://t.me/c/{str(ch)[4:]}")] for ch in not_joined]
        buttons.append([InlineKeyboardButton("✅ Try Again", callback_data=f"retry_{payload}")])
        await message.reply_text(
            "⚠️ You must join all channels to access files!",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    try:
        msg_id = int(payload)
        sent = await client.copy_message(message.chat.id, FILE_CHANNEL, msg_id)
        await message.reply_text(
            f"⚠️ File will be auto-deleted after {AUTO_DELETE_MINUTES} minutes. Save it now!"
        )
        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, payload, user_id))
    except Exception as e:
        await message.reply_text(f"❌ File not found!\n\nDebug: {e}")


async def delete_after(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
        await app.send_message(user_id, THANK_YOU_MSG)
    except:
        pass


# ---------------- ADMIN PANEL ----------------
async def show_admin_panel(msg):
    buttons = [
        [InlineKeyboardButton("🔗 Generate Link", callback_data="genlink_1")],
        [InlineKeyboardButton("📊 View Stats", callback_data="view_stats")],
        [
            InlineKeyboardButton("⏳ Timer 1m", callback_data="set_timer_1"),
            InlineKeyboardButton("⏳ Timer 15m", callback_data="set_timer_15"),
            InlineKeyboardButton("⏳ Timer 60m", callback_data="set_timer_60"),
        ],
        [InlineKeyboardButton("⚙️ View Current Settings", callback_data="view_settings")]
    ]
    await msg.reply_text("⚙️ **Admin Panel**", reply_markup=InlineKeyboardMarkup(buttons))


# ---------------- REQUEST HANDLING ----------------
@app.on_message(filters.private & ~filters.command("start"))
async def handle_requests(client, message):
    user_id = message.from_user.id
    if message.reply_to_message and "Please type your request" in message.reply_to_message.text:
        for admin in ADMINS:
            try:
                await client.send_message(admin, f"📩 New request from {user_id}:\n\n{message.text}")
            except:
                pass
        await message.reply_text("✅ Your request has been sent to admins.")
    elif not is_admin(user_id):
        await message.reply_text("⚠️ Files are only available via sharable links!")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
