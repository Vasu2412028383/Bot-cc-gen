import os
import random
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("8011551620:AAFvDlRL7brL1JF9kEpQJXIVzZf01og4Lc0")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚫 **Legal Notice:** यह बॉट सिर्फ डमी डेटा जनरेट करता है।')

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("कृपया बिन नंबर डालें")
        return

    bin_number = args[0]
    exp_date = None
    cvv = None

    if len(args) > 1:
        exp_date = args[1]
    if len(args) > 2:
        cvv = args[2]

    if not re.match(r"^\d{6,16}$", bin_number):
        await update.message.reply_text("बिन नंबर अवैध है")
        return

    if exp_date and not re.match(r"^\d{1,2}/\d{2}$", exp_date):
        await update.message.reply_text("एक्सपायरी डेट अवैध है")
        return

    if cvv and not re.match(r"^\d{3}$", cvv):
        await update.message.reply_text("CVV अवैध है")
        return

    cards = []
    for _ in range(10):
        card_number = generate_card_number(bin_number)
        if exp_date:
            card_number += f" - {exp_date}"
        if cvv:
            card_number += f" - {cvv}"
        cards.append(card_number)

    await update.message.reply_text("\n".join(cards))

def generate_card_number(bin_number):
    card_number = bin_number + ''.join(str(random.randint(0, 9)) for _ in range(16 - len(bin_number)))
    return card_number

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    dp = application.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gen", generate))
    application.run_polling()

if __name__ == "__main__":
    main()
