import os
import random
import re
import asyncio
import aiohttp
import stripe
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

# ✅ Stripe API Key (Initially None, set via /addsk command)
STRIPE_KEY = None
TOKEN = os.getenv("TELEGRAM_TOKEN")
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

async def addsk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STRIPE_KEY
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to set the Stripe API key!")
        return
    if not context.args:
        await update.message.reply_text("❌ EXAMPLE: /addsk sk_live_xxx")
        return
    STRIPE_KEY = context.args[0]
    await update.message.reply_text("✅ Stripe API Key Set Successfully!")

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

async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1 or not re.match(r"^\d{6}$", context.args[0]):
        await update.message.reply_text("❌ Invalid BIN format!\nExample: `/gen 424242`")
        return

    bin_number = context.args[0]
    cards = []
    for _ in range(15):  # Generate 15 cards
        card_number = generate_luhn_card(bin_number)
        expiry_month = str(random.randint(1, 12)).zfill(2)
        expiry_year = str(random.randint(2025, 2030))  # Full year format
        cvv = str(random.randint(100, 999))
        cards.append(f"{card_number}|{expiry_month}|{expiry_year}|{cvv}")

    bin_info = await get_bin_info(bin_number) or {"vendor": "Unknown", "type": "Unknown", "country_name": "Unknown", "bank": "Unknown"}
    
    message = (
        f"🔥 **Generated Cards** (`/gen`)
"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 **BIN:** {bin_number}\n"
        f"🏦 **Issuer:** {bin_info.get('bank', 'Unknown')}\n"
        f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
        f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Cards (15x)**:\n"
        f"```\n" + "\n".join(cards) + "\n```\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Join @DarkDorking for more!"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def mass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STRIPE_KEY
    if STRIPE_KEY is None:
        await update.message.reply_text("❌ No Stripe API key found! Admin needs to add it using /addsk")
        return

    cards = context.args
    if len(cards) != 15:
        await update.message.reply_text("❌ Please provide exactly 15 cards in the format: `card|mm|yyyy|cvv`")
        return

    stripe.api_key = STRIPE_KEY
    results = []

    for card in cards:
        if not re.match(r"^\d{16}\|\d{2}\|\d{4}\|\d{3}$", card):
            results.append(f"❌ Invalid Format: {card}")
            continue

        card_details = card.split('|')
        try:
            token = stripe.Token.create(
                card={
                    "number": card_details[0],
                    "exp_month": int(card_details[1]),
                    "exp_year": int(card_details[2]),
                    "cvc": card_details[3],
                }
            )
            results.append(f"✅ Live: {card}")
        except stripe.error.CardError as e:
            results.append(f"❌ Dead: {card} - {e.user_message}")
        except Exception as e:
            results.append(f"⚠️ Error: {card} - {str(e)}")

    await update.message.reply_text("\n".join(results))

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("addsk", addsk))
    application.add_handler(CommandHandler("chk", chk))
    application.add_handler(CommandHandler("gen", gen))
    application.add_handler(CommandHandler("mass", mass))
    
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
