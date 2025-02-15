import os
import random
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")  # ✅ Telegram Bot Token 

CARD_CHECK_API_URL = "https://your-api.com/check"  # ✅ API URL डालें
SK_KEY = "sk_live_yourkeyhere"  # ✅ अपनी SK Key डालें

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nThis bot is created for @DarkDorking channel members. Enjoy!"
    await update.message.reply_text(welcome_message)

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            await update.message.reply_text("❌ EXAMPLE: `/gen 424242 [MM/YY] [CVV]`")
            return

        bin_number = args[0]
        if not re.match(r"^\d{4,16}$", bin_number):
            await update.message.reply_text("❌ Wrong B!n Number!")
            return

        exp_date = args[1] if len(args) > 1 else f"{random.randint(1,12):02d}/{random.randint(25,30)}"
        cvv = args[2] if len(args) > 2 else f"{random.randint(100,999)}"

        # 10 डमी कार्ड जनरेट करें
        cards = [
            f"{bin_number}{''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number)))} | {exp_date} | {cvv}"
            for _ in range(10)
        ]

        # फॉर्मेटेड मैसेज
        message = (
            "**Generated Cards 🚀**\n\n"
            + "\n".join([f"`{card}`" for card in cards]) +  # ✅ Mono Font में Card
            "\n\n👉 @DarkDorking (Join Channel)"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SK Key से Card को Live या Dead चेक करें"""
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("❌ EXAMPLE: `/checkcard 4242424242424242 12/26 123`")
            return

        card_number, exp_date, cvv = args[0], args[1], args[2]
        if not re.match(r"^\d{16}$", card_number):
            await update.message.reply_text("❌ Invalid Card Number!")
            return

        # ✅ API कॉल करें (SK Key के साथ)
        headers = {
            "Authorization": f"Bearer {SK_KEY}",
            "Content-Type": "application/json"
        }
        data = {"card": card_number, "exp": exp_date, "cvv": cvv}  

        async with aiohttp.ClientSession() as session:
            async with session.post(CARD_CHECK_API_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    status = result.get("status", "Unknown")
                    card_type = result.get("type", "Unknown")  
                    issuer = result.get("issuer", "Unknown")  
                    country = result.get("country", "Unknown")  
                    flag = result.get("flag", "🌍")  

                    message = (
                        f"💳 **Card Status:** {status.upper()}\n\n"
                        f"📝 **𝗜𝗻𝗳𝗼:** {card_type}\n"
                        f"🏦 **𝐈𝐬𝐬𝐮𝐞𝐫:** {issuer}\n"
                        f"🌍 **𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {country} {flag}\n\n"
                        f"🔢 **Card:** `{card_number}`\n"
                        f"📅 **Exp:** `{exp_date}`\n"
                        f"🔑 **CVV:** `{cvv}`"
                    )

                    await update.message.reply_text(message, parse_mode="Markdown")
                    return

        await update.message.reply_text("⚠️ Error: Unable to check card.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    # Telegram बॉट सेटअप
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("checkcard", check_card))  # ✅ नया चेकिंग फीचर ऐड किया गया

    # HTTP सर्वर (Port 8080)
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()

    # दोनों सर्वर चलाएं
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # अनंत लूप
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
