#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════
#  BD TopSell Bot — @GoTop_Otp_bot
#  Admin: @bd_top_admin | Chat ID: 7831629041
# ═══════════════════════════════════════════════════════════
import logging, json, time, hmac, hashlib, struct, base64, re, io
import os
from datetime import datetime, timezone
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
import firebase_admin
from firebase_admin import credentials, firestore

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════
BOT_TOKEN    = "8665058261:AAGCG0ktyjhjulgfx38A5yjzTy1t12Fcck4"
ADMIN_IDS    = [7831629041]
ADMIN_USERNAME = "@bd_top_admin"
CHANNEL_ID   = "@bd_top_sell_official"
SUPPORT_LINK = "https://t.me/bd_top_sell_official"

FIREBASE_CONFIG = {
    "apiKey": "AIzaSyC1QTJPKzOFFJu6SgjwdpMxZ0WmieMacyQ",
    "authDomain": "james-admin-cb377.firebaseapp.com",
    "projectId": "james-admin-cb377",
    "storageBucket": "james-admin-cb377.firebasestorage.app",
    "messagingSenderId": "119874781926",
    "appId": "1:119874781926:web:b9de4474490ed9f5b7b127"
}

# Task rates
IG_RATE  = 4.60
FB_RATE  = 5.00

# Deposit config
BINANCE_PAY_ID = "849574504"
MIN_DEPOSIT    = 20       # diamonds
USD_TO_DIAMOND = 125      # 1$ = 125 diamonds

# Withdraw methods
WITHDRAW_METHODS = {
    "bkash":   {"name":"bKash",        "emoji":"💳", "charge":5,  "min":50},
    "nagad":   {"name":"Nagad",        "emoji":"🟠", "charge":5,  "min":50},
    "binance": {"name":"Binance (BEP20 USDT)", "emoji":"💛", "charge":10, "min":100},
}

# ═══════════════════════════════════════════
#  FIREBASE INIT
# ═══════════════════════════════════════════
db = None
def init_firebase():
    global db
    try:
        # serviceAccountKey.json must be in same folder as bot.py
        import os
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serviceAccountKey.json")
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("✅ Firebase connected successfully!")
    except Exception as e:
        logger.warning(f"⚠️ Firebase not connected — running in memory mode: {e}")
        db = None

def fb_get(collection, doc_id):
    if not db: return None
    try:
        doc = db.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    except: return None

def fb_set(collection, doc_id, data, merge=True):
    if not db: return False
    try:
        db.collection(collection).document(doc_id).set(data, merge=merge)
        return True
    except: return False

def fb_add(collection, data):
    if not db: return None
    try:
        ref = db.collection(collection).add(data)
        return ref[1].id
    except: return None

def fb_query(collection, field, op, value, limit=50):
    if not db: return []
    try:
        docs = db.collection(collection).where(field, op, value).limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except: return []

def fb_all(collection, limit=100):
    if not db: return []
    try:
        docs = db.collection(collection).limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except: return []

# ═══════════════════════════════════════════
#  IN-MEMORY STORE (fallback when no Firebase)
# ═══════════════════════════════════════════
USERS        = {}   # user_id -> user data
SUBMISSIONS  = {}   # submission_id -> data
IG_ACCOUNTS  = []   # available instagram accounts
FB_ACCOUNTS  = []   # available facebook accounts
PRODUCTS     = {}   # product_id -> product data
SETTINGS     = {}   # bot settings

def load_default_settings():
    global SETTINGS
    SETTINGS = {
        "ig_task": {"name":"Instagram 2FA Task","payment":IG_RATE,"status":"active","daily_limit":5},
        "fb_task": {"name":"Facebook Number Cookie","payment":FB_RATE,"status":"active","daily_limit":5},
        "min_withdraw": 50,
        "ref_percent": 10,
        "lb_prizes": [600,300,200,100,50],
    }

load_default_settings()

# Default ig accounts pool
IG_ACCOUNTS = [
    {"username":"bdtopse14596nuyk","password":"sohan28@","status":"available"},
    {"username":"sumonwxrg739","password":"sohan28@","status":"available"},
    {"username":"karim_test001","password":"sohan28@","status":"available"},
]
FB_ACCOUNTS = [
    {"first_name":"Nayeem","last_name":"Miah","password":"sohan28@","status":"available"},
    {"first_name":"Kamrul","last_name":"Chowdhury","password":"sohan28@","status":"available"},
    {"first_name":"Rifat","last_name":"Ahmed","password":"sohan28@","status":"available"},
]

# ═══════════════════════════════════════════
#  LANGUAGE STRINGS
# ═══════════════════════════════════════════
LANG = {
    "bn": {
        "welcome": "👑 স্বাগতম, <b>{name}</b>!\n\n🤖 <b>BD TopSell Bot</b> এ আপনাকে স্বাগতম।\n\n✅ কাজ করুন → 💰 টাকা আয় করুন → 🏧 উইথড্র করুন\n\nনিচের মেনু থেকে শুরু করুন:",
        "tasks_menu": "📋 কোন কাজ করতে চান?",
        "task_ig": "📸 Instagram Task",
        "task_fb": "📘 Facebook Task",
        "wallet": "💰 ওয়ালেট",
        "profile": "👤 প্রোফাইল",
        "admin": "👑 এডমিন প্যানেল",
        "referral": "🔗 আমার রেফারেল",
        "leaderboard": "🏆 লিডারবোর্ড",
        "support": "💬 সাপোর্ট",
        "buy_product": "🛒 পণ্য কিনুন",
        "deposit": "💎 ডিপোজিট",
        "withdraw": "🏧 উইথড্র",
        "back": "🔙 পিছনে",
        "cancel": "❌ বাতিল",
        "main_menu": "🏠 মেইন মেনু",
        "task_not_available": "⚠️ এই কাজটি এখন বন্ধ আছে।",
        "duplicate_error": "❌ এই {type} আইডি আগেই জমা দেওয়া হয়েছে! ডুপ্লিকেট আইডি গ্রহণযোগ্য নয়।",
        "submitted_ok": "🎉 কাজ সফলভাবে জমা হয়েছে!\n\n📥 আপনার টাস্ক রিভিউতে আছে।\n\n✅ অনুমোদনের পর পেমেন্ট পাবেন।",
        "balance": "💰 আপনার ব্যালেন্স: <b>৳{earn}</b>\n💎 ডিপোজিট: <b>৳{deposit}</b>",
        "lang_changed": "✅ ভাষা বাংলা করা হয়েছে।",
    },
    "en": {
        "welcome": "👑 Welcome, <b>{name}</b>!\n\n🤖 Welcome to <b>BD TopSell Bot</b>.\n\n✅ Do Tasks → 💰 Earn Money → 🏧 Withdraw\n\nUse the menu below to get started:",
        "tasks_menu": "📋 Which task would you like to do?",
        "task_ig": "📸 Instagram Task",
        "task_fb": "📘 Facebook Task",
        "wallet": "💰 Wallet",
        "profile": "👤 Profile",
        "admin": "👑 Admin Panel",
        "referral": "🔗 My Referrals",
        "leaderboard": "🏆 Leaderboard",
        "support": "💬 Support",
        "buy_product": "🛒 Buy Product",
        "deposit": "💎 Deposit",
        "withdraw": "🏧 Withdraw",
        "back": "🔙 Back",
        "cancel": "❌ Cancel",
        "main_menu": "🏠 Main Menu",
        "task_not_available": "⚠️ This task is currently unavailable.",
        "duplicate_error": "❌ This {type} ID has already been submitted! Duplicate IDs are not allowed.",
        "submitted_ok": "🎉 Task submitted successfully!\n\n📥 Your task is under review.\n\n✅ Payment will be sent after approval.",
        "balance": "💰 Your Balance: <b>৳{earn}</b>\n💎 Deposit: <b>৳{deposit}</b>",
        "lang_changed": "✅ Language changed to English.",
    }
}

def t(user_id, key, **kwargs):
    """Get translated string for user"""
    lang = get_user_lang(user_id)
    s = LANG.get(lang, LANG["en"]).get(key, key)
    return s.format(**kwargs) if kwargs else s

def get_user_lang(user_id):
    uid = str(user_id)
    if uid in USERS:
        return USERS[uid].get("language", "en")
    user = fb_get("users", uid)
    if user:
        return user.get("language", "en")
    return "en"

# ═══════════════════════════════════════════
#  USER HELPERS
# ═══════════════════════════════════════════
def get_user(user_id):
    uid = str(user_id)
    if uid in USERS:
        return USERS[uid]
    data = fb_get("users", uid)
    if data:
        USERS[uid] = data
        return data
    return None

def create_user(tg_user, referrer_id=None):
    uid = str(tg_user.id)
    data = {
        "user_id": uid,
        "username": tg_user.username or "",
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name or "",
        "language": "en",
        "earn_balance": 0.0,
        "deposit_balance": 0.0,
        "pending_withdraw": 0.0,
        "total_earned": 0.0,
        "referral_income": 0.0,
        "referrals": 0,
        "completed_tasks": 0,
        "pending_tasks": 0,
        "rejected_tasks": 0,
        "referred_by": str(referrer_id) if referrer_id else None,
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "banned": False,
    }
    USERS[uid] = data
    fb_set("users", uid, data)
    # Referral bonus
    if referrer_id:
        ref = get_user(referrer_id)
        if ref:
            ref["referrals"] = ref.get("referrals", 0) + 1
            fb_set("users", str(referrer_id), ref)
    return data

def save_user(user_id, data):
    uid = str(user_id)
    USERS[uid] = data
    fb_set("users", uid, data)

def is_admin(user_id):
    return int(user_id) in ADMIN_IDS

def is_banned(user_id):
    user = get_user(user_id)
    return user.get("banned", False) if user else False

