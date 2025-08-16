import os
import threading
from flask import Flask

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# ========= Flask (держит веб-порт живым для Render) =========
app = Flask(__name__)

@app.get("/")
def index():
    return "RG Service bot is running ✅"

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

# ========= Telegram Bot =========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Добавь в Render → Environment → BOT_TOKEN

CATEGORIES = [
    ["Тепловой насос (обслуживание)"],
    ["Кондиционер / вентиляция"],
    ["Электромонтаж"],
    ["Видеонаблюдение / Солнечные панели"]
]

WELCOME_RU = (
    "Привет! Я бот **RG Service**.\n\n"
    "Выберите категорию услуги, а затем опишите проблему и оставьте контакты.\n"
    "Команда: /start — начать заново."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(CATEGORIES, resize_keyboard=True)
    await update.message.reply_text(WELCOME_RU, reply_markup=kb)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    # Если выбран один из вариантов — попросим детали
    if text in sum(CATEGORIES, []):
        context.user_data["category"] = text
        await update.message.reply_text(
            "Отлично! Напишите, пожалуйста:\n"
            "• Коротко проблему\n"
            "• Адрес\n"
            "• Телефон\n\n"
            "Пример:\n"
            "«Не греет воздух-вода, Нарва, +372 55 123 456»"
        )
        return

    # Если уже есть категория — считаем это заявкой
    category = context.user_data.get("category")
    if category:
        # Здесь позже можем отправлять в группу/CRM/почту
        await update.message.reply_text(
            "Спасибо! Ваша заявка принята ✅\n"
            f"Категория: {category}\n"
            f"Текст: {text}\n\n"
            "Мы свяжемся с вами в рабочее время."
        )
        # Сброс категории, чтобы можно было создать новую
        context.user_data.pop("category", None)
    else:
        # Если пользователь пишет без выбора категории
        await start(update, context)

def run_telegram():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения!")

    app_ = Application.builder().token(BOT_TOKEN).build()
    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app_.run_polling(allowed_updates=Update.ALL_TYPES)

# ========= Entry point =========
if __name__ == "__main__":
    # Поднимаем Flask на фоне и запускаем бота
    threading.Thread(target=run_flask, daemon=True).start()
    run_telegram()
