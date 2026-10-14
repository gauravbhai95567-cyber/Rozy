import re
from datetime import datetime, timedelta
from telegram import ChatPermissions
from telegram.constants import ChatMemberStatus, ParseMode

OK="✅"; NO="❌"; WARN="⚠️"; INFO="ℹ️"; LOCK="🔒"; UNLOCK="🔓"
BAN="🔨"; KICK="👢"; MUTE="🔇"; UNMUTE="🔊"; STAR="⭐"
CROWN="👑"; SHIELD="🛡"; FIRE="🔥"; SPARK="✨"; BOLT="⚡"
LINE="━━━━━━━━━━━━━━━━━━"

def box(title, body=""):
    return f"<b>{title}</b>\n{LINE}\n{body}"

RESTRICT = ChatPermissions(False, False, False, False, False, False)
FULL = ChatPermissions(True, True, True, True, True, True)

def parse_time(s):
    m = re.match(r"^(\d+)([smhd])$", s.lower())
    if not m: return None
    n = int(m.group(1)); u = m.group(2)
    return n * {"s":1,"m":60,"h":3600,"d":86400}[u]

def mention(u):
    return f'<a href="tg://user?id={u.id}">{u.first_name}</a>'

def fill(text, user, chat):
    return (text.replace("{mention}", mention(user))
                .replace("{first}", user.first_name or "")
                .replace("{last}", user.last_name or "")
                .replace("{username}", f"@{user.username}" if user.username else user.first_name)
                .replace("{id}", str(user.id))
                .replace("{chat}", chat.title or "group"))

async def is_admin(update, context, user_id=None):
    if update.effective_chat.type == "private": return False
    uid = user_id or update.effective_user.id
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return m.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def get_target(update, context):
    msg = update.message or update.edited_message
    if msg and msg.reply_to_message:
        u = msg.reply_to_message.from_user
        return u.id, u.full_name, u
    if context.args:
        a = context.args[0]
        if a.startswith("@"):
            try:
                ch = await context.bot.get_chat(a)
                return ch.id, getattr(ch, "full_name", a), ch
            except Exception: return None
        try:
            uid = int(a)
            try:
                m = await context.bot.get_chat_member(update.effective_chat.id, uid)
                return m.user.id, m.user.full_name, m.user
            except Exception:
                return uid, str(uid), None
        except Exception: return None
    return None