# ═══════════════════════════════════════════
#  2FA TOTP GENERATOR (Real algorithm)
# ═══════════════════════════════════════════
def generate_totp(secret_key: str, digits=6, interval=30) -> tuple[str, int]:
    """Generate real TOTP code. Returns (code, seconds_remaining)"""
    try:
        # Pad secret to valid base32 length
        secret = secret_key.upper().replace(" ", "").replace("-", "")
        pad = (8 - len(secret) % 8) % 8
        secret += "=" * pad
        key = base64.b32decode(secret)
        
        now = int(time.time())
        counter = now // interval
        remaining = interval - (now % interval)
        
        # HMAC-SHA1
        counter_bytes = struct.pack(">Q", counter)
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        
        offset = hmac_hash[-1] & 0x0F
        code_int = (
            (hmac_hash[offset]     & 0x7F) << 24 |
            (hmac_hash[offset + 1] & 0xFF) << 16 |
            (hmac_hash[offset + 2] & 0xFF) << 8  |
            (hmac_hash[offset + 3] & 0xFF)
        )
        code = str(code_int % (10 ** digits)).zfill(digits)
        return code, remaining
    except Exception as e:
        raise ValueError(f"Invalid secret key: {e}")

def validate_totp_key(key: str) -> bool:
    """Validate base32 secret key format"""
    key = key.upper().replace(" ", "").replace("-", "")
    if len(key) < 16:
        return False
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=")
    return all(c in valid_chars for c in key)

# ═══════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════
def main_menu_keyboard(user_id):
    lang = get_user_lang(user_id)
    L = LANG[lang]
    is_adm = is_admin(user_id)
    
    if lang == "bn":
        rows = [
            [KeyboardButton("📋 কাজ"), KeyboardButton("🛒 পণ্য কিনুন")],
            [KeyboardButton("💰 ওয়ালেট"), KeyboardButton("👤 প্রোফাইল")],
            [KeyboardButton("🔗 রেফারেল"), KeyboardButton("🏆 লিডারবোর্ড")],
            [KeyboardButton("💬 সাপোর্ট"), KeyboardButton("🌐 ভাষা পরিবর্তন")],
        ]
        if is_adm:
            rows.insert(2, [KeyboardButton("👑 এডমিন প্যানেল"), KeyboardButton("📢 ব্রডকাস্ট")])
    else:
        rows = [
            [KeyboardButton("📋 Tasks"), KeyboardButton("🛒 Buy Product")],
            [KeyboardButton("💰 Wallet"), KeyboardButton("👤 Profile")],
            [KeyboardButton("🔗 My Referrals"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("💬 Support"), KeyboardButton("🌐 Change Language")],
        ]
        if is_adm:
            rows.insert(2, [KeyboardButton("👑 Admin Panel"), KeyboardButton("📢 Broadcast")])
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def cancel_keyboard(user_id):
    lang = get_user_lang(user_id)
    if lang == "bn":
        return ReplyKeyboardMarkup([[KeyboardButton("❌ বাতিল")]], resize_keyboard=True)
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True)

def back_keyboard(user_id):
    lang = get_user_lang(user_id)
    if lang == "bn":
        return ReplyKeyboardMarkup([[KeyboardButton("🔙 পিছনে"), KeyboardButton("🏠 মেইন মেনু")]], resize_keyboard=True)
    return ReplyKeyboardMarkup([[KeyboardButton("🔙 Back"), KeyboardButton("🏠 Main Menu")]], resize_keyboard=True)

# ═══════════════════════════════════════════
#  CONVERSATION STATES
# ═══════════════════════════════════════════
(
    # Instagram flow
    IG_MAIN, IG_AWAITING_SECRET, IG_CONFIRM_SUBMIT,
    # Bulk submit
    BULK_IG_PASTE, BULK_FB_PASTE,
    # Facebook flow
    FB_MAIN, FB_AWAITING_UID, FB_AWAITING_COOKIE,
    # Wallet
    WALLET_MAIN, DEPOSIT_AWAIT_TRX, WITHDRAW_METHOD, WITHDRAW_AMOUNT, WITHDRAW_ADDRESS,
    # Admin
    ADMIN_MAIN, ADMIN_ADD_ACCOUNT, ADMIN_BROADCAST_MSG, ADMIN_SEARCH_USER,
    ADMIN_BALANCE_USER, ADMIN_BALANCE_AMOUNT,
    # Buy product
    BUY_CAT, BUY_PRODUCT, BUY_CONFIRM,
    # Language
    LANG_SELECT,
) = range(22)

