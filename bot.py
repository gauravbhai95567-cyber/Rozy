import logging
from telegram import Update
from telegram.ext import Application
from telegram.constants import ParseMode

import config
import db
import handlers
import filters_notes
import automation
import menu
import music
import ai_chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

async def on_startup(app: Application):
    ok = await music.start_assistant()
    log.info("Bot started. Music=%s", "ON" if ok else "OFF")

async def on_shutdown(app: Application):
    await music.stop_assistant()

def main():
    db.init()
    app = (Application.builder()
           .token(config.BOT_TOKEN)
           .post_init(on_startup)
           .post_shutdown(on_shutdown)
           .build())

    menu.register(app)
    handlers.register(app)
    filters_notes.register(app)
    automation.register(app)
    music.register(app)
    ai_chat.register(app)

    # filter triggers + moderation + ai (priority group 1)
    from telegram.ext import MessageHandler, filters as f
    app.add_handler(MessageHandler(
        f.TEXT & ~f.COMMAND & ~f.StatusUpdate.ALL,
        filters_notes.on_filter_msg), group=1)
    app.add_handler(MessageHandler(
        f.ALL & ~f.COMMAND & ~f.StatusUpdate.ALL,
        automation.on_message), group=2)
    app.add_handler(MessageHandler(
        f.TEXT & ~f.COMMAND & ~f.StatusUpdate.ALL,
        ai_chat.auto_ai), group=3)

    log.info("🚀 MissRose Pro running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()