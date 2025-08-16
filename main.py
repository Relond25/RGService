# main.py
# -*- coding: utf-8 -*-
import os
import logging
import asyncio
from threading import Thread
from datetime import datetime

from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ===================== НАСТРОЙКИ =====================
TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROUP_ID = os.getenv("GROUP_ID")          # например: -4950654570
ADMIN_ID = os.getenv("ADMIN_ID")          # например: 1124748302

# 4 категории услуг (можете поменять текст)
CATEGORIES = [
    ("Тепловые насосы", "cat_hp"),
    ("Электромонтаж", "cat_elec"),
    ("Видеонаблюдение", "cat_cctv"),
    ("Солнечные панели", "cat_pv"),
]

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("rg-bot")

# ===================== FLASK (healthcheck) =====================
flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def index():
    return "RG Service bot is running", 200

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    flask_app.run(host="0.0.0.0", port=port)

# ===================== ДИАЛОГ ЗАЯВКИ =====================
(
    CHOOSING_CATEGORY,
    ASK_NAME,
    ASK_PHONE,
    ASK_ADDRESS,
    ASK_COMMENT,
    CONFIRM,
) = range(6)


def main_menu_keyboard():
    """Клавиатура с 4 категориями."""
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=code)]
        for (title, code) in CATEGORIES
    ]
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт: показать выбор категории."""
    text = (
        "Привет! Я бот RG Service OÜ.\n\n"
        "Выберите категорию услуги, чтобы оставить заявку:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())
    else:
        await update.callback_query.message.reply_text(text, reply_markup=main_menu_keyboard())
    return CHOOSING_CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь выбрал категорию — просим имя."""
    query = update.callback_query
    await query.answer()

    context.user_data["category"] = next(
        (title for (title, code) in CATEGORIES if code == query.data),
        "Другая услуга",
    )

    await query.message.reply_text("Отлично! Напишите, пожалуйста, ваше *имя и фамилию*.", parse_mode="Markdown")
    return ASK_NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Укажите *телефон* для связи:", parse_mode="Markdown")
    return ASK_PHONE


async def got_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("Укажите *адрес* (город, улица, дом):", parse_mode="Markdown")
    return ASK_ADDRESS


async def got_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text.strip()
    await update.message.reply_text("Опишите *кратко задачу / комментарий*:", parse_mode="Markdown")
    return ASK_COMMENT


def build_summary(data: dict, user: "telegram.User"):
    created = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return (
        "📝 *Новая заявка*\n"
        f"Категория: *{data.get('category','') }*\n"
        f"Имя: *{data.get('name','')}*\n"
        f"Телефон: *{data.get('phone','')}*\n"
        f"Адрес: *{data.get('address','')}*\n"
        f"Комментарий: _{data.get('comment','')}_\n"
        f"Отправитель: @{user.username or user.id}\n"
        f"Создано: {created}"
    )


async def got_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["comment"] = update.message.text.strip()

    summary = build_summary(context.user_data, update.effective_user)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Отправить", callback_data="confirm_send"),
          InlineKeyboardButton("✏️ Изменить", callback_data="edit_start")]]
    )
    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=keyboard)
    return CONFIRM


async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение отправки: шлём в группу/админу и благодарим."""
    query = update.callback_query
    await query.answer()

    if query.data == "edit_start":
        # начать заново
        await query.message.reply_text("Окей, давайте заново. Введите *имя и фамилию*:", parse_mode="Markdown")
        return ASK_NAME

    # Отправляем заявку в группу (если указана)
    summary = build_summary(context.user_data, update.effective_user)
    if GROUP_ID:
        try:
            await context.bot.send_message(chat_id=int(GROUP_ID), text=summary, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Не удалось отправить в группу: {e}")

    # И админу (если указан)
    if ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=int(ADMIN_ID), text=summary, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Не удалось отправить админу: {e}")

    await query.message.reply_text("Спасибо! Ваша заявка отправлена. Наш специалист свяжется с вами.")
    context.user_data.clear()
    # Показать меню категорий снова
    await query.message.reply_text("Хотите отправить ещё одну заявку? Выберите категорию:", reply_markup=main_menu_keyboard())
    return CHOOSING_CATEGORY


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Диалог отменён. Чтобы начать заново, отправьте /start")
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/start — оставить заявку\n"
        "/help — помощь"
    )

# ===================== СБОРКА ПРИЛОЖЕНИЯ =====================
def build_application() -> Application:
    if not TOKEN:
        raise