# ═══════════════════════════════════════════
#  CHECK CHANNEL JOIN
# ═══════════════════════════════════════════
async def check_joined(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Check if user joined the required channel"""
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return True  # if check fails, allow

async def force_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
        InlineKeyboardButton("✅ I Joined", callback_data="check_join"),
    ]])
    await update.message.reply_text(
        "⚠️ <b>Channel Join Required</b>\n\n"
        f"To use this bot, you must join our official channel:\n"
        f"📢 {CHANNEL_ID}\n\n"
        "After joining, tap ✅ I Joined",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

# ═══════════════════════════════════════════
#  /start HANDLER
# ═══════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    
    # Check referral
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id == user.id:
                referrer_id = None
        except: pass
    
    # Get or create user
    db_user = get_user(uid)
    if not db_user:
        db_user = create_user(user, referrer_id)
    
    if is_banned(uid):
        await update.message.reply_text("🚫 Your account has been banned. Contact support.")
        return ConversationHandler.END
    
    # Admin welcome
    if is_admin(user.id):
        await update.message.reply_text(
            f"👑 <b>Welcome Admin {user.first_name} ({ADMIN_USERNAME})!</b>\n\n"
            "You have full administrative controls.\nChoose an option below:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(user.id)
        )
        return ConversationHandler.END
    
    # Force join check
    joined = await check_joined(context, user.id)
    if not joined:
        await force_join_message(update, context)
        return ConversationHandler.END
    
    lang = db_user.get("language", "en")
    name = user.first_name or "User"
    
    await update.message.reply_text(
        t(uid, "welcome", name=name),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(user.id)
    )
    return ConversationHandler.END

# ═══════════════════════════════════════════
#  TASKS HANDLER
# ═══════════════════════════════════════════
async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    lang = get_user_lang(uid)
    
    if lang == "bn":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Instagram Task", callback_data="task_ig")],
            [InlineKeyboardButton("📘 Facebook Task", callback_data="task_fb")],
            [InlineKeyboardButton("📦 Bulk Submit (Excel)", callback_data="task_bulk")],
        ])
        text = "📋 <b>কোন কাজ করতে চান?</b>"
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Instagram Task", callback_data="task_ig")],
            [InlineKeyboardButton("📘 Facebook Task", callback_data="task_fb")],
            [InlineKeyboardButton("📦 Bulk Submit (Excel)", callback_data="task_bulk")],
        ])
        text = "📋 <b>Which task would you like to do?</b>"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ═══════════════════════════════════════════
#  INSTAGRAM TASK FLOW
# ═══════════════════════════════════════════
async def ig_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called from callback: task_ig"""
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    # Check task status
    ig_settings = SETTINGS.get("ig_task", {})
    if ig_settings.get("status") == "inactive":
        await query.edit_message_text(t(uid, "task_not_available"))
        return
    
    # Get available account
    account = next((a for a in IG_ACCOUNTS if a["status"] == "available"), None)
    if not account:
        await query.edit_message_text("⚠️ No Instagram accounts available right now. Try again later.")
        return
    
    # Store in context
    context.user_data["ig_account"] = account
    account["status"] = "in_use"
    
    pay = ig_settings.get("payment", IG_RATE)
    
    if lang == "bn":
        text = (
            f"📸 <b>Instagram 2FA Task</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 পেমেন্ট: <b>৳{pay}</b>\n\n"
            f"📋 <b>একাউন্টের তথ্য:</b>\n"
            f"👤 Username: <code>{account['username']}</code>\n"
            f"🔑 Password: <code>{account['password']}</code>\n\n"
            f"⚡ প্রতিটি তথ্যে ট্যাপ করলে কপি হবে।\n\n"
            f"📌 <b>নির্দেশনা:</b>\n"
            f"এই তথ্য দিয়ে Instagram একাউন্টে লগইন করুন,\n"
            f"তারপর 2FA চালু করুন।"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 2FA Code Generate করুন", callback_data="ig_gen_2fa")],
            [InlineKeyboardButton("📚 Tutorial", callback_data="ig_tutorial"),
             InlineKeyboardButton("❌ বাতিল", callback_data="ig_cancel")],
        ])
    else:
        text = (
            f"📸 <b>Instagram 2FA Task</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Payment: <b>৳{pay}</b>\n\n"
            f"📋 <b>Account Details:</b>\n"
            f"👤 Username: <code>{account['username']}</code>\n"
            f"🔑 Password: <code>{account['password']}</code>\n\n"
            f"⚡ Tap each field to copy.\n\n"
            f"📌 <b>Instructions:</b>\n"
            f"Register/login to Instagram with these exact details,\n"
            f"then enable 2FA."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Generate 2FA Code", callback_data="ig_gen_2fa")],
            [InlineKeyboardButton("📚 Tutorial", callback_data="ig_tutorial"),
             InlineKeyboardButton("❌ Cancel", callback_data="ig_cancel")],
        ])
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def ig_request_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked Generate 2FA → ask for secret key"""
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    if lang == "bn":
        text = (
            "🔔 <b>Instagram Settings এ যান:</b>\n"
            "⚙️ Settings → Security → Two-Factor Authentication → Authentication App\n\n"
            "<b>সেখানে দেখানো 32-character Secret Key পাঠান:</b>"
        )
    else:
        text = (
            "🔔 <b>Go to Instagram Settings:</b>\n"
            "⚙️ Settings → Security → Two-Factor Authentication → Authentication App\n\n"
            "<b>Send the 32-character Secret Key shown there:</b>"
        )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel", callback_data="ig_cancel")
    ]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    context.user_data["state"] = "awaiting_totp_key"

async def ig_handle_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User sent the secret key"""
    if context.user_data.get("state") != "awaiting_totp_key":
        return
    
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    key = update.message.text.strip()
    
    if not validate_totp_key(key):
        err_text = "❌ Enter a valid Secret Key (16+ chars, base32 format):"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="ig_cancel")
        ]])
        await update.message.reply_text(err_text, reply_markup=keyboard)
        return  # Stay in state
    
    try:
        code, remaining = generate_totp(key)
        context.user_data["ig_totp_key"] = key
        context.user_data["ig_totp_code"] = code
        context.user_data["state"] = "awaiting_ig_submit"
        
        if lang == "bn":
            text = (
                f"✅ <b>আপনার 2FA Code:</b>\n\n"
                f"<code>{code}</code>\n\n"
                f"⏱️ মেয়াদ: <b>{remaining} সেকেন্ড</b> বাকি\n\n"
                f"⚡ কোডটি ট্যাপ করে কপি করুন, তারপর Instagram এ দিন।\n"
                f"কাজ শেষ হলে Submit করুন।"
            )
        else:
            text = (
                f"✅ <b>Your 2FA Code:</b>\n\n"
                f"<code>{code}</code>\n\n"
                f"⏱️ Expires in: <b>{remaining} seconds</b>\n\n"
                f"⚡ Tap to copy. Enter this code in Instagram, then submit your task."
            )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Submit Task", callback_data="ig_submit"),
             InlineKeyboardButton("🔄 Refresh Code", callback_data="ig_refresh_code")],
            [InlineKeyboardButton("❌ Cancel", callback_data="ig_cancel")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    except ValueError as e:
        err = "❌ Invalid Secret Key. Please try again:"
        await update.message.reply_text(err)

async def ig_refresh_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh 2FA code"""
    query = update.callback_query
    await query.answer("🔄 Refreshing...")
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    key = context.user_data.get("ig_totp_key")
    if not key:
        await query.answer("❌ No key found", show_alert=True)
        return
    
    code, remaining = generate_totp(key)
    context.user_data["ig_totp_code"] = code
    
    text = (
        f"✅ <b>Your 2FA Code (Refreshed):</b>\n\n"
        f"<code>{code}</code>\n\n"
        f"⏱️ Expires in: <b>{remaining} seconds</b>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Submit Task", callback_data="ig_submit"),
         InlineKeyboardButton("🔄 Refresh", callback_data="ig_refresh_code")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ig_cancel")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def ig_submit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit Instagram task"""
    query = update.callback_query
    await query.answer("⌛ Submitting...")
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    account = context.user_data.get("ig_account")
    totp_key = context.user_data.get("ig_totp_key")
    
    if not account or not totp_key:
        await query.edit_message_text("❌ Session expired. Please start again.")
        return
    
    username = account["username"]
    
    # Check duplicate
    existing = fb_query("task_submissions", "ig_username", "==", username)
    local_dup = any(
        s.get("ig_username") == username and s.get("user_id") == uid
        for s in SUBMISSIONS.values()
    )
    if existing or local_dup:
        await query.edit_message_text(t(uid, "duplicate_error", type="Instagram"))
        account["status"] = "available"
        return
    
    # Create submission
    submission = {
        "user_id": uid,
        "username": query.from_user.username or "",
        "task_type": "instagram",
        "ig_username": account["username"],
        "ig_password": account["password"],
        "totp_secret": totp_key,
        "amount": SETTINGS.get("ig_task", {}).get("payment", IG_RATE),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    sub_id = fb_add("task_submissions", submission)
    if not sub_id:
        sub_id = f"IG{int(time.time())}"
        SUBMISSIONS[sub_id] = submission
    
    # Mark account as used
    account["status"] = "used"
    
    # Update user pending count
    user_data = get_user(uid)
    if user_data:
        user_data["pending_tasks"] = user_data.get("pending_tasks", 0) + 1
        save_user(uid, user_data)
    
    # Notify admin
    await notify_admin_new_submission(query.bot, submission, sub_id)
    
    if lang == "bn":
        text = (
            "🎉 <b>কাজ সফলভাবে জমা হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📥 আপনার টাস্ক রিভিউতে আছে।\n\n"
            "⚠️ <b>গুরুত্বপূর্ণ:</b>\n"
            "একাউন্টে কমপক্ষে:\n"
            "• 10+ following থাকতে হবে\n"
            "• একটি প্রোফাইল ছবি থাকতে হবে\n"
            "• কমপক্ষে 1টি পোস্ট থাকতে হবে\n\n"
            "✅ অনুমোদনের পর পেমেন্ট পাবেন।"
        )
    else:
        text = (
            "🎉 <b>Task Submitted Successfully!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Your task is under review.\n\n"
            "⚠️ <b>Important:</b>\n"
            "Things to do for approval:\n"
            "• At least 10+ following\n"
            "• Add a profile picture\n"
            "• Minimum 1 post\n\n"
            "✅ Payment will be sent after approval."
        )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 Join Payment Group", url=SUPPORT_LINK),
    ]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    context.user_data.clear()

# ═══════════════════════════════════════════
#  FACEBOOK TASK FLOW
# ═══════════════════════════════════════════
async def fb_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    fb_settings = SETTINGS.get("fb_task", {})
    if fb_settings.get("status") == "inactive":
        await query.edit_message_text(t(uid, "task_not_available"))
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📘 FB Number", callback_data="fb_sub_number")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel")],
    ])
    text = "💎 <b>Please select:</b>" if lang == "en" else "💎 <b>সিলেক্ট করুন:</b>"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def fb_sub_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    pay = SETTINGS.get("fb_task", {}).get("payment", FB_RATE)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📘 Number Cookie (৳{pay})", callback_data="fb_start_cookie")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel")],
    ])
    text = "💎 <b>Select an option:</b>"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def fb_start_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    account = next((a for a in FB_ACCOUNTS if a["status"] == "available"), None)
    if not account:
        await query.edit_message_text("⚠️ No Facebook accounts available right now.")
        return
    
    context.user_data["fb_account"] = account
    account["status"] = "in_use"
    context.user_data["state"] = "awaiting_fb_uid"
    
    pay = SETTINGS.get("fb_task", {}).get("payment", FB_RATE)
    
    text = (
        f"⚙️ First Name: <code>{account['first_name']}</code>\n"
        f"〰 Last Name: <code>{account['last_name']}</code>\n"
        f"🔑 Password: <code>{account['password']}</code>\n\n"
        f"⚡ প্রতিটি তথ্যে ট্যাপ করলে কপি হবে।\n\n"
        f"👉 কাজ জমা দিতে নিচের বাটনে ক্লিক করুন।"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ UID সেন্ড করুন!", callback_data="fb_ask_uid")],
        [InlineKeyboardButton("📖 কিভাবে কাজ করব!", callback_data="fb_howto"),
         InlineKeyboardButton("❌ বাতিল!", callback_data="fb_cancel")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def fb_ask_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid_text = "Enter your 🇫 Facebook UID:"
    context.user_data["state"] = "awaiting_fb_uid"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel")]])
    await query.edit_message_text(uid_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def fb_handle_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_fb_uid":
        return
    uid_val = update.message.text.strip()
    if not uid_val.isdigit() or len(uid_val) < 8:
        await update.message.reply_text("❌ Invalid UID. Please enter a valid numeric Facebook UID:")
        return
    
    # Duplicate check
    existing = fb_query("task_submissions", "fb_uid", "==", uid_val)
    local_dup = any(s.get("fb_uid") == uid_val for s in SUBMISSIONS.values())
    if existing or local_dup:
        uid = str(update.effective_user.id)
        await update.message.reply_text(t(uid, "duplicate_error", type="Facebook UID"))
        return
    
    context.user_data["fb_uid"] = uid_val
    context.user_data["state"] = "awaiting_fb_cookie"
    await update.message.reply_text("🔻 Enter your Cookie")

async def fb_handle_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_fb_cookie":
        return
    
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    cookie = update.message.text.strip()
    
    if len(cookie) < 20:
        await update.message.reply_text("❌ Invalid cookie. Please paste the full cookie string:")
        return
    
    # Check duplicate cookie
    existing = fb_query("task_submissions", "fb_cookie", "==", cookie[:50])
    if existing:
        await update.message.reply_text(t(uid, "duplicate_error", type="Cookie"))
        return
    
    context.user_data["fb_cookie"] = cookie
    
    text = "✅ Tap the button below to complete:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ অ্যাকাউন্ট খোলার শেষ", callback_data="fb_submit")],
        [InlineKeyboardButton("❌ বাতিল!", callback_data="fb_cancel")],
    ])
    await update.message.reply_text(text, reply_markup=keyboard)

async def fb_submit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⌛ Submitting...")
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    account = context.user_data.get("fb_account", {})
    fb_uid = context.user_data.get("fb_uid", "")
    cookie = context.user_data.get("fb_cookie", "")
    
    submission = {
        "user_id": uid,
        "username": query.from_user.username or "",
        "task_type": "facebook",
        "fb_first_name": account.get("first_name", ""),
        "fb_last_name": account.get("last_name", ""),
        "fb_password": account.get("password", ""),
        "fb_uid": fb_uid,
        "fb_cookie": cookie[:50],  # store truncated for dedup
        "fb_cookie_full": cookie,
        "amount": SETTINGS.get("fb_task", {}).get("payment", FB_RATE),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    sub_id = fb_add("task_submissions", submission)
    if not sub_id:
        sub_id = f"FB{int(time.time())}"
        SUBMISSIONS[sub_id] = submission
    
    account["status"] = "used"
    user_data = get_user(uid)
    if user_data:
        user_data["pending_tasks"] = user_data.get("pending_tasks", 0) + 1
        save_user(uid, user_data)
    
    await notify_admin_new_submission(query.bot, submission, sub_id)
    
    if lang == "bn":
        text = (
            "🎉 <b>Facebook task submitted successfully!</b>\n\n"
            "📥 রিভিউতে আছে।\n\n"
            "⚠️ <b>গুরুত্বপূর্ণ:</b>\n"
            "• কমপক্ষে 1 follower থাকতে হবে\n"
            "• অনুমোদনের পর পেমেন্ট পাবেন।"
        )
    else:
        text = (
            "🎉 <b>Facebook task submitted successfully!</b>\n\n"
            "📥 Your task is under review.\n\n"
            "⚠️ <b>Important:</b>\n"
            "• Account must have at least 1 follower\n"
            "• Payment after approval."
        )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 Join Payment Group", url=SUPPORT_LINK),
    ]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    context.user_data.clear()

