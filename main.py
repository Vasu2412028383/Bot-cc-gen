import os
import random
import re
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web
import stripe

TOKEN = os.getenv("TELEGRAM_TOKEN")
BIN_LOOKUP_URL = "https://bins.antipublic.cc/bins/"
ADMINS = {"6972264549"}
PREMIUM_USERS = {}
STRIPE_KEYS = {"global": None}

def luhn_generate(bin_number):
    while True:
        card = bin_number + "".join(str(random.randint(0, 9)) for _ in range(15 - len(bin_number)))
        digits = [int(d) for d in card]
        for i in range(len(digits) - 2, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        checksum = (10 - sum(digits) % 10) % 10
        final_card = card + str(checksum)
        if luhn_check(final_card):
            return final_card

def luhn_check(card_number):
    digits = [int(d) for d in str(card_number)][::-1]
    checksum = 0
    for i, digit in enumerate(digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  
    welcome_message = f"Welcome, {user_name}! 🚀\n\nThis bot generates and checks cards with Luhn Algorithm."
    await update.message.reply_text(welcome_message)

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ EXAMPLE: /gen 424242")
        return
    
    bin_number = args[0]
    if not re.match(r"^\d{4,6}$", bin_number):
        await update.message.reply_text("❌ Invalid BIN Number! Must be 4-6 digits.")
        return
    
    cards = [luhn_generate(bin_number) for _ in range(10)]
    message = "Generated Luhn Valid Cards 🚀\n\n" + "\n".join(cards)
    await update.message.reply_text(message, parse_mode="Markdown")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ EXAMPLE: /chk 4242424242424242")
        return
    
    card_number = args[0].replace("|", " ").split()[0]
    if luhn_check(card_number):
        message = f"✅ Valid Luhn Card: {card_number}"
    else:
        message = f"❌ Invalid Card: {card_number}"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def run_services():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("chk", check_card))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_services())
