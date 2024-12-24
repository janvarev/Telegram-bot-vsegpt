# Телеграм-бот для доступа к разным LLM через vsegpt.ru

Просто напишите текст, и бот вернёт ответ от текущей выбранной LLM.
Поддерживается диалог в рамках контекста 4096 знаков. При превышении из истории удаляются старые элементы.

Команды:

- `/start` - Начать работу с ботом
- `/clear` - Сменить тему и начать новый диалог
- `/sonnet` - Выбрать модель anthropic/claude-3.5-sonnet
- `/haiku` - Выбрать модель anthropic/claude-3-5-haiku
- `/gpt` - Выбрать модель openai/gpt-4o-latest
- `/gemini` - Выбрать модель google/gemini-pro-1.5
- `/model` - Выбрать другую модель ИИ (подсказки указаны в `models.py`)

## Установка зависимостей

1. Установите Python 3.9+
2. установите требуемые модули: `pip install -r requirements.txt`

## Конфигурация

Задайте в config.py:

1. `API_TELEGRAM_TOKEN` - токен вашего бота от @botfather
2. `API_VSEGPT_TOKEN` - ваш ключ API vsegpt.ru
3. `ALLOWED_USERS` - Telegram id чатов, из которых разрешён доступ к этому боту, разделённые двоеточием
4. `VSEGPT_API_BASE` - адрес эндпоинта REST API, совместимого с OpenAI

## Запуск бота

- Windows: `python main.py`
- Linux/iOS: `python3 main.py`
