import os
import random
import asyncio
import braintree
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")
BRAINTREE_MERCHANT_ID = os.getenv("xtw6fsgw6387brsz")
BRAINTREE_PUBLIC_KEY = os.getenv("8dfyd6d5czsx2qcj")
BRAINTREE_PRIVATE_KEY = os.getenv("7785bf641215326684b40588d0dd8b22")

# Braintree Configuration
braintree_gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        braintree.Environment.Sandbox,  # Live के लिए 'Production' सेट करें
        merchant_id=BRAINTREE_MERCHANT_ID,
        public_key=BRAINTREE_PUBLIC_KEY,
        private_key=BRAINTREE_PRIVATE_KEY
    )
)

# ✅ Braintree Compatible Test BINs
BRAINTREE_BINS = ["411111", "400551", "555555", "222300", "378282"]

def generate_braintree_card():
    """ Braintree Compatible Test Card Generator (Full Year Format) """
    bin_prefix = random.choice(BRAINTREE_BINS)  # Random BIN select करें
    account_number = "".join(str(random.randint(0, 9)) for _ in range(10))  # 10 random digits
    card_number = bin_prefix + account_number
    exp_month = f"{random.randint(1, 12):02d}"
    exp_year = str(random.randint(2025, 2030))  # Full Year Format (2025, 2026...)
    cvv = f"{random.randint(100, 999)}"
    return f"{card_number}|{exp_month}|{exp_year}|{cvv}"

async def generate_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /gen command के लिए - 10 random cards generate करता है (Full Year Format) """
    try:
        cards = [generate_braintree_card() for _ in range(10)]
        message = "**Generated Braintree Cards 🚀**\n\n" + "\n".join(cards) + "\n\n👉 Join our channel! @DarkDorking"
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /chk command के लिए - Card को $0 Auth से check करता है (Full Year Format) """
    args = context.args

    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: /chk 4111111111111111|12|2025|123")
        return

    card_details = args[0].split('|')
    if len(card_details) < 4:
        await update.message.reply_text("❌ Invalid format! Use: /chk 4111111111111111|12|2025|123")
        return

    card_number, exp_month, exp_year, cvv = card_details

    try:
        result = braintree_gateway.transaction.sale({
            "amount": "0.00",
            "credit_card": {
                "number": card_number,
                "expiration_month": exp_month,
                "expiration_year": exp_year,
                "cvv": cvv
            },
            "options": {
                "submit_for_settlement": False,
                "store_in_vault_on_success": True
            }
        })

        if result.is_success:
            status = "✅ Approved"
            response_message = "Card Verified via Braintree."
        else:
            status = "❌ Declined"
            response_message = result.transaction.processor_response_text if result.transaction else "Transaction Declined"

    except Exception as e:
        status = "⚠️ Error"
        response_message = f"Failed to verify card: {str(e)}"

    message = (
        f"💳 **Card:** {args[0]}\n"
        f"📌 **Status:** {status}\n"
        f"📢 **Response:** {response_message or 'No response from Braintree'}\n"
    )

    await update.message.reply_text(message, parse_mode="Markdown")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("gen", generate_cards))
    application.add_handler(CommandHandler("chk", check_card))

    app = web.Application()
    app.router.add_get("/health", lambda request: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
