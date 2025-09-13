# bot.py
import os
import asyncio
import base64
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# --- ENV / config ---
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Channels: CHANNEL_1 and CHANNEL_2 can be @username or -100...
CHANNEL_1 = os.getenv("CHANNEL_1")       # example: @chan_one  OR -1001234567890
CHANNEL_2 = os.getenv("CHANNEL_2")       # example: @chan_two  OR -1001234567890
CHANNEL_1_INVITE = os.getenv("CHANNEL_1_INVITE")  # optional invite link (if private & no username)
CHANNEL_2_INVITE = os.getenv("CHANNEL_2_INVITE")

FILE_CHANNEL = os.getenv("FILE_CHANNEL")  # MUST be -100... (channel where files/messages are)
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES") or 30)
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None

# validation
if not (API_ID and API_HASH and BOT_TOKEN and FILE_CHANNEL):
    raise RuntimeError("Missing required env vars: set API_ID, API_HASH, BOT_TOKEN, FILE_CHANNEL")

try:
    FILE_CHANNEL_INT = int(FILE_CHANNEL)
except Exception:
    raise RuntimeError("FILE_CHANNEL must be numeric like -1001234567890")

# --- Pyrogram client ---
app = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# --- helpers ---
def encode_payload_for_link(msg_id: str) -> str:
    """
    Creates short urlsafe base64 payload like 'Z2V0LTI' (without padding '=')
    using 'get-<msg_id>' format.
    """
    raw = f"get-{msg_id}"
    enc = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return enc


def decode_start_payload(enc_str: str) -> str | None:
    """
    Robust decode: adds padding if needed, uses urlsafe decode.
    Returns decoded string or None.
    """
    try:
        s = enc_str.replace(" ", "+")  # common fix
        pad = len(s) % 4
        if pad != 0:
            s += "=" * (4 - pad)
        decoded = base64.urlsafe_b64decode(s).decode("utf-8", errors="ignore")
        return decoded
    except Exception:
        return None


