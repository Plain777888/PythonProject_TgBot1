import os
import sys
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Загрузка переменных окружения
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

# Создаем папку для логов, если ее нет
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Настройка форматтера
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Настройка корневого логгера
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Логирование в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Логирование в файл с ротацией
file_handler = RotatingFileHandler(
    filename=f'{log_dir}/bot.log',
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Очистка предыдущих обработчиков
if logger.hasHandlers():
    logger.handlers.clear()

# Добавление обработчиков
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Создаем отдельный логгер для бота
bot_logger = logging.getLogger('telegram_bot')
bot_logger.setLevel(logging.INFO)

# Конфигурация API
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MOSCOW_COORDS = {"latitude": 55.7558, "longitude": 37.6173}


# Функция для безопасного логирования сообщений пользователя
def safe_log_user_info(user_id, username=None, action=None, message_preview=None):
    """Безопасное логирование информации о пользователе без персональных данных"""
    log_data = {
        'user_id': user_id,
        'action': action,
        'message_preview': message_preview[:100] if message_preview else None
    }

    # Имя пользователя логируем только если оно не содержит персональных данных
    if username and not any(keyword in username.lower() for keyword in ['ivan', 'maria', 'alex']):
        log_data['username'] = username

    return str(log_data)