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
    user_name = update.message.from_user.first_name
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nThis bot is created for @DarkDorking channel members. Enjoy!"
    await update.message.reply_text(welcome_message)

def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)][::-1]
    checksum = sum(digits[0::2]) + sum(sum(divmod(2 * d, 10)) for d in digits[1::2])
    return checksum % 10 == 0

async def get_bin_info(bin_number):
    url = f"https://bins.antipublic.cc/bins/{bin_number}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        print(f"BIN API Error: {e}")
    return None

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args or not re.match(r"^\d{4,16}$", args[0]):
            await update.message.reply_text("❌ Invalid BIN format! Please enter a valid BIN (6 to 16 digits). Example: `/gen 424242 [MM/YY] [CVV]`")
            return

        bin_number = args[0]
        bin_info = await get_bin_info(bin_number[:6])
        if not bin_info:
            bin_info = {"vendor": "Unknown", "type": "Unknown", "bank": "Unknown", "country_name": "Unknown"}

        card_type = bin_info.get("vendor", "Unknown").capitalize()
        card_brand = bin_info.get("type", "Unknown")
        issuer = bin_info.get("bank", "Unknown")
        country = bin_info.get("country_name", "Unknown")

        exp_date = args[1] if len(args) > 1 else f"{random.randint(1,12):02d}/{random.randint(25,30)}"
        cvv = args[2] if len(args) > 2 else f"{random.randint(100,999)}"

        cards = []
        for _ in range(10):
            while True:
                card_number = f"{bin_number}{''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number)))}"
                if luhn_check(card_number):
                    cards.append(f"{card_number} | {exp_date} | {cvv}")
                    break

        message = (
            "**Generated Cards 🚀**\n\n"
            f"💳 **Card Type:** {card_type} ({card_brand})\n"
            f"🏦 **Issuer:** {issuer}\n"
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