async def is_user_joined(client: Client, user_id: int, channel) -> bool:
    """
    channel: can be @username or -100... string/int
    returns True if user is member (not left/kicked)
    """
    try:
        ch = channel
        if isinstance(ch, str) and ch.startswith("-100"):
            ch = int(ch)
        member = await client.get_chat_member(ch, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False


# --- bot commands / handlers ---
@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    """
    Handles private /start and /start <payload>
    Payload expected: base64 of "get-<msg_id>" OR plain "get-<msg_id>" OR plain msg_id
    """
    user_id = message.from_user.id

    # plain /start
    if len(message.command) == 1:
        await message.reply_text(
            "👋 Hello!\n\n"
            "मुझे चैनल के बटन से बुलाओ — जैसे channel में बने लिंक पर क्लिक करके आना होगा।\n"
            "अगर तुम एडमिन हो और लिंक बनाना चाहते हो, तो /genlink <message_id> (owner only) की मदद लो."
        )
        return

    encoded = message.command[1]
    decoded = decode_start_payload(encoded)
    if decoded:
        payload = decoded
    else:
        # fallback: use raw token (so both encoded and plain small keys work)
        payload = encoded

    # expected formats: "get-<id>" or "<id>"
    if payload.startswith("get-"):
        payload_id = payload.split("get-", 1)[1]
    else:
        payload_id = payload

    # validate numeric message id
    try:
        msg_id = int(payload_id)
    except Exception:
        await message.reply_text("❌ Invalid link.")
        return

    # check subscriptions
    joined1 = await is_user_joined(client, user_id, CHANNEL_1) if CHANNEL_1 else True
    joined2 = await is_user_joined(client, user_id, CHANNEL_2) if CHANNEL_2 else True

    if not joined1 or not joined2:
        buttons = []
        if not joined1:
            if CHANNEL_1 and CHANNEL_1.startswith("@"):
                buttons.append([InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1.strip('@')}")])
            elif CHANNEL_1_INVITE:
                buttons.append([InlineKeyboardButton("📢 Join Channel 1", url=f"{CHANNEL_1_INVITE}")])
            else:
                # fallback: try username if present
                if CHANNEL_1:
                    buttons.append([InlineKeyboardButton("📢 Open Channel 1", url=f"https://t.me/{str(CHANNEL_1).strip('@')}")])
        if not joined2:
            if CHANNEL_2 and CHANNEL_2.startswith("@"):
                buttons.append([InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2.strip('@')}")])
            elif CHANNEL_2_INVITE:
                buttons.append([InlineKeyboardButton("📢 Join Channel 2", url=f"{CHANNEL_2_INVITE}")])
            else:
                if CHANNEL_2:
                    buttons.append([InlineKeyboardButton("📢 Open Channel 2", url=f"https://t.me/{str(CHANNEL_2).strip('@')}")])

        # Try Again button passes the same encoded payload back
        buttons.append([InlineKeyboardButton("✅ Try Again", callback_data=f"retry_{encoded}")])

        await message.reply_text(
            "⚠️ पहले नीचे दिए चैनल्स join करें, फिर Try Again दबाएँ।",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # all checks passed -> send file
    await send_stored_file(client, user_id, msg_id, encoded)


# retry callback
@app.on_callback_query()
async def callback_handler(client, query):
    data = query.data or ""
    if data.startswith("retry_"):
        encoded = data.split("_", 1)[1]
        decoded = decode_start_payload(encoded) or encoded
        if decoded.startswith("get-"):
            payload_id = decoded.split("get-", 1)[1]
        else:
            payload_id = decoded
        try:
            msg_id = int(payload_id)
        except:
            await query.answer("Invalid file id.", show_alert=True)
            return

        user_id = query.from_user.id
        joined1 = await is_user_joined(client, user_id, CHANNEL_1) if CHANNEL_1 else True
        joined2 = await is_user_joined(client, user_id, CHANNEL_2) if CHANNEL_2 else True

        if joined1 and joined2:
            try:
                await query.message.delete()
            except:
                pass
            await send_stored_file(client, user_id, msg_id, encoded)
            await query.answer("Sending file...", show_alert=False)
        else:
            await query.answer("अभी भी सभी channels join नहीं किए!", show_alert=True)


# send file (copy from FILE_CHANNEL into user's chat)
async def send_stored_file(client, user_id: int, msg_id: int, encoded_payload: str):
    try:
        sent = await client.copy_message(chat_id=user_id, from_chat_id=FILE_CHANNEL_INT, message_id=msg_id)

        await client.send_message(
            user_id,
            f"⚠️ Important:\nThis message/file will be deleted after {AUTO_DELETE_MINUTES} minutes. Save it if needed."
        )

        # schedule delete
        asyncio.create_task(delete_after(sent.chat.id, sent.message_id, encoded_payload, user_id))

    except Exception as e:
        await client.send_message(user_id, f"❌ File not found or expired!\n\nDebug: {e}")


# delete after and send "Get Again" button
async def delete_after(chat_id: int, msg_id: int, payload: str, user_id: int):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    try:
        await app.delete_messages(chat_id, msg_id)
    except:
        pass

    # notify user with Get Again
    try:
        await app.send_message(
            user_id,
            "🗑 Your file was deleted.\nIf you want it again, press below:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔁 Get File Again", callback_data=f"retry_{payload}")]]
            )
        )
    except:
        pass


# admin helper: generate encoded link (only owner if OWNER_ID set)
@app.on_message(filters.private & filters.command("genlink"))
async def genlink_cmd(client, message):
    if OWNER_ID and message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ You are not allowed to use this.")
    if len(message.command) < 2:
        return await message.reply_text("Usage: /genlink <message_id>")
    raw_id = message.command[1].strip()
    try:
        int(raw_id)
    except:
        return await message.reply_text("message_id must be a number (the message id inside the file channel)")
    enc = encode_payload_for_link(raw_id)
    me = await client.get_me()
    bot_username = me.username or "YOUR_BOT_USERNAME"
    link = f"https://t.me/{bot_username}?start={enc}"
    await message.reply_text(f"Here is the encoded link:\n\n`{link}`", parse_mode="markdown")


if __name__ == "__main__":
    print("Bot starting...")
    app.run()