# ═══════════════════════════════════════════
#  BULK SUBMIT (Excel paste)
# ═══════════════════════════════════════════
async def bulk_submit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Bulk Instagram Submit", callback_data="bulk_ig")],
        [InlineKeyboardButton("📘 Bulk Facebook Submit", callback_data="bulk_fb")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_bulk")],
    ])
    
    text = (
        "📦 <b>Bulk Submit</b>\n\n"
        "একসাথে অনেকগুলো account submit করুন!\n"
        "Excel থেকে copy করে paste করুন।\n\n"
        "📌 Format:\n"
        "<b>Instagram:</b> username|password|2fa_secret (per line)\n"
        "<b>Facebook:</b> first|last|password|uid|cookie (per line)\n\n"
        "✅ Maximum 1000 entries at once"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def bulk_ig_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = "bulk_ig_paste"
    text = (
        "📸 <b>Bulk Instagram Submit</b>\n\n"
        "Paste your data below (one per line):\n"
        "<code>username|password|2fa_secret</code>\n\n"
        "Example:\n"
        "<code>user1|pass123|JBSWY3DPEHPK3PXP\n"
        "user2|pass456|ABCDEFGH12345678</code>"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_bulk")]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def bulk_fb_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = "bulk_fb_paste"
    text = (
        "📘 <b>Bulk Facebook Submit</b>\n\n"
        "Paste your data below (one per line):\n"
        "<code>first_name|last_name|password|uid|cookie</code>\n\n"
        "Example:\n"
        "<code>John|Doe|pass123|726672728|datr=abc...</code>"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_bulk")]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def handle_bulk_paste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state not in ("bulk_ig_paste", "bulk_fb_paste"):
        return
    
    uid = str(update.effective_user.id)
    lines = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    
    if not lines:
        await update.message.reply_text("❌ No data found. Please paste valid data.")
        return
    
    if len(lines) > 1000:
        await update.message.reply_text("❌ Maximum 1000 entries at once!")
        return
    
    success = 0
    duplicates = 0
    errors = 0
    
    processing_msg = await update.message.reply_text(f"⌛ Processing {len(lines)} entries...")
    
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        
        if state == "bulk_ig_paste":
            if len(parts) < 3:
                errors += 1
                continue
            ig_user, ig_pass, secret = parts[0], parts[1], parts[2]
            
            # Duplicate check
            existing = fb_query("task_submissions", "ig_username", "==", ig_user)
            local_dup = any(s.get("ig_username") == ig_user for s in SUBMISSIONS.values())
            if existing or local_dup:
                duplicates += 1
                continue
            
            submission = {
                "user_id": uid, "username": update.effective_user.username or "",
                "task_type": "instagram", "ig_username": ig_user,
                "ig_password": ig_pass, "totp_secret": secret,
                "amount": SETTINGS.get("ig_task", {}).get("payment", IG_RATE),
                "status": "pending", "bulk": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        else:  # bulk_fb_paste
            if len(parts) < 5:
                errors += 1
                continue
            fname, lname, fpass, fuid, fcookie = parts[0], parts[1], parts[2], parts[3], parts[4]
            
            existing = fb_query("task_submissions", "fb_uid", "==", fuid)
            if existing:
                duplicates += 1
                continue
            
            submission = {
                "user_id": uid, "username": update.effective_user.username or "",
                "task_type": "facebook", "fb_first_name": fname, "fb_last_name": lname,
                "fb_password": fpass, "fb_uid": fuid, "fb_cookie_full": fcookie,
                "fb_cookie": fcookie[:50],
                "amount": SETTINGS.get("fb_task", {}).get("payment", FB_RATE),
                "status": "pending", "bulk": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        
        sub_id = fb_add("task_submissions", submission)
        if not sub_id:
            sub_id = f"BULK{int(time.time())}{success}"
            SUBMISSIONS[sub_id] = submission
        success += 1
    
    user_data = get_user(uid)
    if user_data:
        user_data["pending_tasks"] = user_data.get("pending_tasks", 0) + success
        save_user(uid, user_data)
    
    result = (
        f"📦 <b>Bulk Submit Complete!</b>\n\n"
        f"✅ Success: {success}\n"
        f"🔁 Duplicates skipped: {duplicates}\n"
        f"❌ Errors: {errors}\n\n"
        f"Total: {len(lines)}"
    )
    await processing_msg.edit_text(result, parse_mode=ParseMode.HTML)
    context.user_data.clear()

# ═══════════════════════════════════════════
#  WALLET HANDLER
# ═══════════════════════════════════════════
async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    user_data = get_user(uid) or {}
    
    earn = user_data.get("earn_balance", 0.0)
    deposit = user_data.get("deposit_balance", 0.0)
    pending_w = user_data.get("pending_withdraw", 0.0)
    total = user_data.get("total_earned", 0.0)
    ref_inc = user_data.get("referral_income", 0.0)
    done = user_data.get("completed_tasks", 0)
    pending_t = user_data.get("pending_tasks", 0)
    rejected = user_data.get("rejected_tasks", 0)
    
    if lang == "bn":
        text = (
            f"💰 <b>আপনার ওয়ালেট</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 উপার্জন ব্যালেন্স: <b>৳{earn:.2f}</b>\n"
            f"   <i>(টাস্ক ইনকাম — উইথড্র করা যাবে)</i>\n"
            f"💎 ডিপোজিট ব্যালেন্স: <b>৳{deposit:.2f}</b>\n"
            f"   <i>(পণ্য কেনার জন্য)</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏳ পেন্ডিং উইথড্র: ৳{pending_w:.2f}\n"
            f"💸 মোট উপার্জন: ৳{total:.2f}\n"
            f"🔗 রেফারেল ইনকাম: ৳{ref_inc:.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ সম্পন্ন কাজ: {done}\n"
            f"⏳ রিভিউতে: {pending_t}\n"
            f"❌ বাতিল: {rejected}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="wallet_balance"),
             InlineKeyboardButton("💎 ডিপোজিট ব্যালেন্স", callback_data="wallet_dep_bal")],
            [InlineKeyboardButton("➕ ডিপোজিট", callback_data="wallet_deposit"),
             InlineKeyboardButton("🏧 উইথড্র", callback_data="wallet_withdraw")],
            [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")],
        ])
    else:
        text = (
            f"💰 <b>Your Wallet</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 Earn Balance: <b>৳{earn:.2f}</b>\n"
            f"   <i>(Task income — withdrawable)</i>\n"
            f"💎 Deposit Balance: <b>৳{deposit:.2f}</b>\n"
            f"   <i>(For buying products)</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Pending Withdrawal: ৳{pending_w:.2f}\n"
            f"💸 Total Earned (Lifetime): ৳{total:.2f}\n"
            f"🔗 Referral Income: ৳{ref_inc:.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ Completed Tasks: {done}\n"
            f"⏳ In Review: {pending_t}\n"
            f"❌ Rejected: {rejected}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Balance", callback_data="wallet_balance"),
             InlineKeyboardButton("💎 Deposit Balance", callback_data="wallet_dep_bal")],
            [InlineKeyboardButton("➕ Deposit", callback_data="wallet_deposit"),
             InlineKeyboardButton("🏧 Withdraw", callback_data="wallet_withdraw")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ])
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ═══════════════════════════════════════════
#  DEPOSIT FLOW
# ═══════════════════════════════════════════
async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    context.user_data["state"] = "awaiting_trx_id"
    
    text = (
        f"💎 <b>Deposit</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>Binance Pay ID:</b> <code>{BINANCE_PAY_ID}</code>\n\n"
        f"📊 Rate: 1 USD = {USD_TO_DIAMOND} 💎\n"
        f"⚠️ Minimum Deposit: {MIN_DEPOSIT} 💎 ($0.20)\n\n"
        f"<b>Steps:</b>\n"
        f"1️⃣ Send payment to Binance Pay ID above\n"
        f"2️⃣ Copy your Transaction ID / Order ID\n"
        f"3️⃣ Paste it below:\n\n"
        f"👇 <b>Enter your Transaction ID:</b>"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="wallet_back")]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def deposit_handle_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_trx_id":
        return
    
    uid = str(update.effective_user.id)
    trx_id = update.message.text.strip()
    
    if len(trx_id) < 5:
        await update.message.reply_text("❌ Invalid Transaction ID. Please try again.")
        return
    
    # Check duplicate trx
    existing = fb_query("deposit_requests", "trx_id", "==", trx_id)
    if existing:
        await update.message.reply_text("❌ This Transaction ID has already been submitted!")
        return
    
    # Create deposit request
    deposit_req = {
        "user_id": uid,
        "username": update.effective_user.username or "",
        "trx_id": trx_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    fb_add("deposit_requests", deposit_req)
    
    # Notify admin
    user_data = get_user(uid)
    username = user_data.get("username", uid) if user_data else uid
    admin_text = (
        f"💎 <b>New Deposit Request!</b>\n\n"
        f"👤 User: @{username} ({uid})\n"
        f"🔢 TRX ID: <code>{trx_id}</code>\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Approve 20💎", callback_data=f"dep_approve_{uid}_{trx_id}_20"),
         InlineKeyboardButton(f"✅ 125💎", callback_data=f"dep_approve_{uid}_{trx_id}_125")],
        [InlineKeyboardButton(f"✅ 250💎", callback_data=f"dep_approve_{uid}_{trx_id}_250"),
         InlineKeyboardButton(f"✅ 500💎", callback_data=f"dep_approve_{uid}_{trx_id}_500")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"dep_reject_{uid}_{trx_id}")],
    ])
    for admin_id in ADMIN_IDS:
        try:
            await update.message.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except: pass
    
    await update.message.reply_text(
        "✅ <b>Deposit request submitted!</b>\n\n"
        "⏳ Admin will review and approve shortly.\n"
        f"🔢 TRX ID: <code>{trx_id}</code>",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()

# ═══════════════════════════════════════════
#  WITHDRAW FLOW
# ═══════════════════════════════════════════
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    lang = get_user_lang(uid)
    
    text = (
        "🏧 <b>How would you like to receive payment?</b>\n\n"
        "⚠️ A charge will be deducted per withdrawal (varies by method)."
    )
    buttons = []
    for key, method in WITHDRAW_METHODS.items():
        buttons.append([InlineKeyboardButton(
            f"{method['emoji']} {method['name']} | চার্জ ৳{method['charge']} | Min ৳{method['min']}",
            callback_data=f"wd_method_{key}"
        )])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="wallet_back")])
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def withdraw_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    method_key = query.data.split("_")[-1]
    await query.answer()
    uid = str(query.from_user.id)
    
    method = WITHDRAW_METHODS.get(method_key)
    if not method:
        await query.answer("❌ Invalid method", show_alert=True)
        return
    
    context.user_data["withdraw_method"] = method_key
    context.user_data["state"] = "awaiting_withdraw_amount"
    
    user_data = get_user(uid)
    earn = user_data.get("earn_balance", 0.0) if user_data else 0.0
    
    text = (
        f"{method['emoji']} <b>{method['name']} selected.</b>\n\n"
        f"💰 Available Balance: <b>৳{earn:.2f}</b>\n"
        f"💸 Charge: ৳{method['charge']}\n"
        f"📊 Minimum: ৳{method['min']}\n\n"
        f"Enter amount to withdraw (৳):"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="wallet_back")]])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def withdraw_handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_withdraw_amount":
        return
    
    uid = str(update.effective_user.id)
    try:
        amount = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Invalid amount. Enter a number:")
        return
    
    method_key = context.user_data.get("withdraw_method")
    method = WITHDRAW_METHODS.get(method_key)
    user_data = get_user(uid)
    earn = user_data.get("earn_balance", 0.0) if user_data else 0.0
    
    if amount < method["min"]:
        await update.message.reply_text(f"❌ Minimum withdrawal is ৳{method['min']}")
        return
    if amount > earn:
        await update.message.reply_text(f"❌ Insufficient balance. Available: ৳{earn:.2f}")
        return
    
    context.user_data["withdraw_amount"] = amount
    context.user_data["state"] = "awaiting_withdraw_address"
    
    address_prompt = {
        "bkash": "📱 Enter your bKash number:",
        "nagad": "🟠 Enter your Nagad number:",
        "binance": "💛 Enter your BEP20 wallet address (0x...):",
    }
    await update.message.reply_text(address_prompt.get(method_key, "Enter address:"))

