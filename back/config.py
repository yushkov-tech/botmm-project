import pytz
import os

class Config:
    """Класс для хранения конфигурации"""
    def __init__(self):
        # Имя бота для идентификации
        
        # Загружаем переменные окружения
        self._load_config()
        
        # Временные зоны
        self.ekb_tz = pytz.timezone('Asia/Yekaterinburg')
        self.msk_tz = pytz.timezone('Europe/Moscow')
        self.bot_name = os.getenv("BOT_NAME", "unknown")[:22]
        print(f"🚀 Initializing bot: {self.bot_name}")
        
        print(f"✅ Configuration loaded for {self.bot_name}")
    
    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        # Mattermost
        self.mattermost_server_url = os.getenv("MATTERMOST_SERVER_URL", "")
        self.channel_id = os.getenv("MATTERMOST_CHANNEL_ID", "")
        self.mattermost_bearer_token = os.getenv("MATTERMOST_BEARER_TOKEN", "")
        self.bot_user_id = os.getenv("MATTERMOST_BOT_USER_ID", "")
        self.bot_mm_name = os.getenv("BOT_MM_NAME", "")[:22]
        
        # Telegram
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.manager_chat_id = os.getenv("MANAGER_CHAT_ID", "")
        
        # Флаги функциональности
        self.enable_mentions = self._get_bool("ENABLE_MENTIONS", True)
        self.enable_working_hours_check = self._get_bool("ENABLE_WORKING_HOURS_CHECK", True)
        self.enable_responses = self._get_bool("ENABLE_RESPONSES", True)
        self.enable_reminders = self._get_bool("ENABLE_REMINDERS", True)
        self.enable_manager_notifications = self._get_bool("ENABLE_MANAGER_NOTIFICATIONS", True)
        self.enable_user_registration = self._get_bool("ENABLE_USER_REGISTRATION", True)
        self.require_mention = self._get_bool("REQUIRE_MENTION", True)
        self.all_root = self._get_bool("ALL_ROOT", True)
        self.enable_commands = self._get_bool("ENABLE_COMMANDS", True)
        
        # Таймауты
        self.polling_interval = int(os.getenv("POLLING_INTERVAL", "30"))
        self.mattermosttimeout = int(os.getenv("MATTERMOSTTIMEOUT", "20"))
        self.massagetimeout = int(os.getenv("MASSAGETIMEOUT", "10"))
        self.usertimeout = int(os.getenv("USERTIMEOUT", "15"))
        self.error_retry_interval = int(os.getenv("ERROR_RETRY_INTERVAL", "15"))
        
        # Валидация
        self._validate_config()
    
    def _get_bool(self, key, default):
        """Получает булево значение из переменной окружения"""
        value = os.getenv(key)
        if value is None:
            return default
        value = value.lower()
        return value in ['true', '1', 'yes', 'y', 't']
    
    def _validate_config(self):
        """Проверяет обязательные настройки"""
        required = [
            ("TELEGRAM_BOT_TOKEN", self.telegram_bot_token),
            ("TELEGRAM_CHAT_ID", self.telegram_chat_id),
            ("MATTERMOST_SERVER_URL", self.mattermost_server_url),
            ("MATTERMOST_CHANNEL_ID", self.channel_id),
        ]
        
        for name, value in required:
            if not value:
                print(f"⚠️ WARNING: {name} is not set for bot {self.bot_name}")