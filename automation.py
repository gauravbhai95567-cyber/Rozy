from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from helpers import *
from db import connect, get_group, set_group, ensure_group
import random

LOCK_TYPES = ["text","media","stickers","polls","links","invites","all"]

# -------- LOCKS --------
async def apply_locks(chat_id, context):
    with connect() as c:
        rows = c.execute("SELECT lock_type FROM locks WHERE chat_id=?", (chat_id,)).fetchall()
    locked = {r["lock_type"] for r in rows}
    def free(k): return k not in locked and "all" not in locked
    perms = ChatPermissions(
        can_send_messages=free("text"),
        can_send_media_messages=free("media"),
        can_send_polls=free("polls"),
        can_send_other_messages=free("stickers"),
        can_add_web_page_previews=free("links"),
        can_invite_users=free("invites"),
    )
    try: await context.bot.set_chat_permissions(chat_id, perms)
    except Exception: pass

async def lock(update, context):
    if not await is_admin(update, context): return
    if not context.args: return await update.message.reply_text(f"{NO} Types: {', '.join(LOCK_TYPES)}")
    lt = context.args[0].lower()
    if lt not in LOCK_TYPES: return
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO locks VALUES(?,?)", (update.effective_chat.id, lt))
    await apply_locks(update.effective_chat.id, context)
    await update.message.reply_text(f"{LOCK} Locked: {lt}")

async def unlock(update, context):
    if not await is_admin(update, context): return
    if not context.args: return
    lt = context.args[0].lower()
    with connect() as c:
        c.execute("DELETE FROM locks WHERE chat_id=? AND lock_type=?", (update.effective_chat.id, lt))
    await apply_locks(update.effective_chat.id, context)
    await update.message.reply_text(f"{UNLOCK} Unlocked: {lt}")

async def locks_cmd(update, context):
    with connect() as c:
        rows = c.execute("SELECT lock_type FROM locks WHERE chat_id=?", (update.effective_chat.id,)).fetchall()
    await update.message.reply_text(box(f"{LOCK} Locks",
        ", ".join(r["lock_type"] for r in rows) or "—"), parse_mode=ParseMode.HTML)

# -------- WELCOME / GOODBYE --------
async def setwelcome(update, context):
    if not await is_admin(update, context): return
    text = " ".join(context.args)
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or update.message.reply_to_message.caption
    if not text: return await update.message.reply_text(f"{NO} Text do.")
    set_group(update.effective_chat.id, welcome=text)
    await update.message.reply_text(f"{OK} Welcome set.")

async def setgoodbye(update, context):
    if not await is_admin(update, context): return
    text = " ".join(context.args)
    if not text: return
    set_group(update.effective_chat.id, goodbye=text)
    await update.message.reply_text(f"{OK} Goodbye set.")

async def setrules(update, context):
    if not await is_admin(update, context): return
    text = " ".join(context.args)
    if not text: return
    set_group(update.effective_chat.id, rules=text)
    await update.message.reply_text(f"{OK} Rules set.")

async def rules_cmd(update, context):
    g = get_group(update.effective_chat.id)
    await update.message.reply_text(box(f"{INFO} Rules", g["rules"] or "—"), parse_mode=ParseMode.HTML)

async def welcomebtn(update, context):
    if not await is_admin(update, context): return
    t = " ".join(context.args)
    if "|" not in t: return await update.message.reply_text(f"{NO} Usage: /welcomebtn Text|url")
    set_group(update.effective_chat.id, welcome_btn=t)
    await update.message.reply_text(f"{OK} Welcome button set.")

# -------- BLACKLIST --------
async def blacklist(update, context):
    chat_id = update.effective_chat.id
    if not context.args:
        return await update.message.reply_text(f"{NO} Usage: /blacklist add|remove|list <word>")
    sub = context.args[0].lower()
    if sub == "list":
        with connect() as c:
            rows = c.execute("SELECT word FROM blacklist_words WHERE chat_id=?", (chat_id,)).fetchall()
        return await update.message.reply_text(box("🚫 Blacklisted",
            "\n".join(f"• <code>{r['word']}</code>" for r in rows) or "—"), parse_mode=ParseMode.HTML)
    if not await is_admin(update, context): return
    if len(context.args) < 2: return
    w = context.args[1].lower()
    with connect() as c:
        if sub == "add": c.execute("INSERT OR IGNORE INTO blacklist_words VALUES(?,?)", (chat_id, w))
        else: c.execute("DELETE FROM blacklist_words WHERE chat_id=? AND word=?", (chat_id, w))
    await update.message.reply_text(f"{OK} {'Added' if sub=='add' else 'Removed'}: {w}")

