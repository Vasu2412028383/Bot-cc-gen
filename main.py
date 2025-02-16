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

# ✅ Admin Commands
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

async def listvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to view VIP users!")
        return
    vip_list = "\n".join(str(user) for user in VIP_USERS) if VIP_USERS else "No VIP users added."
    await update.message.reply_text(f"🔹 VIP Users:\n{vip_list}")

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

    results.sort(key=lambda x: "✅" not in x)  # Live cards first
    await update.message.reply_text("\n".join(results))

# ✅ Bot Setup
async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("addsk", addsk))
    application.add_handler(CommandHandler("chk", chk))
    application.add_handler(CommandHandler("mass", mass))
    application.add_handler(CommandHandler("addvip", addvip))
    application.add_handler(CommandHandler("removevip", removevip))
    application.add_handler(CommandHandler("listvip", listvip))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
