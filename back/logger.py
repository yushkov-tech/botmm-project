import logging
import os

# Получаем уровень логирования из переменной окружения
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

# Преобразуем строку в константу logging
if log_level == 'DEBUG':
    level = logging.DEBUG
elif log_level == 'WARNING':
    level = logging.WARNING
elif log_level == 'ERROR':
    level = logging.ERROR
else:
    level = logging.INFO  # по умолчанию

# Настройка логирования
logging.basicConfig(
    level=level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger(__name__)

# Логируем текущий уровень для проверки
LOGGER.info(f"Logging level set to: {log_level}")
