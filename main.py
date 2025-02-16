import os
import random
import re
import asyncio
import aiohttp
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
        braintree.Environment.Sandbox,  # Sandbox Mode (Live के लिए बदलें)
        merchant_id=BRAINTREE_MERCHANT_ID,
        public_key=BRAINTREE_PUBLIC_KEY,
        private_key=BRAINTREE_PRIVATE_KEY
    )
)

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

def generate_braintree_card():
    iin = "400000"  # Braintree test IIN (first 6 digits)
    account_number = "".join(str(random.randint(0, 9)) for _ in range(9))
    card_number = iin + account_number
    exp_month = f"{random.randint(1, 12):02d}"
    exp_year = f"{random.randint(25, 30)}"
    cvv = f"{random.randint(100, 999)}"
    return f"{card_number}|{exp_month}|{exp_year}|{cvv}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    welcome_message = (
        f"🌟 Welcome, {user_name}! 🌟\n\n"
        "🚀 This bot allows you to generate and verify Braintree cards easily!\n"
        "🔹 Use /gen to generate test cards.\n"
        "🔹 Use /chk to check a card using Braintree.\n"
        "🔹 Use /bin to get BIN details.\n"
        "💡 Stay secure and use responsibly!\n\n"
        "✨ Enjoy your experience! ✨"
    )
    await update.message.reply_text(welcome_message)

async def get_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not re.match(r"^\d{6}$", args[0]):
        await update.message.reply_text("❌ EXAMPLE: /bin 400000")
        return
    
    bin_number = args[0]
    bin_info = await get_bin_info(bin_number)
    
    if not bin_info:
        message = f"❌ No details found for BIN {bin_number}"
    else:
        message = (
            f"💳 **BIN:** {bin_number}\n"
            f"🏦 **Bank:** {bin_info.get('bank', 'Unknown')}\n"
            f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
            f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
        )
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cards = [generate_braintree_card() for _ in range(10)]
        message = "**Generated Braintree Cards 🚀**\n\n" + "\n".join(cards) + "\n\n👉 Join our channel! @DarkDorking"
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: /chk 4111111111111111|12|25|123")
        return
    
    card_details = args[0].split('|')
    bin_number = card_details[0][:6]
    bin_info = await get_bin_info(bin_number)
    
    try:
        result = braintree_gateway.credit_card.verify(
            {
                "number": card_details[0],
                "expiration_month": card_details[1],
                "expiration_year": card_details[2],
                "cvv": card_details[3],
            }
        )
        
        if result.is_success:
            status = "✅ Approved"
            response_message = "Card Verified via Braintree."
        else:
            status = "❌ Declined"
            response_message = result.message
    
    except Exception as e:
        status = "⚠️ Error"
        response_message = f"Failed to verify card: {str(e)}"
    
    message = (
        f"💳 **Card:** {args[0]}\n"
        f"📌 **Status:** {status}\n"
        f"📢 **Response:** {response_message}\n"
        f"🏦 **Issuer:** {bin_info.get('bank', 'Unknown')}\n"
        f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
        f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("chk", check_card))
    application.add_handler(CommandHandler("bin", get_bin))
    
    app = web.Application()
    app.router.add_get("/health", health_check)  # Health check route fixed
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)  # Ensuring it's accessible
    await site.start()
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
