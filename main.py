import os
import asyncio
import threading
import time
import requests
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji
from flask import Flask
from dotenv import load_dotenv

# === Загружаем переменные из .env ===
load_dotenv()

# === Настройки из .env ===
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен бота (строка)
GROUP_ID = int(os.getenv("GROUP_ID"))  # Должно быть числом
FEEDBACK_CHAT_ID = int(os.getenv("FEEDBACK_CHAT_ID"))  # Должно быть числом
INFO_TOPIC_ID = int(os.getenv("INFO_TOPIC_ID"))  # Должно быть числом

# === Бот ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === Flask сервер для keep-alive запросов ===
@app.route('/')
def home():
    return "Бот работает!"


# === Функция keep-alive (запускается в отдельном потоке) ===
def keep_alive_loop():
    project_url = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.replit.dev"
    print(f"🔁 Keep-alive URL: {project_url}")

    while True:
        try:
            response = requests.get(project_url)
            logger.info(f"✅ Ping: {response.status_code} | {response.text[:20]}...")
        except Exception as e:
            logger.error(f"❌ Ошибка при ping: {e}")
        time.sleep(60)  # Пинг каждую минуту


# === Обработчики команд ===

# Команда /fb — отправляет фидбек в группу админов
@dp.message(Command("fb"))
async def handle_feedback(message: Message):
    if message.chat.id != GROUP_ID:
        return

    args = message.text[len("/fb"):].strip()
    if not args:
        await message.reply("Пожалуйста, напишите текст после команды /fb.")
        return

    user = message.from_user

    feedback_text = f"""
📥 <b>Новый фидбек</b>

👤 Пользователь: {user.full_name} (@{user.username} | ID: {user.id})
💬 Текст: {args}
📌 Время: {message.date.strftime('%Y-%m-%d %H:%M')}
"""

    try:
        await bot.send_message(chat_id=FEEDBACK_CHAT_ID, text=feedback_text)
    except Exception as e:
        logger.error(f"Ошибка при отправке фидбека: {e}")

    # Ставим реакцию на исходное сообщение
    try:
        await bot.set_message_reaction(
            chat_id=GROUP_ID,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="✅")]
        )
    except Exception as e:
        logger.error(f"Не удалось поставить реакцию: {e}")

    # Отправляем ответ
    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=message.message_thread_id,
            text="✅ Ваш фидбек успешно отправлен модераторам!"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить ответ: {e}")


# === Команда /say — публикация от имени бота ===
@dp.message(Command("say"))
async def handle_say(message: Message):
    admins = await get_admins(GROUP_ID)
    if message.from_user.id not in admins:
        await message.reply("❌ У вас нет прав использовать эту команду.")
        return

    args = message.text[len("/say"):].strip()
    if not args:
        await message.reply("Используйте: /say [topic_id] [текст]")
        return

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Используйте: /say [topic_id] [текст]")
        return

    try:
        topic_id = int(parts[0])
    except ValueError:
        await message.reply("Первый аргумент должен быть числом (topic_id).")
        return

    text = parts[1]

    try:
        await bot.send_message(chat_id=GROUP_ID, message_thread_id=topic_id, text=text)
        await message.reply("✅ Сообщение успешно опубликовано.")
    except Exception as e:
        await message.reply(f"❌ Не удалось опубликовать сообщение: {e}")


# === Защита топика "Инфо" ===
@dp.message()
async def restrict_info_topic(message: Message):
    if message.chat.id != GROUP_ID or message.message_thread_id != INFO_TOPIC_ID:
        return

    if message.from_user.is_bot:
        return

    admins = await get_admins(GROUP_ID)
    if message.from_user.id in admins:
        return

    await message.delete()
    try:
        await message.answer("❌ Только админы могут писать в этом топике.", delete_after=5)
    except:
        pass


# === Получение списка администраторов группы ===
async def get_admins(chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return {admin.user.id for admin in admins}
    except Exception as e:
        logger.error(f"❌ Не удалось получить администраторов: {e}")
        return set()


# === Запуск Flask и бота ===
async def main():
    print("✅ Бот запущен")

    # Запуск Flask сервера в отдельном потоке
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
    flask_thread.start()

    # Запуск keep-alive в отдельном потоке
    keep_alive_thread = threading.Thread(target=keep_alive_loop)
    keep_alive_thread.start()

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
