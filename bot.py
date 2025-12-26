import telebot
from telebot import types
import requests
import time
import logging  # Добавлен импорт модуля logging
from datetime import datetime
from database import Database
from notes_handler import NotesHandler
# ИМПОРТ КЛАВИАТУР
from keyboards import (
    create_main_keyboard,
    create_notes_keyboard,
    create_cancel_keyboard,
    create_echo_keyboard,
    create_hide_keyboard
)
# ========== КОНФИГУРАЦИЯ ==========
import os
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

from config import (
    BOT_TOKEN, bot_logger, OPEN_METEO_URL, MOSCOW_COORDS,
    safe_log_user_info
)
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

# Настройка логирования
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(
    filename=f'{log_dir}/bot.log',
    maxBytes=5*1024*1024,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(console_handler)
logger.addHandler(file_handler)

bot_logger = logging.getLogger('telegram_bot')
bot_logger.setLevel(logging.INFO)

# Словарь для хранения состояний (если понадобится в будущем)
user_states = {}
# Словарь для хранения временных данных
user_temp_data = {}

# Константы для состояний пользователя
STATE_ECHO = "waiting_echo"
# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Инициализация базы данных и обработчика заметок
db = Database()
notes_handler = NotesHandler(bot)
notes_handler.set_database(db)

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ЗАМЕТОК ==========
notes_handler.register_handlers()
notes_handler.register_callbacks()



# Настройка логирования
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(
    filename=f'{log_dir}/bot.log',
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(console_handler)
logger.addHandler(file_handler)

bot_logger = logging.getLogger('telegram_bot')
bot_logger.setLevel(logging.INFO)

# Конфигурация API
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MOSCOW_COORDS = {"latitude": 55.7558, "longitude": 37.6173}


def safe_log_user_info(user_id, username=None, action=None, message_preview=None):
    """Безопасное логирование информации о пользователе"""
    log_data = {
        'user_id': user_id,
        'action': action,
        'message_preview': message_preview[:100] if message_preview else None
    }

    if username and not any(keyword in username.lower() for keyword in ['ivan', 'maria', 'alex']):
        log_data['username'] = username

    return str(log_data)




def get_weather_moscow():

    """Получение текущей погоды в Москве через Open-Meteo API"""
    try:
        params = {
            "latitude": MOSCOW_COORDS["latitude"],
            "longitude": MOSCOW_COORDS["longitude"],
            "current": ["temperature_2m", "weather_code", "wind_speed_10m", "relative_humidity_2m"],
            "timezone": "Europe/Moscow"
        }

        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        temperature = current.get("temperature_2m")
        wind_speed = current.get("wind_speed_10m")
        weather_code = current.get("weather_code")
        humidity = current.get("relative_humidity_2m")

        # Простая интерпретация кодов погоды
        weather_descriptions = {
            0: "ясно ☀️",
            1: "в основном ясно 🌤",
            2: "переменная облачность ⛅",
            3: "пасмурно ☁️",
            45: "туман 🌫",
            48: "туман с инеем 🌫",
            51: "легкая морось 🌧",
            53: "умеренная морось 🌧",
            55: "сильная морось 🌧",
            61: "небольшой дождь 🌦",
            63: "умеренный дождь 🌧",
            65: "сильный дождь 🌧",
            80: "ливни 🌧",
            95: "гроза ⛈"
        }

        weather_desc = weather_descriptions.get(weather_code, "неизвестно")

        if temperature is not None:
            weather_text = (
                f"🌤 Погода в Москве сейчас:\n"
                f"• Температура: {temperature}°C\n"
                f"• Состояние: {weather_desc}\n"
                f"• Влажность: {humidity}%\n"
                f"• Ветер: {wind_speed} км/ч"
            )
            bot_logger.info(f"Получены данные погоды: {temperature}°C, {weather_desc}")
            return weather_text
        else:
            return "Не удалось получить данные о погоде. Попробуйте позже."

    except requests.exceptions.RequestException as e:
        bot_logger.error(f"Ошибка при запросе погоды: {str(e)[:100]}...")
        return "Ошибка при получении данных о погоде. Сервис временно недоступен."
    except Exception as e:
        bot_logger.error(f"Неожиданная ошибка в get_weather_moscow: {str(e)[:100]}...")
        return "Произошла непредвиденная ошибка."


@bot.message_handler(commands=['weather'])
def handle_weather(message):
    """Обработка команды /weather - показывает погоду в Москве"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'weather',
        message.text
    )
    bot_logger.info(f"WEATHER: {user_info}")

    # Получаем погоду в Москве
    weather_info = get_weather_moscow()

    # Отправляем пользователю
    bot.send_message(
        message.chat.id,
        weather_info
    )



def create_main_keyboard():
    """Создание клавиатуры с reply-кнопками"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        types.KeyboardButton("❓ О боте"),
        types.KeyboardButton("☀️ Погода Москва"),
        types.KeyboardButton("🤝 Помощь"),
        types.KeyboardButton("📝 Заметки"),
        types.KeyboardButton("🪄 Эхо команда"),
        types.KeyboardButton("⬇️ Скрыть клавиатуру")
    ]

    keyboard.add(*buttons)
    return keyboard


def create_notes_keyboard():
    """Создание клавиатуры для работы с заметками"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        types.KeyboardButton("📝 Новая заметка"),
        types.KeyboardButton("📋 Список заметок"),
        types.KeyboardButton("🔍 Поиск заметок"),
        types.KeyboardButton("📊 Статистика"),
        types.KeyboardButton("📁 Экспорт заметок"),
        types.KeyboardButton("🔙 Главное меню")
    ]

    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(func=lambda message: message.text == "❌ Отмена")
def create_cancel_keyboard(message):
    """Обработка кнопки 'Отмена'"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("❌ Отмена"))

    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'cancel',
        message.text
    )
    bot_logger.info(f"CANCEL: {user_info}")

    #hide_markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,"❌ Операция отменена, возвращаю вас в меню заметок...")
    handle_notes_main(message)




