# keyboards.py
from telebot import types


def create_main_keyboard():
    """Создание основной клавиатуры бота"""
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


def create_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("❌ Отмена"))
    return keyboard


def create_echo_keyboard():
    """Клавиатура для команды эхо"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        types.KeyboardButton("Пример текста"),
        types.KeyboardButton("Отменить эхо"),
        types.KeyboardButton("Показать клавиатуру"),
        types.KeyboardButton("Скрыть клавиатуру")
    ]

    keyboard.add(*buttons)
    return keyboard


def create_hide_keyboard():
    """Клавиатура для скрытия (только одна кнопка)"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Скрыть клавиатуру"))
    return keyboard


def create_note_categories_keyboard():
    """Клавиатура с категориями заметок"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

    buttons = [
        types.KeyboardButton("📌 Общее"),
        types.KeyboardButton("💼 Работа"),
        types.KeyboardButton("🏠 Личное"),
        types.KeyboardButton("🎓 Учеба"),
        types.KeyboardButton("🛒 Покупки"),
        types.KeyboardButton("📅 Планы"),
        types.KeyboardButton("⏭ Пропустить")
    ]

    keyboard.add(*buttons)
    return keyboard