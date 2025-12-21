import telebot
from telebot import types
import requests
import time
import logging
from datetime import datetime
from config import (
    BOT_TOKEN, bot_logger, OPEN_METEO_URL, MOSCOW_COORDS,
    safe_log_user_info
)

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Словарь для хранения состояний (если понадобится в будущем)
user_states = {}


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


def create_main_keyboard():
    """Создание клавиатуры с reply-кнопками"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        types.KeyboardButton("О боте"),
        types.KeyboardButton("Погода Москва"),
        types.KeyboardButton("Помощь")
    ]

    keyboard.add(*buttons)
    return keyboard


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
        "👋 Привет! Я демонстрационный бот.\n\n"
        "Доступные команды:\n"
        "• /start - начать работу\n"
        "• /help - помощь\n"
        "• /about - информация о боте\n"
        "• /ping - проверка работоспособности\n"
        "• /sum X Y Z - сумма чисел\n\n"
        "Также используйте кнопки ниже ⬇️"
    )

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=create_main_keyboard()
    )


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
        "• /sum X Y Z - вычисляет сумму чисел\n"
        "   Пример: /sum 5 10 15\n\n"
        "Кнопки:\n"
        "• О боте - информация о боте\n"
        "• Погода Москва - текущая погода\n"
        "• Помощь - эта справка"
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
@bot.message_handler(func=lambda message: message.text == "О боте")
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


@bot.message_handler(func=lambda message: message.text == "Погода Москва")
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


@bot.message_handler(func=lambda message: message.text == "Помощь")
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
        response,
        reply_markup=create_main_keyboard()
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

        # Запуск long polling
        bot_logger.info("Запуск Long Polling...")
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60,
            logger_level=logging.INFO
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