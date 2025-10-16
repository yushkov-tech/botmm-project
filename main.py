import time
from threading import Thread, Event

from massage_varibles import *
from varibles import *

from back.database import *
from back.logger import *
from back.mattermost_poller import *
from back.message_processor import *
from back.config import *

def main():
    """Основная функция запуска"""
    stop_event = Event()
    
    try:
        config = Config()
        db = Database()
        processor = MessageProcessor(config, db)
        
        # Запускаем обработчик сообщений
        Thread(target=processor.start_processing, args=(stop_event,), daemon=True).start()
        
        # Запускаем поллинг Mattermost
        poller = MattermostPoller(config, processor)
        Thread(target=poller.poll, args=(stop_event,), daemon=True).start()
        
        # Запускаем Telegram бота
        Thread(target=processor.telegram_bot.infinity_polling, daemon=True).start()
        
        # Основной цикл
        while not stop_event.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        LOGGER.error(SHUTDOWN_MESSAGE)
        stop_event.set()
    except Exception as e:
        error=str(e)
        LOGGER.error(FATAL_ERROR).format(error=error)
        stop_event.set()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    main()