def create_hide_keyboard():
    """Создание клавиатуры только с кнопкой 'Скрыть клавиатуру'"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Скрыть клавиатуру"))
    return keyboard


def create_echo_options_keyboard():
    """Создание клавиатуры с опциями для команды echo"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        types.KeyboardButton("Пример текста"),
        types.KeyboardButton("Отменить эхо"),
        types.KeyboardButton("Показать клавиатуру"),
        types.KeyboardButton("Скрыть клавиатуру")
    ]

    keyboard.add(*buttons)
    return keyboard


def create_inline_confirmation_keyboard(message_id=None):
    """Создание inline-клавиатуры для подтверждения"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    # Добавляем callback_data с message_id если он передан
    if message_id:
        confirm_btn = types.InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm_echo:{message_id}"
        )
        cancel_btn = types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=f"cancel_echo:{message_id}"
        )
    else:
        confirm_btn = types.InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data="confirm_general"
        )
        cancel_btn = types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_general"
        )

    edit_btn = types.InlineKeyboardButton(
        text="✏️ Изменить текст",
        callback_data="edit_echo"
    )
    show_btn = types.InlineKeyboardButton(
        text="👁 Показать предпросмотр",
        callback_data="preview_echo"
    )

    keyboard.add(confirm_btn, cancel_btn, edit_btn, show_btn)
    return keyboard


def create_inline_echo_options_keyboard():
    """Создание inline-клавиатуры с опциями для эхо"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    buttons = [
        types.InlineKeyboardButton("🔤 Без изменений", callback_data="echo_as_is"),
        types.InlineKeyboardButton("🔠 В ВЕРХНЕМ РЕГИСТРЕ", callback_data="echo_upper"),
        types.InlineKeyboardButton("🔡 в нижнем регистре", callback_data="echo_lower"),
        types.InlineKeyboardButton("✨ С заглавной буквы", callback_data="echo_capitalize"),
        types.InlineKeyboardButton("🔃 В обратном порядке", callback_data="echo_reverse"),
        types.InlineKeyboardButton("🚫 Отмена", callback_data="echo_cancel")
    ]

    keyboard.add(*buttons)
    return keyboard


def create_inline_actions_keyboard():
    """Создание inline-клавиатуры с действиями"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    buttons = [
        types.InlineKeyboardButton("📊 Статистика", callback_data="action_stats"),
        types.InlineKeyboardButton("🔄 Повторить", callback_data="action_repeat"),
        types.InlineKeyboardButton("✂️ Обрезать", callback_data="action_trim"),
        types.InlineKeyboardButton("🔢 Посчитать слова", callback_data="action_count"),
        types.InlineKeyboardButton("🔍 Найти повторы", callback_data="action_find_duplicates"),
        types.InlineKeyboardButton("🎲 Случайный вариант", callback_data="action_random")
    ]

    keyboard.add(*buttons)
    return keyboard


def handle_notes_main(message):
    """Обработка кнопки 'Заметки'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'button_notes',
        message.text
    )
    bot_logger.info(f"BUTTON_NOTES: {user_info}")

    # Показываем меню заметок с правильной клавиатурой
    markup = notes_handler.create_main_notes_keyboard()  # Используем существующий handler

    bot.send_message(
        message.chat.id,
        "📝 *Менеджер заметок*\n\n"
        "Выберите действие:\n"
        "• 📝 Новая заметка - добавить заметку\n"
        "• 📋 Список заметок - просмотреть все\n"
        "• 🔍 Поиск заметок - найти по тексту\n"
        "• 📊 Статистика - количество заметок\n"
        "• 📁 Экспорт заметок - скачать файл\n\n"
        "Или используйте команды:\n"
        "/note_add - добавить заметку\n"
        "/note_list - список заметок\n"
        "/note_find - поиск заметок\n"
        "/note_count - статистика",
        reply_markup=markup

    )