async def withdraw_handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "awaiting_withdraw_address":
        return
    
    uid = str(update.effective_user.id)
    address = update.message.text.strip()
    method_key = context.user_data.get("withdraw_method")
    amount = context.user_data.get("withdraw_amount")
    method = WITHDRAW_METHODS.get(method_key)
    
    # Create withdraw request
    wd_req = {
        "user_id": uid,
        "username": update.effective_user.username or "",
        "method": method_key,
        "method_name": method["name"],
        "amount": amount,
        "charge": method["charge"],
        "net_amount": amount - method["charge"],
        "address": address,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    fb_add("withdraw_requests", wd_req)
    
    # Deduct from balance
    user_data = get_user(uid)
    if user_data:
        user_data["earn_balance"] = max(0, user_data.get("earn_balance", 0) - amount)
        user_data["pending_withdraw"] = user_data.get("pending_withdraw", 0) + amount
        save_user(uid, user_data)
    
    # Notify admin
    admin_text = (
        f"🏧 <b>New Withdraw Request!</b>\n\n"
        f"👤 User: @{update.effective_user.username} ({uid})\n"
        f"💰 Amount: ৳{amount}\n"
        f"💸 Net: ৳{amount - method['charge']}\n"
        f"📱 Method: {method['name']}\n"
        f"📬 Address: <code>{address}</code>"
    )
    wd_id = f"WD{int(time.time())}"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"wd_approve_{uid}_{wd_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{uid}_{wd_id}"),
    ]])
    for admin_id in ADMIN_IDS:
        try:
            await update.message.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except: pass
    
    await update.message.reply_text(
        f"✅ <b>Withdrawal requested!</b>\n\n"
        f"💰 Amount: ৳{amount}\n"
        f"💸 Net after charge: ৳{amount - method['charge']}\n"
        f"📱 Method: {method['name']}\n\n"
        f"⏳ Admin will process shortly.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(uid)
    )
    context.user_data.clear()

# ═══════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════
async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    user = update.effective_user
    user_data = get_user(uid) or {}
    
    joined = user_data.get("joined_at", "N/A")[:10] if user_data.get("joined_at") else "N/A"
    earn = user_data.get("earn_balance", 0.0)
    deposit = user_data.get("deposit_balance", 0.0)
    ref_inc = user_data.get("referral_income", 0.0)
    refs = user_data.get("referrals", 0)
    done = user_data.get("completed_tasks", 0)
    
    if lang == "bn":
        text = (
            f"👤 <b>আপনার প্রোফাইল</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 নাম: <b>{user.first_name} {user.last_name or ''}</b>\n"
            f"🔤 ইউজারনেম: @{user.username or 'N/A'}\n"
            f"🆔 Chat ID: <code>{uid}</code>\n"
            f"📅 যোগদান: {joined}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 উপার্জন ব্যালেন্স: ৳{earn:.2f}\n"
            f"💎 ডিপোজিট: ৳{deposit:.2f}\n"
            f"🔗 রেফারেল ইনকাম: ৳{ref_inc:.2f}\n"
            f"👥 রেফারেল: {refs}\n"
            f"✅ সম্পন্ন কাজ: {done}\n\n"
            f"🌐 ভাষা: {'🇧🇩 বাংলা' if lang=='bn' else '🇬🇧 English'}"
        )
    else:
        text = (
            f"👤 <b>Your Profile</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 Name: <b>{user.first_name} {user.last_name or ''}</b>\n"
            f"🔤 Username: @{user.username or 'N/A'}\n"
            f"🆔 Chat ID: <code>{uid}</code>\n"
            f"📅 Joined: {joined}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Earn Balance: ৳{earn:.2f}\n"
            f"💎 Deposit Balance: ৳{deposit:.2f}\n"
            f"🔗 Referral Income: ৳{ref_inc:.2f}\n"
            f"👥 Referrals: {refs}\n"
            f"✅ Completed Tasks: {done}\n\n"
            f"🌐 Language: 🇬🇧 English"
        )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 Change Language", callback_data="change_lang"),
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ═══════════════════════════════════════════
#  REFERRAL
# ═══════════════════════════════════════════
async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    user_data = get_user(uid) or {}
    
    ref_link = f"https://t.me/{context.bot.username}?start={uid}"
    refs = user_data.get("referrals", 0)
    ref_inc = user_data.get("referral_income", 0.0)
    percent = SETTINGS.get("ref_percent", 10)
    
    if lang == "bn":
        text = (
            f"🔗 <b>আপনার রেফারেল</b>\n\n"
            f"🔗 আপনার লিংক:\n{ref_link}\n\n"
            f"⚙️ মোট রেফারেল: {refs}\n"
            f"💚 রেফারেল আয়: ৳{ref_inc:.2f}\n"
            f"🏆 কমিশন হার: {percent}%\n\n"
            f"📢 বন্ধুদের শেয়ার করুন এবং প্রতি রেফারেলে {percent}% কমিশন পান!"
        )
    else:
        text = (
            f"🔗 <b>Your Referrals</b>\n\n"
            f"🔗 Your Link:\n{ref_link}\n\n"
            f"⚙️ Total Referrals: {refs}\n"
            f"💚 Referral Income: ৳{ref_inc:.2f}\n"
            f"🏆 Commission Rate: {percent}%\n\n"
            f"📢 Share with friends and earn {percent}% commission per referral!"
        )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ═══════════════════════════════════════════
