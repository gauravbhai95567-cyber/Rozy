from datetime import datetime, timedelta
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes
from helpers import *
from db import connect

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text(f"{NO} Sirf admins.")
    t = await get_target(update, context)
    if not t: return await update.message.reply_text(f"{NO} User reply karo.")
    uid, name, _ = t
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"{BAN} Banned: <b>{name}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"{NO} <code>{e}</code>", parse_mode=ParseMode.HTML)

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return await update.message.reply_text(f"{NO} User reply karo.")
    uid, name, _ = t
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"{OK} Unbanned: <b>{name}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"{NO} <code>{e}</code>", parse_mode=ParseMode.HTML)

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"{KICK} Kicked: <b>{name}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"{NO} <code>{e}</code>", parse_mode=ParseMode.HTML)

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, uid, RESTRICT)
        await update.message.reply_text(f"{MUTE} Muted: <b>{name}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"{NO} <code>{e}</code>", parse_mode=ParseMode.HTML)

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, uid, FULL)
        await update.message.reply_text(f"{UNMUTE} Unmuted: <b>{name}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"{NO} <code>{e}</code>", parse_mode=ParseMode.HTML)

async def tmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if not context.args: return
    time_arg = context.args[-1]
    secs = parse_time(time_arg)
    if not secs: return await update.message.reply_text(f"{NO} Time: 5m, 1h")
    if update.message.reply_to_message:
        t = await get_target(update, context)
    else:
        context.args = [context.args[0]]
        t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, uid, RESTRICT,
            until_date=datetime.now() + timedelta(seconds=secs))
        await update.message.reply_text(f"{MUTE} Muted {name} for {time_arg}", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"{NO} <code>{e}</code>", parse_mode=ParseMode.HTML)

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    reason = " ".join(context.args[1:]) if update.message.reply_to_message else " ".join(context.args[1:]) or "No reason"
    with connect() as c:
        r = c.execute("SELECT count, reasons FROM warns WHERE chat_id=? AND user_id=?",
                      (update.effective_chat.id, uid)).fetchone()
        if r:
            cnt = r["count"] + 1
            c.execute("UPDATE warns SET count=?, reasons=? WHERE chat_id=? AND user_id=?",
                      (cnt, (r["reasons"] + "|" + reason).strip("|"), update.effective_chat.id, uid))
        else:
            cnt = 1
            c.execute("INSERT INTO warns VALUES(?,?,?,?)", (update.effective_chat.id, uid, 1, reason))
    if cnt >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            with connect() as c:
                c.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (update.effective_chat.id, uid))
            await update.message.reply_text(f"{BAN} {name} → 3 warns → banned.", parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text(f"{NO} {e}")
    else:
        await update.message.reply_text(
            f"{WARN} <b>Warn {cnt}/3</b>\n<b>User:</b> {name}\n<b>Reason:</b> {reason}",
            parse_mode=ParseMode.HTML)

async def warns_cmd(update, context):
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    with connect() as c:
        r = c.execute("SELECT count, reasons FROM warns WHERE chat_id=? AND user_id=?",
                      (update.effective_chat.id, uid)).fetchone()
    cnt = r["count"] if r else 0
    rs = (r["reasons"] if r and r["reasons"] else "—").split("|")
    body = "\n".join(f"• {x}" for x in rs)
    await update.message.reply_text(box(f"{WARN} Warns — {name}", f"Total: {cnt}/3\n{body}"),
                                    parse_mode=ParseMode.HTML)

async def resetwarns(update, context):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    with connect() as c:
        c.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (update.effective_chat.id, uid))
    await update.message.reply_text(f"{OK} Warns reset: {name}")

async def promote(update, context):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    try:
        await context.bot.promote_chat_member(update.effective_chat.id, uid,
            can_change_info=True, can_delete_messages=True, can_invite_users=True,
            can_restrict_members=True, can_pin_messages=True, can_promote_members=False)
        await update.message.reply_text(f"{STAR} Promoted: {name}")
    except Exception as e:
        await update.message.reply_text(f"{NO} {e}")

async def demote(update, context):
    if not await is_admin(update, context): return
    t = await get_target(update, context)
    if not t: return
    uid, name, _ = t
    try:
        await context.bot.promote_chat_member(update.effective_chat.id, uid,
            can_change_info=False, can_delete_messages=False, can_invite_users=False,
            can_restrict_members=False, can_pin_messages=False, can_promote_members=False)
        await update.message.reply_text(f"Demoted: {name}")
    except Exception as e:
        await update.message.reply_text(f"{NO} {e}")

async def pin(update, context):
    if not await is_admin(update, context): return
    if not update.message.reply_to_message:
        return await update.message.reply_text(f"{NO} Message reply karo.")
    try:
        await context.bot.pin_chat_message(update.effective_chat.id,
            update.message.reply_to_message.message_id)
        await update.message.reply_text("📌 Pinned.")
    except Exception as e:
        await update.message.reply_text(f"{NO} {e}")

async def adminlist(update, context):
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    lines = [f"{CROWN if a.status=='creator' else SHIELD} {mention(a.user)} — <code>{a.user.id}</code>"
             for a in admins]
    await update.message.reply_text(box(f"{SHIELD} Admins", "\n".join(lines)),
                                    parse_mode=ParseMode.HTML)

async def id_cmd(update, context):
    txt = f"<b>Chat ID:</b> <code>{update.effective_chat.id}</code>\n<b>Your ID:</b> <code>{update.effective_user.id}</code>"
    if update.message.reply_to_message:
        u = update.message.reply_to_message.from_user
        txt += f"\n<b>User:</b> {mention(u)} = <code>{u.id}</code>"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

def register(app):
    cmds = {
        "ban": ban, "unban": unban, "kick": kick,
        "mute": mute, "unmute": unmute, "tmute": tmute,
        "warn": warn, "warns": warns_cmd, "resetwarns": resetwarns,
        "promote": promote, "demote": demote,
        "pin": pin, "adminlist": adminlist, "id": id_cmd,
    }
    for k, v in cmds.items():
        app.add_handler(CommandHandler(k, v))