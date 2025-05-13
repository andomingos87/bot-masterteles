from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot ativo! Vamos começar seu atendimento.")
    await servidores(update, context)


async def servidores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Fast Play", callback_data="srv_fastplay")],
        [InlineKeyboardButton("Club",      callback_data="srv_club")],
        [InlineKeyboardButton("P2 Cine",   callback_data="srv_p2cine")],
    ]
    await update.message.reply_text(
        "Escolha um servidor:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("servidores", servidores))
