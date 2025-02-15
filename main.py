import os
import random
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")  # ✅ Telegram Bot Token

BIN_LOOKUP_URL = "https://bins.antipublic.cc/bins/"  # ✅ Free BIN Lookup URL

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nThis bot is created for @DarkDorking channel members. Enjoy!"
    await update.message.reply_text(welcome_message)

async def get_bin_info(bin_number):
    """✅ Free BIN Lookup से जानकारी प्राप्त करें (No API Key Required)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BIN_LOOKUP_URL}{bin_number}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "brand": data.get("brand", "Unknown"),
                        "type": data.get("type", "Unknown"),
                        "level": data.get("level", "Unknown"),
                        "bank": data.get("bank", "Unknown"),
                        "country": data.get("country", "Unknown"),
                        "flag": data.get("flag", "🌍")
                    }
    except:
        return None

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

        bin_info = await get_bin_info(bin_number[:6])  # ✅ BIN की जानकारी प्राप्त करें

        # 10 डमी कार्ड जनरेट करें
        cards = [
            f"{bin_number}{''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number)))} | {exp_date} | {cvv}"
            for _ in range(10)
        ]

        bin_details = (
            f"📝 **𝗜𝗻𝗳𝗼:** {bin_info['brand']} - {bin_info['type']} - {bin_info['level']}\n"
            f"🏦 **𝐈𝐬𝐬𝐮𝐞𝐫:** {bin_info['bank']}\n"
            f"🌍 **𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {bin_info['country']} {bin_info['flag']}\n\n"
        ) if bin_info else "⚠️ **BIN Info Not Available**\n\n"

        # फॉर्मेटेड मैसेज
        message = (
            "**Generated Cards 🚀**\n\n"
            + bin_details
            + "\n".join([f"`{card}`" for card in cards]) +  # ✅ Mono Font में Card
            "\n\n👉 @DarkDorking (Join Channel)"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    # Telegram बॉट सेटअप
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))

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