#  LEADERBOARD
# ═══════════════════════════════════════════
async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    
    # Get top users
    users_list = fb_all("users", 100)
    if not users_list:
        users_list = [{"user_id":"demo","username":"Nn","completed_tasks":120},
                      {"user_id":"demo2","username":"Md","completed_tasks":71}]
    
    users_sorted = sorted(users_list, key=lambda x: x.get("completed_tasks", 0), reverse=True)[:5]
    prizes = SETTINGS.get("lb_prizes", [600, 300, 200, 100, 50])
    medals = ["🥇", "🥈", "🥉", "🏅", "🎖️"]
    
    # Next reset (Friday 9PM)
    now = datetime.now()
    days_to_friday = (4 - now.weekday()) % 7
    if days_to_friday == 0 and now.hour >= 21:
        days_to_friday = 7
    remaining_seconds = days_to_friday * 86400 + (21 - now.hour) * 3600 - now.minute * 60
    days_left = remaining_seconds // 86400
    hours_left = (remaining_seconds % 86400) // 3600
    mins_left = (remaining_seconds % 3600) // 60
    
    if lang == "bn":
        text = "🏆 <b>সাপ্তাহিক লিডারবোর্ড — টপ ৫ (সঠিক কাজ)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for i, u in enumerate(users_sorted):
            prize = prizes[i] if i < len(prizes) else 0
            text += f"{medals[i]} <b>{u.get('username', 'User')}</b> — {u.get('completed_tasks', 0)}টি কাজ (পুরস্কার: ৳{prize})\n"
        text += f"\n⏰ আর মাত্র {days_left} দিন {hours_left} ঘন্টা {mins_left} মিনিট বাকি!\n\n"
        text += "<i>(প্রতি সপ্তাহে লিডারবোর্ডে থাকা Top 5 জনকে পুরস্কৃত করা হবে। লিডারবোর্ড প্রতি শুক্রবার রাত ৯টায় রিসেট হয়)</i>"
    else:
        text = "🏆 <b>Weekly Leaderboard — Top 5 (Verified Tasks)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for i, u in enumerate(users_sorted):
            prize = prizes[i] if i < len(prizes) else 0
            text += f"{medals[i]} <b>{u.get('username', 'User')}</b> — {u.get('completed_tasks', 0)} tasks (Prize: ৳{prize})\n"
        text += f"\n⏰ {days_left}d {hours_left}h {mins_left}m remaining!\n\n"
        text += "<i>(Top 5 users rewarded weekly. Resets every Friday at 9PM)</i>"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏅 My Rank", callback_data="my_rank"),
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ═══════════════════════════════════════════
#  BUY PRODUCT
# ═══════════════════════════════════════════
async def buy_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    
    if lang == "bn":
        text = "🛒 <b>কোন প্রোডাক্ট কিনতে চান?</b>"
    else:
        text = "🛒 <b>What would you like to buy?</b>"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 TrustedMail", callback_data="buy_mail"),
         InlineKeyboardButton("🔑 All VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton("🌐 IP-PROXY", callback_data="buy_proxy"),
         InlineKeyboardButton("📱 Premium App", callback_data="buy_app")],
        [InlineKeyboardButton("🦉 Owl Proxy", callback_data="buy_owl")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def buy_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cat = query.data.replace("buy_", "")
    await query.answer()
    uid = str(query.from_user.id)
    
    # VPN products
    vpn_products = [
        ("Atlas VPN - 7d", 25, 740), ("Avast VPN - 7d", 25, 803),
        ("Betternet VPN - 7d", 25, 868), ("Nord VPN - 7D", 25, 757),
        ("Express VPN - 3D", 15, 744), ("Proton VPN - 14D", 50, 878),
        ("Surfshark VPN - 7D", 25, 811), ("PIA VPN - 7d", 25, 964),
        ("HMA VPN - 7D", 25, 539), ("IP Vanish - 7D", 30, 648),
        ("Panda VPN - 3d", 15, 885), ("Octohide VPN - 14d", 50, 887),
    ]
    proxy_products = [
        ("KAFKA Proxy 1GB", 110, 774), ("Nodemaven 120MB", 50, 866),
        ("Nodemaven 240MB", 90, 676), ("Nodemaven 500MB", 180, 670),
        ("Nodemaven 1GB", 350, 349), ("Rapid Proxy 200MB", 40, 261),
        ("Rapid Proxy 500MB", 80, 122), ("ABC Proxy 1GB", 290, 889),
        ("Rocket Proxy 1GB", 170, 893), ("Mesh Proxy 1GB", 160, 382),
    ]
    
    cat_map = {"vpn": vpn_products, "proxy": proxy_products}
    products = cat_map.get(cat, vpn_products)
    
    buttons = []
    for name, price, stock in products:
        emoji = "🔑" if cat == "vpn" else "🌐"
        buttons.append([InlineKeyboardButton(
            f"💎 {name} | {price} | Stock: {stock}",
            callback_data=f"buy_item_{name.replace(' ', '_')}_{price}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="buy_back")])
    
    text = f"🛒 <b>সাব-প্রোডাক্ট সিলেক্ট করুন:</b>"
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def buy_item_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    price = int(parts[-1])
    name = " ".join(parts[2:-1]).replace("_", " ")
    await query.answer()
    uid = str(query.from_user.id)
    
    user_data = get_user(uid) or {}
    dep_balance = user_data.get("deposit_balance", 0.0)
    
    if dep_balance < price:
        await query.edit_message_text(
            f"❌ <b>Insufficient deposit balance!</b>\n\n"
            f"💎 Product: {name}\n"
            f"💰 Price: ৳{price}\n"
            f"💎 Your balance: ৳{dep_balance:.2f}\n\n"
            f"Please deposit first.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 Deposit", callback_data="wallet_deposit"),
                InlineKeyboardButton("🔙 Back", callback_data="buy_back"),
            ]])
        )
        return
    
    context.user_data["buy_item"] = {"name": name, "price": price}
    
    text = (
        f"🛒 <b>Confirm Purchase</b>\n\n"
        f"📦 Product: <b>{name}</b>\n"
        f"💰 Price: <b>৳{price}</b>\n"
        f"💎 Your balance: ৳{dep_balance:.2f}\n\n"
        f"⚠️ An admin will deliver your order after confirmation."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="buy_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="buy_back")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⌛ Processing...")
    uid = str(query.from_user.id)
    
    item = context.user_data.get("buy_item")
    if not item:
        await query.edit_message_text("❌ Session expired.")
        return
    
    user_data = get_user(uid)
    if user_data:
        user_data["deposit_balance"] = max(0, user_data.get("deposit_balance", 0) - item["price"])
        save_user(uid, user_data)
    
    # Create order
    order = {
        "user_id": uid,
        "username": query.from_user.username or "",
        "product": item["name"],
        "price": item["price"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    fb_add("product_orders", order)
    
    # Notify admin
    admin_text = (
        f"🛒 <b>New Product Order!</b>\n\n"
        f"👤 User: @{query.from_user.username} ({uid})\n"
        f"📦 Product: {item['name']}\n"
        f"💰 Amount: ৳{item['price']}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await query.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
        except: pass
    
    await query.edit_message_text(
        f"✅ <b>Order placed!</b>\n\n"
        f"📦 {item['name']}\n"
        f"💰 ৳{item['price']}\n\n"
        f"⏳ Admin will deliver soon.",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()

# ═══════════════════════════════════════════
#  LANGUAGE CHANGE
# ═══════════════════════════════════════════
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    uid = str(update.effective_user.id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")],
    ])
    text = "🌐 আপনার পছন্দের ভাষা নির্বাচন করুন:\nSelect your preferred language:"
    
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.data.split("_")[-1]
    await query.answer()
    uid = str(query.from_user.id)
    
    user_data = get_user(uid) or {}
    user_data["language"] = lang
    save_user(uid, user_data)
    
    msg = "✅ ভাষা বাংলা করা হয়েছে।" if lang == "bn" else "✅ Language changed to English."
    await query.edit_message_text(msg)

# ═══════════════════════════════════════════
#  ADMIN PANEL
# ═══════════════════════════════════════════
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if not is_admin(int(uid)):
        await update.message.reply_text("❌ Access denied.")
        return
    
    # Stats
    users_list = fb_all("users", 200)
    subs_list = fb_all("task_submissions", 200)
    
    total_users = len(users_list) or len(USERS) or 0
    total_subs = len(subs_list) or len(SUBMISSIONS) or 0
    pending = sum(1 for s in subs_list if s.get("status") == "pending")
    approved = sum(1 for s in subs_list if s.get("status") == "approved")
    
    text = (
        f"👑 <b>Admin Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"📋 Total Submissions: <b>{total_subs}</b>\n"
        f"⏳ Pending Review: <b>{pending}</b>\n"
        f"✅ Approved: <b>{approved}</b>\n\n"
        f"Choose an action:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 User List", callback_data="adm_users"),
         InlineKeyboardButton("📋 Pending Tasks", callback_data="adm_pending")],
        [InlineKeyboardButton("💰 Approve Payment", callback_data="adm_pay"),
         InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔍 Search User", callback_data="adm_search"),
         InlineKeyboardButton("💎 Add Balance", callback_data="adm_add_bal")],
        [InlineKeyboardButton("⚙️ Task Settings", callback_data="adm_settings"),
         InlineKeyboardButton("📦 Add IG Account", callback_data="adm_add_ig")],
        [InlineKeyboardButton("📊 Export Data", callback_data="adm_export"),
         InlineKeyboardButton("🔄 Reset Leaderboard", callback_data="adm_lb_reset")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def admin_pending_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subs = fb_all("task_submissions", 50)
    pending = [s for s in subs if s.get("status") == "pending"]
    
    if not pending:
        await query.edit_message_text("✅ No pending tasks!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]]))
        return
    
    text = f"⏳ <b>Pending Tasks ({len(pending)})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for s in pending[:10]:
        text += f"• @{s.get('username', s.get('user_id', '?'))} — {s.get('task_type', '?').upper()} — ID: {s.get('id', '?')[:8]}\n"
    
    if len(pending) > 10:
        text += f"\n...and {len(pending)-10} more"
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]]))

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    if not is_admin(int(uid)):
        return
    
    context.user_data["state"] = "admin_broadcast"
    await query.edit_message_text(
        "📢 <b>Broadcast Message</b>\n\n"
        "Send the message you want to broadcast to all users:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
    )

async def admin_handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "admin_broadcast":
        return
    if not is_admin(update.effective_user.id):
        return
    
    message = update.message.text
    users_list = fb_all("users", 500)
    
    sent = 0
    failed = 0
    status_msg = await update.message.reply_text(f"📢 Sending to {len(users_list)} users...")
    
    for user in users_list:
        try:
            await context.bot.send_message(int(user["user_id"]), message, parse_mode=ParseMode.HTML)
            sent += 1
        except:
            failed += 1
        
        if sent % 20 == 0:
            await status_msg.edit_text(f"📢 Progress: {sent}/{len(users_list)}")
            await asyncio.sleep(0.5)
    
    await status_msg.edit_text(f"✅ Broadcast done!\n\n✉️ Sent: {sent}\n❌ Failed: {failed}")
    context.user_data.clear()

