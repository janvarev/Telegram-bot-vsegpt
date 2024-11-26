import logging
import asyncio
from typing import Dict, List

import openai
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
# from aiogram.utils.markdown import code

from models import LLM_MODELS
# Включите логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота
from config import (
    API_TELEGRAM_TOKEN,
    API_VSEGPT_TOKEN,
    ALLOWED_USERS,
    VSEGPT_API_BASE
)

bot = Bot(
    token=API_TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML
                                 )
)
dp = Dispatcher()

openai.api_base = VSEGPT_API_BASE
openai.api_key = API_VSEGPT_TOKEN
bot_users = [int(id_str) for id_str in ALLOWED_USERS.split(':')]
llm_model = LLM_MODELS[0]

class CommonMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Update, data: dict):
        message = event.message
        if message:
            await bot.send_chat_action(chat_id=message.from_user.id, action='typing')

            # Проверка идентификатора чата
            if message.chat.id not in bot_users:
                await message.reply(f"Извините, я вас не знаю. Не пишите мне больше.\nЕсли я должен вас знать, передайте моему владельцу ваш Telegram ID <code>{message.chat.id}</code>")
                return
        
        try:
            result = await handler(event, data)
            await bot.set_message_reaction(chat_id=message.from_user.id, message_id=message.message_id, reaction=[{'type':'emoji', 'emoji':'👌'}])
            return result
        except Exception as e:
            print(f'Exception: {e}')
            await bot.set_message_reaction(chat_id=message.from_user.id, message_id=message.message_id, reaction=[{'type':'emoji', 'emoji':'🤷‍♂'}])
            await message.answer(f'🤷‍♂️ Ошибка: {e}')
            return

dp.update.middleware(CommonMiddleware())  # Регистрация middleware

# Словарь для хранения истории разговоров
conversation_history = {}

# Функция для обрезки истории разговора
def trim_history(history, max_length=4096):
    current_length = sum(len(message["content"]) for message in history)
    while history and current_length > max_length:
        removed_message = history.pop(0)
        current_length -= len(removed_message["content"])
    return history

async def change_model(message: types.Message, model = None) -> None:
    global llm_model
    if not model:
        # Если аргументов нет, показываем список доступных моделей
        models_list = "\n".join([f"<code>/model {model}</code>" for model in LLM_MODELS])
        await message.answer(
            f"Сейчас выбрана модель {llm_model}" + 
            "\n\nНажми на команду выбора одной из доступных моделей, чтобы скопировать её, а затем отправь эту команду мне:\n\n" + models_list +
            "\n\nМожно написать в команде название модели вручную, но если такой модели не существует, то вместо ответа я верну ошибку. В таком случае выбери правильную модель."
        )
        return
    
    llm_model = model
    await message.answer(f"Модель изменена на <b>{llm_model}</b>.")

@dp.message(Command('start'))
async def process_start_command(message: types.Message):
    commands_info = """
Добро пожаловать в ИИ-бот!

Доступные команды:
/start - показать это сообщение
/clear - очистить историю диалога
/model - просмотр и выбор модели ИИ

Просто отправляйте сообщения, и я буду на них отвечать!
"""
    await message.answer(commands_info)


@dp.message(Command('clear'))
async def process_clear_command(message: types.Message):
    user_id = message.from_user.id
    conversation_history[user_id] = []
    await message.reply("История диалога очищена.")


@dp.message(Command('model'))
async def process_model_command(message: types.Message):
    """Handle model selection command"""
    
    # Получаем аргумент команды
    args = message.text.split()[1:]
    model = args[0] if len(args) > 0 else None
    await change_model(message, model)    

@dp.message(Command('sonnet'))
async def process_model_sonnet_command(message: types.Message):
    await change_model(message, "anthropic/claude-3.5-sonnet")

@dp.message(Command('haiku'))
async def process_model_haiku_command(message: types.Message):
    await change_model(message, "anthropic/claude-3-5-haiku")

@dp.message(Command('gpt'))
async def process_model_haiku_command(message: types.Message):
    await change_model(message, "openai/gpt-4o-latest")

@dp.message(F.text)
async def process_message(message: types.Message):
    user_id = message.from_user.id
    if user_id not in bot_users:
        await message.answer("Извините, я вас не знаю. Не пишите мне больше")
        return
    
    user_input = message.text

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_input})
    conversation_history[user_id] = trim_history(conversation_history[user_id])

    chat_history = conversation_history[user_id]

    try:
        response = await openai.ChatCompletion.acreate(
            model=llm_model,
            messages=chat_history

        )
        chat_gpt_response = response["choices"][0]["message"]["content"]
    except Exception as e:
        print(e)
        chat_gpt_response = f"Извините, произошла ошибка: {e}"

    conversation_history[user_id].append({"role": "assistant", "content": chat_gpt_response})
    print(conversation_history)
    length = sum(len(message["content"]) for message in conversation_history[user_id])
    print(length)
    await message.answer(chat_gpt_response)

# Установка команд бота
async def set_commands():
    commands = [
        types.BotCommand(command="start", description="Начать работу с ботом"),
        types.BotCommand(command="clear", description="Сменить тему и начать новый диалог"),
        types.BotCommand(command="sonnet", description="Выбрать модель anthropic/claude-3.5-sonnet"),
        types.BotCommand(command="haiku", description="Выбрать модель anthropic/claude-3-5-haiku"),
        types.BotCommand(command="gpt", description="Выбрать модель openai/gpt-4o-latest"),
        types.BotCommand(command="model", description="Выбрать другую модель ИИ"),
    ]
    await bot.set_my_commands(commands)

# Запуск бота
async def main():
    await set_commands()  # Добавляем эту строку
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
