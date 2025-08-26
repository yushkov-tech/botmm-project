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
                return
            
            elif message.text.startswith('/'):
                if message.text=='/start' or message.text=='/start@taxmon_python_test_bot':
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton(
                            text="Познакомиться",
                            callback_data='introduce'
                        ))
                        
                    self.telegram_bot.send_message(
                        message.chat.id,
                        "Добро пожаловать! Я бот Валера. \nЯ помогу вам держать контакт между телеграмом и маттермостом.",
                        parse_mode='HTML',
                        reply_markup=markup,
                        disable_web_page_preview=True
                    )

                elif message.text=='/help' or message.text=='/help@taxmon_python_test_bot':
                    help_text = (
                        "Доступные команды:\n"
                        "/start - Начать взаимодействие с ботом\n"
                        "/help - Получить список доступных команд\n"
                        "/info - Получить информацию о боте\n"
                        "/ярмарка - Получить информацию о боте\n"
                    )
                    self.telegram_bot.reply_to(message, help_text)
                    return

                elif message.text == '/ярмарка' or message.text=='/ярмарка@taxmon_python_test_bot':
                    random_user = self._get_random_user_by_position('Специалист по интеграции')
                    if random_user:
                        user_info = f"Случайный специалист по внедрению:\n" \
                                    f"Имя: {random_user[3]}\n" \
                                    f"Фамилия: {random_user[4]}\n" \
                                    f"Email: {random_user[6]}\n" \
                                    f"Telegram: {random_user[7]}"
                                # Отправка гифки
                        gif_url = "https://i.pinimg.com/originals/7d/a9/f0/7da9f09c8b61866d87a5c0db8e4957db.gif"
                        self.telegram_bot.send_animation(message.chat.id, gif_url)
                        self.telegram_bot.send_message(message.chat.id, user_info)
                    else:
                        self.telegram_bot.send_message(message.chat.id, "❌ Нет специалистов по внедрению.")
                
                elif message.text=='/info' or message.text=='/info@taxmon_python_test_bot':
                    info_text = (
                        "🌟 **Добро пожаловать в мир оперативного (налогового) мониторинга!** 🌟\n\n"
                        "Этот бот создан для того, чтобы вы могли быстро реагировать на сообщения в Mattermost, даже вне рабочего времени.\n\n"
                        "🔔 **Что вас ждет?**\n"
                        "- Вне рабочего времени по Екатеринбургу вы будете получать уведомления в чат из Mattermost.\n"
                        "- Вы можете взять задачи в работу, ответить на них, перейти по ссылкам для подробностей или просто проигнорировать.\n\n"
                        "💬 **Как это работает?**\n"
                        "- Если вы отвечаете на сообщения бота, ваше сообщение автоматически отправляется в тред Mattermost.\n"
                        "- Если вы берете задачу в работу, она закрепляется за вами. Если никто не взял её, сообщение будет отправлено менеджменту проекта.\n\n"
                        "🔗 **Не забывайте:**\n"
                        "Чтобы узнать подробности о сообщении, просто пройдите по ссылкам или нажмите на кнопки, предоставленные ботом.\n\n"
                        "🤖 **Давайте сделаем вашу работу более эффективной!**"
                    )
                    self.telegram_bot.reply_to(message, info_text, parse_mode='Markdown')
                    return

            # Обработчик текстовых сообщений
            elif message.reply_to_message is not None:
                if message.reply_to_message.from_user.username == 'taxmon_python_test_bot' and message.reply_to_message.html_text=='📧 Пожалуйста, ответьте на это сообщение вашей корпоративную почтой:':
                    def _is_valid_email(email: str) -> bool:
                        """Проверяет валидность email адреса"""
                        pattern = r'^[a-zA-Z0-9._%+-]+@skbkontur.ru$'
                        return re.match(pattern, email) is not None
                    email = message.text.strip()
                    
                    # Проверяем валидность email
                    if not _is_valid_email(email):
                        self.telegram_bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректный email адрес(@skbkontur.ru).")
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
                                f"✅ Информация обновлена!\n"
                                f"Email: {email}\n"
                                f"Теперь вы связаны с этим аккаунтом."
                            )
                            if time_zone == None:
                                self.telegram_bot.send_message(message.chat.id, '🌏 Пожалуйста, ответьте на это сообщение вашим часовым поясом (Мск/Екб)')
                        else:
                            self.telegram_bot.send_message(message.chat.id, "❌ Ошибка при обновлении информации.")
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
                                f"✅ Отлично! Ваш email сохранен: {email}\n"
                            )
                        else:
                            self.telegram_bot.send_message(message.chat.id, "❌ Ошибка при сохранении email.")
                elif message.reply_to_message.from_user.username == 'taxmon_python_test_bot' and message.reply_to_message.html_text=='🌏 Пожалуйста, ответьте на это сообщение вашим часовым поясом (Мск/Екб)':
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
                                f"✅ Ваш часовой пояс сохранен: {time_zone}\n"
                            )
                        else:
                            self.telegram_bot.send_message(message.chat.id, "❌ Ошибка при обновлении часового пояса.")
                    else:
                        self.telegram_bot.send_message(message.chat.id, "❌ Пользователь не найден в базе данных.")                        

        @self.telegram_bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            message_data = self.pending_responses.get(call.message.message_id)
            if call.data == "introduce":
                self.telegram_bot.send_message(call.message.chat.id, "📧 Пожалуйста, ответьте на это сообщение вашей корпоративную почтой:")
            elif message_data and call.data == "take_work":
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
                    text=call.message.html_text,
                    parse_mode='HTML',
                    reply_markup=markup
                )
                
                # Подтверждаем, что запрос обработан
                self.telegram_bot.answer_callback_query(call.id)

    def _get_message_hash(self, message: str, channel_id: str, post_id: str) -> str:
        """Генерирует уникальный хеш для сообщения"""
        return md5(f"{message}-{channel_id}-{post_id}".encode()).hexdigest()
    
    def _is_working_time(self) -> bool:
        """Проверяет, находится ли текущее время в нерабочих часах"""
        now_ekb = datetime.now(self.config.ekb_tz)
        now_msk = datetime.now(self.config.msk_tz)
        
        ekb_hour = now_ekb.hour
        msk_hour = now_msk.hour
        
        ekb_time = self.config.non_working_hours['екб']
        msk_time = self.config.non_working_hours['мск']
        
        return (ekb_time['start'] <= ekb_hour < ekb_time['end'] and 
                msk_time['start'] <= msk_hour < msk_time['end'])
    
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
                timeout=5
            )
            if response.status_code == 200:
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
        
        # Получаем текущее время в нужном часовом поясе
        current_time = datetime.now(self.config.ekb_tz)
        current_hour = current_time.hour

        # Получаем всех пользователей с их часовыми поясами
        users_in_time_zone = self.db.get_users_with_time_zone()

        # Список пользователей, которые могут получать сообщения
        working_usernames  = []
        
        for user in users_in_time_zone:
            user_id, username_tg, position, time_zone = user
            if user_id is not None and time_zone.lower() in self.config.non_working_hours:
                working_hours = self.config.non_working_hours[time_zone.lower()]
                if working_hours['start'] <= current_hour < working_hours['end']:
                    working_usernames.append(username_tg)

        # Создаем текст сообщения
        message_text = (
            f"🚨 Новое сообщение! 🚨\n\n"
            f"От: {position}:<a href='https://staff.skbkontur.ru/profile/{username}'><b> {first_name} {last_name}</b></a>\n\n"
            f"Сообщение: {message_data['message']}\n"
        )
        # Добавляем информацию о рабочих пользователях, если есть
        if working_usernames:
            message_text += "Внимание: "
        for working in working_usernames:
            message_text += '@' + working + ' '

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