@bot.message_handler(func=lambda message: message.text == "📝 Заметки")
def handle_notes_button(message):
    """Обработка кнопки 'Заметки'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'button_notes',
        message.text
    )
    bot_logger.info(f"BUTTON_NOTES: {user_info}")

    # Показываем меню заметок с правильной клавиатурой
    markup = notes_handler.create_main_notes_keyboard()  # Используем существующий handler

    bot.send_message(
        message.chat.id,
        "📝 *Менеджер заметок*\n\n"
        "Выберите действие:\n"
        "• 📝 Новая заметка - добавить заметку\n"
        "• 📋 Список заметок - просмотреть все\n"
        "• 🔍 Поиск заметок - найти по тексту\n"
        "• 📊 Статистика - количество заметок\n"
        "• 📁 Экспорт заметок - скачать файл\n\n"
        "Или используйте команды:\n"
        "/note_add - добавить заметку\n"
        "/note_list - список заметок\n"
        "/note_find - поиск заметок\n"
        "/note_count - статистика",
        reply_markup=markup

    )


# После обработчика handle_notes_button добавьте:

@bot.message_handler(func=lambda message: message.text == "📝 Новая заметка")
def handle_new_note_button(message):
    """Обработка кнопки 'Новая заметка'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'new_note_button',
        message.text
    )
    bot_logger.info(f"NEW_NOTE_BUTTON: {user_info}")
    notes_handler.handle_note_add1(message)

    # bot.send_message(
    #     message.chat.id,
    #     "📝 Создание новой заметки\n\n"
    #     "Введите заголовок заметки:",
    #     reply_markup=notes_handler.create_cancel_keyboard()#create_cancel_keyboard(message)
    # )


@bot.message_handler(func=lambda message: message.text == "📋 Список заметок")
def handle_list_notes_button(message):
    """Обработка кнопки 'Список заметок'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'list_notes_button',
        message.text
    )
    bot_logger.info(f"LIST_NOTES_BUTTON: {user_info}")

    # Используем обработчик из notes_handler
    notes_handler.handle_note_list1(message)


@bot.message_handler(func=lambda message: message.text == "🔍 Поиск заметок")
def handle_search_notes_button(message):
    """Обработка кнопки 'Поиск заметок'"""
    # user_info = safe_log_user_info(
    #     message.from_user.id,
    #     message.from_user.username,
    #     'search_notes_button',
    #     message.text
    # )
    # bot_logger.info(f"SEARCH_NOTES_BUTTON: {user_info}")
    notes_handler.handle_note_find1(message)
    #
    # bot.send_message(
    #     message.chat.id,
    #     "🔍 Поиск заметок\n\nВведите текст для поиска:",
    #     reply_markup=notes_handler.create_cancel_keyboard()
    # )


@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def handle_stats_button(message):
    """Обработка кнопки 'Статистика'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'stats_button',
        message.text
    )
    bot_logger.info(f"STATS_BUTTON: {user_info}")

    notes_handler.handle_note_count1(message)


@bot.message_handler(func=lambda message: message.text == "📁 Экспорт заметок")
def handle_export_button(message):
    """Обработка кнопки 'Экспорт заметок'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'export_button',
        message.text
    )
    bot_logger.info(f"EXPORT_BUTTON: {user_info}")

    notes_handler.handle_note_export1(message)


@bot.message_handler(func=lambda message: message.text == "🔙 Главное меню")
def handle_back_to_main_button(message):
    """Обработка кнопки 'Главное меню'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'back_to_main_button',
        message.text
    )
    bot_logger.info(f"BACK_TO_MAIN_BUTTON: {user_info}")

    bot.send_message(
        message.chat.id,
        "🔙 Возвращаюсь в главное меню...",
        reply_markup=create_main_keyboard()
    )
