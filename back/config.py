# back/config.py
import pytz
import os
from dotenv import load_dotenv

from massage_varibles import *
from varibles import *

class Config:
    """Класс для хранения конфигурации"""
    def __init__(self):
        # Загружаем переменные окружения
        load_dotenv()
        
        # Mattermost
        self.mattermost_server_url = os.getenv("MATTERMOST_SERVER_URL")
        self.channel_id = os.getenv("MATTERMOST_CHANNEL_ID")
        self.mattermost_bearer_token = os.getenv("MATTERMOST_BEARER_TOKEN")
        self.bot_user_id = os.getenv("MATTERMOST_BOT_USER_ID")
        
        # Telegram
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.manager_chat_id = os.getenv("MANAGER_CHAT_ID")
        
        # Флаги функциональности
        self.enable_mentions = self._str_to_bool(os.getenv("ENABLE_MENTIONS", "true"))
        self.enable_working_hours_check = self._str_to_bool(os.getenv("ENABLE_WORKING_HOURS_CHECK", "true"))
        self.enable_responses = self._str_to_bool(os.getenv("ENABLE_RESPONSES", "true"))
        self.enable_reminders = self._str_to_bool(os.getenv("ENABLE_REMINDERS", "true"))
        self.enable_manager_notifications = self._str_to_bool(os.getenv("ENABLE_MANAGER_NOTIFICATIONS", "true"))
        self.enable_user_registration = self._str_to_bool(os.getenv("ENABLE_USER_REGISTRATION", "true"))
        self.require_mention = self._str_to_bool(os.getenv("REQUIRE_MENTION", "true"))
        self.enable_commands = self._str_to_bool(os.getenv("ENABLE_COMMANDS", "true"))
        
        # Таймауты
        self.polling_interval = int(os.getenv("POLLING_INTERVAL", "30"))
        self.mattermosttimeout = int(os.getenv("MATTERMOSTTIMEOUT", "20"))
        self.massagetimeout = int(os.getenv("MASSAGETIMEOUT", "10"))
        self.usertimeout = int(os.getenv("USERTIMEOUT", "15"))
        self.error_retry_interval = int(os.getenv("ERROR_RETRY_INTERVAL", "15"))
        
        # Временные зоны
        self.ekb_tz = pytz.timezone('Asia/Yekaterinburg')
        self.msk_tz = pytz.timezone('Europe/Moscow')
    
    def _str_to_bool(self, value: str) -> bool:
        """Преобразует строку в булево значение"""
        if not value:
            return False
        return value.lower() in ['true', '1', 't', 'yes', 'y']