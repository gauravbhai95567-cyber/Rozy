from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from helpers import box, SPARK, INFO, BACK, LINE

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Commands", callback_data="menu_help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
    ])

PAGES = {
    "h_admin": ("🛡 Admin", "/promote /demote /pin /adminlist /id"),
    "h_bans": ("🔨 Bans", "/ban /unban /kick"),
    "h_mute": ("🔇 Mute", "/mute /unmute /tmute 5m"),
    "h_warn": ("⚠️ Warns", "/warn /warns /resetwarns"),
    "h_locks": ("🔒 Locks", "/lock text|media|stickers|polls|links|invites|all"),
    "h_bl": ("🚫 Blacklist", "/blacklist add|remove|list <word>\n/blacklistuser add|remove"),
    "h_filters": ("💬 Filters", "/filter add hello Hi!\n/filter remove hello\n/filters"),
    "h_notes": ("📝 Notes", "/save name content\n/get name\n/notes\n#name shortcut"),
    "h_welcome": ("👋 Welcome", "/setwelcome {mention}!\n/setgoodbye Bye {first}\n/welcomebtn Text|url"),
    "h_auto": ("🤖 Automation", "/captcha on\n/antispam on\n/antiflood 5 10\n/nightmode on"),
    "h_music": ("🎵 Music", "/play <link/name>\n/video <link/name>\n/pause /resume /skip /stop"),
    "h_ai": ("🧠 AI", "/ai <question>\n/chatbot on\n/resetai"),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    txt = box(f"{SPARK} <b>MissRose Pro</b>",
              f"Namaste <b>{u.first_name}</b>!\nGroup manager + Music + AI.")
    await update.message.reply_text(txt, reply_markup=kb_main(), parse_mode=ParseMode.HTML)

async def help_cmd(update, context):
    rows = [
        [InlineKeyboardButton("🛡 Admin", "h_admin"), InlineKeyboardButton("🔨 Bans", "h_bans")],
        [InlineKeyboardButton("🔇 Mute", "h_mute"), InlineKeyboardButton("⚠️ Warns", "h_warn")],
        [InlineKeyboardButton("🔒 Locks", "h_locks"), InlineKeyboardButton("🚫 Blacklist", "h_bl")],
        [InlineKeyboardButton("💬 Filters", "h_filters"), InlineKeyboardButton("📝 Notes", "h_notes")],
        [InlineKeyboardButton("👋 Welcome", "h_welcome"), InlineKeyboardButton("🤖 Automation", "h_auto")],
        [InlineKeyboardButton("🎵 Music", "h_music"), InlineKeyboardButton("🧠 AI", "h_ai")],
    ]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in row] for row in rows])
    await update.message.reply_text(box(f"{SPARK} Categories", "Chuno 👇"),
                                    reply_markup=kb, parse_mode=ParseMode.HTML)

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "menu_about":
        txt = box(f"{INFO} About", "MissRose Pro v2\nPython + PTB + pytgcalls")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(BACK, callback_data="menu_main")]])
        return await q.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
    if q.data == "menu_main":
        return await q.edit_message_text(box(f"{SPARK} MissRose Pro", "Menu:"),
                                         reply_markup=kb_main(), parse_mode=ParseMode.HTML)
    if q.data == "menu_help":
        rows = [
            [InlineKeyboardButton("🛡 Admin", "h_admin"), InlineKeyboardButton("🔨 Bans", "h_bans")],
            [InlineKeyboardButton("🔇 Mute", "h_mute"), InlineKeyboardButton("⚠️ Warns", "h_warn")],
            [InlineKeyboardButton("🔒 Locks", "h_locks"), InlineKeyboardButton("🚫 Blacklist", "h_bl")],
            [InlineKeyboardButton("💬 Filters", "h_filters"), InlineKeyboardButton("📝 Notes", "h_notes")],
            [InlineKeyboardButton("👋 Welcome", "h_welcome"), InlineKeyboardButton("🤖 Automation", "h_auto")],
            [InlineKeyboardButton("🎵 Music", "h_music"), InlineKeyboardButton("🧠 AI", "h_ai")],
            [InlineKeyboardButton(BACK, callback_data="menu_main")],
        ]
        kb = InlineKeyboardMarkup(rows)
        return await q.edit_message_text(box(f"{SPARK} Categories", "Chuno 👇"),
                                         reply_markup=kb, parse_mode=ParseMode.HTML)
    if q.data in PAGES:
        title, body = PAGES[q.data]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(BACK, callback_data="menu_help")]])
        return await q.edit_message_text(box(title, body), reply_markup=kb, parse_mode=ParseMode.HTML)

def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(cb))