# Обработчики команд
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработка команды /start"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'start',
        message.text
    )
    bot_logger.info(f"START: {user_info}")

    welcome_text = (
        "👋 *Привет! Я умный бот с заметками.*\n\n"
        "*Основные возможности:*\n"
        "• 📝 Система заметок с поиском и категориями\n"
        "• 🌤 Погода в Москве в реальном времени\n"
        "• 🔢 Математические вычисления\n"
        "• 🔄 Эхо-команда с разными вариантами\n"
        "• 📊 Логирование всех действий\n\n"
        "*Команды заметок:*\n"
        "/note_add - добавить заметку\n"
        "/note_list - список заметок\n"
        "/note_find - поиск по заметкам\n"
        "/note_count - статистика\n\n"
        "Для получения полного списка команд и возможностей\n"
        "Воспользуйтесь командой /help\n"
        "или используйте Используйте кнопки ниже ⬇️"
    )

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup = create_main_keyboard()
    )


@bot.message_handler(commands=['echo'])
def handle_echo(message):
    """Обработка команды /echo"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'echo',
        message.text
    )
    bot_logger.info(f"ECHO_COMMAND: {user_info}")

    # Проверяем, есть ли текст после команды
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        # Если текст передан сразу, обрабатываем его
        echo_text = args[1]
        process_echo_text(message, echo_text)
    else:
        # Если текст не передан, запрашиваем его
        user_states[message.from_user.id] = STATE_ECHO

        echo_instructions = (
            "📝 Команда Эхо\n\n"
            "Отправьте мне текст, и я его повторю.\n"
            "Вы можете:\n"
            "• Отправить любой текст\n"
            "• Использовать кнопки ниже для примеров\n"
            "• Нажать 'Отменить эхо' для выхода\n\n"
            "Что вы хотите, чтобы я повторил?"
        )

        # Отправляем сообщение с inline-кнопками
        msg = bot.send_message(
            message.chat.id,
            echo_instructions
        )

        # Сохраняем ID сообщения для возможного редактирования
        user_temp_data[message.from_user.id] = {
            'echo_message_id': msg.message_id
        }


@bot.message_handler(func=lambda message: message.text == "🪄 Эхо команда")
def handle_echo_button(message):
    """Обработка кнопки 'Эхо команда'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'button_echo',
        message.text
    )
    bot_logger.info(f"BUTTON_ECHO: {user_info}")
    handle_echo(message)


@bot.message_handler(func=lambda message: message.text == "⬇️ Скрыть клавиатуру")
def handle_hide_keyboard(message):
    """Обработка кнопки 'Скрыть клавиатуру'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'hide_keyboard',
        message.text
    )
    bot_logger.info(f"HIDE_KEYBOARD: {user_info}")

    hide_markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "⌨️ Клавиатура скрыта. Используйте /start чтобы вернуть её.",
        reply_markup=hide_markup)


@bot.message_handler(func=lambda message: message.text == "Показать клавиатуру")
def handle_show_keyboard(message):
    """Обработка кнопки 'Показать клавиатуру'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'show_keyboard',
        message.text
    )
    bot_logger.info(f"SHOW_KEYBOARD: {user_info}")

    hide_markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "⌨️ Возвращаю основную клавиатуру..."
    )


@bot.message_handler(func=lambda message: message.text == "Пример текста")
def handle_example_text(message):
    """Обработка кнопки 'Пример текста'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'example_text',
        message.text
    )
    bot_logger.info(f"EXAMPLE_TEXT: {user_info}")

    example = "Это пример текста для команды эхо! Вы можете изменить его."

    # Отправляем пример с inline-кнопками
    msg = bot.send_message(
        message.chat.id,
        f"📋 Пример:\n`{example}`\n\nХотите использовать этот текст?"
    )

    # Сохраняем пример для этого пользователя
    user_temp_data[message.from_user.id] = {
        'echo_text': example,
        'example_message_id': msg.message_id
    }


@bot.message_handler(func=lambda message: message.text == "Отменить эхо")
def handle_cancel_echo(message):
    """Обработка кнопки 'Отменить эхо'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'cancel_echo',
        message.text
    )
    bot_logger.info(f"CANCEL_ECHO: {user_info}")

    # Удаляем состояние пользователя
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]

    if message.from_user.id in user_temp_data:
        del user_temp_data[message.from_user.id]

    bot.send_message(
        message.chat.id,
        "❌ Эхо отменено. Возвращаю основное меню..."
    )


