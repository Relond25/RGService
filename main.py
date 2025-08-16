import os
import threading
import logging
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# --------- логирование, чтобы видеть причину падений в Render logs ----------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
log = logging.getLogger("rg-bot")

# --------- Flask: держит процесс живым на Render ----------
app = Flask(__name__)

@app.get("/")
def root():
    return "RG Service bot is running"

@app.get("/health")
def health():
    return "ok"

# --------- Telegram бота пишем на python-telegram-bot v20 ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # добавь в Render → Environment

async def start_cmd(update, ctx):
    await update.message.reply_text(
        "Привет! Я бот RG Service. Напиши /help, чтобы выбрать услугу."
    )

async def help_cmd(update, ctx):
    await update.message.reply_text(
        "Доступные услуги:\n"
        "1) Тепловые насосы\n"
        "2) Электромонтаж\n"
        "3) Видеонаблюдение\n"
        "4) Солнечные панели\n\n"
        "Напишите номер услуги и кратко опишите задачу."
    )

async def echo_handler(update, ctx):
    # Простейший «эхо»-диалог: отвечает и показывает, что бот жив
    text = update.message.text or ""
    await update.message.reply_text(f"Принял: {text}\nСкоро свяжемся!")

def run_bot_polling():
    if not BOT_TOKEN:
        log.error("ENV BOT_TOKEN is empty — задайте переменную в Render.")
        return
    app_tg = Application.builder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start_cmd))
    app_tg.add_handler(CommandHandler("help", help_cmd))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
    log.info("Starting Telegram polling…")
    app_tg.run_polling(close_loop=False)

if __name__ == "__main__":
    # Запускаем polling в отдельном потоке,
    # а Flask — в главном (чтобы Render видел веб-сервис)
    threading.Thread(target=run_bot_polling, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    log.info(f"Starting Flask on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
