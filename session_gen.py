import asyncio
from pyrogram import Client
import config

async def main():
    async with Client("assistant", api_id=config.API_ID, api_hash=config.API_HASH) as app:
        me = await app.get_me()
        print(f"\n✅ Logged in: {me.first_name} (@{me.username})\n")
        s = await app.export_session_string()
        print(f"🔑 SESSION_STRING:\n{s}\n")
        print("Ise .env me SESSION_STRING= ke aage paste karo.")

if __name__ == "__main__":
    asyncio.run(main())