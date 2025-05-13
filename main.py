import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji
from aiohttp import web

# === Настройки из .env или Render.env ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
FEEDBACK_CHAT_ID = int(os.getenv("FEEDBACK_CHAT_ID"))
INFO_TOPIC_ID = int(os.getenv("INFO_TOPIC_ID"))

# === Бот ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Фиктивный веб-сервер для Render ===
async def handle(request):
    return web.Response(text="Bot is running")

app = web.Application()
app.router.add_get("/", handle)


# === Команда /fb — отправляет фидбек в группу админов ===
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
        print(f"Ошибка при отправке фидбека: {e}")

    # Ставим реакцию
    try:
        await bot.set_message_reaction(
            chat_id=GROUP_ID,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="✅")]
        )
    except Exception as e:
        print(f"Не удалось поставить реакцию: {e}")

    # Отправляем ответ
    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=message.message_thread_id,
            text="✅ Ваш фидбек успешно отправлен модераторам!"
        )
    except Exception as e:
        print(f"Не удалось отправить ответ: {e}")


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
        print(f"❌ Не удалось получить администраторов: {e}")
        return set()


# === Запуск бота и сервера ===
async def start_bot():
    print("✅ Бот запущен")
    await dp.start_polling(bot)


async def start_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Веб-сервер запущен на порту 8080")


async def run():
    await asyncio.gather(
        start_bot(),
        start_server()
    )


if __name__ == "__main__":
    asyncio.run(run())  # ← Это важно!
