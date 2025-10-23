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
        
        LOGGER.info("Инициализация MessageProcessor")
        # Инициализация Telegram бота
        self._setup_telegram_handlers()
    
    def _setup_telegram_handlers(self):
        """Настройка обработчиков команд Telegram"""
        LOGGER.debug("Настройка обработчиков Telegram")
        
        @self.telegram_bot.message_handler(func=lambda message: True)
        def handle_message(message):
            LOGGER.debug(f"Получено сообщение в Telegram: {message.text[:50]}... от пользователя {message.from_user.id}")
            
            if message.reply_to_message and message.reply_to_message.message_id in self.pending_responses:
                LOGGER.info(f"Обработка ответа на сообщение {message.reply_to_message.message_id}")
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
                LOGGER.info(f"Ответ отправлен в Mattermost для сообщения {original_msg['post_id']}")
                return
            
            elif message.text.startswith('/'):
                if message.text==BOT_COMMAND_START or (BOT_COMMAND_START in message.text and '@taxmon-manager-assistant'in message.text):
                    LOGGER.info(f"Обработка команды /start от пользователя {message.from_user.id}")
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
                    LOGGER.info(f"Обработка команды /help от пользователя {message.from_user.id}")
                    help_text = HELP_MESSAGE
                    self.telegram_bot.reply_to(message, help_text)
                    return

                elif message.text == BOT_COMMAND_FAIR or (BOT_COMMAND_FAIR in message.text and '@taxmon-manager-assistant'in message.text):
                    LOGGER.info(f"Обработка команды /fair от пользователя {message.from_user.id}")
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
                        LOGGER.info(f"Информация о специалисте отправлена пользователю {message.from_user.id}")
                    else:
                        self.telegram_bot.send_message(message.chat.id, NO_SPECIALISTS_ERROR)
                        LOGGER.warning("Не найдены специалисты по интеграции для команды /fair")
                
                elif message.text==BOT_COMMAND_INFO or (BOT_COMMAND_INFO in message.text and '@taxmon-manager-assistant'in message.text):
                    LOGGER.info(f"Обработка команды /info от пользователя {message.from_user.id}")
                    info_text = INFO_MESSAGE
                    self.telegram_bot.reply_to(message, info_text, parse_mode='Markdown')
                    return

            # Обработчик текстовых сообщений
            elif message.reply_to_message is not None:
                if message.reply_to_message.from_user.username == 'taxmon-manager-assistant' and message.reply_to_message.html_text==EMAIL_PROMPT:
                    LOGGER.info(f"Обработка email от пользователя {message.from_user.id}")
                    def _is_valid_email(email: str) -> bool:
                        """Проверяет валидность email адреса"""
                        pattern = EMAIL_PATTERN
                        return re.match(pattern, email) is not None
                    email = message.text.strip()
                    
                    # Проверяем валидность email
                    if not _is_valid_email(email):
                        LOGGER.warning(f"Невалидный email от пользователя {message.from_user.id}: {email}")
                        self.telegram_bot.send_message(message.chat.id, EMAIL_VALIDATION_ERROR)
                        return
                    
                    user_id = message.from_user.id
                    username = message.from_user.username
                    first_name = message.from_user.first_name
                    last_name = message.from_user.last_name
                    
                    # Проверяем, есть ли уже такой email в базе
                    existing_user = self.db.get_user_by_email(email)
                    
                    if existing_user:
                        LOGGER.info(f"Обновление существующего пользователя с email: {email}")
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
                            self.telegram_bot.send_message(message.chat.id, TIMEZONE_PROMPT)
                            LOGGER.info(f"Email пользователя обновлен: {email}")
                        else:
                            self.telegram_bot.send_message(message.chat.id, EMAIL_UPDATE_ERROR)
                            LOGGER.error(f"Ошибка обновления email: {email}")
                    else:
                        LOGGER.info(f"Создание нового пользователя с email: {email}")
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
                            LOGGER.info(f"Email сохранен для нового пользователя: {email}")
                        else:
                            self.telegram_bot.send_message(message.chat.id, EMAIL_SAVE_ERROR)
                            LOGGER.error(f"Ошибка сохранения email: {email}")
                elif message.reply_to_message.from_user.username == 'taxmon-manager-assistant' and message.reply_to_message.html_text==TIMEZONE_PROMPT:
                    LOGGER.info(f"Обработка часового пояса от пользователя {message.from_user.id}")
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
                            LOGGER.info(f"Часовой пояс сохранен для пользователя {user_id}: {time_zone}")
                        else:
                            self.telegram_bot.send_message(message.chat.id, TIMEZONE_SAVE_ERROR)
                            LOGGER.error(f"Ошибка сохранения часового пояса для пользователя {user_id}")
                    else:
                        self.telegram_bot.send_message(message.chat.id, USER_NOT_FOUND_ERROR)
                        LOGGER.warning(f"Пользователь не найден при сохранении часового пояса: {user_id}")


        """Настройка обработчиков команд Telegram"""
        @self.telegram_bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            LOGGER.info(f"Обработка callback: {call.data} от пользователя {call.from_user.id}")
            message_data = self.pending_responses.get(call.message.message_id)
            if call.data == "introduce":
                LOGGER.info(f"Пользователь {call.from_user.id} начал процесс знакомства")
                self.telegram_bot.send_message(call.message.chat.id, EMAIL_PROMPT)
            elif message_data and call.data == "take_work":
                user_id = call.from_user.id
                
                # Определяем текущее состояние
                current_state = message_data.get('is_actual', True)
                
                if current_state:
                    LOGGER.info(f"Пользователь {call.from_user.id} взял задачу в работу")
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
                    LOGGER.info(f"Пользователь {call.from_user.id} вернул задачу в поиск исполнителя")
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

                    if 'stop_reminder' in message_data:
                        message_data['stop_reminder'].set()  
                    
                    message_data['is_actual'] = True  # Напоминания ВКЛЮЧЕНЫ
                
                # Обновляем сообщение с новой кнопкой
                self._update_message_with_new_button(call.message, message_data, button_text)
                
                # Подтверждаем, что запрос обработан
                self.telegram_bot.answer_callback_query(call.id)
                LOGGER.info(f"Callback обработан: {call.data}")

    def _send_periodic_reminders(self, message_data: dict, stop_event: Event):
        """Отправляет периодические напоминания об активной задаче"""
        LOGGER.info(f"Запуск напоминаний для задачи {message_data['message_hash']}")
        reminder_count = 0

        while not stop_event.is_set() and reminder_count < MAX_REMINDERS:
            # Ждем 7 минут перед отправкой напоминания
            stop_event.wait(REMINDER_TIME * 60)  # 7 минут в секундах
            
            if stop_event.is_set():
                LOGGER.info(f"Напоминания остановлены для задачи {message_data['message_hash']}")
                break
                
            # Проверяем, что задача все еще активна (напоминания ВКЛЮЧЕНЫ)
            if not message_data.get('is_actual', True):
                LOGGER.info(f"Задача больше не активна, остановка напоминаний: {message_data['message_hash']}")
                break
                
            # Проверяем, был ли ответ на сообщение
            db_message = self.db.get_message_by_hash(message_data['message_hash'])
            if db_message and db_message[8]!=0:  # is_responded
                LOGGER.info(f"Получен ответ на задачу, остановка напоминаний: {message_data['message_hash']}")
                break
                
            # Отправляем напоминание
            LOGGER.info(f"Отправка напоминания #{reminder_count + 1} для задачи {message_data['message_hash']}")
            self._send_reminder_to_telegram(message_data, reminder_count + 1)
            reminder_count += 1
        
        LOGGER.info(f"Завершены напоминания для задачи {message_data['message_hash']}, отправлено: {reminder_count}")

    def _update_message_with_new_button(self, message, message_data: dict, button_text: str):
        """Обновляет сообщение с новой кнопкой"""
        LOGGER.debug(f"Обновление кнопки в сообщении {message.message_id}")
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
        LOGGER.debug(f"Отправка напоминания #{reminder_number} для задачи {message_data['message_hash']}")
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
            LOGGER.info(f"Напоминание #{reminder_number} отправлено для задачи {message_data['message_hash']}")
            
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
            LOGGER.debug("Текущее время - выходной день")
            return False
        
        # Проверяем рабочие часы
        ekb_hour = now_ekb.hour
        msk_hour = now_msk.hour
        
        # True - рабочее время, False - нерабочее время
        is_working = (WORK_TIME['start'] <= ekb_hour < WORK_TIME['end'] and 
                WORK_TIME['start'] <= msk_hour < WORK_TIME['end'])
        
        LOGGER.debug(f"Проверка рабочего времени: ЕКБ {ekb_hour}ч, МСК {msk_hour}ч - {'рабочее' if is_working else 'нерабочее'}")
        return is_working
    
    def process_message(self, message: str, channel_id: str, post_id: str, user_id: str):
        """Обрабатывает входящее сообщение"""
        LOGGER.info(f"Обработка сообщения от пользователя {user_id}, post_id: {post_id}")
        message_hash = self._get_message_hash(message, channel_id, post_id)
        
        # Проверяем, было ли сообщение уже обработано
        db_message = self.db.get_message_by_hash(message_hash)
        if db_message and db_message[7]:  # is_processed
            LOGGER.debug(f"Сообщение уже обработано: {message_hash}")
            return
        
        # Добавляем сообщение в базу данных
        message_id = self.db.add_message(message_hash, message, channel_id, post_id, user_id, time.time())
        
        with self.lock:
            if message_hash in self.processed_messages:
                LOGGER.debug(f"Сообщение уже в обработке: {message_hash}")
                return
            self.processed_messages.add(message_hash)
        
        if self._is_working_time():
            LOGGER.info(f"Сообщение отложено (рабочее время): {message_hash}")
            return
        
        LOGGER.info(f"Сообщение добавлено в очередь: {message_hash}")
        self.message_queue.put({
            'message': message,
            'channel_id': channel_id,
            'post_id': post_id,
            'user_id': user_id,
            'message_hash': message_hash,
            'timestamp': time.time()
        })
    
    def _get_random_user_by_position(self, position: str):
        LOGGER.debug(f"Поиск случайного пользователя с позицией: {position}")
        random_user=self.db.get_random_user_by_position(position)
        return random_user
    
    def _get_user_info(self, user_id: str) -> dict:
        """Получает информацию о пользователе из Mattermost и сохраняет в БД"""
        LOGGER.debug(f"Получение информации о пользователе: {user_id}")
        # Сначала проверяем локальную базу данных
        db_user = self.db.get_user_info(user_id)
        if db_user:
            LOGGER.debug(f"Пользователь найден в локальной БД: {user_id}")
            return {
                'username': db_user[2],
                'first_name': db_user[3],
                'last_name': db_user[4],
                'position': db_user[5],
                'email': db_user[6]
            }
        
        # Если нет в базе, запрашиваем из Mattermost
        LOGGER.info(f"Запрос информации о пользователе из Mattermost: {user_id}")
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
                    LOGGER.info(f"Пользователь с email уже существует: {user_data.get('email')}")
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
                    LOGGER.info(f"Создание нового пользователя в БД: {user_data.get('username')}")
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
        LOGGER.debug(f"Отправка сообщения в Mattermost, channel: {channel_id}")
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
            if response.status_code == HTTP_CREATED:
                LOGGER.info(f"Сообщение успешно отправлено в Mattermost")
            else:
                error=response.text
                LOGGER.error(MM_USER_INFO_ERROR).format(error=error)
        except Exception as e:
            error=str(e)
            LOGGER.error(MM_USER_INFO_ERROR).format(error=error)
            
    def _format_mattermost_link(self, post_id: str) -> str:
        """Форматирует правильную ссылку на сообщение в Mattermost"""
        if not post_id or len(post_id) != MATTERMOST_POST_ID_LENGTH:
            LOGGER.warning(f"Некорректный post_id для формирования ссылки: {post_id}")
            return "Ссылка недоступна"
        
        # Удаляем возможные пробелы или спецсимволы в post_id
        clean_post_id = post_id.strip()
        return f"{self.config.mattermost_server_url}/kontur/pl/{clean_post_id}"

    def _send_to_telegram(self, message_data: dict):
        LOGGER.info(f"Отправка сообщения в Telegram: {message_data['message_hash']}")
        # Пропускаем сообщения от бота
        if message_data['user_id'] == self.config.bot_user_id:
            LOGGER.debug("Сообщение от бота, пропуск")
            return
        if message_data['message'].startswith('Ответ от внедренца'):
            LOGGER.debug("Сообщение является ответом от внедренца, пропуск")
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
        LOGGER.debug(f"Найдено пользователей с часовыми поясами: {len(users_in_time_zone)}")

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
            
            LOGGER.info(f"Сообщение отправлено в Telegram, ID: {sent_msg.message_id}")
            
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
        LOGGER.info(f"Запуск проверки ответа для задачи {message_data['message_hash']}")
        time.sleep(RESPONSE_CHECK_TIMEOUT)  # Ждем 1 час
        
        with self.lock:
            if message_data['post_id'] not in [msg['post_id'] for msg in self.pending_responses.values()]:
                LOGGER.debug(f"Задача больше не в ожидании ответа: {message_data['message_hash']}")
                return
        
        # Проверяем в базе данных, был ли ответ
        db_message = self.db.get_message_by_hash(message_data['message_hash'])
        if db_message and db_message[8]:  # is_responded
            LOGGER.info(f"Ответ получен для задачи {message_data['message_hash']}")
            return
        
        # Если ответа не было, уведомляем руководителя
        LOGGER.warning(f"Ответ не получен, уведомление руководителя: {message_data['message_hash']}")
        self._notify_manager(message_data)
    
    def _notify_manager(self, message_data: dict):
        """Уведомляет руководителя об отсутствии ответа"""
        LOGGER.info(f"Уведомление руководителя об отсутствии ответа: {message_data['message_hash']}")
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
            LOGGER.info(f"Уведомление руководителя отправлено: {sent_msg.message_id}")
            
        except Exception as e:
            error=str(e)
            LOGGER.error(TG_SEND_ERROR).format(error=error)
    
    def start_processing(self, stop_event: Event):
        """Запускает обработку сообщений"""
        LOGGER.info("Запуск обработки сообщений из очереди")
        processed_count = 0
        
        while not stop_event.is_set():
            try:
                message_data = self.message_queue.get(timeout=1)
                self._send_to_telegram(message_data)
                self.message_queue.task_done()
                processed_count += 1
                
                # Периодически логируем статистику обработки
                if processed_count % 100 == 0:
                    LOGGER.info(f"Обработано сообщений из очереди: {processed_count}")
                    
            except Exception as e:
                continue
        
        LOGGER.info(f"Завершена обработка сообщений. Всего обработано: {processed_count}")