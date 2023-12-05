import logging

import openai
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Включите логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота
API_TELEGRAM_TOKEN = 'ТОКЕН ДЛЯ ТЕЛЕГРАМ БОТА'
API_VSEGPT_TOKEN = "АПИ КЛЮЧ С САЙТА VSEGPT"

bot = Bot(token=API_TELEGRAM_TOKEN)
dp = Dispatcher(bot)

openai.api_base = "https://api.vsegpt.ru:6070/v1"
openai.api_key = API_VSEGPT_TOKEN

# Словарь для хранения истории разговоров
conversation_history = {}

# Функция для обрезки истории разговора
def trim_history(history, max_length=4096):
    current_length = sum(len(message["content"]) for message in history)
    while history and current_length > max_length:
        removed_message = history.pop(0)
        current_length -= len(removed_message["content"])
    return history


@dp.message_handler(commands=['clear'])
async def process_clear_command(message: types.Message):
    user_id = message.from_user.id
    conversation_history[user_id] = []
    await message.reply("История диалога очищена.")

# Обработчик для каждого нового сообщения
@dp.message_handler()
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_input = message.text

    if user_input == "/start":
        await message.answer("Добро пожаловать в ChatGPT-бот!")
        return

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_input})
    conversation_history[user_id] = trim_history(conversation_history[user_id])

    chat_history = conversation_history[user_id]

    try:
        response = await openai.ChatCompletion.acreate(
            model="openai/gpt-3.5-turbo",
            messages=chat_history

        )
        chat_gpt_response = response["choices"][0]["message"]["content"]
    except Exception as e:
        print(e)
        chat_gpt_response = "Извините, произошла ошибка."

    conversation_history[user_id].append({"role": "assistant", "content": chat_gpt_response})
    print(conversation_history)
    length = sum(len(message["content"]) for message in conversation_history[user_id])
    print(length)
    await message.answer(chat_gpt_response)


# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