def process_echo_text(message, text):
    """Обработка текста для эхо-команды"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'process_echo',
        text[:50] + "..." if len(text) > 50 else text
    )
    bot_logger.info(f"PROCESS_ECHO: {user_info}")

    # Сбрасываем состояние пользователя
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]

    # Отправляем текст с inline-кнопками для выбора действия
    msg = bot.send_message(
        message.chat.id,
        f"📝 Ваш текст ({len(text)} символов):\n\n`{text[:100]}{'...' if len(text) > 100 else ''}`\n\nВыберите действие:"
    )

    # Сохраняем текст и ID сообщения
    user_temp_data[message.from_user.id] = {
        'echo_text': text,
        'options_message_id': msg.message_id
    }


# Обработчик текстовых сообщений для состояния ECHO
@bot.message_handler(func=lambda message:
message.from_user.id in user_states and
user_states[message.from_user.id] == STATE_ECHO)
def handle_echo_state(message):
    """Обработка текста в состоянии ожидания эхо"""
    process_echo_text(message, message.text)


@bot.message_handler(commands=['test_inline'])
def test_inline_buttons(message):
    """Тестовая команда для проверки inline-кнопок"""
    bot_logger.info(f"TEST_INLINE: user_id={message.from_user.id}")

    # Создаем простую inline-клавиатуру
    markup = types.InlineKeyboardMarkup()

    # Добавляем кнопки разными способами
    markup.add(
        types.InlineKeyboardButton("Кнопка 1", callback_data="test_1"),
        types.InlineKeyboardButton("Кнопка 2", callback_data="test_2")
    )

    markup.row(
        types.InlineKeyboardButton("Кнопка 3", callback_data="test_3")
    )

    markup.add(
        types.InlineKeyboardButton("Кнопка 4", callback_data="test_4"),
        types.InlineKeyboardButton("Кнопка 5", callback_data="test_5")
    )

    # Отправляем сообщение с кнопками
    bot.send_message(
        message.chat.id,
        "🔄 *Тест inline-кнопок*\n\n"
        "Нажмите на любую кнопку ниже. "
        "Должно появиться всплывающее уведомление.",
        parse_mode='Markdown',
        reply_markup=markup
    )
# Обработчик inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    """Обработка нажатий inline-кнопок"""
    user_info = safe_log_user_info(
        call.from_user.id,
        call.from_user.username,
        'inline_button',
        call.data
    )
    bot_logger.info(f"INLINE_BUTTON: {user_info}, data={call.data}")

    # Разделяем callback_data на части
    callback_parts = call.data.split(':')
    callback_type = callback_parts[0]

    if callback_type == "confirm_echo":
        # Подтверждение эхо
        if len(callback_parts) > 1:
            message_id = callback_parts[1]

            # Получаем сохраненный текст
            user_data = user_temp_data.get(call.from_user.id, {})
            echo_text = user_data.get('echo_text', '')

            if echo_text:
                # Отправляем подтвержденный текст
                bot.send_message(
                    call.message.chat.id,
                    f"✅ Подтверждено!\n\n{echo_text}"
                )

                # Редактируем исходное сообщение
                bot.edit_message_text(
                    "✅ Эхо подтверждено и отправлено!",
                    call.message.chat.id,
                    call.message.message_id
                )

                # Удаляем временные данные
                if call.from_user.id in user_temp_data:
                    del user_temp_data[call.from_user.id]

    elif callback_type == "cancel_echo":
        # Отмена эхо
        if len(callback_parts) > 1:
            message_id = callback_parts[1]

            bot.edit_message_text(
                "❌ Эхо отменено.",
                call.message.chat.id,
                call.message.message_id
            )

            # Удаляем временные данные
            if call.from_user.id in user_temp_data:
                del user_temp_data[call.from_user.id]

    elif callback_type == "confirm_general":
        # Общее подтверждение
        bot.answer_callback_query(call.id, "Действие подтверждено!")

        # Получаем текст из сообщения
        original_text = call.message.text
        lines = original_text.split('\n')
        if lines and '`' in lines[0]:
            # Извлекаем текст из markdown
            text_line = lines[0].strip('`')
            bot.send_message(
                call.message.chat.id,
                f"✅ {text_line}"
            )

    elif callback_type == "cancel_general":
        # Общая отмена
        bot.answer_callback_query(call.id, "Действие отменено!")
        bot.edit_message_text(
            "❌ Действие отменено пользователем.",
            call.message.chat.id,
            call.message.message_id
        )

    elif callback_type == "edit_echo":
        # Редактирование текста
        bot.answer_callback_query(call.id, "Введите новый текст...")

        # Устанавливаем состояние редактирования
        user_states[call.from_user.id] = STATE_ECHO

        bot.send_message(
            call.message.chat.id,
            "✏️ Введите новый текст для эхо:"
        )

    elif callback_type == "preview_echo":
        # Показать предпросмотр
        user_data = user_temp_data.get(call.from_user.id, {})
        echo_text = user_data.get('echo_text', '')

        if echo_text:
            preview = echo_text[:200] + ("..." if len(echo_text) > 200 else "")
            bot.answer_callback_query(
                call.id,
                f"Предпросмотр: {preview}",
                show_alert=True
            )
        else:
            bot.answer_callback_query(call.id, "Текст не найден")

    elif callback_type.startswith("echo_"):
        # Обработка вариантов эхо
        echo_variant = callback_type.replace("echo_", "")
        user_data = user_temp_data.get(call.from_user.id, {})
        original_text = user_data.get('echo_text', '')

        if original_text:
            # Применяем преобразование
            if echo_variant == "as_is":
                result = original_text
            elif echo_variant == "upper":
                result = original_text.upper()
            elif echo_variant == "lower":
                result = original_text.lower()
            elif echo_variant == "capitalize":
                result = original_text.capitalize()
            elif echo_variant == "reverse":
                result = original_text[::-1]
            elif echo_variant == "cancel":
                bot.edit_message_text(
                    "❌ Эхо отменено.",
                    call.message.chat.id,
                    call.message.message_id
                )
                return

            # Отправляем результат
            bot.send_message(
                call.message.chat.id,
                f"🔤 Результат ({echo_variant}):\n\n{result}"
            )

            # Редактируем исходное сообщение
            bot.edit_message_text(
                f"✅ Эхо выполнено! Вариант: {echo_variant}",
                call.message.chat.id,
                call.message.message_id
            )

            # Удаляем временные данные
            if call.from_user.id in user_temp_data:
                del user_temp_data[call.from_user.id]

        bot.answer_callback_query(call.id)

    elif callback_type.startswith("action_"):
        # Обработка действий
        action = callback_type.replace("action_", "")
        user_data = user_temp_data.get(call.from_user.id, {})
        original_text = user_data.get('echo_text', '')

        if original_text:
            if action == "stats":
                # Статистика
                stats_text = (
                    f"📊 Статистика текста:\n"
                    f"• Символов: {len(original_text)}\n"
                    f"• Слов: {len(original_text.split())}\n"
                    f"• Строк: {len(original_text.splitlines())}\n"
                    f"• Уникальных символов: {len(set(original_text))}"
                )
                bot.send_message(call.message.chat.id, stats_text)

            elif action == "repeat":
                # Повторить
                bot.send_message(call.message.chat.id, f"🔄 {original_text}")

            elif action == "trim":
                # Обрезать пробелы
                trimmed = original_text.strip()
                bot.send_message(call.message.chat.id, f"✂️ Обрезано:\n{trimmed}")

            elif action == "count":
                # Посчитать слова
                words = original_text.split()
                word_count = len(words)
                unique_words = len(set(words))
                bot.send_message(
                    call.message.chat.id,
                    f"🔢 Слов: {word_count}\nУникальных слов: {unique_words}"
                )

            elif action == "find_duplicates":
                # Найти повторяющиеся слова
                words = original_text.lower().split()
                word_counts = {}
                for word in words:
                    if len(word) > 2:  # Игнорируем короткие слова
                        word_counts[word] = word_counts.get(word, 0) + 1

                duplicates = {k: v for k, v in word_counts.items() if v > 1}
                if duplicates:
                    dup_text = "\n".join([f"• {k}: {v} раз" for k, v in duplicates.items()][:5])
                    bot.send_message(call.message.chat.id, f"🔍 Повторяющиеся слова:\n{dup_text}")
                else:
                    bot.send_message(call.message.chat.id, "✅ Повторяющихся слов не найдено")

            elif action == "random":
                # Случайный вариант
                import random
                words = original_text.split()
                if len(words) > 1:
                    random.shuffle(words)
                    result = " ".join(words)
                    bot.send_message(call.message.chat.id, f"🎲 Перемешано:\n{result}")
                else:
                    bot.send_message(call.message.chat.id, "❌ Недостаточно слов для перемешивания")

        bot.answer_callback_query(call.id)

@bot.message_handler(commands=['ping'])
def handle_ping(message):
    """Обработка команды /ping - проверка работоспособности"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'ping',
        message.text
    )
    bot_logger.info(f"PING: {user_info}")

    # Измеряем время ответа
    start_time = time.time()

    # Проверяем доступность API погоды
    api_status = "доступно ✅" if test_api_connection() else "недоступно ❌"

    response_time = round((time.time() - start_time) * 1000, 2)

    ping_text = (
        "🏓 Pong!\n\n"
        f"• Время ответа: {response_time} мс\n"
        f"• API погоды: {api_status}\n"
        f"• Бот запущен: {get_bot_uptime()}\n"
        f"• Текущее время: {datetime.now().strftime('%H:%M:%S')}"
    )

    bot.send_message(message.chat.id, ping_text)



