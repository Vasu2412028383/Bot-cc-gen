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
STRIPE_KEYS = {}
GLOBAL_STRIPE_KEY = None  # ✅ Global SK Key

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\n\nThis bot is created for @DarkDorking channel members. Enjoy!"
    await update.message.reply_text(welcome_message)

async def add_sk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in ADMINS:
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ EXAMPLE: `/addsk sk_test_123456`")
        return
    
    global GLOBAL_STRIPE_KEY
    GLOBAL_STRIPE_KEY = args[0]
    await update.message.reply_text("✅ Global Stripe Key Set!")

async def remove_sk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in ADMINS:
        return
    
    global GLOBAL_STRIPE_KEY
    GLOBAL_STRIPE_KEY = None
    await update.message.reply_text("✅ Global Stripe Key Removed!")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in ADMINS:
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ EXAMPLE: `/ban user_id`")
        return
    
    del PREMIUM_USERS[args[0]]
    await update.message.reply_text("✅ User Banned!")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if user_id not in PREMIUM_USERS and USER_CHECK_LIMIT.get(user_id, 0) >= 10:
        await update.message.reply_text("❌ Daily limit reached! Buy Premium to check more cards.")
        return
    
    if GLOBAL_STRIPE_KEY:
        stripe.api_key = GLOBAL_STRIPE_KEY
    else:
        await update.message.reply_text("❌ No Stripe key found! Admin needs to add it.")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: `/chk 4242424242424242|12/25|123`")
        return
    
    card_details = args[0].split('|')
    
    try:
        token = stripe.Token.create(
            card={
                "number": card_details[0],
                "exp_month": int(card_details[1].split('/')[0]),
                "exp_year": int(card_details[1].split('/')[1]),
                "cvc": card_details[2]
            }
        )
        message = f"✅ LIVE: `{args[0]}`"
        USER_CHECK_LIMIT[user_id] = USER_CHECK_LIMIT.get(user_id, 0) + 1
    except stripe.error.CardError:
        message = f"❌ DEAD: `{args[0]}`"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addsk", add_sk))
    application.add_handler(CommandHandler("removesk", remove_sk))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("chk", check_card))
    
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="OK"))
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
