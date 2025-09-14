import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== CONFIG ==========
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # jaha files rehti hain

ADMINS = [8324187938, 603360648]  # Admin IDs
FORCE_CHANNELS = []  # panel se add/remove honge
AUTO_DELETE_MINUTES = 60  # default 60 min
# ============================

app = Client("FileShareBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Users memory
USERS = set()

# Utils
def make_keyboard():
    btns = []
    for ch in FORCE_CHANNELS:
        btns.append([InlineKeyboardButton(f"Join Channel", url=f"https://t.me/{ch}")])
    btns.append([InlineKeyboardButton("🔄 Try Again", callback_data="checksub")])
    return InlineKeyboardMarkup(btns)

async def check_sub(client, user_id):
    if not FORCE_CHANNELS:
        return True
    for ch in FORCE_CHANNELS:
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                return False
        except Exception:
            return False
    return True

# ========== START ==========
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    USERS.add(message.from_user.id)

    if len(message.command) > 1:
        code = message.command[1]
        try:
            msg_id = int(code)
            if not await check_sub(client, message.from_user.id):
                await message.reply("⚠️ पहले सभी चैनल join करो:", reply_markup=make_keyboard())
                return
            file = await client.get_messages(FILE_CHANNEL, msg_id)
            sent = await file.copy(message.chat.id)
            # Auto delete
            if AUTO_DELETE_MINUTES > 0:
                await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
                await sent.delete()
        except Exception as e:
            await message.reply(f"❌ File not found!\n\nDebug: {e}")
    else:
        await message.reply("👋 Welcome! Send `/panel` (Admins only).")

# ========== ADMIN PANEL ==========
@app.on_message(filters.command("panel") & filters.user(ADMINS))
async def panel(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="addch")],
        [InlineKeyboardButton("➖ Remove Channel", callback_data="remch")],
        [InlineKeyboardButton("📜 View Channels", callback_data="viewch")],
        [InlineKeyboardButton("⏱ Set AutoDelete", callback_data="setdel")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ])
    await message.reply("⚙️ Admin Panel:", reply_markup=keyboard)

@app.on_callback_query(filters.user(ADMINS))
async def admin_panel(client, query):
    global AUTO_DELETE_MINUTES
    if query.data == "addch":
        await query.message.reply("Send channel username (without @):")
        return
    elif query.data == "remch":
        await query.message.reply("Send channel username to remove:")
        return
    elif query.data == "viewch":
        txt = "📜 Force-Sub Channels:\n"
        if FORCE_CHANNELS:
            txt += "\n".join([f"• {c}" for c in FORCE_CHANNELS])
        else:
            txt += "❌ None"
        await query.message.reply(txt)
    elif query.data == "setdel":
        await query.message.reply("⏱ Send minutes (0 = disable):")
    elif query.data == "stats":
        await query.message.reply(f"👥 Users: {len(USERS)}\n📂 Files: Auto from channel")

# Capture text replies from admin
@app.on_message(filters.user(ADMINS) & filters.text)
async def admin_text(client, message):
    global AUTO_DELETE_MINUTES
    text = message.text.strip()

    if text.isdigit():  # Auto delete set
        AUTO_DELETE_MINUTES = int(text)
        await message.reply(f"✅ Auto-delete set to {AUTO_DELETE_MINUTES} minutes.")
    elif text.startswith("remove "):
        ch = text.split(" ", 1)[1]
        if ch in FORCE_CHANNELS:
            FORCE_CHANNELS.remove(ch)
            await message.reply(f"❌ Removed channel: {ch}")
    else:
        # Add channel
        if text not in FORCE_CHANNELS:
            FORCE_CHANNELS.append(text)
            await message.reply(f"✅ Added channel: {text}")

print("Bot is running...")
app.run()