@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обработка команды /help"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'help',
        message.text
    )
    bot_logger.info(f"HELP: {user_info}")

    help_text = (
        "📖 Справка по использованию бота:\n\n"
        "Команды:\n"
        "• /start - начало работы с ботом\n"
        "• /help - эта справка\n"
        "• /about - информация о боте\n"
        "• /ping - проверка работоспособности\n"
        "• /weather - Актуальная погода\n"
        "• /echo - повторяет ваш текст с разными вариантами\n"
        "• /sum X Y Z - вычисляет сумму чисел\n"
        "   Пример: /sum 5 10 15\n\n"
        "*Команды заметок:*\n"
        "• /note_add - добавить заметку\n"
        "• /note_list - список всех заметок\n"
        "• /note_find - найти заметку по словам\n"
        "• /note_edit - редактор заметок\n"
        "• /note_del - удалить заметку\n"
        "• /note_count - сколько всего заметок\n"
        "• /note_export - скачать файл с заметками\n\n"
        "Кнопки:\n"
        "• О боте - информация о боте\n"
        "• Погода Москва - текущая погода\n"
        "• Помощь - эта справка\n"
        "• Эхо команда - запуск команды эхо\n"  # Добавлено
        "• Скрыть клавиатуру - скрыть reply-клавиатуру"
    )

    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['about'])
