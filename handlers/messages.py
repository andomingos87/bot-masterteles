from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters

async def texto_recebido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data

    if d.get("awaiting_name"):
        nome = update.message.text.strip()
        d.update(entered_name=nome, awaiting_name=False, awaiting_name_confirm=True)
        kb = [[InlineKeyboardButton("Sim", callback_data="name_yes"),
               InlineKeyboardButton("Não", callback_data="name_no")]]
        await update.message.reply_text(
            f"Confirma este nome: *{nome}* ?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
        return

    if d.get("awaiting_email"):
        email = update.message.text.strip()
        d.update(entered_email=email, awaiting_email=False, awaiting_email_confirm=True)
        kb = [[InlineKeyboardButton("Sim", callback_data="email_yes"),
               InlineKeyboardButton("Não", callback_data="email_no")]]
        await update.message.reply_text(
            f"Confirma este e-mail: *{email}* ?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("Use /servidores para iniciar o fluxo.")
    
def register(app):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_recebido))