async def blacklistuser(update, context):
    if not await is_admin(update, context): return
    if not context.args: return
    sub = context.args[0].lower()
    if sub == "list":
        with connect() as c:
            rows = c.execute("SELECT user_id FROM blacklist_users WHERE chat_id=?", (update.effective_chat.id,)).fetchall()
        return await update.message.reply_text("BL users: " + ", ".join(str(r["user_id"]) for r in rows) or "—")
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    with connect() as c:
        if sub == "add": c.execute("INSERT OR IGNORE INTO blacklist_users VALUES(?,?)", (update.effective_chat.id, uid))
        else: c.execute("DELETE FROM blacklist_users WHERE chat_id=? AND user_id=?", (update.effective_chat.id, uid))
    await update.message.reply_text(f"{OK} {sub}: {name}")

# -------- TOGGLES --------
async def captcha_toggle(update, context):
    if not await is_admin(update, context): return
    v = 1 if (context.args and context.args[0].lower()=="on") else 0
    set_group(update.effective_chat.id, captcha=v)
    await update.message.reply_text(f"{OK} Captcha {'ON' if v else 'OFF'}")

async def antispam_toggle(update, context):
    if not await is_admin(update, context): return
    v = 1 if (context.args and context.args[0].lower()=="on") else 0
    set_group(update.effective_chat.id, antispam=v)
    await update.message.reply_text(f"{OK} Antispam {'ON' if v else 'OFF'}")

async def antiflood(update, context):
    if not await is_admin(update, context): return
    if len(context.args) < 2: return
    n, t = int(context.args[0]), int(context.args[1])
    set_group(update.effective_chat.id, antiflood_n=n, antiflood_t=t)
    await update.message.reply_text(f"{OK} Antiflood: {n} msgs / {t}s")

async def nightmode(update, context):
    if not await is_admin(update, context): return
    v = 1 if (context.args and context.args[0].lower()=="on") else 0
    set_group(update.effective_chat.id, night_mode=v)
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, RESTRICT if v else FULL)
    except Exception: pass
    await update.message.reply_text(f"{OK} Night mode {'ON' if v else 'OFF'}")

async def disable(update, context):
    if not await is_admin(update, context): return
    if not context.args: return
    cmd = context.args[0].lower().lstrip("/")
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO disabled_cmds VALUES(?,?)", (update.effective_chat.id, cmd))
    await update.message.reply_text(f"{OK} Disabled /{cmd}")

async def enable(update, context):
    if not await is_admin(update, context): return
    if not context.args: return
    cmd = context.args[0].lower().lstrip("/")
    with connect() as c:
        c.execute("DELETE FROM disabled_cmds WHERE chat_id=? AND cmd=?", (update.effective_chat.id, cmd))
    await update.message.reply_text(f"{OK} Enabled /{cmd}")