def handle_about(message):
    """Обработка команды /about"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'about',
        message.text
    )
    bot_logger.info(f"ABOUT: {user_info}")

    about_text = (
        "🤖 Информация о боте\n\n"
        "Это демонстрационный бот, созданный с использованием:\n"
        "• pyTelegramBotAPI (TeleBot)\n"
        "• Open-Meteo API для данных о погоде\n"
        "• Long Polling для получения обновлений\n\n"
        "Бот предназначен для обучения и демонстрации возможностей.\n\n"
        "📊 Логирование: все действия записываются в файл logs/bot.log"
    )

    bot.send_message(message.chat.id, about_text)


@bot.message_handler(commands=['sum'])
def handle_sum(message):
    """Обработка команды /sum - вычисление суммы чисел"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'sum',
        message.text
    )
    bot_logger.info(f"SUM_REQUEST: {user_info}")

    try:
        # Извлекаем числа из текста команды
        args = message.text.split()[1:]

        if not args:
            bot.send_message(
                message.chat.id,
                "❌ Пожалуйста, укажите числа для сложения.\n"
                "Пример: /sum 5 10 15"
            )
            bot_logger.warning(f"SUM_EMPTY_ARGS: {user_info}")
            return

        # Преобразуем аргументы в целые числа
        numbers = [int(arg) for arg in args]
        total = sum(numbers)

        # Формируем красивый ответ
        numbers_str = " + ".join(map(str, numbers))
        result_text = f"🔢 Результат: {numbers_str} = {total}"

        bot_logger.info(f"SUM_CALCULATED: {user_info}, numbers={numbers}, total={total}")
        bot.send_message(message.chat.id, result_text)

    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: пожалуйста, вводите только целые числа.\n"
            "Пример: /sum 5 10 15"
        )
        bot_logger.warning(f"SUM_VALUE_ERROR: {user_info}")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при вычислении суммы.")
        bot_logger.error(f"SUM_EXCEPTION: {user_info}, error={str(e)[:100]}...")


# Обработчики текстовых сообщений (reply-кнопки)
@bot.message_handler(func=lambda message: message.text == "❓ О боте")
def handle_about_button(message):
    """Обработка кнопки 'О боте'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'button_about',
        message.text
    )
    bot_logger.info(f"BUTTON_ABOUT: {user_info}")
    handle_about(message)


@bot.message_handler(func=lambda message: message.text == "☀️ Погода Москва")
def handle_weather_button(message):
    """Обработка кнопки 'Погода Москва'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'button_weather',
        message.text
    )
    bot_logger.info(f"BUTTON_WEATHER: {user_info}")

    bot.send_message(message.chat.id, "⏳ Загружаю данные о погоде...")
    weather_info = get_weather_moscow()
    bot.send_message(message.chat.id, weather_info)


