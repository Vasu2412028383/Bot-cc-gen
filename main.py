import os
import random
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚫 **Legal Notice:** यह बॉट सिर्फ डमी डेटा जनरेट करता है।')

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            await update.message.reply_text("❌ उदाहरण: `/gen 424242 [MM/YY] [CVV]`")
            return

        # बिन नंबर वैलिडेट करें
        bin_number = args[0]
        if not re.match(r"^\d{6,16}$", bin_number):
            await update.message.reply_text("❌ अवैध बिन नंबर!")
            return

        # एक्सपायरी डेट और CVV (अगर दिया गया हो)
        exp_date = args[1] if len(args) > 1 else f"{random.randint(1,12):02d}/{random.randint(25,30)}"
        cvv = args[2] if len(args) > 2 else f"{random.randint(100,999)}"

        # 10 डमी कार्ड जनरेट करें
        cards = []
        for _ in range(10):
            card = (
                bin_number + 
                ''.join(str(random.randint(0,9)) for _ in range(16 - len(bin_number))) + 
                f" | {exp_date} | {cvv}"
            )
            cards.append(card)

        await update.message.reply_text("\n".join(cards))

    except Exception as e:
        await update.message.reply_text(f"⚠️ एरर: {str(e)}")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    application.run_polling()

if __name__ == "__main__":
    main()
