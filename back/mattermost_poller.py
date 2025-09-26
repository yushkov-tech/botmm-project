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
    
    def poll(self, stop_event: Event):
        """Основной цикл поллинга"""
        headers = {
            'Authorization': f'Bearer {self.config.mattermost_bearer_token}',
            'Content-Type': 'application/json'
        }
        
        while not stop_event.is_set():
            try:
                response = requests.get(
                    f"{self.config.mattermost_server_url}/api/v4/channels/{self.config.channel_id}/posts",
                    headers=headers,
                    params={'since': int(self.last_post_time.timestamp() * 1000)},
                    timeout=MATTERMOSTTIMEOUT
                )
                
                if response.status_code == HTTP_SUCCESS:
                    self._process_messages(response.json())
                else:
                    error=response.text
                    LOGGER.error(MM_POLL_ERROR).format(error=error)
                
                time.sleep(POLLING_INTERVAL)
            except Exception as e:
                error=str(e)
                LOGGER.error(MM_POLL_EXCEPTION)
                time.sleep(ERROR_RETRY_INTERVAL)
    
    def _process_messages(self, messages: dict):
        """Обрабатывает полученные сообщения"""
        for post_id in messages.get('order', []):
            post = messages['posts'][post_id]
            
            # Игнорируем сообщения от бота
            if post['user_id'] == self.config.bot_user_id:
                continue
            
            # Проверяем время создания сообщения
            create_at = post.get('create_at', 0) / 1000  # Приводим к миллисекундам
            message_time = datetime.fromtimestamp(create_at, timezone.utc)
            # Игнорируем сообщения, отправленные до последнего времени обработки
            if message_time <= self.last_post_time:
                continue
            
            # Обрабатываем сообщение
            self.processor.process_message(
                post['message'],
                self.config.channel_id,
                post_id,
                post['user_id']
            )
            
            # Обновляем время последнего сообщения
            self.last_post_time = message_time
