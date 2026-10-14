import asyncio, os, re, logging
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality
from pytgcalls.types.stream import StreamAudioEnded, StreamVideoEnded
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import CommandHandler, ContextTypes
from helpers import is_admin, LINE
import config

DL = config.DOWNLOAD_DIR
os.makedirs(DL, exist_ok=True)

assistant = None
call = None
QUEUES: dict = {}
NOW: dict = {}

YT_OPTS_AUDIO = {
    "quiet": True, "no_warnings": True, "noplaylist": True,
    "format": "bestaudio/best",
    "outtmpl": f"{DL}/%(id)s.%(ext)s",
    "socket_timeout": 20,
}
YT_OPTS_VIDEO = {
    "quiet": True, "no_warnings": True, "noplaylist": True,
    "format": "best[height<=720][ext=mp4]/best[ext=mp4]/best",
    "outtmpl": f"{DL}/%(id)s.%(ext)s",
    "socket_timeout": 30,
}

def _extract(query, video=False):
    opts = dict(YT_OPTS_VIDEO if video else YT_OPTS_AUDIO)
    if not re.match(r"^https?://", query):
        opts["default_search"] = "ytsearch1"
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
    if "entries" in info: info = info["entries"][0]
    return info

async def resolve(query, video=False):
    return await asyncio.to_thread(_extract, query, video)

def _get_stream_url(info):
    with YoutubeDL({"quiet": True, "no_warnings": True, "format": "bestaudio/best"}) as ydl:
        data = ydl.extract_info(info["webpage_url"], download=False)
    for f in reversed(data.get("formats", [])):
        if f.get("acodec") != "none" and f.get("url"):
            return f["url"]
    return None

async def start_assistant():
    global assistant, call
    if not config.SESSION_STRING or not config.API_ID:
        logging.warning("Assistant session missing — music disabled.")
        return False
    assistant = Client(":memory:", api_id=config.API_ID, api_hash=config.API_HASH,
                       session_string=config.SESSION_STRING)
    await assistant.start()
    call = PyTgCalls(assistant)
    await call.start()

    @call.on_update()
    async def _upd(client, update):
        if isinstance(update, (StreamAudioEnded, StreamVideoEnded)):
            cid = update.chat_id
            await _next_track(cid)

    logging.info("🎵 Assistant + pytgcalls ready.")
    return True

async def stop_assistant():
    try:
        if call: await call.stop()
        if assistant: await assistant.stop()
    except Exception: pass

async def _next_track(chat_id):
    q = QUEUES.get(chat_id, [])
    if not q:
        try: await call.leave_group_call(chat_id)
        except Exception: pass
        NOW.pop(chat_id, None)
        return
    nxt = q.pop(0)
    try:
        if nxt["video"]:
            await _play_video(chat_id, nxt["info"], nxt["by"], announce=False)
        else:
            await _play_audio(chat_id, nxt["info"], nxt["by"], announce=False)
    except Exception as e:
        logging.warning(f"next_track: {e}")

async def _play_audio(chat_id, info, by, announce=True):
    url = await asyncio.to_thread(_get_stream_url, info)
    if not url:
        raise RuntimeError("Stream URL nahi mila")
    await call.play(chat_id, MediaStream(url, AudioQuality.HIGH))
    NOW[chat_id] = {"title": info.get("title"), "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""), "url": info["webpage_url"],
                    "by": by, "video": False}

async def _play_video(chat_id, info, by, announce=True):
    url = await asyncio.to_thread(_get_stream_url, info)
    if not url: raise RuntimeError("Stream URL nahi mila")
    await call.play(chat_id, MediaStream(url, VideoQuality.HD_720p))
    NOW[chat_id] = {"title": info.get("title"), "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""), "url": info["webpage_url"],
                    "by": by, "video": True}

async def _cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, video=False):
    if not call:
        return await update.message.reply_text(
            "❌ Music disabled. Assistant session set karo (.env me SESSION_STRING).")
    if not context.args:
        return await update.message.reply_text(
            f"Usage: /{'video' if video else 'play'} &lt;YouTube link ya naam&gt;",
            parse_mode=ParseMode.HTML)
    q = " ".join(context.args)
    m = await update.message.reply_text(f"🔎 Searching: <b>{q}</b>...", parse_mode=ParseMode.HTML)
    try:
        info = await resolve(q, video)
    except Exception as e:
        return await m.edit_text(f"❌ Search fail: <code>{e}</code>", parse_mode=ParseMode.HTML)
    chat_id = update.effective_chat.id
    by = update.effective_user.first_name
    if chat_id in NOW:
        QUEUES.setdefault(chat_id, []).append({"info": info, "by": by, "video": video})
        return await m.edit_text(
            f"📥 Queue me add: <b>{info.get('title')}</b>\n"
            f"⏱ {info.get('duration', 0)}s", parse_mode=ParseMode.HTML)
    await m.edit_text(f"⏳ Joining voice chat: <b>{info.get('title')}</b>", parse_mode=ParseMode.HTML)
    try:
        if video: await _play_video(chat_id, info, by)
        else: await _play_audio(chat_id, info, by)
        await m.edit_text(
            f"{'🎬' if video else '▶️'} <b>Now Playing</b>\n{LINE}\n"
            f"<b>{info.get('title')}</b>\n"
            f"⏱ {info.get('duration', 0)}s  •  👤 {info.get('uploader','')}\n"
            f"🔗 <a href='{info['webpage_url']}'>YouTube</a>",
            parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        await m.edit_text(f"❌ Stream fail: <code>{e}</code>\n\n"
                          f"• Voice chat start kiya?\n• Assistant group me hai?",
                          parse_mode=ParseMode.HTML)

async def play_cmd(update, context): await _cmd(update, context, False)
async def video_cmd(update, context): await _cmd(update, context, True)

async def pause(update, context):
    try:
        await call.pause_stream(update.effective_chat.id)
        await update.message.reply_text("⏸ Paused.")
    except Exception as e: await update.message.reply_text(f"❌ {e}")

async def resume(update, context):
    try:
        await call.resume_stream(update.effective_chat.id)
        await update.message.reply_text("▶️ Resumed.")
    except Exception as e: await update.message.reply_text(f"❌ {e}")

async def stop(update, context):
    try:
        await call.leave_group_call(update.effective_chat.id)
        NOW.pop(update.effective_chat.id, None)
        QUEUES.pop(update.effective_chat.id, None)
        await update.message.reply_text("⏹ Stopped.")
    except Exception as e: await update.message.reply_text(f"❌ {e}")

async def skip(update, context):
    chat_id = update.effective_chat.id
    q = QUEUES.get(chat_id, [])
    if not q:
        return await stop(update, context)
    nxt = q.pop(0)
    try:
        if nxt["video"]: await _play_video(chat_id, nxt["info"], nxt["by"], False)
        else: await _play_audio(chat_id, nxt["info"], nxt["by"], False)
        await update.message.reply_text(f"⏭ Skipped → <b>{nxt['info'].get('title')}</b>",
                                        parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"❌ {e}")

async def nowplaying(update, context):
    np = NOW.get(update.effective_chat.id)
    if not np: return await update.message.reply_text("Kuch nahi chal raha.")
    await update.message.reply_text(
        f"🎵 <b>Now Playing</b>\n{np['title']}\n"
        f"⏱ {np['duration']}s  •  👤 {np['uploader']}\n🙋 {np['by']}",
        parse_mode=ParseMode.HTML)

def register(app):
    app.add_handler(CommandHandler(["play","song","music"], play_cmd))
    app.add_handler(CommandHandler("video", video_cmd))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("nowplaying", nowplaying))