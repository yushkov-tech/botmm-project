import requests
import time
from threading import Thread, Event, Lock
from datetime import datetime
import telebot
from queue import Queue
from hashlib import md5
import re

from back.database import *

from back.config import *

from massage_varibles import *
from varibles import *

class MessageProcessor:
    """Обработчик сообщений с расширенной функциональностью"""
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.telegram_bot = telebot.TeleBot(config.telegram_bot_token)
        self.message_queue = Queue(maxsize=MESSAGE_QUEUE_MAXSIZE)
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
                    RESPONSE_SENT_CONFIRMATION,
                    reply_to_message_id=message.message_id
                )
                return
            
            elif message.text.startswith('/'):
                if message.text==BOT_COMMAND_START or (BOT_COMMAND_START in message.text and '@taxmon-manager-assistant'in message.text):
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton(
                            text=BUTTON_INTRODUCE,
                            callback_data=CALLBACK_INTRODUCE
                        ))
                        
                    self.telegram_bot.send_message(
                        message.chat.id,
                        WELCOME_MESSAGE,
                        parse_mode='HTML',
                        reply_markup=markup,
                        disable_web_page_preview=True
                    )

                elif message.text==BOT_COMMAND_HELP or message.text==(BOT_COMMAND_HELP in message.text and '@taxmon-manager-assistant'in message.text):
                    help_text = HELP_MESSAGE
                    self.telegram_bot.reply_to(message, help_text)
                    return

                elif message.text == BOT_COMMAND_FAIR or (BOT_COMMAND_FAIR in message.text and '@taxmon-manager-assistant'in message.text):
                    random_user = self._get_random_user_by_position('Специалист по интеграции')
                    if random_user:
                        first_name=random_user[3]
                        last_name=random_user[4]
                        email=random_user[6]
                        telegram=random_user[8]
                        user_info = SPECIALIST_INFO_TEMPLATE.format(
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            telegram=telegram,
                        )
                        # Отправка гифки
                        gif_url = "https://i.pinimg.com/originals/7d/a9/f0/7da9f09c8b61866d87a5c0db8e4957db.gif"
                        self.telegram_bot.send_animation(message.chat.id, gif_url)
                        self.telegram_bot.send_message(message.chat.id, user_info)
                    else:
                        self.telegram_bot.send_message(message.chat.id, NO_SPECIALISTS_ERROR)
                
                elif message.text==BOT_COMMAND_INFO or (BOT_COMMAND_INFO in message.text and '@taxmon-manager-assistant'in message.text):
                    info_text = INFO_MESSAGE
                    self.telegram_bot.reply_to(message, info_text, parse_mode='Markdown')
                    return

            # Обработчик текстовых сообщений
            elif message.reply_to_message is not None:
                if message.reply_to_message.from_user.username == 'taxmon-manager-assistant' and message.reply_to_message.html_text==EMAIL_PROMPT:
                    def _is_valid_email(email: str) -> bool:
                        """Проверяет валидность email адреса"""
                        pattern = EMAIL_PATTERN
                        return re.match(pattern, email) is not None
                    email = message.text.strip()
                    
                    # Проверяем валидность email
                    if not _is_valid_email(email):
                        self.telegram_bot.send_message(message.chat.id, EMAIL_VALIDATION_ERROR)
                        return
                    
                    user_id = message.from_user.id
                    username = message.from_user.username
                    first_name = message.from_user.first_name
                    last_name = message.from_user.last_name
                    
                    # Проверяем, есть ли уже такой email в базе
                    existing_user = self.db.get_user_by_email(email)
                    
                    if existing_user:
                        # Email уже существует - обновляем информацию о пользователе
                        existing_user_id, existing_username, existing_first_name, existing_last_name, existing_position, time_zone = existing_user
                        
                        if self.db.add_or_update_user(
                            user_id = existing_user_id,
                            username = existing_username,
                            first_name = existing_first_name,
                            last_name = existing_last_name,
                            position=existing_position,
                            email = email,
                            id_tg = user_id,
                            username_tg = username,
                            time_zone = time_zone
                        ):
                            self.telegram_bot.send_message(
                                message.chat.id,
                                EMAIL_UPDATE_SUCCESS.format(email=email)
                            )
                            if time_zone == None:
                                self.telegram_bot.send_message(message.chat.id, TIMEZONE_PROMPT)
                        else:
                            self.telegram_bot.send_message(message.chat.id, EMAIL_UPDATE_ERROR)
                    else:
                        # Новый email - создаем запись
                        if self.db.add_or_update_user(
                            user_id=user_id,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email
                        ):
                            self.telegram_bot.send_message(
                                message.chat.id,
                                EMAIL_SAVE_SUCCESS.format(email=email)
                            )
                        else:
                            self.telegram_bot.send_message(message.chat.id, EMAIL_SAVE_ERROR)
                elif message.reply_to_message.from_user.username == 'taxmon-manager-assistant' and message.reply_to_message.html_text==TIMEZONE_PROMPT:
                    time_zone = message.text.strip()
                    
                    user_id = message.from_user.id
                    
                    # Проверяем, есть ли пользователь в базе
                    existing_user = self.db.get_user_info_tg(user_id)
                    
                    if existing_user:
                        if self.db.add_or_update_user(
                            user_id = existing_user[1],
                            username = existing_user[2],
                            first_name = existing_user[3],
                            last_name = existing_user[4],
                            position = existing_user[5],
                            email = existing_user[6],
                            id_tg = existing_user[7],
                            username_tg = existing_user[8],
                            time_zone = time_zone
                        ):
                            self.telegram_bot.send_message(
                                message.chat.id,
                                TIMEZONE_SAVE_SUCCESS.format(time_zone=time_zone)
                            )
                        else:
                            self.telegram_bot.send_message(message.chat.id, TIMEZONE_SAVE_ERROR)
                    else:
                        self.telegram_bot.send_message(message.chat.id, USER_NOT_FOUND_ERROR)


        """Настройка обработчиков команд Telegram"""
        @self.telegram_bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            message_data = self.pending_responses.get(call.message.message_id)
            if call.data == "introduce":
                self.telegram_bot.send_message(call.message.chat.id, EMAIL_PROMPT)
            elif message_data and call.data == "take_work":
                user_id = call.from_user.id
                
                # Определяем текущее состояние
                current_state = message_data.get('is_actual', True)
                
                if current_state:
                    # Кнопка нажата впервые - ОСТАНАВЛИВАЕМ напоминания
                    user_name = f'{call.from_user.first_name} {call.from_user.last_name}'
                    button_text = TASK_TAKEN_CONFIRMATION.format(user_name=user_name)
                    message_data['is_actual'] = False  # Напоминания ВЫКЛЮЧЕНЫ
                    
                    # ОТМЕЧАЕМ В БД, ЧТО ОТВЕТ ПРОИЗОШЕЛ
                    self.db.update_message_response(
                        message_data['message_hash'],
                        f"Задача взята в работу пользователем {user_name} (TG ID: {user_id})",
                        str(user_id),
                        time.time()
                    )
                    
                    # Создаем задачу в базе данных
                    db_message = self.db.get_message_by_hash(message_data['message_hash'])
                    if db_message:
                        self.db.create_task(db_message[0], str(user_id))
                    
                    # Останавливаем напоминания
                    if 'stop_reminder' in message_data:
                        message_data['stop_reminder'].set()
                    user_profile = self.db.get_user_info_tg(user_id)
                    if user_profile:
                        self._send_to_mattermost(
                            message_data['channel_id'],
                            f"Вашей задачей будет заниматься: @{user_profile[2]}",
                            message_data['post_id']
                        )
                    else:
                        self._send_to_mattermost(
                            message_data['channel_id'],
                            f"Ваша задача взята в работу",
                            message_data['post_id']
                        )
                        
                else:
                    # Кнопка нажата повторно - ВКЛЮЧАЕМ напоминания снова
                    button_text = BUTTON_TAKE_WORK
                    
                    # Запускаем новые напоминания
                    message_data['stop_reminder'] = Event()
                    message_data['reminder_thread'] = Thread(
                        target=self._send_periodic_reminders, 
                        args=(message_data, message_data['stop_reminder']),
                        daemon=True
                    )
                    message_data['reminder_thread'].start()

                    self._send_to_mattermost(
                        message_data['channel_id'],
                        f"Задача ищет нового исполнителя",
                        message_data['post_id']
                    )
                
                # Обновляем сообщение с новой кнопкой
                self._update_message_with_new_button(call.message, message_data, button_text)
                
                # Подтверждаем, что запрос обработан
                self.telegram_bot.answer_callback_query(call.id)


    def _send_periodic_reminders(self, message_data: dict, stop_event: Event):
        """Отправляет периодические напоминания об активной задаче"""
        reminder_count = 0

        while not stop_event.is_set() and reminder_count < MAX_REMINDERS:
            # Ждем 7 минут перед отправкой напоминания
            stop_event.wait(REMINDER_TIME * 60)  # 7 минут в секундах
            
            if stop_event.is_set():
                break
                
            # Проверяем, что задача все еще активна (напоминания ВКЛЮЧЕНЫ)
            if not message_data.get('is_actual', True):
                break
                
            # Проверяем, был ли ответ на сообщение
            db_message = self.db.get_message_by_hash(message_data['message_hash'])
            if db_message and db_message[8]!=0:  # is_responded
                break
                
            # Отправляем напоминание
            self._send_reminder_to_telegram(message_data, reminder_count + 1)
            reminder_count += 1


    def _update_message_with_new_button(self, message, message_data: dict, button_text: str):
        """Обновляет сообщение с новой кнопкой"""
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
            url=MM_DIRECT_MESSAGE_URL_TEMPLATE.format(username=username)
        ))
        markup.add(telebot.types.InlineKeyboardButton(
            text=button_text,
            callback_data="take_work"
        ))
        
        # Обновляем сообщение
        self.telegram_bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=message.html_text,
            parse_mode='HTML',
            reply_markup=markup
        )


    def _send_reminder_to_telegram(self, message_data: dict, reminder_number: int):
        """Отправляет напоминание в ответ на оригинальное сообщение"""
        # Находим ID первого сообщения о этой задаче
        first_message_id = self._find_first_message_id(message_data['message_hash'])
        
        if not first_message_id:
            # Если не нашли первое сообщение, пропускаем напоминание
            LOGGER.warning(f"Не найдено первое сообщение для напоминания #{reminder_number}")
            return
        
        try:
            # Просто отправляем текст напоминания как reply на первое сообщение
            reminder_text = REMINDER_MESSAGE.format(reminder_number=reminder_number)
            
            self.telegram_bot.send_message(
                self.config.telegram_chat_id,
                reminder_text,
                parse_mode='HTML',
                reply_to_message_id=first_message_id,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            error = str(e)
            LOGGER.error(TG_SEND_ERROR).format(error=error)

    def _find_first_message_id(self, message_hash: str) -> int:
        """Находит ID первого сообщения в Telegram по хешу задачи"""
        for telegram_message_id, message_data in self.pending_responses.items():
            if message_data.get('message_hash') == message_hash:
                return telegram_message_id
        return None

    def _get_message_hash(self, message: str, channel_id: str, post_id: str) -> str:
        """Генерирует уникальный хеш для сообщения"""
        return md5(f"{message}-{channel_id}-{post_id}".encode()).hexdigest()
    
    def _is_working_time(self) -> bool:
        """Проверяет, находится ли текущее время в рабочих часах и рабочих днях"""
        now_ekb = datetime.now(self.config.ekb_tz)
        now_msk = datetime.now(self.config.msk_tz)
        
        # Проверяем, является ли сегодня выходным днем (суббота или воскресенье)
        if now_ekb.weekday() >= 5:  # 5 - суббота, 6 - воскресенье
            return False
        
        # Проверяем рабочие часы
        ekb_hour = now_ekb.hour
        msk_hour = now_msk.hour
        
        # True - рабочее время, False - нерабочее время
        return (WORK_TIME['start'] <= ekb_hour < WORK_TIME['end'] and 
                WORK_TIME['start'] <= msk_hour < WORK_TIME['end'])
    
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
        
        if self._is_working_time():
            return
        
        self.message_queue.put({
            'message': message,
            'channel_id': channel_id,
            'post_id': post_id,
            'user_id': user_id,
            'message_hash': message_hash,
            'timestamp': time.time()
        })
    
    def _get_random_user_by_position(self, position: str):
        random_user=self.db.get_random_user_by_position(position)
        return random_user
    
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
                timeout=MASSAGETIMEOUT
            )
            if response.status_code == HTTP_SUCCESS:
                user_data = response.json()
                user_data_from_bd=self.db.get_user_email(user_data.get('email'))
                if user_data_from_bd != None:
                    # Email уже существует - обновляем информацию о пользователе
                    email, user_id, username, time_zone = user_data_from_bd[5:8]
                    
                    self.db.add_or_update_user(
                        user_id=user_data.get('id'),
                        username=user_data.get('username'),
                        first_name=user_data.get('first_name'),
                        last_name=user_data.get('last_name'),
                        position=user_data.get('position'),
                        email = email,
                        id_tg = user_id,
                        username_tg = username,
                        time_zone = time_zone
                    )
                else:
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
        
        if post_id and len(post_id) == MATTERMOST_POST_ID_LENGTH:
            payload["root_id"] = post_id
            
        try:
            response = requests.post(
                f"{self.config.mattermost_server_url}/api/v4/posts",
                headers=headers,
                json=payload,
                timeout=USERTIMEOUT
            )
            if response.status_code != HTTP_CREATED:
                error=response.text
                LOGGER.error(MM_USER_INFO_ERROR).format(error=error)
        except Exception as e:
            error=str(e)
            LOGGER.error(MM_USER_INFO_ERROR).format(error=error)
            
    def _format_mattermost_link(self, post_id: str) -> str:
        """Форматирует правильную ссылку на сообщение в Mattermost"""
        if not post_id or len(post_id) != MATTERMOST_POST_ID_LENGTH:
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

        # Получаем всех пользователей с их часовыми поясами
        users_in_time_zone = self.db.get_users_with_time_zone()

        # Список пользователей, которые могут получать сообщения
        working_usernames  = []
        
        for user in users_in_time_zone:
            user_id, username_tg, position, time_zone = user
            if user_id is not None and time_zone is not None:
                # Определяем временную зону
                if time_zone.lower() == 'мск':
                    current_time = datetime.now(self.config.msk_tz)
                elif time_zone.lower() == 'екб':
                    current_time = datetime.now(self.config.ekb_tz)
                else:
                    # Если временная зона не указана или неизвестна, пропускаем пользователя
                    continue
                
                # Получаем текущий час
                current_hour = current_time.hour
                
                # Проверяем рабочее время
                if not (WORK_TIME['start'] <= current_hour < WORK_TIME['end']):
                    working_usernames.append(username_tg)

        # Создаем текст сообщения
        profile_url=STAFF_PROFILE_URL_TEMPLATE.format(username=username)
        message=message_data['message'].replace('@taxmon-manager-assistant', '').strip().replace('@taxmon-manager-assista', '').strip()
        message_text = MESSAGE_TEMPLATE.format(
            status=NEW_MESSAGE,
            position=position,
            profile_url=profile_url,
            first_name=first_name,
            last_name=last_name,
            message=message)
        # Добавляем информацию о рабочих пользователях, если есть
        if working_usernames:
            message_text += ATTENTION_PREFIX
        for working in working_usernames:
            message_text += '@' + working + ' '

        try:
            # Создаем клавиатуру с кнопкой
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text=BUTTON_GO_TO_MM,
                url=mm_link
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text=BUTTON_GO_TO_DM,
                url=MM_DIRECT_MESSAGE_URL_TEMPLATE.format(username=username)
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text=BUTTON_TAKE_WORK,
                callback_data=CALLBACK_TAKE_WORK
            ))
            
            # Отправляем сообщение
            sent_msg = self.telegram_bot.send_message(
                self.config.telegram_chat_id,
                message_text,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            
            # Изначально задача активна - напоминания ВКЛЮЧЕНЫ
            message_data['is_actual'] = True
            self.pending_responses[sent_msg.message_id] = {
                **message_data
            }
            
            # ЗАПУСКАЕМ напоминания сразу при получении сообщения
            message_data['stop_reminder'] = Event()
            message_data['reminder_thread'] = Thread(
                target=self._send_periodic_reminders, 
                args=(message_data, message_data['stop_reminder']),
                daemon=True
            )
            message_data['reminder_thread'].start()
            
            Thread(target=self._check_response, args=(message_data,)).start()
            
        except Exception as e:
            error=str(e)
            LOGGER.error(TG_SEND_ERROR).format(error=error)

    def _check_response(self, message_data: dict):
        """Проверяет, был ли ответ на сообщение"""
        time.sleep(RESPONSE_CHECK_TIMEOUT)  # Ждем 1 час
        
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
        profile_url=STAFF_PROFILE_URL_TEMPLATE.format(username=username)
        message=message_data['message'].replace('@taxmon-manager-assistant', '').strip().replace('@taxmon-manager-assista', '').strip()
        message_text = MESSAGE_TEMPLATE.format(
            status=NO_RESPONSE_MESSAGE,
            position=position,
            profile_url=profile_url,
            first_name=first_name,
            last_name=last_name,
            message=message)

        try:
            # Создаем клавиатуру с кнопкой
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти к сообщению в Mattermost",
                url=mm_link
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти к сообщению в лс Mattermost",
                url=MM_DIRECT_MESSAGE_URL_TEMPLATE.format(username=username)
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                text=BUTTON_TAKE_WORK,
                callback_data=CALLBACK_TAKE_WORK
            ))
            
            # Отправляем сообщение
            sent_msg = self.telegram_bot.send_message(
                self.config.manager_chat_id,
                message_text,
                parse_mode='HTML',
                reply_markup=markup,
                disable_web_page_preview=True
            )
            message_data['is_actual'] = True
            self.pending_responses[sent_msg.message_id] = {
                **message_data,
            }
            
        except Exception as e:
            error=str(e)
            LOGGER.error(TG_SEND_ERROR).format(error=error)
    
    def start_processing(self, stop_event: Event):
        """Запускает обработку сообщений"""
        while not stop_event.is_set():
            try:
                message_data = self.message_queue.get(timeout=1)
                self._send_to_telegram(message_data)
                self.message_queue.task_done()
            except Exception as e:
                continue