async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = "admin_search"
    await query.edit_message_text(
        "🔍 Enter username or user ID to search:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
    )

async def admin_handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "admin_search":
        return
    if not is_admin(update.effective_user.id):
        return
    
    query_str = update.message.text.strip().lstrip("@")
    users_list = fb_all("users", 200)
    
    found = [u for u in users_list if
             query_str.lower() in (u.get("username", "") or "").lower() or
             query_str == str(u.get("user_id", ""))]
    
    if not found:
        await update.message.reply_text("❌ User not found.")
        return
    
    u = found[0]
    earn = u.get("earn_balance", 0.0)
    dep = u.get("deposit_balance", 0.0)
    done = u.get("completed_tasks", 0)
    banned = u.get("banned", False)
    uid_found = u.get("user_id")
    
    text = (
        f"👤 <b>User Found</b>\n\n"
        f"🆔 ID: <code>{uid_found}</code>\n"
        f"👤 @{u.get('username', 'N/A')}\n"
        f"📛 {u.get('first_name', '')} {u.get('last_name', '')}\n"
        f"💰 Earn: ৳{earn:.2f}\n"
        f"💎 Deposit: ৳{dep:.2f}\n"
        f"✅ Tasks: {done}\n"
        f"🚫 Banned: {'Yes' if banned else 'No'}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_addbal_{uid_found}"),
         InlineKeyboardButton("➖ Deduct", callback_data=f"adm_deduct_{uid_found}")],
        [InlineKeyboardButton("🚫 Ban" if not banned else "✅ Unban", callback_data=f"adm_ban_{uid_found}")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    context.user_data.clear()

async def admin_add_ig_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    context.user_data["state"] = "admin_add_ig"
    await query.edit_message_text(
        "📸 <b>Add Instagram Accounts</b>\n\n"
        "Format: username|password (one per line)\n\n"
        "Example:\n<code>ig_user123|password123\nig_user456|pass456</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
    )

async def admin_handle_add_ig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "admin_add_ig":
        return
    if not is_admin(update.effective_user.id):
        return
    
    lines = update.message.text.strip().split("\n")
    added = 0
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) >= 2:
            IG_ACCOUNTS.append({"username": parts[0].strip(), "password": parts[1].strip(), "status": "available"})
            added += 1
    
    await update.message.reply_text(f"✅ Added {added} Instagram accounts!\nTotal available: {sum(1 for a in IG_ACCOUNTS if a['status']=='available')}")
    context.user_data.clear()

