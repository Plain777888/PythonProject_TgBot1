import telebot
from telebot import types
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)


# ========== ФУНКЦИИ КЛАВИАТУР ==========
def create_main_keyboard():
    """Создание основной клавиатуры"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        types.KeyboardButton("❓ О боте"),
        types.KeyboardButton("☀️ Погода Москва"),
        types.KeyboardButton("🤝 Помощь"),
        types.KeyboardButton("📝 Заметки"),
        types.KeyboardButton("⬇️ Скрыть клавиатуру")
    ]

    keyboard.add(*buttons)
    return keyboard


# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработка команды /start"""
    print(f"START: {message.from_user.id}")

    bot.send_message(
        message.chat.id,
        "👋 Привет! Используй кнопки ниже:",
        reply_markup=create_main_keyboard()
    )


# ========== ОБРАБОТЧИКИ REPLY-КНОПОК ==========
@bot.message_handler(func=lambda message: message.text == "❓ О боте")
def handle_about_button(message):
    """Обработка кнопки 'О боте'"""
    print(f"ABOUT_BUTTON: {message.from_user.id}")
    bot.send_message(message.chat.id, "🤖 Это тестовый бот для проверки кнопок")


@bot.message_handler(func=lambda message: message.text == "☀️ Погода Москва")
def handle_weather_button(message):
    """Обработка кнопки 'Погода Москва'"""
    print(f"WEATHER_BUTTON: {message.from_user.id}")
    bot.send_message(message.chat.id, "🌤 Погода в Москве: +15°C, солнечно")


@bot.message_handler(func=lambda message: message.text == "🤝 Помощь")
def handle_help_button(message):
    """Обработка кнопки 'Помощь'"""
    print(f"HELP_BUTTON: {message.from_user.id}")
    bot.send_message(message.chat.id, "📖 Напиши /help для справки")


@bot.message_handler(func=lambda message: message.text == "📝 Заметки")
def handle_notes_button(message):
    """Обработка кнопки 'Заметки'"""
    print(f"NOTES_BUTTON: {message.from_user.id}")
    bot.send_message(message.chat.id, "📝 Раздел заметок")


@bot.message_handler(func=lambda message: message.text == "⬇️ Скрыть клавиатуру")
def handle_hide_button(message):
    """Обработка кнопки 'Скрыть клавиатуру'"""
    print(f"HIDE_BUTTON: {message.from_user.id}")
    hide_markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "⌨️ Клавиатура скрыта. Напиши /start чтобы вернуть.",
        reply_markup=hide_markup
    )


# ========== ОБРАБОТКА ТЕКСТА ==========
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработка текстовых сообщений"""
    print(f"TEXT: {message.from_user.id}: {message.text}")
    bot.send_message(
        message.chat.id,
        f"Я получил: '{message.text}'\nИспользуй кнопки ниже:",
        reply_markup=create_main_keyboard()
    )


# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 Тестовый бот запущен...")
    print("Нажмите Ctrl+C для остановки")
    bot.infinity_polling()