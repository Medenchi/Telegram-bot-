import logging
import threading

from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# === Настройки ===
BOT_TOKEN = '8124960394:AAFBpzmNFnl53Pjt-JE8y_S2CLb3ElpDcAo'  # Замените на ваш токен
TARGET_CHAT_ID = -1002516656067  # ID группы, где искать #ФБ
NOTIFY_CHAT_ID = -1002344286804  # Куда отправлять уведомление

# === Логирование ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Telegram бот ===
async def check_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if chat.type not in ['group', 'supergroup']:
        return

    text = message.text or ""
    
    if "#фб" in text.lower():
        link = f"https://t.me/c/{str(chat.id)[4:]}/{message.message_id}"
        notification = f"📢 В группе обнаружен фидбэк!\n\n[Ссылка на сообщение]({link})"
        
        await context.bot.send_message(
            chat_id=NOTIFY_CHAT_ID,
            text=notification,
            parse_mode="Markdown"
        )

# === Инициализация и запуск бота в отдельном потоке ===
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handler = MessageHandler(filters.TEXT & ~filters.COMMAND, check_feedback)
    app.add_handler(handler)
    app.run_polling()

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
