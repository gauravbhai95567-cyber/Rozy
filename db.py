import sqlite3
from contextlib import contextmanager
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    chat_id INTEGER PRIMARY KEY,
    welcome TEXT DEFAULT '✨ Welcome {mention} to <b>{chat}</b>!',
    goodbye TEXT DEFAULT '👋 {first} left the group.',
    rules TEXT DEFAULT 'No rules yet.',
    captcha INTEGER DEFAULT 0,
    antispam INTEGER DEFAULT 0,
    antiflood_n INTEGER DEFAULT 0,
    antiflood_t INTEGER DEFAULT 10,
    night_mode INTEGER DEFAULT 0,
    log_channel INTEGER DEFAULT 0,
    welcome_btn TEXT
);
CREATE TABLE IF NOT EXISTS filters (
    chat_id INTEGER, keyword TEXT, reply TEXT,
    kind TEXT DEFAULT 'text', btn_text TEXT, btn_url TEXT,
    PRIMARY KEY(chat_id, keyword)
);
CREATE TABLE IF NOT EXISTS notes (
    chat_id INTEGER, name TEXT, content TEXT,
    PRIMARY KEY(chat_id, name)
);
CREATE TABLE IF NOT EXISTS warns (
    chat_id INTEGER, user_id INTEGER,
    count INTEGER DEFAULT 0, reasons TEXT DEFAULT '',
    PRIMARY KEY(chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS blacklist_words (
    chat_id INTEGER, word TEXT, PRIMARY KEY(chat_id, word)
);
CREATE TABLE IF NOT EXISTS blacklist_users (
    chat_id INTEGER, user_id INTEGER, PRIMARY KEY(chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS locks (
    chat_id INTEGER, lock_type TEXT, PRIMARY KEY(chat_id, lock_type)
);
CREATE TABLE IF NOT EXISTS disabled_cmds (
    chat_id INTEGER, cmd TEXT, PRIMARY KEY(chat_id, cmd)
);
CREATE TABLE IF NOT EXISTS fed_bans (
    user_id INTEGER PRIMARY KEY, reason TEXT
);
CREATE TABLE IF NOT EXISTS fed_admins (user_id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS flood (
    chat_id INTEGER, user_id INTEGER, ts REAL
);
CREATE TABLE IF NOT EXISTS approvals (
    chat_id INTEGER, user_id INTEGER, PRIMARY KEY(chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS gbans (user_id INTEGER PRIMARY KEY, reason TEXT);
"""

@contextmanager
def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init():
    with connect() as c:
        c.executescript(SCHEMA)

def ensure_group(chat_id: int):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO groups(chat_id) VALUES(?)", (chat_id,))

def get_group(chat_id: int):
    ensure_group(chat_id)
    with connect() as c:
        return c.execute("SELECT * FROM groups WHERE chat_id=?", (chat_id,)).fetchone()

def set_group(chat_id: int, **kw):
    if not kw: return
    ensure_group(chat_id)
    sets = ", ".join(f"{k}=?" for k in kw)
    vals = list(kw.values()) + [chat_id]
    with connect() as c:
        c.execute(f"UPDATE groups SET {sets} WHERE chat_id=?", vals)