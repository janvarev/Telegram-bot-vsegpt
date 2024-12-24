import logging
import asyncio
import time
from typing import Dict, List

import openai
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.text_decorations import html_decoration
# from aiogram.utils.markdown import code

from models import LLM_MODELS, SYSTEM_PROMPT
# Включите логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%m-%d %H:%M:%S'
)

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
            logging.error(f'Exception: {e}')
            await bot.set_message_reaction(chat_id=message.from_user.id, message_id=message.message_id, reaction=[{'type':'emoji', 'emoji':'🤷‍♂'}])
            await answer_message(message, f'🤷‍♂️ Ошибка: {e}')
            return

dp.update.middleware(CommonMiddleware())  # Регистрация middleware

# Словарь для хранения истории разговоров
conversation_history = {}
# Словарь для хранения моделей пользователей
user_models = {}

# Функция для обрезки истории разговора
def trim_history(history: list, max_length=4096):
    current_length = sum(len(message["content"]) for message in history)
    while history and current_length > max_length:
        removed_message = history.pop(0)
        current_length -= len(removed_message["content"])
    return history

async def change_model(message: types.Message, model = None) -> None:
    user_id = message.from_user.id
    current_model = user_models.get(user_id, LLM_MODELS[0])
    
    if not model:
        # Если аргументов нет, показываем список доступных моделей
        models_list = "\n".join([f"<code>/model {model}</code>" for model in LLM_MODELS])
        await answer_message(message, 
            f"Сейчас выбрана модель {current_model}" + 
            "\n\nНажми на команду выбора одной из доступных моделей, чтобы скопировать её, а затем отправь эту команду мне:\n\n" + models_list +
            "\n\nМожно написать в команде название модели вручную, но если такой модели не существует, то вместо ответа я верну ошибку. В таком случае выбери правильную модель."
        )
        return
    
    user_models[user_id] = model
    await answer_message(message, f"Модель изменена на <b>{model}</b>.")

@dp.message(Command('start'))
async def process_start_command(message: types.Message):
    commands_info = """
Добро пожаловать в ИИ-бот!

Доступные команды:
/start - показать это сообщение
/clear - очистить историю диалога
/model - просмотр и выбор модели ИИ
... больше команд в меню

Просто отправляйте свои вопросы или мысли, и я буду на них отвечать!
"""
    await answer_message(message, commands_info)


@dp.message(Command('clear'))
async def process_clear_command(message: types.Message):
    user_id = message.from_user.id
    conversation_history[user_id] = []
    await answer_message(message, "История диалога очищена.")


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

@dp.message(Command('gemini'))
async def process_model_gemini_command(message: types.Message):
    await change_model(message, "google/gemini-pro-1.5")

@dp.message(F.text)
async def process_message(message: types.Message):
    user_id = message.from_user.id
    if user_id not in bot_users:
        await answer_message(message, "Извините, я вас не знаю. Не пишите мне больше")
        return
    
    user_input = message.text
    if message.from_user.username:
        username = "@" + message.from_user.username
    else:
        username = "user"
    logging.info(f"Got text from {username} ({user_id}), len: {len(user_input)}")

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_input})
    conversation_history[user_id] = trim_history(conversation_history[user_id])

    chat_history = conversation_history[user_id]

    try:
        # Используем модель пользователя или модель по умолчанию
        current_model = user_models.get(user_id, LLM_MODELS[0])
        # Добавляем системный промпт к истории сообщений
        full_messages = [SYSTEM_PROMPT] + chat_history
        response = await openai.ChatCompletion.acreate(
            model=current_model,
            messages=full_messages
        )
        if isinstance(response, dict):
            chat_gpt_response = response["choices"][0]["message"]["content"]
        else:
            chat_gpt_response = str(response)
          
        logging.info(f"Got AI answer, len: {len(chat_gpt_response)}")

        # print(f"{chat_gpt_response=}")

        chat_gpt_response = html_decoration.quote(chat_gpt_response)
    except Exception as e:
        logging.error(e)
        chat_gpt_response = f"Извините, произошла ошибка: {e}"

    conversation_history[user_id].append({"role": "assistant", "content": chat_gpt_response})
    # print(conversation_history)
    length = sum(len(message["content"]) for message in conversation_history[user_id])
    # print(length)
    await answer_message(message, chat_gpt_response)

async def answer_message(message: types.Message, answer_text: str):
    # Telegram limit is 4096 characters in a message
    msg_len_limit = 4000
    if len(answer_text) <= msg_len_limit:
        await message.answer(answer_text)
    else:
        chunks = text_to_chunks(answer_text, msg_len_limit)
        for chunk in chunks:
            try:
                await message.answer(chunk)
            except Exception as e:
                await message.answer(f'🤷‍♂️ {e}')
            time.sleep(0.03)


def text_to_chunks(text, max_len):
    """ Accepts a string text and splits it into parts of up to max_len characters. Returns a list of parts"""
    sentences = [piece.strip() + '.' for piece in text.split('.')]
    texts = []
    chunk = ''

    for sentence in sentences:
        if len(sentence) > max_len or len(chunk + ' ' + sentence) > max_len:
            # This sentence does not fit into the current chunk
            if len(chunk) > 0:
                # If there is something in the chunk, save it
                texts.append(chunk.strip(' '))
                chunk = ''
            # Chunk is empty, start filling it
            if len(sentence) > max_len:
                # If the current sentence is too long, put only as much as fits into the chunk
                words = sentence.split(' ')
                for word in words:
                    if len(chunk + ' ' + word) < max_len:
                        # This word fits into the current chunk, add it
                        chunk += ' ' + word
                    else:
                        # This word does not fit into the current chunk
                        texts.append(chunk.strip(' '))
                        chunk = word
            else:
                # Chunk was empty, so just add the sentence to it
                chunk = sentence

        else:
            # This sentence fits into the current chunk, add it
            chunk += ' ' + sentence
    # Save the last chunk, if it is not empty
    if len(chunk) > 0: texts.append(chunk.strip(' '))
    return texts

# Установка команд бота
async def set_commands():
    commands = [
        types.BotCommand(command="clear", description="Сменить тему и начать новый диалог"),
        types.BotCommand(command="sonnet", description="Выбрать модель anthropic/claude-3.5-sonnet"),
        types.BotCommand(command="haiku", description="Выбрать модель anthropic/claude-3-5-haiku"),
        types.BotCommand(command="gpt", description="Выбрать модель openai/gpt-4o-latest"),
        types.BotCommand(command="gemini", description="Выбрать модель google/gemini-pro-1.5"),
        types.BotCommand(command="model", description="Выбрать другую модель ИИ"),
    ]
    await bot.set_my_commands(commands)

# Запуск бота
async def main():
    await set_commands()  # Добавляем эту строку
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
