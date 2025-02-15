import os
import random
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  # यूजर का नाम प्राप्त करें
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nThis bot is created for @DarkDorking channel members. Enjoy!"
    await update.message.reply_text(welcome_message)

async def get_bin_info(bin_number):
    """BIN की जानकारी API से प्राप्त करें"""
    url = f"https://lookup.binlist.net/{bin_number}"
    headers = {"Accept-Version": "3"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return None

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            await update.message.reply_text("❌ EXAMPLE: `/gen 424242 [MM/YY] [CVV]`")
            return

        bin_number = args[0]
        if not re.match(r"^\\d{4,16}$", bin_number):
            await update.message.reply_text("❌ Wrong B!n Number!")
            return

        # BIN की जानकारी प्राप्त करें
        bin_info = await get_bin_info(bin_number)
        if not bin_info:
            await update.message.reply_text("⚠️ Could not fetch BIN details. Try another BIN.")
            return

        card_type = bin_info.get("scheme", "Unknown").capitalize()
        card_brand = bin_info.get("brand", "Unknown")
        country = bin_info.get("country", {}).get("name", "Unknown")
        
        exp_date = args[1] if len(args) > 1 else f"{random.randint(1,12):02d}/{random.randint(25,30)}"
        cvv = args[2] if len(args) > 2 else f"{random.randint(100,999)}"

        cards = [
            f"{bin_number}{''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number)))} | {exp_date} | {cvv}"
            for _ in range(10)
        ]

        message = (
            "**Generated Cards 🚀**\n\n"
            f"💳 **Card Type:** {card_type} ({card_brand})\n"
            f"🌍 **Country:** {country}\n\n"
            + "\n".join(cards) + 
            "\n\n👉 @DarkDorking (Join Channel)"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
