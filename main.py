import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji

# === Настройки из переменных среды ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
FEEDBACK_CHAT_ID = int(os.getenv("FEEDBACK_CHAT_ID"))
INFO_TOPIC_ID = int(os.getenv("INFO_TOPIC_ID"))
ALLOWED_FB_TOPIC_ID = int(os.getenv("ALLOWED_FB_TOPIC_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Команда /fb — принимает текст и медиа ===
@dp.message(Command("fb"))
async def handle_feedback(message: Message):
    if message.chat.id != GROUP_ID or message.message_thread_id != ALLOWED_FB_TOPIC_ID:
        return

    user = message.from_user
    caption = f"""
📥 <b>Новый фидбек</b>

👤 Пользователь: {user.full_name} (@{user.username} | ID: {user.id})
📌 Время: {message.date.strftime('%Y-%m-%d %H:%M')}
"""

    # Если есть фото — отправляем его
    if message.photo:
        photo = message.photo[-1]  # самое большое фото
        await bot.send_photo(
            chat_id=FEEDBACK_CHAT_ID,
            photo=photo.file_id,
            caption=caption,
            parse_mode="HTML"
        )
        await bot.set_message_reaction(
            chat_id=GROUP_ID,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="✅")]
        )
        await message.reply("✅ Фото отправлено модераторам!")

    # Если есть видео — отправляем его
    elif message.video:
        video = message.video
        await bot.send_video(
            chat_id=FEEDBACK_CHAT_ID,
            video=video.file_id,
            caption=caption,
            parse_mode="HTML"
        )
        await bot.set_message_reaction(
            chat_id=GROUP_ID,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="✅")]
        )
        await message.reply("✅ Видео отправлено модераторам!")

    # Если текст — отправляем текст
    elif message.text:
        text = message.text[len("/fb"):].strip()
        if not text:
            await message.reply("Пожалуйста, напишите текст после команды /fb.")
            return

        feedback_text = f"{caption}\n💬 Текст: {text}"
        await bot.send_message(chat_id=FEEDBACK_CHAT_ID, text=feedback_text, parse_mode="HTML")
        await bot.set_message_reaction(
            chat_id=GROUP_ID,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="✅")]
        )
        await message.reply("✅ Ваш фидбек успешно отправлен модераторам!")

    else:
        await message.reply("⚠️ Неподдерживаемый формат. Используйте текст, фото или видео.")

# === Команда /say — публикация от имени бота (без уведомления об успехе) ===
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


# === Получение списка админов ===
async def get_admins(chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return {admin.user.id for admin in admins}
    except Exception as e:
        logger.error(f"Не удалось получить администраторов: {e}")
        return set()


# === Запуск бота ===
async def main():
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
