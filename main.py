import os
import random
import re
import asyncio
import aiohttp
import braintree  # Importing Braintree SDK
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")
BRAINTREE_KEY = None  # Global variable for storing Braintree API keys
ADMIN_ID = 6972264549  # Admin ID for restricted commands

# Braintree configuration
def configure_braintree():
    braintree.Configuration.configure(
        braintree.Environment.Sandbox,  # Use Sandbox for testing or .Production for live
        merchant_id=BRAINTREE_KEY['xtw6fsgw6387brsz'],
        public_key=BRAINTREE_KEY['g3q4dw5ykhjtgcqy'],
        private_key=BRAINTREE_KEY['0276dac6121e9cf5f914b018493902ca']
    )

# Function to get a valid Braintree client token
async def get_braintree_client_token():
    configure_braintree()
    return braintree.ClientToken.generate()

# Function to process payment using Braintree
async def process_braintree_payment(amount, payment_method_nonce):
    configure_braintree()
    transaction = braintree.Transaction.sale({
        "amount": amount,
        "payment_method_nonce": payment_method_nonce,
        "options": {
            "submit_for_settlement": True
        }
    })
    if transaction.is_success:
        return f"Payment of {amount} was successful!"
    else:
        return f"Payment failed: {transaction.message}"

# BIN info function (same as before)
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

# Luhn check for validating the card number
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

# Generate a valid Luhn card number (same as before)
def generate_luhn_card(bin_number):
    while True:
        card_number = bin_number + ''.join(str(random.randint(0, 9)) for _ in range(16 - len(bin_number)))
        if luhn_check(card_number):
            return card_number

# /start command for the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nEnjoy!"
    await update.message.reply_text(welcome_message)

# /addsk command to set Braintree API keys
async def add_sk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BRAINTREE_KEY
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to set the Braintree API keys!")
        return
    if len(context.args) < 3:
        await update.message.reply_text("❌ EXAMPLE: /addsk <merchant_id> <public_key> <private_key>")
        return
    BRAINTREE_KEY = {
        'merchant_id': context.args[0],
        'public_key': context.args[1],
        'private_key': context.args[2]
    }
    await update.message.reply_text("✅ Braintree API keys set successfully!")

# /chk command to check the card and process payment using Braintree
async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BRAINTREE_KEY
    if BRAINTREE_KEY is None:
        await update.message.reply_text("❌ No Braintree API keys found! Admin needs to add them using /addsk")
        return

    args = context.args
    if len(args) < 1 or not re.match(r"^\d{16}\|\d{2}\|\d{2}\|\d{3}$", args[0]):
        await update.message.reply_text("❌ Invalid format!\n**Example:** `/chk 4242424242424242|12|25|123`")
        return

    card_details = args[0].split('|')
    bin_number = card_details[0][:6]
    amount = 1  # Amount to charge (you can modify this as needed)
    payment_method_nonce = card_details[3]  # CVC as payment method nonce (this should be securely handled)

    # Get BIN info
    bin_info = await get_bin_info(bin_number) or {"vendor": "Unknown", "type": "Unknown", "country_name": "Unknown", "bank": "Unknown"}

    try:
        # Use Braintree to process the payment
        payment_status = await process_braintree_payment(amount, payment_method_nonce)
        message = (
            f"🔥 **Braintree Payment** (`/chk`) | Free\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 **Card:** `{args[0]}`\n"
            f"📌 **Status:** {payment_status}\n"
            f"📢 **Response:** {payment_status}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💲 **Gateway:** Braintree\n"
            f"🏦 **Issuer:** {bin_info.get('bank', 'Unknown')}\n"
            f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
            f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Checked by:** @{update.message.from_user.username}\n"
            f"📢 **Join @DarkDorking Channel**"
        )
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Unexpected error: {str(e)}")

# /gen command to generate a valid card
async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1 or len(context.args[0]) != 6 or not context.args[0].isdigit():
        await update.message.reply_text("❌ Please provide a valid BIN number (6 digits). Example: `/gen 424242`")
        return
    
    bin_number = context.args[0]
    generated_card = generate_luhn_card(bin_number)

    # Get BIN info for the generated card
    bin_info = await get_bin_info(bin_number) or {"vendor": "Unknown", "type": "Unknown", "country_name": "Unknown", "bank": "Unknown"}

    # Send the generated card info with BIN details
    message = (
        f"🔥 **Generated Card** (`/gen`) | Free\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Generated Card:** `{generated_card}`\n"
        f"🏦 **Issuer:** {bin_info.get('bank', 'Unknown')}\n"
        f"🌍 **Country:** {bin_info.get('country_name', 'Unknown')}\n"
        f"🔖 **Type:** {bin_info.get('type', 'Unknown')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📢 **Join @DarkDorking Channel**"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# Health check endpoint
async def health_check(request):
    return web.Response(text="OK")

# Run the bot and services
async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addsk", add_sk))
    application.add_handler(CommandHandler("chk", check_card))
    application.add_handler(CommandHandler("gen", gen))  # Added the /gen command
    
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