# -------- WELCOME / GOODBYE / CAPTCHA EVENTS --------
async def new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.new_chat_members: return
    chat = update.effective_chat
    g = get_group(chat.id)
    for m in msg.new_chat_members:
        if m.is_bot: continue
        if g["captcha"]:
            try: await context.bot.restrict_chat_member(chat.id, m.id, RESTRICT)
            except Exception: pass
            a, b = random.randint(1,9), random.randint(1,9)
            ans = a + b
            opts = [ans, ans+1, ans-1, ans+2]
            random.shuffle(opts)
            rows = [[InlineKeyboardButton(str(o), callback_data=f"cap|{m.id}|{'ok' if o==ans else 'no'}") for o in opts[:2]],
                    [InlineKeyboardButton(str(o), callback_data=f"cap|{m.id}|{'ok' if o==ans else 'no'}") for o in opts[2:4]]]
            await msg.reply_text(f"🧩 Captcha\n{mention(m)}, solve: <b>{a} + {b} = ?</b>",
                                 reply_markup=InlineKeyboardMarkup(rows), parse_mode=ParseMode.HTML)
        w = g["welcome"] or "Welcome {mention}!"
        kb = None
        if g["welcome_btn"] and "|" in g["welcome_btn"]:
            t_, u_ = g["welcome_btn"].split("|", 1)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(t_, url=u_)]])
        try: await msg.reply_text(fill(w, m, chat), parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception: pass
    try: await msg.delete()
    except Exception: pass

async def left_member(update, context):
    msg = update.message
    if not msg or not msg.left_chat_member: return
    m = msg.left_chat_member
    if m.is_bot: return
    g = get_group(update.effective_chat.id)
    if g["goodbye"]:
        try: await msg.reply_text(fill(g["goodbye"], m, update.effective_chat), parse_mode=ParseMode.HTML)
        except Exception: pass
    try: await msg.delete()
    except Exception: pass

async def captcha_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    _, uid, res = q.data.split("|")
    uid = int(uid)
    if q.from_user.id != uid:
        return await q.answer("Yeh tumhara captcha nahi.", show_alert=True)
    if res == "ok":
        try:
            await context.bot.restrict_chat_member(q.message.chat.id, uid, FULL)
            await q.message.delete()
            await q.answer("✅ Verified!")
        except Exception as e: await q.answer(f"Error: {e}")
    else:
        try:
            await context.bot.ban_chat_member(q.message.chat.id, uid)
            await q.message.delete()
        except Exception: pass
        await q.answer("❌ Wrong!", show_alert=True)

# -------- MODERATION MESSAGE HANDLER --------
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not update.effective_chat: return
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private": return
    ensure_group(chat.id)
    g = get_group(chat.id)
    admin = await is_admin(update, context)
    text = msg.text or msg.caption or ""
    tl = text.lower()

    # blacklist words
    if not admin and tl:
        with connect() as c:
            words = [r["word"] for r in c.execute("SELECT word FROM blacklist_words WHERE chat_id=?", (chat.id,)).fetchall()]
        import re
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", tl):
                try:
                    await msg.delete()
                    await context.bot.ban_chat_member(chat.id, user.id)
                except Exception: pass
                return

    # bl users
    if not admin:
        with connect() as c:
            if c.execute("SELECT 1 FROM blacklist_users WHERE chat_id=? AND user_id=?", (chat.id, user.id)).fetchone():
                try: await msg.delete(); await context.bot.ban_chat_member(chat.id, user.id)
                except Exception: pass
                return
            if c.execute("SELECT 1 FROM fed_bans WHERE user_id=?", (user.id,)).fetchone():
                try: await msg.delete(); await context.bot.ban_chat_member(chat.id, user.id)
                except Exception: pass
                return
            if c.execute("SELECT 1 FROM gbans WHERE user_id=?", (user.id,)).fetchone():
                try: await msg.delete(); await context.bot.ban_chat_member(chat.id, user.id)
                except Exception: pass
                return

    # antiflood
    if not admin and g["antiflood_n"] and g["antiflood_n"] > 0:
        import time
        now = time.time()
        with connect() as c:
            c.execute("DELETE FROM flood WHERE ts < ?", (now - g["antiflood_t"],))
            c.execute("INSERT INTO flood VALUES(?,?,?)", (chat.id, user.id, now))
            cnt = c.execute("SELECT COUNT(*) FROM flood WHERE chat_id=? AND user_id=?", (chat.id, user.id)).fetchone()[0]
        if cnt > g["antiflood_n"]:
            try:
                await msg.delete()
                await context.bot.restrict_chat_member(chat.id, user.id, RESTRICT,
                    until_date=datetime.now() + timedelta(minutes=5))
            except Exception: pass
            with connect() as c:
                c.execute("DELETE FROM flood WHERE chat_id=? AND user_id=?", (chat.id, user.id))
            return

    # antispam
    if not admin and g["antispam"] and tl:
        last = context.chat_data.get(f"last_{user.id}")
        if last == tl:
            try: await msg.delete()
            except Exception: pass
        context.chat_data[f"last_{user.id}"] = tl

    # #note shortcut
    if text.startswith("#"):
        name = text[1:].split()[0].lower()
        with connect() as c:
            r = c.execute("SELECT content FROM notes WHERE chat_id=? AND name=?", (chat.id, name)).fetchone()
        if r: await msg.reply_text(r["content"], parse_mode=ParseMode.HTML)

    # disabled command
    if msg.text and msg.text.startswith("/"):
        cmd = msg.text.split()[0][1:].split("@")[0].lower()
        with connect() as c:
            d = c.execute("SELECT 1 FROM disabled_cmds WHERE chat_id=? AND cmd=?", (chat.id, cmd)).fetchone()
        if d and not admin:
            try: await msg.delete()
            except Exception: pass

def register(app):
    cmds = {
        "lock": lock, "unlock": unlock, "locks": locks_cmd,
        "setwelcome": setwelcome, "setgoodbye": setgoodbye,
        "welcomebtn": welcomebtn,
        "setrules": setrules, "rules": rules_cmd,
        "blacklist": blacklist, "blacklistuser": blacklistuser,
        "captcha": captcha_toggle, "antispam": antispam_toggle,
        "antiflood": antiflood, "nightmode": nightmode,
        "disable": disable, "enable": enable,
    }
    for k, v in cmds.items():
        app.add_handler(CommandHandler(k, v))
    app.add_handler(CallbackQueryHandler(captcha_cb, pattern=r"^cap\|"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member))