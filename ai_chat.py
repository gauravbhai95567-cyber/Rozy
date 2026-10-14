import os, logging
from openai import AsyncOpenAI
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
import config

SYSTEM = ("You are MissRose AI, a helpful Telegram group assistant. "
          "Reply in the same language the user writes in (Hindi, English, Hinglish OK). "
          "Keep answers short and useful.")

_client = None
MODEL = "gpt-4o-mini"

if config.OPENAI_API_KEY:
    _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
elif config.GROQ_API_KEY:
    _client = AsyncOpenAI(api_key=config.GROQ_API_KEY,
                          base_url="https://api.groq.com/openai/v1")
    MODEL = "llama-3.3-70b-versatile"

_mem: dict = {}
_on: dict = {}
MAX = 10

def _esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

async def _ask(uid, text):
    if _client is None:
        return "🤖 <i>AI key set nahi hai.</i>"
    h = _mem.setdefault(uid, [])
    h.append({"role":"user","content":text})
    h[:] = h[-MAX*2:]
    try:
        r = await _client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"system","content":SYSTEM}, *h],
            temperature=0.7, max_tokens=600)
        ans = r.choices[0].message.content.strip()
        h.append({"role":"assistant","content":ans})
        return ans
    except Exception as e:
        return f"⚠️ <code>{_esc(str(e))}</code>"

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("🤖 Usage: <code>/ai your question</code>",
                                               parse_mode=ParseMode.HTML)
    q = " ".join(context.args)
    m = await update.message.reply_text("🤖 <i>Soch raha hoon...</i>", parse_mode=ParseMode.HTML)
    ans = await _ask(update.effective_user.id, q)
    await m.edit_text(f"🤖 {_esc(ans)}", parse_mode=ParseMode.HTML)

async def chatbot(update, context):
    v = bool(context.args and context.args[0].lower() == "on")
    _on[update.effective_chat.id] = v
    await update.message.reply_text(f"🤖 Chatbot: {'🟢 ON' if v else '🔴 OFF'}")

async def resetai(update, context):
    _mem.pop(update.effective_user.id, None)
    await update.message.reply_text("✅ Memory cleared.")

async def auto_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat: return
    cid = update.effective_chat.id
    if not _on.get(cid): return
    txt = update.message.text or update.message.caption
    if not txt or txt.startswith("/") or txt.startswith("#"): return
    if update.effective_chat.type != "private":
        me = context.bot.username
        m = f"@{me}" in txt
        r = (update.message.reply_to_message and
             update.message.reply_to_message.from_user.id == context.bot.id)
        if not (m or r): return
        txt = txt.replace(f"@{me}", "").strip()
    try:
        await context.bot.send_chat_action(cid, ChatAction.TYPING)
        ans = await _ask(update.effective_user.id, txt)
        await update.message.reply_text(f"🤖 {_esc(ans)}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.warning(f"auto_ai: {e}")

def register(app):
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler(["chatbot","aichat"], chatbot))
    app.add_handler(CommandHandler(["resetai","reset_ai"], resetai))