import requests
import time
from threading import Event
from datetime import datetime, timedelta, timezone

from back.database import *
from back.config import *
from back.message_processor import *

class MattermostPoller:
    """Поллинг Mattermost на новые сообщения"""
    def __init__(self, config: Config, processor: MessageProcessor):
        self.config = config
        self.processor = processor
        self.last_post_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
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
                    timeout=15
                )
                
                if response.status_code == 200:
                    self._process_messages(response.json())
                else:
                    LOGGER.error(f"Mattermost poll error: {response.text}")
                
                time.sleep(5)
            except Exception as e:
                LOGGER.error(f"Mattermost poll exception: {str(e)}")
                time.sleep(10)
    
    def _process_messages(self, messages: dict):
        """Обрабатывает полученные сообщения"""
        for post_id in messages.get('order', []):
            post = messages['posts'][post_id]
            
            if post['user_id'] == self.config.bot_user_id:
                continue
                
            self.processor.process_message(
                post['message'],
                self.config.channel_id,
                post_id,
                post['user_id']
            )
            
            # Обновляем время последнего сообщения
            create_at = post.get('create_at', 0) / 1000
            self.last_post_time = datetime.fromtimestamp(create_at, timezone.utc)
