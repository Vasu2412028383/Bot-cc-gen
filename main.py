import os
import random
import re
import asyncio
import aiohttp
from datetime import datetime
import stripe
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_TOKEN")
BIN_LOOKUP_URL = "https://bins.antipublic.cc/bins/"
ADMINS = {"6972264549"}  # Replace with your Telegram ID
PREMIUM_USERS = {}
USER_CHECK_LIMIT = {}
STRIPE_KEYS = {"global": None}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis is @DarkDorking CC Generator Bot.\nEnjoy!"
    await update.message.reply_text(welcome_message)

async def add_sk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("❌ EXAMPLE: `/addsk sk_key_here`")
        return
    STRIPE_KEYS["global"] = context.args[0]
    await update.message.reply_text("✅ Stripe Key Set Successfully!")

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
    user_id = str(update.message.from_user.id)
    if user_id not in PREMIUM_USERS:
        USER_CHECK_LIMIT[user_id] = USER_CHECK_LIMIT.get(user_id, 10)
        if USER_CHECK_LIMIT[user_id] <= 0:
            await update.message.reply_text("❌ You have reached today's limit!")
            return
    
    if STRIPE_KEYS["global"] is None:
        await update.message.reply_text("❌ No Stripe key found! Admin needs to add it.")
        return
    stripe.api_key = STRIPE_KEYS["global"]
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: `/chk 4242424242424242|08|27|123`")
        return
    
    card_details = re.split(r'\|', args[0])
    
    if len(card_details[1]) == 2:
        exp_month, exp_year = int(card_details[1]), 2000 + int(card_details[2])
    else:
        exp_month, exp_year = int(card_details[1]), int(card_details[2])
    
    try:
        token = stripe.Token.create(
            card={
                "number": card_details[0],
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": card_details[3]
            }
        )
        status = "✅ LIVE"
    except stripe.error.CardError:
        status = "❌ DEAD"
    
    bin_info = await get_bin_info(card_details[0][:6])
    bin_details = (f"📝 **𝗜𝗻𝗳𝗼:** {bin_info['brand']} - {bin_info['type']} - {bin_info['level']}\n"
                   f"🏦 **𝐈𝐬𝐬𝐮𝐞𝐫:** {bin_info['bank']}\n"
                   f"🌍 **𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {bin_info['country']} {bin_info['flag']}\n\n") if bin_info else "⚠️ **BIN Info Not Available**\n\n"
    
    message = f"{status}: `{args[0]}`\n\n{bin_details}"
    await update.message.reply_text(message, parse_mode="Markdown")
    
    if user_id not in PREMIUM_USERS:
        USER_CHECK_LIMIT[user_id] -= 1
        await update.message.reply_text(f"🔹 Remaining daily checks: {USER_CHECK_LIMIT[user_id]}")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ EXAMPLE: `/gen 424242`")
        return
    
    bin_number = args[0]
    bin_info = await get_bin_info(bin_number[:6])
    
    cards = [
        f"{bin_number}{''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number)))} | "
        f"{random.randint(1,12):02d}|{random.randint(25,30)} | {random.randint(100,999)}"
        for _ in range(10)
    ]
    
    bin_details = (f"📝 **𝗜𝗻𝗳𝗼:** {bin_info['brand']} - {bin_info['type']} - {bin_info['level']}\n"
                   f"🏦 **𝐈𝐬𝐬𝐮𝐞𝐫:** {bin_info['bank']}\n"
                   f"🌍 **𝗖𝗼𝘂𝗻𝘁𝗿𝘆:** {bin_info['country']} {bin_info['flag']}\n\n") if bin_info else "⚠️ **BIN Info Not Available**\n\n"
    
    message = f"**Generated Cards 🚀 @DarkDorking**\n\n{bin_details}" + "\n".join([f"`{card}`" for card in cards])
    await update.message.reply_text(message, parse_mode="Markdown")