@bot.message_handler(func=lambda message: message.text == "🤝 Помощь")
def handle_help_button(message):
    """Обработка кнопки 'Помощь'"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'button_help',
        message.text
    )
    bot_logger.info(f"BUTTON_HELP: {user_info}")
    handle_help(message)

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ЗАМЕТОК ==========
# Регистрируем команды заметок


# @bot.message_handler(commands=['note_add'])
# def handle_note_add_command(message):
#     notes_handler.register_handlers()

@bot.message_handler(commands=['note_list'])
def handle_note_list_command(message):
    notes_handler.handle_note_list(message)

@bot.message_handler(commands=['note_find'])
def handle_note_find_command(message):
    notes_handler.handle_note_find(message)

@bot.message_handler(commands=['note_count'])
def handle_note_count_command(message):
    notes_handler.handle_note_count(message)

@bot.message_handler(commands=['note_export'])
def handle_note_export_command(message):
    notes_handler.handle_note_export(message)

# Регистрируем reply-кнопки заметок
# @bot.message_handler(func=lambda message: message.text == "📝 Новая заметка")
# def handle_new_note_button(message):
#     notes_handler.handle_note_add(message)
#
# @bot.message_handler(func=lambda message: message.text == "❌ Отмена")
# def create_cancel_keyboard():
#     notes_handler.create_main_notes_keyboard()
#
# @bot.message_handler(func=lambda message: message.text == "📋 Список заметок")
# def handle_list_notes_button(message):
#     notes_handler.handle_note_list(message)
#
# @bot.message_handler(func=lambda message: message.text == "🔍 Поиск заметок")
# def handle_search_notes_button(message):
#     notes_handler.handle_note_find(message)
#
# @bot.message_handler(func=lambda message: message.text == "📊 Статистика")
# def handle_stats_button(message):
#     notes_handler.handle_note_count(message)
#
# @bot.message_handler(func=lambda message: message.text == "📁 Экспорт заметок")
# def handle_export_button(message):
#     notes_handler.handle_note_export(message)
#
# @bot.message_handler(func=lambda message: message.text == "🔙 Главное меню")
# def handle_back_to_main_button(message):
#     notes_handler.handle_back_to_main(message)
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Обработка всех остальных сообщений"""
    user_info = safe_log_user_info(
        message.from_user.id,
        message.from_user.username,
        'unknown_command',
        message.text
    )
    bot_logger.info(f"UNKNOWN_COMMAND: {user_info}")

    response = (
        "Я не понимаю эту команду. 😕\n\n"
        "Используйте команды из меню или кнопки ниже.\n"
        "Для справки нажмите /help"
    )
    bot.send_message(
        message.chat.id,
        response
    )


# Вспомогательные функции
def test_api_connection():
    """Проверка доступности Open-Meteo API"""
    try:
        params = {
            "latitude": MOSCOW_COORDS["latitude"],
            "longitude": MOSCOW_COORDS["longitude"],
            "current": "temperature_2m"
        }
        response = requests.get(OPEN_METEO_URL, params=params, timeout=5)
        return response.status_code == 200
    except:
        return False


# Переменная для отслеживания времени запуска
_start_time = datetime.now()


def get_bot_uptime():
    """Получение времени работы бота"""
    uptime = datetime.now() - _start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м {seconds}с"
    else:
        return f"{minutes}м {seconds}с"


def main():
    """Основная функция запуска бота"""
    bot_logger.info("=" * 50)
    bot_logger.info("Запуск телеграм-бота...")


    try:
        # Получаем информацию о боте для логирования
        bot_info = bot.get_me()
        bot_logger.info(f"Бот @{bot_info.username} запущен успешно")
        bot_logger.info(f"Имя бота: {bot_info.first_name}")
        bot_logger.info(f"ID бота: {bot_info.id}")
        bot_logger.info(f"Логирование: файл logs/bot.log")
        bot_logger.info(f"База данных: notes.db")


        # Запуск long polling
        bot_logger.info("Запуск Long Polling...")
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60,
            logger_level=logging.INFO  # Теперь logging доступен
        )

    except telebot.apihelper.ApiException as e:
        bot_logger.error(f"Ошибка API Telegram: {str(e)[:200]}")
    except KeyboardInterrupt:
        bot_logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        bot_logger.error(f"Неожиданная ошибка при запуске: {str(e)[:200]}")
    finally:
        bot_logger.info("Бот остановлен")
        bot_logger.info("=" * 50)


if __name__ == "__main__":
    main()