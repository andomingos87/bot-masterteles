from telegram.ext import ApplicationBuilder
from settings import TELEGRAM_TOKEN
from handlers import commands, callbacks, messages

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    commands.register(app)
    callbacks.register(app)
    messages.register(app)
    app.run_polling()

if __name__ == "__main__":
    main()
