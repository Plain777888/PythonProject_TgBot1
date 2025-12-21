import telebot
from telebot import types
import requests
import logging
from config import BOT_TOKEN, logger, OPEN_METEO_URL, MOSCOW_COORDS

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения состояний (если понадобится в будущем)
user_states = {}


def get_weather_moscow():
    """Получение текущей погоды в Москве через Open-Meteo API"""
    try:
        params = {
            "latitude": MOSCOW_COORDS["latitude"],
            "longitude": MOSCOW_COORDS["longitude"],
            "current": ["temperature_2m", "weather_code", "wind_speed_10m"],
            "timezone": "Europe/Moscow"
        }

        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        temperature = current.get("temperature_2m")
        wind_speed = current.get("wind_speed_10m")
        weather_code = current.get("weather_code")

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
                f"• Скорость ветра: {wind_speed} км/ч"
            )
            logger.info(f"Получены данные погоды: {temperature}°C, {weather_desc}")
            return weather_text
        else:
            return "Не удалось получить данные о погоде. Попробуйте позже."

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе погоды: {e}")
        return "Ошибка при получении данных о погоде. Сервис временно недоступен."
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
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
    logger.info(f"Пользователь {message.from_user.id} запустил бота")

    welcome_text = (
        "👋 Привет! Я демонстрационный бот.\n\n"
        "Доступные команды:\n"
        "• /start - начать работу\n"
        "• /help - помощь\n"
        "• /about - информация о боте\n"
        "• /sum X Y Z - сумма чисел\n\n"
        "Также используйте кнопки ниже ⬇️"
    )

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=create_main_keyboard()
    )


@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обработка команды /help"""
    logger.info(f"Пользователь {message.from_user.id} запросил помощь")

    help_text = (
        "📖 Справка по использованию бота:\n\n"
        "Команды:\n"
        "• /start - начало работы с ботом\n"
        "• /help - эта справка\n"
        "• /about - информация о боте\n"
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
    logger.info(f"Пользователь {message.from_user.id} запросил информацию о боте")

    about_text = (
        "🤖 Информация о боте\n\n"
        "Это демонстрационный бот, созданный с использованием:\n"
        "• pyTelegramBotAPI (TeleBot)\n"
        "• Open-Meteo API для данных о погоде\n"
        "• Long Polling для получения обновлений\n\n"
        "Бот предназначен для обучения и демонстрации возможностей."
    )

    bot.send_message(message.chat.id, about_text)


@bot.message_handler(commands=['sum'])
def handle_sum(message):
    """Обработка команды /sum - вычисление суммы чисел"""
    logger.info(f"Пользователь {message.from_user.id} использовал команду /sum")

    try:
        # Извлекаем числа из текста команды
        args = message.text.split()[1:]

        if not args:
            bot.send_message(
                message.chat.id,
                "❌ Пожалуйста, укажите числа для сложения.\n"
                "Пример: /sum 5 10 15"
            )
            return

        # Преобразуем аргументы в целые числа
        numbers = [int(arg) for arg in args]
        total = sum(numbers)

        # Формируем красивый ответ
        numbers_str = " + ".join(map(str, numbers))
        result_text = f"🔢 Результат: {numbers_str} = {total}"

        logger.info(f"Вычислена сумма: {numbers_str} = {total}")
        bot.send_message(message.chat.id, result_text)

    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: пожалуйста, вводите только целые числа.\n"
            "Пример: /sum 5 10 15"
        )
        logger.warning(f"Пользователь {message.from_user.id} ввел некорректные данные для /sum")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при вычислении суммы.")
        logger.error(f"Ошибка в команде /sum: {e}")


# Обработчики текстовых сообщений (reply-кнопки)
@bot.message_handler(func=lambda message: message.text == "О боте")
def handle_about_button(message):
    """Обработка кнопки 'О боте'"""
    logger.info(f"Пользователь {message.from_user.id} нажал кнопку 'О боте'")
    handle_about(message)


@bot.message_handler(func=lambda message: message.text == "Погода Москва")
def handle_weather_button(message):
    """Обработка кнопки 'Погода Москва'"""
    logger.info(f"Пользователь {message.from_user.id} запросил погоду в Москве")

    bot.send_message(message.chat.id, "⏳ Загружаю данные о погоде...")
    weather_info = get_weather_moscow()
    bot.send_message(message.chat.id, weather_info)


@bot.message_handler(func=lambda message: message.text == "Помощь")
def handle_help_button(message):
    """Обработка кнопки 'Помощь'"""
    logger.info(f"Пользователь {message.from_user.id} нажал кнопку 'Помощь'")
    handle_help(message)


@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Обработка всех остальных сообщений"""
    logger.info(f"Пользователь {message.from_user.id} отправил сообщение: {message.text[:50]}...")

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


def main():
    """Основная функция запуска бота"""
    logger.info("Запуск бота...")

    try:
        # Получаем информацию о боте для логирования
        bot_info = bot.get_me()
        logger.info(f"Бот @{bot_info.username} запущен успешно")
        logger.info(f"Имя бота: {bot_info.first_name}")

        # Запуск long polling
        logger.info("Запуск Long Polling...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)

    except telebot.apihelper.ApiException as e:
        logger.error(f"Ошибка API Telegram: {e}")
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")


if __name__ == "__main__":
    main()