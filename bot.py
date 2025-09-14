import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────
# ENV variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # channel where files are stored
ADMINS = [8324187938, 603360648]  # your admin IDs
# ─────────────────────────────

# runtime settings
FORCE_CHANNELS = []
THANK_YOU_MSG = "🙏 Thanks for using me! Please share our channel with your friends ❤️"
AUTO_DELETE_MINUTES = 15

USERS = set()
WAITING_MODE = {}  # {admin_id: "mode"}
app = Client("main-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ─────────────────────────────
# Helpers
async def is_admin(user_id: int):
    return user_id in ADMINS

async def check_force_join(user_id: int):
    if not FORCE_CHANNELS:
        return True, []
    not_joined = []
    for ch in FORCE_CHANNELS:
        try:
            member = await app.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return len(not_joined) == 0, not_joined


# ─────────────────────────────
# Commands
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    USERS.add(user_id)

    if len(message.command) == 1:
        if await is_admin(user_id):
            await message.reply_text(
                "👋 Welcome Admin!\n\nUse /panel to open the control panel."
            )
        else:
            await message.reply_text(
                f"Hello {message.from_user.first_name} ✨\n\n"
                "Send me any sharable link to get your file 📂\n\n"
                "Only sharable links will work, random /start codes will not."
            )
    else:
        payload = message.command[1]
        await handle_payload(message, payload)


@app.on_message(filters.private & filters.command("panel"))
async def panel_cmd(client, message):
    if not await is_admin(message.from_user.id):
        return
    await message.reply_text(
        "⚙️ **Admin Panel**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Generate Sharable Link", callback_data="genlink")],
            [InlineKeyboardButton("📊 View Stats", callback_data="stats")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ])
    )


# ─────────────────────────────
# Payload handler
async def handle_payload(message, payload):
    user_id = message.from_user.id
    ok, not_joined = await check_force_join(user_id)
    if not ok:
        btns = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.replace('@','')}")] for ch in not_joined]
        btns.append([InlineKeyboardButton("✅ I Joined, Try Again", callback_data=f"retry_{payload}")])
        await message.reply_text("❌ Please join required channels to continue:", reply_markup=InlineKeyboardMarkup(btns))
        return

    try:
        msg_id = int(payload)
        sent = await app.copy_message(user_id, FILE_CHANNEL, msg_id)

        await message.reply_text(
            f"⚠️ Save or forward this file. It will be deleted after {AUTO_DELETE_MINUTES} minutes."
        )

        asyncio.create_task(auto_delete(sent.chat.id, sent.id, payload, user_id))
    except Exception as e:
        await message.reply_text(f"❌ File not found!\n\nDebug: {e}")


# ─────────────────────────────
# Auto delete + Thank you
async def auto_delete(chat_id, msg_id, payload, user_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
        await app.send_message(
            user_id,
            "🗑️ Your file was auto-deleted.\n\n"
            "Click below to get it again 👇",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again", callback_data=f"retry_{payload}")]]
            )
        )
        await app.send_message(user_id, THANK_YOU_MSG)
    except:
        pass


# ─────────────────────────────
# Callbacks
@app.on_callback_query()
async def callbacks(client, cq):
    data = cq.data
    uid = cq.from_user.id

    if data == "stats":
        await cq.message.reply_text(
            f"📊 Stats:\n\nTotal Users: {len(USERS)}\nAdmins: {len(ADMINS)}"
        )

    elif data == "genlink":
        await cq.message.reply_text("📩 Send me the file from file channel.")

    elif data.startswith("retry_"):
        payload = data.split("_", 1)[1]
        await handle_payload(cq.message, payload)

    elif data == "settings":
        if not await is_admin(uid): return
        await cq.message.reply_text(
            "⚙️ Settings Menu",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📌 Manage Force Join Channels", callback_data="forcechannels")],
                [InlineKeyboardButton("🙏 Change Thank You Msg", callback_data="changethanks")],
                [InlineKeyboardButton("⏳ Change Auto Delete Timer", callback_data="changetimer")],
                [InlineKeyboardButton("👁 View Current Settings", callback_data="viewsettings")]
            ])
        )

    elif data == "forcechannels":
        WAITING_MODE[uid] = "force"
        await cq.message.reply_text(
            f"📌 Current Force Channels:\n{FORCE_CHANNELS or 'None'}\n\n"
            "Send @channelusername to add/remove."
        )

    elif data == "changethanks":
        WAITING_MODE[uid] = "thanks"
        await cq.message.reply_text("🙏 Send me the new Thank You message.")

    elif data == "changetimer":
        WAITING_MODE[uid] = "timer"
        await cq.message.reply_text("⏳ Send me new auto delete time (in minutes).")

    elif data == "viewsettings":
        await cq.message.reply_text(
            f"⚙️ Current Settings:\n\nForce Channels: {FORCE_CHANNELS}\n"
            f"Thank You Msg: {THANK_YOU_MSG}\n"
            f"Auto Delete: {AUTO_DELETE_MINUTES} minutes"
        )


# ─────────────────────────────
# Messages listener (for admin settings update)
@app.on_message(filters.private & filters.text)
async def admin_updates(client, message):
    uid = message.from_user.id
    text = message.text.strip()

    if not await is_admin(uid):
        return

    if uid in WAITING_MODE:
        mode = WAITING_MODE.pop(uid)

        if mode == "force":
            if text.startswith("@"):
                if text in FORCE_CHANNELS:
                    FORCE_CHANNELS.remove(text)
                    await message.reply_text(f"❌ Removed {text} from force join list.")
                else:
                    FORCE_CHANNELS.append(text)
                    await message.reply_text(f"✅ Added {text} to force join list.")
            else:
                await message.reply_text("❌ Please send valid @channelusername")

        elif mode == "thanks":
            global THANK_YOU_MSG
            THANK_YOU_MSG = text
            await message.reply_text("✅ Thank You message updated.")

        elif mode == "timer":
            global AUTO_DELETE_MINUTES
            try:
                AUTO_DELETE_MINUTES = int(text)
                await message.reply_text(f"✅ Auto delete timer set to {AUTO_DELETE_MINUTES} minutes.")
            except:
                await message.reply_text("❌ Invalid number.")
        return


# ─────────────────────────────
print("Bot started ✅")
app.run()
