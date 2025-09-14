import os
import base64
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG =========
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL"))  # -100 से शुरू होना चाहिए
ADMINS = [8324187938, 603360648]  # तुम्हारे admin IDs
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES", 15))
BOT_USERNAME = os.getenv("BOT_USERNAME", "Anime_Chaser_Bot")

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ========= START =========
@app.on_message(filters.command("start"))
async def start(_, message):
    user_id = message.from_user.id
    args = message.command

    if len(args) > 1:
        # मतलब link से आया
        payload = args[1]
        try:
            decoded = base64.urlsafe_b64decode(payload.encode()).decode()
            data = json.loads(decoded)
            file_id = data.get("file_id")

            if not file_id:
                await message.reply("❌ Invalid link payload!")
                return

            # File forward करने की कोशिश
            try:
                sent = await app.forward_messages(
                    chat_id=message.chat.id,
                    from_chat_id=FILE_CHANNEL,
                    message_ids=int(file_id)
                )

                # Auto delete info
                await message.reply(
                    f"✅ Here’s your file!\n\nThis message will auto-delete in {AUTO_DELETE_MINUTES} minutes. "
                    "Save or forward it now!"
                )

            except Exception as e:
                await message.reply("❌ File not found or bot cannot access it.")
                # Debug to admins
                for admin in ADMINS:
                    try:
                        await app.send_message(
                            chat_id=admin,
                            text=f"⚠️ ERROR while fetching file\nPayload: {payload}\nError: {e}"
                        )
                    except:
                        pass

        except Exception as e:
            await message.reply("❌ Invalid or expired link!")
            for admin in ADMINS:
                try:
                    await app.send_message(
                        chat_id=admin,
                        text=f"⚠️ ERROR decoding payload: {payload}\nError: {e}"
                    )
                except:
                    pass

    else:
        # Normal start (users)
        if user_id in ADMINS:
            await message.reply(
                "👋 Welcome Admin!\nSend /panel to open the control panel."
            )
        else:
            await message.reply(
                f"Hello {message.from_user.first_name} ✨\n\n"
                "Send me any file and I’ll give you a sharable link 📂\n\n"
                "Users can access stored messages only by clicking those links.\n\n"
                "To know more, click the Help button 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❓ Help", url=f"https://t.me/{BOT_USERNAME}")]]
                )
            )


# ========= HANDLE FILES =========
@app.on_message(filters.document | filters.video | filters.audio)
async def save_file(_, message):
    user_id = message.from_user.id

    if user_id not in ADMINS:
        await message.reply("❌ Only admins can generate sharable links.")
        return

    try:
        file_message = await message.forward(FILE_CHANNEL)
        file_id = file_message.id

        payload = json.dumps({"file_id": str(file_id)})
        b64_payload = base64.urlsafe_b64encode(payload.encode()).decode()

        share_link = f"https://t.me/{BOT_USERNAME}?start={b64_payload}"

        await message.reply(
            f"✅ File received and saved!\n\nSharable Link:\n{share_link}"
        )

    except Exception as e:
        await message.reply("❌ Failed to save file!")
        for admin in ADMINS:
            try:
                await app.send_message(
                    chat_id=admin,
                    text=f"⚠️ ERROR saving file\nError: {e}"
                )
            except:
                pass


# ========= ADMIN PANEL =========
@app.on_message(filters.command("panel") & filters.user(ADMINS))
async def admin_panel(_, message):
    keyboard = [
        [InlineKeyboardButton("📂 Generate Sharable Link", callback_data="gen_link")],
        [InlineKeyboardButton("📊 View Stats", callback_data="view_stats")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ]

    await message.reply(
        "🔐 Admin Panel:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


app.run()
