import os
import threading
from flask import Flask
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# 1) Токен берём из переменных окружения Render (Settings → Environment → BOT_TOKEN)
TOKEN = os.getenv("BOT_TOKEN")

# --- Telegram бот ---
def start(update, context):
    update.message.reply_text(
        "Привет! Я бот RG Service.\n"
        "Выберите категорию услуги:\n"
        "1. Электрика\n2. Тепловые насосы\n3. Солнечные панели\n4. Умный дом"
    )

def echo(update, context):
    update.message.reply_text(f"Вы написали: {update.message.text}")

def run_bot():
    if not TOKEN:
        print("ERROR: BOT_TOKEN is not set")
        return
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    updater.start_polling()
    updater.idle()

# --- Flask (health check для Render) ---
app = Flask(__name__)

@app.get("/")
def index():
    return "OK", 200

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

    # Запускаем веб-сервер и слушаем порт, который даёт Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
