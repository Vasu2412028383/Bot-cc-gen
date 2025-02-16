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
        f"━━━━━━━━━━━━━━━━━━\n"
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

# ✅ SK Key Commands
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

async def viewsk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STRIPE_KEY
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to view the Stripe API key!")
        return
    await update.message.reply_text(f"🔑 Current Stripe API Key: `{STRIPE_KEY}`", parse_mode="Markdown")

# ✅ VIP User Management
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to modify VIP users!")
        return
    if not context.args:
        await update.message.reply_text("❌ EXAMPLE: /addvip 123456789")
        return
    user_id = int(context.args[0])
    VIP_USERS.add(user_id)
    await update.message.reply_text(f"✅ User {user_id} added to VIP users!")

async def removevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to modify VIP users!")
        return
    if not context.args:
        await update.message.reply_text("❌ EXAMPLE: /removevip 123456789")
        return
    user_id = int(context.args[0])
    VIP_USERS.discard(user_id)
    await update.message.reply_text(f"✅ User {user_id} removed from VIP users!")

# ✅ Health Check Endpoint
async def health_check(request):
    return web.Response(text="OK")

# ✅ Bot Initialization
async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("addsk", addsk))
    application.add_handler(CommandHandler("viewsk", viewsk))
    application.add_handler(CommandHandler("gen", gen))
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
