import envparse
import pytz

from back.database import *

class Config:
    """Класс для хранения конфигурации"""
    def __init__(self):
        envparse.env.read_envfile()
        # Mattermost
        self.mattermost_server_url = envparse.env.str("MATTERMOST_SERVER_URL")
        self.channel_id = envparse.env.str("MATTERMOST_CHANNEL_ID")
        self.mattermost_bearer_token = envparse.env.str("MATTERMOST_BEARER_TOKEN")
        self.bot_user_id = envparse.env.str("MATTERMOST_BOT_USER_ID")
        
        # Telegram
        self.telegram_bot_token = envparse.env.str("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = envparse.env.str("TELEGRAM_CHAT_ID")
        self.manager_chat_id = envparse.env.str("MANAGER_CHAT_ID")
        
        # Временные зоны
        self.ekb_tz = pytz.timezone('Asia/Yekaterinburg')
        self.msk_tz = pytz.timezone('Europe/Moscow')
        
        # Настройки времени
        self.non_working_hours = {
            'ekb': {'start': 9  , 'end': 10},  # 6-8 утра ЕКБ
            'msk': {'start': 9, 'end': 10}   # 8-10 утра МСК
        }
        
        # Внедренцы
        self.implementers = {
            'ekb': ['user1_id', 'user2_id'],
            'msk': ['user3_id', 'user4_id']
        }
