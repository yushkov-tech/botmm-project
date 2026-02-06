import time
from threading import Thread, Event
import os

from massage_varibles import *
from varibles import *

from back.database import *
from back.logger import *
from back.mattermost_poller import *
from back.message_processor import *
from back.config import *
from requests.exceptions import ReadTimeout, ConnectionError

def run_telegram_bot(processor):
    """Функция для запуска бота в потоке"""
    retry_count = 0
    
    while True:
        try:
            LOGGER.info(f"Запуск Telegram бота (попытка {retry_count + 1})...")
            retry_count = 0  # Сбрасываем счетчик при успешном запуске
            processor.telegram_bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                restart_on_change=True
            )
        except (ReadTimeout, ConnectionError) as e:
            retry_count += 1
            LOGGER.warning(f"Сетевая ошибка Telegram бота ({retry_count}): {e}")
            wait_time = 10  # Короткая пауза для сетевых ошибок
            LOGGER.info(f"Перезапуск через {wait_time} секунд...")
            time.sleep(wait_time)
        except KeyboardInterrupt:
            LOGGER.info("Telegram бот остановлен пользователем")
            break
        except Exception as e:
            LOGGER.error(f"Критическая ошибка в Telegram боте: {e}")
            LOGGER.info("Перезапуск через 1 минуту...")
            time.sleep(60)


def main():
    """Основная функция запуска"""
    stop_event = Event()
    db = None
    
    try:
        config = Config()
        db = Database()
        processor = MessageProcessorTemplate(config, db)
        
        # Запускаем обработчик сообщений
        Thread(target=processor.start_processing, args=(stop_event,), daemon=True).start()
        
        # Запускаем поллинг Mattermost
        poller = MattermostPollerTemplate(config, processor)
        Thread(target=poller.poll, args=(stop_event,), daemon=True).start()
        
        # Запускаем Telegram бота
        Thread(target=run_telegram_bot, args=(processor,), daemon=True).start()
        
        # Основной цикл
        while not stop_event.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        LOGGER.error(SHUTDOWN_MESSAGE)
        stop_event.set()
    except Exception as e:
        error = str(e)
        LOGGER.error(FATAL_ERROR.format(error=error))
        stop_event.set()
    finally:
        if db is not None:
            db.close()

if __name__ == '__main__':
    main()