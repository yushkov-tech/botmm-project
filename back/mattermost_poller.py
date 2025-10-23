import requests
import time
from threading import Event
from datetime import datetime, timedelta, timezone

from back.database import *
from back.config import *
from back.message_processor import *

from massage_varibles import *
from varibles import *

class MattermostPoller:
    """Поллинг Mattermost на новые сообщения"""
    def __init__(self, config: Config, processor: MessageProcessor):
        self.config = config
        self.processor = processor
        self.last_post_time = datetime.now(timezone.utc) - timedelta(minutes=POLLING_INTERVAL)
        # Статистика поллингов
        self.poll_count = 0
        self.successful_polls = 0
        self.failed_polls = 0
        self.last_statistics_time = time.time()
    
    def get_current_statistics(self):
        """Возвращает текущую статистику поллингов"""
        success_rate = (self.successful_polls / self.poll_count) * 100 if self.poll_count > 0 else 0
        return {
            'total_polls': self.poll_count,
            'successful_polls': self.successful_polls,
            'failed_polls': self.failed_polls,
            'success_rate': success_rate
        }
    
    def poll(self, stop_event: Event):
        """Основной цикл поллинга"""
        LOGGER.info("Запуск поллинга Mattermost")
        headers = {
            'Authorization': f'Bearer {self.config.mattermost_bearer_token}',
            'Content-Type': 'application/json'
        }
        
        while not stop_event.is_set():
            try:
                LOGGER.debug("Выполнение запроса к Mattermost API")
                self.poll_count += 1
                
                response = requests.get(
                    f"{self.config.mattermost_server_url}/api/v4/channels/{self.config.channel_id}/posts",
                    headers=headers,
                    params={'since': int(self.last_post_time.timestamp() * 1000)},
                    timeout=MATTERMOSTTIMEOUT
                )
                
                if response.status_code == HTTP_SUCCESS:
                    LOGGER.debug("Успешный ответ от Mattermost API")
                    self.successful_polls += 1
                    self._process_messages(response.json())
                else:
                    error=response.text
                    LOGGER.error(MM_POLL_ERROR).format(error=error)
                    self.failed_polls += 1
                
                # Вывод статистики каждые 10000 поллингов
                if self.poll_count % 10000 == 0:
                    self._print_statistics()
                
                time.sleep(POLLING_INTERVAL)
            except Exception as e:
                error=str(e)
                LOGGER.error(MM_POLL_EXCEPTION)
                self.failed_polls += 1
                time.sleep(ERROR_RETRY_INTERVAL)
    
    def _print_statistics(self):
        """Вывод статистики поллингов"""
        success_rate = (self.successful_polls / self.poll_count) * 100 if self.poll_count > 0 else 0
        current_time = time.time()
        elapsed_time = current_time - self.last_statistics_time
        polls_per_minute = (10000 / elapsed_time) * 60 if elapsed_time > 0 else 0
        
        LOGGER.info(
            "=== СТАТИСТИКА ПОЛЛИНГА ==="
        )
        LOGGER.info(f"Всего поллингов: {self.poll_count}")
        LOGGER.info(f"Успешных: {self.successful_polls}")
        LOGGER.info(f"Неуспешных: {self.failed_polls}")
        LOGGER.info(f"Успешность: {success_rate:.2f}%")
        LOGGER.info(f"Пропускная способность: {polls_per_minute:.2f} поллингов/мин")
        LOGGER.info(
            "==========================="
        )
        
        # Сбрасываем время для следующего интервала
        self.last_statistics_time = current_time
    
    def _process_messages(self, messages: dict):
        """Обрабатывает полученные сообщения"""
        LOGGER.debug(f"Начало обработки {len(messages.get('order', []))} сообщений")
        processed_count = 0
        
        for post_id in messages.get('order', []):
            post = messages['posts'][post_id]
            
            # Игнорируем сообщения от бота
            if post['user_id'] == self.config.bot_user_id or '@taxmon-manager-assista' not in post['message']:
                LOGGER.debug(f"Сообщение {post_id} пропущено (от бота или без упоминания)")
                continue
            
            # Проверяем время создания сообщения
            create_at = post.get('create_at', 0) / 1000  # Приводим к миллисекундам
            message_time = datetime.fromtimestamp(create_at, timezone.utc)
            # Игнорируем сообщения, отправленные до последнего времени обработки
            if message_time <= self.last_post_time:
                LOGGER.debug(f"Сообщение {post_id} пропущено (устаревшее)")
                continue
            
            # Обрабатываем сообщение
            LOGGER.info(f"Обработка нового сообщения {post_id} от пользователя {post['user_id']}")
            self.processor.process_message(
                post['message'],
                self.config.channel_id,
                post_id,
                post['user_id']
            )
            processed_count += 1
            
            # Обновляем время последнего сообщения
            self.last_post_time = message_time
        
        if processed_count > 0:
            LOGGER.info(f"Обработано {processed_count} новых сообщений")
