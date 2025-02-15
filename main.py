import os
import random
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web
import stripe  # ✅ Stripe API for Checking Cards

TOKEN = os.getenv("TELEGRAM_TOKEN")  # ✅ Telegram Bot Token
BIN_LOOKUP_URL = "https://bins.antipublic.cc/bins/"  # ✅ Free BIN Lookup URL

# ✅ Admins & Premium Users Storage
ADMINS = {"6972264549"}  # 🔹 Replace with your Telegram ID
PREMIUM_USERS = {}
USER_CHECK_LIMIT = {}
STRIPE_KEYS = {"global": None}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is @DarkDorking Free CC Generator Bot.\nEnjoy!"
    await update.message.reply_text(welcome_message)

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in PREMIUM_USERS:
        if user_id not in USER_CHECK_LIMIT:
            USER_CHECK_LIMIT[user_id] = 10
        if USER_CHECK_LIMIT[user_id] <= 0:
            await update.message.reply_text("❌ Daily limit reached! Come back tomorrow.")
            return
    
    if STRIPE_KEYS["global"] is None:
        await update.message.reply_text("❌ No Stripe key found! Admin needs to add it.")
        return
    stripe.api_key = STRIPE_KEYS["global"]
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: `/chk 5154620020084230|08|27|413`")
        return
    
    card_details = args[0].split('|')
    exp_month = int(card_details[1])
    exp_year = int(card_details[2])
    if exp_year < 100:  # Convert YY to YYYY
        exp_year += 2000
    
    try:
        token = stripe.Token.create(
            card={
                "number": card_details[0],
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": card_details[3]
            }
        )
        message = f"✅ LIVE: `{args[0]}`"
    except stripe.error.CardError:
        message = f"❌ DEAD: `{args[0]}`"
    
    bin_info = await get_bin_info(card_details[0][:6])
    bin_details = (
        f"📝 **𝗜𝗻𝗳𝗼:** {bin_info['brand']} - {bin_info['type']} - {bin_info['level']}\n"
        f"🏦 **𝐈𝐬𝐬𝐮𝐞𝐫:** {bin_info['bank']}\n"
        f"🌍 **𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {bin_info['country']} {bin_info['flag']}\n"
    ) if bin_info else "⚠️ **BIN Info Not Available**\n"
    
    if user_id not in PREMIUM_USERS:
        USER_CHECK_LIMIT[user_id] -= 1
        remaining = USER_CHECK_LIMIT[user_id]
        message += f"\n🎟️ Checks Left Today: {remaining}/10"
    
    await update.message.reply_text(f"{message}\n\n{bin_details}", parse_mode="Markdown")

async def get_bin_info(bin_number):
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

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chk", check_card))
    
    app = web.Application()
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
