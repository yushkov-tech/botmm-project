import requests
import time
from threading import Thread, Event, Lock
from datetime import datetime
import telebot
from queue import Queue
from hashlib import md5

from back.database import *

from back.config import *

class MessageProcessor:
    """Обработчик сообщений с расширенной функциональностью"""
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.telegram_bot = telebot.TeleBot(config.telegram_bot_token)
        self.message_queue = Queue(maxsize=100)
        self.processed_messages = set()
        self.pending_responses = {}
        self.lock = Lock()
        
        # Инициализация Telegram бота
        self._setup_telegram_handlers()
    
    def _setup_telegram_handlers(self):
        """Настройка обработчиков команд Telegram"""
        @self.telegram_bot.message_handler(func=lambda message: True)
        def handle_message(message):
            if message.reply_to_message and message.reply_to_message.message_id in self.pending_responses:
                original_msg = self.pending_responses[message.reply_to_message.message_id]
                self._send_to_mattermost(
                    original_msg['channel_id'],
                    f"Ответ от внедренца: {message.text}",
                    original_msg['post_id']
                )
                
                # Сохраняем ответ в базу данных
                self.db.update_message_response(
                    original_msg['message_hash'],
                    message.text,
                    str(message.from_user.id),
                    time.time()
                )
                
                self.telegram_bot.send_message(
                    message.chat.id,
                    "Ваш ответ отправлен в Mattermost!",
                    reply_to_message_id=message.message_id
                )

        @self.telegram_bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            message_data = self.pending_responses.get(call.message.message_id)
            
            if message_data and call.data == "take_work":
                user_id = call.from_user.id
                
                # Переключаем состояние is_actual
                message_data['is_actual'] = not message_data['is_actual']
                
                # Обновляем текст кнопки
                if message_data['is_actual']:
                    button_text = "Взять в работу"
                else:
                    button_text = f"Задача взята в работу пользователем: {call.from_user.first_name} {call.from_user.last_name}"
                    
                    # Создаем задачу в базе данных
                    db_message = self.db.get_message_by_hash(message_data['message_hash'])
                    if db_message:
                        self.db.create_task(db_message[0], str(user_id))
                
                # Обновляем сообщение с новой кнопкой
                mm_link = self._format_mattermost_link(message_data['post_id'])
                user_info = self._get_user_info(message_data['user_id'])
                username = user_info.get('username', '') if user_info else ''
                
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(
                    text="Перейти к сообщению в Mattermost",
                    url=mm_link
                ))
                markup.add(telebot.types.InlineKeyboardButton(
                    text="Перейти к сообщению в лс Mattermost",
                    url=f"https://chat.skbkontur.ru/kontur/messages/@{username}"
                ))
                markup.add(telebot.types.InlineKeyboardButton(
                    text=button_text,
                    callback_data="take_work"
                ))
                
                # Обновляем сообщение
                self.telegram_bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text,
                    parse_mode='HTML',
                    reply_markup=markup
                )
                
                # Подтверждаем, что запрос обработан
                self.telegram_bot.answer_callback_query(call.id)

    def _get_message_hash(self, message: str, channel_id: str, post_id: str) -> str:
        """Генерирует уникальный хеш для сообщения"""
        return md5(f"{message}-{channel_id}-{post_id}".encode()).hexdigest()
    
    def _is_non_working_time(self) -> bool:
        """Проверяет, находится ли текущее время в нерабочих часах"""
        now_ekb = datetime.now(self.config.ekb_tz)
        now_msk = datetime.now(self.config.msk_tz)
        
        ekb_hour = now_ekb.hour
        msk_hour = now_msk.hour
        
        ekb_time = self.config.non_working_hours['ekb']
        msk_time = self.config.non_working_hours['msk']
        
        return (ekb_time['start'] <= ekb_hour < ekb_time['end'] or 
                msk_time['start'] <= msk_hour < msk_time['end'])
    
    def _get_implementers(self) -> list:
        """Возвращает список внедренцев для текущего времени"""
        now_ekb = datetime.now(self.config.ekb_tz).hour
        now_msk = datetime.now(self.config.msk_tz).hour
        
        if self.config.non_working_hours['ekb']['start'] <= now_ekb < self.config.non_working_hours['ekb']['end']:
            return self.config.implementers['ekb']
        else:
            return self.config.implementers['msk']
    
    def process_message(self, message: str, channel_id: str, post_id: str, user_id: str):
        """Обрабатывает входящее сообщение"""
        message_hash = self._get_message_hash(message, channel_id, post_id)
        
        # Проверяем, было ли сообщение уже обработано
        db_message = self.db.get_message_by_hash(message_hash)
        if db_message and db_message[7]:  # is_processed
            return
        
        # Добавляем сообщение в базу данных
        message_id = self.db.add_message(message_hash, message, channel_id, post_id, user_id, time.time())
        
        with self.lock:
            if message_hash in self.processed_messages:
                return
            self.processed_messages.add(message_hash)
        
        if self._is_non_working_time():
            self._send_to_mattermost(
                channel_id,
                "Спасибо за сообщение! Мы обработаем его в рабочее время (с 8 до 18).",
                post_id
            )
            return
        
        self.message_queue.put({
            'message': message,
            'channel_id': channel_id,
            'post_id': post_id,
            'user_id': user_id,
            'message_hash': message_hash,
            'timestamp': time.time()
        })
    
    def _get_user_info(self, user_id: str) -> dict:
        """Получает информацию о пользователе из Mattermost и сохраняет в БД"""
        # Сначала проверяем локальную базу данных
        db_user = self.db.get_user_info(user_id)
        if db_user:
            return {
                'username': db_user[2],
                'first_name': db_user[3],
                'last_name': db_user[4],
                'position': db_user[5],
                'email': db_user[6]
            }
        
        # Если нет в базе, запрашиваем из Mattermost
        headers = {
            'Authorization': f'Bearer {self.config.mattermost_bearer_token}',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.get(
                f"{self.config.mattermost_server_url}/api/v4/users/{user_id}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                user_data = response.json()
                # Сохраняем пользователя в базу данных
                self.db.add_or_update_user(
                    user_id=user_id,
                    username=user_data.get('username'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    position=user_data.get('position'),
                    email=user_data.get('email')
                )
                return user_data
        except Exception as e:
            LOGGER.error(f"Ошибка получения информации о пользователе: {str(e)}")
        
        return {'username': user_id}  # Возвращаем ID если не удалось получить информацию

    def _send_to_mattermost(self, channel_id: str, message: str, post_id: str = None):
        """Отправляет сообщение в Mattermost"""
        headers = {
            'Authorization': f'Bearer {self.config.mattermost_bearer_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "channel_id": channel_id,
            "message": message,
        }
        
        if post_id and len(post_id) == 26:
            payload["root_id"] = post_id
            
        try:
            response = requests.post(
                f"{self.config.mattermost_server_url}/api/v4/posts",
                headers=headers,
                json=payload,
                timeout=10
            )
            if response.status_code != 201:
                LOGGER.error(f"Mattermost error: {response.text}")
        except Exception as e:
            LOGGER.error(f"Mattermost send error: {str(e)}")
    
    def _format_mattermost_link(self, post_id: str) -> str:
        """Форматирует правильную ссылку на сообщение в Mattermost"""
        if not post_id or len(post_id) != 26:
            return "Ссылка недоступна"
        
        # Удаляем возможные пробелы или спецсимволы в post_id
        clean_post_id = post_id.strip()
        return f"{self.config.mattermost_server_url}/kontur/pl/{clean_post_id}"

    def _send_to_telegram(self, message_data: dict):
        # Пропускаем сообщения от бота
        if message_data['user_id'] == self.config.bot_user_id:
            return
        if message_data['message'].startswith('Ответ от внедренца'):
            return

        # Получаем информацию об отправителе
        user_info = self._get_user_info(message_data['user_id'])
        username = user_info.get('username', '')
        first_name = user_info.get('first_name', 'Неизвестный')
        last_name = user_info.get('last_name', 'Неизвестный')
        position = user_info.get('position', '')
        email = user_info.get('email', '')

        # Форматируем ссылку
        mm_link = self._format_mattermost_link(message_data['post_id'])
        
        # Создаем текст сообщения
        message_text = (
            f"🚨 Новое сообщение! 🚨\n\n"
            f"От: {position}:<a href='https://staff.skbkontur.ru/profile/{username}'><b> {first_name} {last_name}</b></a>\n\n"
            f"Сообщение: {message_data['message']}\n"
        )

        try:
            # Создаем клавиатуру с кнопкой
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти к сообщению в Mattermost",
                url=mm_link
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти к сообщению в лс Mattermost",
                url=f"https://chat.skbkontur.ru/kontur/messages/@{username}"
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text="Взять в работу",
                callback_data="take_work"
            ))
            
            # Отправляем сообщение
            sent_msg = self.telegram_bot.send_message(
                self.config.telegram_chat_id,
                message_text,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            
            self.pending_responses[sent_msg.message_id] = {
                **message_data,
                'is_actual': True  # Изначально задача активна
            }
            Thread(target=self._check_response, args=(message_data,)).start()
            
        except Exception as e:
            LOGGER.error(f"Ошибка отправки в Telegram: {str(e)}")

    def _check_response(self, message_data: dict):
        """Проверяет, был ли ответ на сообщение"""
        time.sleep(360)  # Ждем 1 час
        
        with self.lock:
            if message_data['post_id'] not in [msg['post_id'] for msg in self.pending_responses.values()]:
                return
        
        # Проверяем в базе данных, был ли ответ
        db_message = self.db.get_message_by_hash(message_data['message_hash'])
        if db_message and db_message[8]:  # is_responded
            return
        
        # Если ответа не было, уведомляем руководителя
        self._notify_manager(message_data)
    
    def _notify_manager(self, message_data: dict):
        """Уведомляет руководителя об отсутствии ответа"""
        # Получаем информацию об отправителе
        user_info = self._get_user_info(message_data['user_id'])
        username = user_info.get('username', '')
        first_name = user_info.get('first_name', 'Неизвестный')
        last_name = user_info.get('last_name', 'Неизвестный')
        position = user_info.get('position', '')
        email = user_info.get('email', '')

        # Форматируем ссылку
        mm_link = self._format_mattermost_link(message_data['post_id'])
        
        # Создаем текст сообщения
        message_text = (
            f"⚠️ Никто не ответил на обращение ⚠️\n\n"
            f"От: {position}:<a href='https://staff.skbkontur.ru/profile/{username}'><b> {first_name} {last_name}</b></a>\n\n"
            f"Сообщение: {message_data['message']}\n"
        )

        try:
            # Создаем клавиатуру с кнопкой
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти к сообщению в Mattermost",
                url=mm_link
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти к сообщению в лс Mattermost",
                url=f"https://chat.skbkontur.ru/kontur/messages/@{username}"
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text="Взять в работу",
                callback_data="take_work"
            ))
            
            # Отправляем сообщение
            sent_msg = self.telegram_bot.send_message(
                self.config.manager_chat_id,
                message_text,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            
            self.pending_responses[sent_msg.message_id] = {
                **message_data,
                'is_actual': True  # Изначально задача активна
            }
            Thread(target=self._check_response, args=(message_data,)).start()
            
        except Exception as e:
            LOGGER.error(f"Ошибка отправки в Telegram: {str(e)}")
    
    def start_processing(self, stop_event: Event):
        """Запускает обработку сообщений"""
        while not stop_event.is_set():
            try:
                message_data = self.message_queue.get(timeout=1)
                self._send_to_telegram(message_data)
                self.message_queue.task_done()
            except Exception as e:
                continue
