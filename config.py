import os
from dotenv import load_dotenv
import logging

# Загрузка переменных окружения
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Конфигурация API
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MOSCOW_COORDS = {"latitude": 55.7558, "longitude": 37.6173}