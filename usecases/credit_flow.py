from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def pedir_creditos(chat, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.update(awaiting_credits=True)
    keyboard = [[InlineKeyboardButton(str(q), callback_data=f"cred_{q}")]
                for q in (10, 20, 30, 50)]
    await chat.reply_text(
        "Quantos créditos deseja comprar?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
