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
STRIPE_KEYS = {"global": None}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is the Free CC Generator Bot.\nEnjoy!"
    await update.message.reply_text(welcome_message)

async def add_sk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("❌ EXAMPLE: `/addsk sk_key_here`")
        return
    STRIPE_KEYS["global"] = context.args[0]
    await update.message.reply_text("✅ Stripe Key Set Successfully for All Users!")

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMINS:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ EXAMPLE: `/addpremium user_id days`")
        return
    PREMIUM_USERS[args[0]] = int(args[1])
    await update.message.reply_text("✅ Premium added!")

async def remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMINS:
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: `/removepremium user_id`")
        return
    PREMIUM_USERS.pop(args[0], None)
    await update.message.reply_text("✅ Premium removed!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMINS:
        return
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("❌ EXAMPLE: `/broadcast Your Message Here`")
        return
    for user in PREMIUM_USERS.keys():
        try:
            await context.bot.send_message(chat_id=user, text=message)
        except:
            pass
    await update.message.reply_text("✅ Broadcast Sent!")

async def get_bin_info(bin_number):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BIN_LOOKUP_URL}{bin_number}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "brand": data.get("brand", "Unknown"),
                        "type": data.get("type", "Unknown"),
                        "level": data.get("level", "Unknown"),
                        "bank": data.get("bank", "Unknown"),
                        "country": data.get("country", "Unknown"),
                        "flag": data.get("flag", "🌍")
                    }
    except:
        return None

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if STRIPE_KEYS["global"] is None:
        await update.message.reply_text("❌ No Stripe key found! Admin needs to add it.")
        return
    stripe.api_key = STRIPE_KEYS["global"]
    
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
    except stripe.error.CardError:
        message = f"❌ DEAD: `{args[0]}`"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ EXAMPLE: `/gen 424242 [MM/YY] [CVV]`")
        return
    
    bin_number = args[0]
    if not re.match(r"^\d{4,16}$", bin_number):
        await update.message.reply_text("❌ Wrong B!n Number!")
        return
    
    exp_date = args[1] if len(args) > 1 else f"{random.randint(1,12):02d}/{random.randint(25,30)}"
    cvv = args[2] if len(args) > 2 else f"{random.randint(100,999)}"
    
    bin_info = await get_bin_info(bin_number[:6])
    
    cards = [
        f"{bin_number}{''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number)))} | {exp_date} | {cvv}"
        for _ in range(10)
    ]
    
    bin_details = (
        f"📝 **𝗜𝗻𝗳𝗼:** {bin_info['brand']} - {bin_info['type']} - {bin_info['level']}\n"
        f"🏦 **𝐈𝐬𝐬𝐮𝐞𝐫:** {bin_info['bank']}\n"
        f"🌍 **𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {bin_info['country']} {bin_info['flag']}\n\n"
    ) if bin_info else "⚠️ **BIN Info Not Available**\n\n"
    
    message = f"**Generated Cards 🚀**\n\n{bin_details}\n" + "\n".join([f"`{card}`" for card in cards])
    await update.message.reply_text(message, parse_mode="Markdown")

async def health_check(request):
    return web.Response(text="OK")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("chk", check_card))
    application.add_handler(CommandHandler("addsk", add_sk))
    application.add_handler(CommandHandler("addpremium", add_premium))
    application.add_handler(CommandHandler("removepremium", remove_premium))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
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
