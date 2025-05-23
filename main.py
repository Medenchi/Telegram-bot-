import os
import logging
import threading
import asyncio

from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# === Загрузка переменных из .env (локально) ===
from dotenv import load_dotenv
load_dotenv()

# === Настройки из env ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
FEEDBACK_CHAT_ID = int(os.getenv("FEEDBACK_CHAT_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))

# === Логирование ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Telegram бот ===
async def check_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if chat.id != GROUP_ID:
        return  # Игнорируем сообщения не из целевой группы

    text = message.text or ""
    
    if "#фб" in text.lower():
        link = f"https://t.me/c/{str(chat.id)[4:]}/{message.message_id}"
        notification = f"📢 В группе обнаружен фидбэк!\n\n[Ссылка на сообщение]({link})"
        
        await context.bot.send_message(
            chat_id=FEEDBACK_CHAT_ID,
            text=notification,
            parse_mode="Markdown"
        )

# === Инициализация и запуск бота в отдельном потоке ===
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & ~filters.COMMAND, check_feedback)
    app.add_handler(handler)
    loop.run_until_complete(app.run_polling())

# === Flask сервер для "оживления" Render/хостинга ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

# === Запуск всего вместе ===
if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    flask_thread = threading.Thread(target=run_flask)

    bot_thread.start()
    flask_thread.start()
