import os
import random
import re
import asyncio
import aiohttp
import braintree
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

# ✅ Braintree API Keys (Directly Embedded)
BRAINTREE_CREDENTIALS = {
    "merchant_id": "xtw6fsgw6387brsz",
    "public_key": "g3q4dw5ykhjtgcqy",
    "private_key": "0276dac6121e9cf5f914b018493902ca",
}

# ✅ Initialize Braintree Gateway
try:
    gateway = braintree.BraintreeGateway(
        braintree.Configuration(
            braintree.Environment.Sandbox,  # Change to Production if needed
            merchant_id=BRAINTREE_CREDENTIALS["merchant_id"],
            public_key=BRAINTREE_CREDENTIALS["public_key"],
            private_key=BRAINTREE_CREDENTIALS["private_key"],
        )
    )
    print("✅ Braintree API Initialized Successfully!")
except Exception as e:
    print(f"⚠️ Error initializing Braintree: {str(e)}")
    exit()

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
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nJoin @DarkDorking for updates!"
    await update.message.reply_text(welcome_message)

async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1 or not re.match(r"^\d{6}$", context.args[0]):
        await update.message.reply_text("❌ Invalid BIN format!\nExample: `/gen 424242`")
        return

    bin_number = context.args[0]
    cards = []
    for _ in range(15):  # Generate 15 cards
        card_number = generate_luhn_card(bin_number)
        expiry_month = str(random.randint(1, 12)).zfill(2)
        expiry_year = str(random.randint(25, 30))  # Future expiry year
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

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", gen))
    
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
