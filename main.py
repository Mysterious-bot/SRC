import os, time, asyncio, requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MONGO_URL = os.environ.get("MONGO_URL", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# Fixed Settings (As per your data)
AD_API = "80009a5fc0ab91a0ebb481f11daaa55921e9e377" 
AUTH_CH_ID = -1003984449510  
CH_LINK = "https://t.me/ArjunBotz"
HELP_LINK = "https://t.me/ArjunBotzHelp"

app = Client("ArjunBotz", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = MongoClient(MONGO_URL)['ArjunBotzDB']['users']

# Web Server for Uptime
web = Flask(__name__)
@web.route('/')
def home(): return "ArjunBotz is Online!"
def run_web(): web.run(host='0.0.0.0', port=8080)

def get_adrino_link(url):
    api_endpoint = f"https://adrinolinks.in/api?api={AD_API}&url={url}"
    try:
        r = requests.get(api_endpoint).json()
        if r['status'] == 'success': return r['shortenedUrl']
    except: pass
    return url

# --- START & FORCE JOIN ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    uid = message.from_user.id
    if not db.find_one({"_id": uid}):
        db.insert_one({"_id": uid, "join_date": time.time()})

    if uid != OWNER_ID:
        try:
            await client.get_chat_member(AUTH_CH_ID, uid)
        except:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("JOIN CHANNEL 📢", url=CH_LINK)]])
            return await message.reply_text("❌ **Access Denied!**\n\nJoin our channel to use this bot.", reply_markup=btn)

    if len(message.command) > 1 and message.command[1] == "verify":
        db.update_one({"_id": uid}, {"$set": {"verified_at": time.time()}}, upsert=True)
        return await message.reply_text("✅ **Token Verified!** 4h access granted.\n\n`Maintained by @ArjunBotz`")

    welcome_text = (
        "Hi, 🐥 ''\n\n"
        "✨ **Save posts, videos & audio — even when forwarding is OFF.** ''\n\n"
        "🔥 **Higher download limits — FREE..,**\n"
        "⚡ **Fast • Smooth • Reliable.** ''\n\n"
        "🎀 **MAINTAINED BY: ARJUN BOTZ** 🎀 ''"
    )
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("JOIN CHANNEL 🚀", url=CH_LINK)],
        [InlineKeyboardButton("BATCH MODE 🔓", callback_data="batch_logic"), 
         InlineKeyboardButton("HELP MENU ❓", callback_data="help_pg1")],
        [InlineKeyboardButton("CONTACT ADMIN 👤", url=HELP_LINK)]
    ])
    await message.reply_text(welcome_text, reply_markup=btn)

# --- DOWNLOADER & BATCH LOGIC ---
@app.on_message(filters.text & filters.private)
async def downloader(client, message):
    uid = message.from_user.id
    text = message.text

    if not text.startswith("https://t.me/"): return

    user = db.find_one({"_id": uid}) or {"last": 0, "verified_at": 0}
    is_owner = (uid == OWNER_ID)
    is_verified = (time.time() - user.get("verified_at", 0)) < 14400 
    
    if not is_owner:
        if not is_verified:
            short_url = get_adrino_link(f"https://t.me/{app.me.username}?start=verify")
            return await message.reply_text("🔐 **Locked!** Verify for 4h access.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Verify Now ✅", url=short_url)]]))
        
        now = time.time()
        if (now - user.get("last", 0)) < 250:
            return await message.reply_text(f"⏳ Cooldown: `{int(250 - (now - user.get('last', 0)))}s`")

    # Handling /batch links (e.g., link/10-110)
    if "-" in text and "/" in text.split("/")[-1]:
        await message.reply_text("🔢 **Batch Processing Started (Max 100)...**")
        # Yahan batch loop logic aayega
        return

    m = await message.reply_text("⚡ **Processing...**")
    try:
        parts = text.split("/")
        msg_id = int(parts[-1])
        chat_id = int("-100" + parts[-2]) if "t.me/c/" in text else parts[-2]
        await client.copy_message(uid, chat_id, msg_id)
        db.update_one({"_id": uid}, {"$set": {"last": time.time()}})
        await m.delete()
    except Exception as e:
        await m.edit(f"❌ **Error:** {e}")

# --- HELP & CALLBACKS ---
@app.on_callback_query()
async def cb_handler(client, cb):
    if cb.data == "help_pg1":
        text = "📝 **Bot Commands (1/2):**\n1. `/login` - Private\n2. `/batch` - 100 Limit\n\n**🎀 Maintained By: ARJUN BOTZ 🎀**"
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Next ⏩", callback_data="help_pg2")]]))
    elif cb.data == "help_pg2":
        text = "📝 **Bot Commands (2/2):**\n3. `/settings` - UI Control\n4. `/logout` - Exit\n\n🌌🎀 *Maintained By: ARJUN BOTZ* 🎀🌌"
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏪ Back", callback_data="help_pg1")]]))
    elif cb.data == "batch_logic":
        await cb.message.reply_text("🔓 **Batch Mode:** Send links in `link/start-end` format (Max 100).")

# --- BROADCAST (Owner Only) ---
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client, message):
    if not message.reply_to_message: return await message.reply_text("Reply to a msg!")
    success = 0
    for user in db.find():
        try:
            await message.reply_to_message.copy(user["_id"])
            success += 1
            await asyncio.sleep(0.3)
        except: pass
    await message.reply_text(f"✅ Broadcast Sent to `{success}` users.")

if __name__ == "__main__":
    Thread(target=run_web).start()
    app.run()