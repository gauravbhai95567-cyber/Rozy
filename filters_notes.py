from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes
from helpers import *
from db import connect

def _btn_kb(text, url):
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, url=url)]]) if text and url else None

# ---------- FILTERS ----------
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        return await update.message.reply_text(
            f"<b>Filters</b>\n/filter add &lt;kw&gt; &lt;reply&gt;\n/filter remove &lt;kw&gt;\n/filters",
            parse_mode=ParseMode.HTML)
    sub = context.args[0].lower()
    if sub == "list":
        with connect() as c:
            rows = c.execute("SELECT keyword FROM filters WHERE chat_id=?", (chat_id,)).fetchall()
        return await update.message.reply_text(
            box("💬 Filters", "\n".join(f"• <code>{r['keyword']}</code>" for r in rows) or "—"),
            parse_mode=ParseMode.HTML)
    if not await is_admin(update, context): return
    if sub == "remove":
        if len(context.args) < 2: return
        with connect() as c:
            c.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (chat_id, context.args[1].lower()))
        return await update.message.reply_text(f"{OK} Removed.")
    if sub == "add":
        if len(context.args) < 3: return
        kw = context.args[1].lower()
        rest = context.args[2:]
        btn_text = btn_url = None
        if "-btn" in rest:
            i = rest.index("-btn")
            btn = " ".join(rest[i+1:])
            if "|" in btn:
                btn_text, btn_url = btn.split("|", 1)
            rest = rest[:i]
        reply = " ".join(rest)
        kind = "text"
        if update.message.reply_to_message:
            m = update.message.reply_to_message
            if m.sticker: reply, kind = m.sticker.file_id, "sticker"
            elif m.photo: reply, kind = m.photo[-1].file_id, "photo"
            elif m.video: reply, kind = m.video.file_id, "video"
            elif m.document: reply, kind = m.document.file_id, "document"
            elif m.animation: reply, kind = m.animation.file_id, "animation"
            elif m.text: reply, kind = m.text, "text"
        with connect() as c:
            c.execute("""INSERT INTO filters(chat_id,keyword,reply,kind,btn_text,btn_url)
                         VALUES(?,?,?,?,?,?)
                         ON CONFLICT(chat_id,keyword) DO UPDATE SET
                         reply=excluded.reply, kind=excluded.kind,
                         btn_text=excluded.btn_text, btn_url=excluded.btn_url""",
                      (chat_id, kw, reply, kind, btn_text, btn_url))
        return await update.message.reply_text(f"{OK} Filter added: <code>{kw}</code>", parse_mode=ParseMode.HTML)

# ---------- NOTES ----------
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if not context.args: return await update.message.reply_text(f"{NO} Usage: /save &lt;name&gt; &lt;content&gt;", parse_mode=ParseMode.HTML)
    name = context.args[0].lower()
    content = update.message.reply_to_message.text if update.message.reply_to_message else " ".join(context.args[1:])
    if not content: return
    with connect() as c:
        c.execute("""INSERT INTO notes(chat_id,name,content) VALUES(?,?,?)
                     ON CONFLICT(chat_id,name) DO UPDATE SET content=excluded.content""",
                  (update.effective_chat.id, name, content))
    await update.message.reply_text(f"{OK} Note saved: <code>#{name}</code>", parse_mode=ParseMode.HTML)

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    name = context.args[0].lower().lstrip("#")
    with connect() as c:
        r = c.execute("SELECT content FROM notes WHERE chat_id=? AND name=?",
                      (update.effective_chat.id, name)).fetchone()
    if not r: return await update.message.reply_text(f"{NO} Note nahi mila.")
    await update.message.reply_text(r["content"], parse_mode=ParseMode.HTML)

async def notes_list(update, context):
    with connect() as c:
        rows = c.execute("SELECT name FROM notes WHERE chat_id=?", (update.effective_chat.id,)).fetchall()
    await update.message.reply_text(
        box("📝 Notes", "\n".join(f"• <code>#{r['name']}</code>" for r in rows) or "—"),
        parse_mode=ParseMode.HTML)

async def clear_note(update, context):
    if not await is_admin(update, context): return
    if not context.args: return
    with connect() as c:
        c.execute("DELETE FROM notes WHERE chat_id=? AND name=?",
                  (update.effective_chat.id, context.args[0].lower()))
    await update.message.reply_text(f"{OK} Cleared.")

# ---------- HANDLER for filter triggers ----------
async def on_filter_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return
    chat_id = update.effective_chat.id
    key = msg.text.strip().lower()
    with connect() as c:
        r = c.execute("SELECT * FROM filters WHERE chat_id=? AND keyword=?", (chat_id, key)).fetchone()
    if not r: return
    kb = _btn_kb(r["btn_text"], r["btn_url"])
    try:
        if r["kind"] == "text": await msg.reply_text(r["reply"], reply_markup=kb, parse_mode=ParseMode.HTML)
        elif r["kind"] == "sticker": await msg.reply_sticker(r["reply"], reply_markup=kb)
        elif r["kind"] == "photo": await msg.reply_photo(r["reply"], reply_markup=kb)
        elif r["kind"] == "video": await msg.reply_video(r["reply"], reply_markup=kb)
        elif r["kind"] == "document": await msg.reply_document(r["reply"], reply_markup=kb)
        elif r["kind"] == "animation": await msg.reply_animation(r["reply"], reply_markup=kb)
    except Exception: pass

def register(app):
    app.add_handler(CommandHandler("filter", filter_cmd))
    app.add_handler(CommandHandler("filters", filter_cmd))
    app.add_handler(CommandHandler("save", save))
    app.add_handler(CommandHandler("get", get_note))
    app.add_handler(CommandHandler("notes", notes_list))
    app.add_handler(CommandHandler("clear", clear_note))