import os
import random
import re
import asyncio
import aiohttp
import stripe
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")
STRIPE_KEY = None  # Global variable for storing Stripe API key
ADMIN_ID = 6972264549  # Admin ID

def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)][::-1]
    checksum = sum(digits[0::2]) + sum(sum(divmod(d * 2, 10)) for d in digits[1::2])
    return checksum % 10 == 0

def generate_card(bin_number):
    while True:
        card_number = bin_number + "".join(str(random.randint(0, 9)) for _ in range(16 - len(bin_number)))
        if luhn_check(card_number):
            return card_number

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nEnjoy!"
    await update.message.reply_text(welcome_message)

async def add_sk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STRIPE_KEY
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to set the Stripe API key!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ EXAMPLE: /addsk sk_live_xxx")
        return
    STRIPE_KEY = context.args[0]
    await update.message.reply_text("✅ Stripe API Key Set Successfully!")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STRIPE_KEY
    if STRIPE_KEY is None:
        await update.message.reply_text("❌ No Stripe API key found! Admin needs to add it using /addsk")
        return
    
    args = context.args
    if len(args) < 1 or not re.match(r"^\d{16}\|\d{2}/\d{2}\|\d{3}$", args[0]):
        await update.message.reply_text("❌ EXAMPLE: /chk 4242424242424242|12/25|123")
        return
    
    card_details = args[0].split('|')
    stripe.api_key = STRIPE_KEY
    
    try:
        token = stripe.Token.create(
            card={
                "number": card_details[0],
                "exp_month": int(card_details[1].split('/')[0]),
                "exp_year": int(card_details[1].split('/')[1]),
                "cvc": card_details[2]
            }
        )
        message = f"✅ LIVE: {args[0]}"
    except stripe.error.CardError:
        message = f"❌ DEAD: {args[0]}"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            await update.message.reply_text("❌ EXAMPLE: /gen 424242 [MM/YY] [CVV]")
            return

        bin_number = args[0]
        if not re.match(r"^\d{6,16}$", bin_number):
            await update.message.reply_text("❌ Wrong BIN Number! Format: First 6-16 digits of card number.")
            return

        bin_info = await get_bin_info(bin_number)
        if not bin_info:
            bin_info = {"vendor": "Unknown", "type": "Unknown", "country_name": "Unknown"}

        card_type = bin_info.get("vendor", "Unknown").capitalize()
        card_brand = bin_info.get("type", "Unknown")
        country = bin_info.get("country_name", "Unknown")
        
        exp_date = args[1] if len(args) > 1 else f"{random.randint(1,12):02d}/{random.randint(25,30)}"
        cvv = args[2] if len(args) > 2 else f"{random.randint(100,999)}"

        cards = [
            f"{generate_card(bin_number)} | {exp_date} | {cvv}"
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
    application.add_handler(CommandHandler("addsk", add_sk))
    application.add_handler(CommandHandler("chk", check_card))
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