async def admin_export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export task data as Excel"""
    query = update.callback_query
    await query.answer("⌛ Generating Excel...")
    
    subs = fb_all("task_submissions", 500)
    if not subs:
        subs = list(SUBMISSIONS.values())
    
    # Instagram data
    ig_data = [[
        "#", "Username", "Password", "2FA Secret", "Submitted By", "Date"
    ]]
    fb_data_rows = [[
        "#", "First Name", "Last Name", "Password", "UID", "Cookie", "Date"
    ]]
    
    ig_count = 0
    fb_count = 0
    
    for s in subs:
        if s.get("task_type") == "instagram":
            ig_count += 1
            ig_data.append([
                ig_count,
                s.get("ig_username", ""),
                s.get("ig_password", ""),
                s.get("totp_secret", ""),
                s.get("username", s.get("user_id", "")),
                s.get("created_at", "")[:10],
            ])
        elif s.get("task_type") == "facebook":
            fb_count += 1
            fb_data_rows.append([
                fb_count,
                s.get("fb_first_name", ""),
                s.get("fb_last_name", ""),
                s.get("fb_password", ""),
                s.get("fb_uid", ""),
                s.get("fb_cookie_full", s.get("fb_cookie", ""))[:100],
                s.get("created_at", "")[:10],
            ])
    
    # Create Excel in memory
    import openpyxl
    from io import BytesIO
    
    wb = openpyxl.Workbook()
    
    # Instagram sheet
    ws_ig = wb.active
    ws_ig.title = "Instagram"
    for row in ig_data:
        ws_ig.append(row)
    
    # Facebook sheet
    ws_fb = wb.create_sheet("Facebook")
    for row in fb_data_rows:
        ws_fb.append(row)
    
    # Save to buffer
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    filename = f"task_data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    await query.message.reply_document(
        document=buf,
        filename=filename,
        caption=f"📊 Task Data Export\n\n📸 Instagram: {ig_count} records\n📘 Facebook: {fb_count} records"
    )

async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_uid = query.data.split("_")[-1]
    await query.answer()
    
    user_data = get_user(target_uid) or {}
    current_banned = user_data.get("banned", False)
    user_data["banned"] = not current_banned
    save_user(target_uid, user_data)
    
    action = "Unbanned" if current_banned else "Banned"
    await query.edit_message_text(f"{'✅' if current_banned else '🚫'} User {target_uid} {action}!")

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[2]  # addbal or deduct
    target_uid = parts[3]
    await query.answer()
    
    context.user_data["state"] = f"admin_{action}"
    context.user_data["target_uid"] = target_uid
    
    await query.edit_message_text(
        f"{'➕ Enter amount to add:' if action=='addbal' else '➖ Enter amount to deduct:'}\n"
        f"User: {target_uid}"
    )

async def admin_handle_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state not in ("admin_addbal", "admin_deduct"):
        return
    if not is_admin(update.effective_user.id):
        return
    
    target_uid = context.user_data.get("target_uid")
    try:
        amount = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Invalid amount")
        return
    
    user_data = get_user(target_uid) or {}
    if state == "admin_addbal":
        user_data["earn_balance"] = user_data.get("earn_balance", 0) + amount
        action = f"Added ৳{amount}"
    else:
        user_data["earn_balance"] = max(0, user_data.get("earn_balance", 0) - amount)
        action = f"Deducted ৳{amount}"
    
    save_user(target_uid, user_data)
    
    # Notify user
    try:
        msg = f"💰 Your balance has been updated!\n{action}"
        await context.bot.send_message(int(target_uid), msg)
    except: pass
    
    await update.message.reply_text(f"✅ Done! {action} for user {target_uid}")
    context.user_data.clear()

# ═══════════════════════════════════════════
#  DEPOSIT/WITHDRAW ADMIN APPROVE
# ═══════════════════════════════════════════
async def admin_deposit_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[1]  # approve or reject
    user_id = parts[2]
    trx_id = parts[3]
    amount = int(parts[4]) if action == "approve" and len(parts) > 4 else 0
    await query.answer()
    
    if action == "approve":
        user_data = get_user(user_id) or {}
        user_data["deposit_balance"] = user_data.get("deposit_balance", 0) + amount
        save_user(user_id, user_data)
        
        try:
            await context.bot.send_message(int(user_id),
                f"🎉 <b>ডিপোজিট অনুমোদিত!</b>\n\n"
                f"💎 +{amount} diamonds added to your balance!\n"
                f"🔢 TRX: {trx_id}",
                parse_mode=ParseMode.HTML)
        except: pass
        
        await query.edit_message_text(f"✅ Approved! +{amount}💎 for user {user_id}")
    else:
        try:
            await context.bot.send_message(int(user_id),
                f"❌ Deposit rejected.\nTRX: {trx_id}\nContact support for help.")
        except: pass
        await query.edit_message_text(f"❌ Rejected deposit for {user_id}")

async def admin_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[1]  # approve or reject
    user_id = parts[2]
    await query.answer()
    
    if action == "approve":
        try:
            await context.bot.send_message(int(user_id),
                "✅ <b>Withdrawal approved!</b>\nYour payment has been processed.",
                parse_mode=ParseMode.HTML)
        except: pass
        await query.edit_message_text(f"✅ Withdraw approved for {user_id}")
    else:
        user_data = get_user(user_id) or {}
        # Restore balance
        pending = user_data.get("pending_withdraw", 0)
        user_data["earn_balance"] = user_data.get("earn_balance", 0) + pending
        user_data["pending_withdraw"] = 0
        save_user(user_id, user_data)
        
        try:
            await context.bot.send_message(int(user_id),
                "❌ Withdrawal rejected. Balance restored.")
        except: pass
        await query.edit_message_text(f"❌ Withdraw rejected for {user_id}, balance restored")

# ═══════════════════════════════════════════
#  SUPPORT + MISC
# ═══════════════════════════════════════════
async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    
    if lang == "bn":
        text = f"💬 <b>সাপোর্ট</b>\n\nযেকোনো সমস্যায় আমাদের সাপোর্ট গ্রুপে যোগ দিন:\n{SUPPORT_LINK}"
    else:
        text = f"💬 <b>Support</b>\n\nFor any issues, join our support group:\n{SUPPORT_LINK}"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 Support Group", url=SUPPORT_LINK)
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def notify_admin_new_submission(bot, submission, sub_id):
    """Notify admin of new task submission"""
    task_type = submission.get("task_type", "unknown")
    uid = submission.get("user_id")
    username = submission.get("username", uid)
    
    if task_type == "instagram":
        details = f"👤 IG Username: {submission.get('ig_username', 'N/A')}"
    else:
        details = f"🔢 FB UID: {submission.get('fb_uid', 'N/A')}"
    
    text = (
        f"📥 <b>New {task_type.title()} Task!</b>\n\n"
        f"👤 User: @{username} ({uid})\n"
        f"{details}\n"
        f"💰 Amount: ৳{submission.get('amount', 0)}\n"
        f"🆔 Sub ID: {sub_id}"
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_sub_{sub_id}_{uid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_sub_{sub_id}_{uid}"),
    ]])
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except: pass

async def approve_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    sub_id = parts[2]
    user_id = parts[3]
    await query.answer("✅ Approving...")
    
    # Get submission
    sub = SUBMISSIONS.get(sub_id) or fb_get("task_submissions", sub_id)
    if not sub:
        await query.edit_message_text("❌ Submission not found")
        return
    
    amount = float(sub.get("amount", 0))
    
    # Update submission status
    fb_set("task_submissions", sub_id, {"status": "approved"})
    if sub_id in SUBMISSIONS:
        SUBMISSIONS[sub_id]["status"] = "approved"
    
    # Add balance to user
    user_data = get_user(user_id) or {}
    user_data["earn_balance"] = user_data.get("earn_balance", 0) + amount
    user_data["completed_tasks"] = user_data.get("completed_tasks", 0) + 1
    user_data["total_earned"] = user_data.get("total_earned", 0) + amount
    user_data["pending_tasks"] = max(0, user_data.get("pending_tasks", 0) - 1)
    save_user(user_id, user_data)
    
    # Handle referral commission
    referrer_id = user_data.get("referred_by")
    if referrer_id:
        ref_data = get_user(referrer_id) or {}
        commission = amount * SETTINGS.get("ref_percent", 10) / 100
        ref_data["earn_balance"] = ref_data.get("earn_balance", 0) + commission
        ref_data["referral_income"] = ref_data.get("referral_income", 0) + commission
        save_user(referrer_id, ref_data)
        try:
            await context.bot.send_message(int(referrer_id),
                f"🎉 Referral commission: ৳{commission:.2f} earned!")
        except: pass
    
    # Notify user
    try:
        await context.bot.send_message(int(user_id),
            f"✅ <b>Task Approved!</b>\n\n"
            f"💰 ৳{amount:.2f} added to your balance!\n"
            f"💵 New balance: ৳{user_data['earn_balance']:.2f}",
            parse_mode=ParseMode.HTML)
    except: pass
    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Approved (+৳{amount})", callback_data="done")
    ]]))

async def reject_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    sub_id = parts[2]
    user_id = parts[3]
    await query.answer("❌ Rejecting...")
    
    fb_set("task_submissions", sub_id, {"status": "rejected"})
    if sub_id in SUBMISSIONS:
        SUBMISSIONS[sub_id]["status"] = "rejected"
    
    user_data = get_user(user_id) or {}
    user_data["rejected_tasks"] = user_data.get("rejected_tasks", 0) + 1
    user_data["pending_tasks"] = max(0, user_data.get("pending_tasks", 0) - 1)
    save_user(user_id, user_data)
    
    try:
        await context.bot.send_message(int(user_id),
            "❌ <b>Task Rejected.</b>\n\nYour submission was not approved. Contact support for details.",
            parse_mode=ParseMode.HTML)
    except: pass
    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Rejected", callback_data="done")
    ]]))

# ═══════════════════════════════════════════
#  CALLBACK ROUTER
# ═══════════════════════════════════════════
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # Task flows
    if data == "task_ig":
        await ig_task_start(update, context)
    elif data == "ig_gen_2fa":
        await ig_request_secret(update, context)
    elif data == "ig_refresh_code":
        await ig_refresh_code(update, context)
    elif data == "ig_submit":
        await ig_submit_task(update, context)
    elif data in ("ig_cancel", "fb_cancel", "cancel_bulk"):
        await query.answer("Cancelled")
        await query.edit_message_text("❌ Cancelled.", reply_markup=None)
        context.user_data.clear()
    elif data == "task_fb":
        await fb_task_start(update, context)
    elif data == "fb_sub_number":
        await fb_sub_number(update, context)
    elif data == "fb_start_cookie":
        await fb_start_cookie(update, context)
    elif data == "fb_ask_uid":
        await fb_ask_uid(update, context)
    elif data == "fb_submit":
        await fb_submit_task(update, context)
    elif data == "task_bulk":
        await bulk_submit_menu(update, context)
    elif data == "bulk_ig":
        await bulk_ig_ask(update, context)
    elif data == "bulk_fb":
        await bulk_fb_ask(update, context)
    # Wallet
    elif data == "wallet_deposit":
        await deposit_start(update, context)
    elif data == "wallet_withdraw":
        await withdraw_start(update, context)
    elif data.startswith("wd_method_"):
        await withdraw_method_selected(update, context)
    elif data == "wallet_back":
        await query.edit_message_text("Cancelled.")
        context.user_data.clear()
    # Admin
    elif data == "check_join":
        joined = await check_joined(context, query.from_user.id)
        if joined:
            await query.edit_message_text("✅ Verified! Use /start to begin.")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)
    elif data == "adm_pending":
        await admin_pending_tasks(update, context)
    elif data == "adm_broadcast":
        await admin_broadcast_start(update, context)
    elif data == "adm_search":
        await admin_search_user(update, context)
    elif data == "adm_add_ig":
        await admin_add_ig_account(update, context)
    elif data == "adm_export":
        await admin_export_data(update, context)
    elif data.startswith("adm_ban_"):
        await admin_ban_user(update, context)
    elif data.startswith("adm_addbal_") or data.startswith("adm_deduct_"):
        await admin_add_balance(update, context)
    elif data.startswith("approve_sub_"):
        await approve_submission(update, context)
    elif data.startswith("reject_sub_"):
        await reject_submission(update, context)
    elif data.startswith("dep_approve_"):
        await admin_deposit_action(update, context)
    elif data.startswith("dep_reject_"):
        await admin_deposit_action(update, context)
    elif data.startswith("wd_approve_"):
        await admin_withdraw_action(update, context)
    elif data.startswith("wd_reject_"):
        await admin_withdraw_action(update, context)
    elif data == "change_lang":
        await change_language(update, context)
    elif data.startswith("set_lang_"):
        await set_language(update, context)
    elif data == "buy_back":
        await buy_product_handler_cb(update, context)
    elif data.startswith("buy_"):
        cat = data.replace("buy_", "")
        if cat in ("vpn", "proxy", "mail", "app", "owl"):
            await buy_category(update, context)
        elif cat.startswith("item_"):
            await buy_item_selected(update, context)
        elif cat == "confirm":
            await buy_confirm(update, context)
    elif data == "adm_back":
        await query.edit_message_text("🔙 Back to admin.", reply_markup=None)
    elif data == "done":
        await query.answer()
    else:
        await query.answer()

async def buy_product_handler_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = str(query.from_user.id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 TrustedMail", callback_data="buy_mail"),
         InlineKeyboardButton("🔑 All VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton("🌐 IP-PROXY", callback_data="buy_proxy"),
         InlineKeyboardButton("📱 Premium App", callback_data="buy_app")],
    ])
    await query.edit_message_text("🛒 <b>What would you like to buy?</b>", parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ═══════════════════════════════════════════
#  MESSAGE ROUTER
# ═══════════════════════════════════════════
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    uid = str(update.effective_user.id)
    lang = get_user_lang(uid)
    
    # Check banned
    if is_banned(uid):
        await update.message.reply_text("🚫 Your account has been banned.")
        return
    
    # Handle states first
    state = context.user_data.get("state")
    if state == "awaiting_totp_key":
        await ig_handle_secret(update, context)
        return
    if state == "awaiting_fb_uid":
        await fb_handle_uid(update, context)
        return
    if state == "awaiting_fb_cookie":
        await fb_handle_cookie(update, context)
        return
    if state == "awaiting_trx_id":
        await deposit_handle_trx(update, context)
        return
    if state == "awaiting_withdraw_amount":
        await withdraw_handle_amount(update, context)
        return
    if state == "awaiting_withdraw_address":
        await withdraw_handle_address(update, context)
        return
    if state == "bulk_ig_paste":
        await handle_bulk_paste(update, context)
        return
    if state == "bulk_fb_paste":
        await handle_bulk_paste(update, context)
        return
    if state == "admin_broadcast":
        await admin_handle_broadcast(update, context)
        return
    if state == "admin_search":
        await admin_handle_search(update, context)
        return
    if state in ("admin_addbal", "admin_deduct"):
        await admin_handle_balance_amount(update, context)
        return
    if state == "admin_add_ig":
        await admin_handle_add_ig(update, context)
        return
    
    # Menu buttons (both bn and en)
    if text in ("📋 কাজ", "📋 Tasks"):
        await tasks_menu(update, context)
    elif text in ("💰 ওয়ালেট", "💰 Wallet"):
        await wallet_handler(update, context)
    elif text in ("👤 প্রোফাইল", "👤 Profile"):
        await profile_handler(update, context)
    elif text in ("🛒 পণ্য কিনুন", "🛒 Buy Product"):
        await buy_product_handler(update, context)
    elif text in ("🔗 রেফারেল", "🔗 My Referrals"):
        await referral_handler(update, context)
    elif text in ("🏆 লিডারবোর্ড", "🏆 Leaderboard"):
        await leaderboard_handler(update, context)
    elif text in ("💬 সাপোর্ট", "💬 Support"):
        await support_handler(update, context)
    elif text in ("🌐 ভাষা পরিবর্তন", "🌐 Change Language"):
        await change_language(update, context)
    elif text in ("👑 এডমিন প্যানেল", "👑 Admin Panel"):
        await admin_panel(update, context)
    elif text in ("📢 ব্রডকাস্ট", "📢 Broadcast"):
        if is_admin(update.effective_user.id):
            context.user_data["state"] = "admin_broadcast"
            await update.message.reply_text("📢 Send the message to broadcast:")
    elif text in ("❌ বাতিল", "❌ Cancel"):
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled.", reply_markup=main_menu_keyboard(uid))
    elif text in ("🏠 মেইন মেনু", "🏠 Main Menu"):
        context.user_data.clear()
        name = update.effective_user.first_name or "User"
        await update.message.reply_text(
            t(uid, "welcome", name=name),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(uid)
        )
    else:
        # Unknown message — show menu
        await update.message.reply_text(
            "Use the menu below 👇",
            reply_markup=main_menu_keyboard(uid)
        )

# ═══════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════
import asyncio

def main():
    init_firebase()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    
    # Callback queries
    app.add_handler(CallbackQueryHandler(callback_router))
    
    # All text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    
    logger.info("🤖 BD TopSell Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
