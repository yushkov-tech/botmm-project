from threading import Lock
import sqlite3
from sqlite3 import Error
import random

from back.logger import *

from massage_varibles import *
from varibles import *

class Database:
    """Класс для работы с базой данных SQLite"""
    def __init__(self, db_file="messages.db"):
        self.db_file = db_file
        self.conn = None
        self.lock = Lock()
        self._initialize_db()

    def _initialize_db(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            cursor = self.conn.cursor()
            
            # Таблица для сообщений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_hash TEXT UNIQUE NOT NULL,
                    message_text TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    is_processed INTEGER DEFAULT 0,
                    is_responded INTEGER DEFAULT 0,
                    response_text TEXT,
                    response_time REAL,
                    responder_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    position TEXT,
                    email TEXT,
                    id_tg TEXT,
                    username_tg TEXT,
                    time_zone TEXT,
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для задач
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    assigned_to TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    taken_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            """)
            
            self.conn.commit()
        except Error as e:
            error=str(e)
            LOGGER.error(DB_INIT_ERROR).format(error=error)
            raise

    def add_message(self, message_hash: str, message_text: str, channel_id: str, 
                   post_id: str, user_id: str, timestamp: float):
        """Добавляет сообщение в базу данных"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO messages 
                    (message_hash, message_text, channel_id, post_id, user_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (message_hash, message_text, channel_id, post_id, user_id, timestamp))
                self.conn.commit()
                return cursor.lastrowid
            except Error as e:
                error=str(e)
                LOGGER.error(DB_ADD_MESSAGE_ERROR).format(error=error)
                return None

    def get_message_by_hash(self, message_hash: str):
        """Получает сообщение по хешу"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT * FROM messages WHERE message_hash = ?
                """, (message_hash,))
                return cursor.fetchone()
            except Error as e:
                error=str(e)
                LOGGER.error(DB_GET_MESSAGE_ERROR).format(error=error)
                return None

    def update_message_response(self, message_hash: str, response_text: str, 
                              responder_id: str, response_time: float):
        """Обновляет информацию об ответе на сообщение"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE messages 
                    SET is_responded = 1, response_text = ?, 
                        responder_id = ?, response_time = ?
                    WHERE message_hash = ?
                """, (response_text, responder_id, response_time, message_hash))
                self.conn.commit()
                return cursor.rowcount > 0
            except Error as e:
                error=str(e)
                LOGGER.error(DB_UPDATE_RESPONSE_ERROR).format(error=error)
                return False

    def add_or_update_user(self, user_id: str, username: str = None, 
                            first_name: str = None, last_name: str = None, 
                            position: str = None, email: str = None, id_tg: str = None, username_tg: str = None, time_zone: str = None):
        """Добавляет или обновляет информацию о пользователе"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, position, email, id_tg, username_tg, time_zone, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        user_id = COALESCE(excluded.user_id, user_id),
                        username = COALESCE(excluded.username, username),
                        first_name = COALESCE(excluded.first_name, first_name),
                        last_name = COALESCE(excluded.last_name, last_name),
                        position = COALESCE(excluded.position, position),
                        email = COALESCE(excluded.email, email),
                        id_tg = COALESCE(excluded.id_tg, id_tg),
                        username_tg = COALESCE(excluded.username_tg, username_tg),
                        time_zone = COALESCE(excluded.time_zone, time_zone),
                        last_seen = CURRENT_TIMESTAMP
                """, (user_id, username, first_name, last_name, position, email, id_tg, username_tg, time_zone))
                self.conn.commit()
                return True
            except Error as e:
                error=str(e)
                LOGGER.error(DB_USER_UPDATE_ERROR).format(error=error)
                return False

    def get_user_info(self, user_id: str):
        """Получает информацию о пользователе"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT * FROM users WHERE user_id = ?
                """, (user_id,))
                return cursor.fetchone()
            except Error as e:
                error=str(e)
                LOGGER.error(DB_GET_USER_ERROR).format(error=error)
                return None
    
    def get_user_info_tg(self, user_id: str):
        """Получает информацию о пользователе"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT * FROM users WHERE id_tg = ?
                """, (user_id,))
                return cursor.fetchone()
            except Error as e:
                error=str(e)
                LOGGER.error(DB_GET_USER_ERROR).format(error=error)
                return None
            
    def get_user_email(self, user_email: str):
        """Получает информацию о пользователе"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT * FROM users WHERE email = ?
                """, (user_email,))
                return cursor.fetchone()
            except Error as e:
                error=str(e)
                LOGGER.error(DB_GET_USER_ERROR).format(error=error)
                return None

    def get_users_with_time_zone(self):
        """Получает всех пользователей с их часовыми поясами из базы данных."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT id_tg, username_tg, position, time_zone
                    FROM users
                """)
                users = cursor.fetchall()
                return users  # Возвращаем список кортежей с данными пользователей
            except Error as e:
                error=str(e)
                LOGGER.error(DB_GET_USERS_TZ_ERROR).format(error=error)
                return []

    def get_random_user_by_position(self, position: str):
        """Получает случайного пользователя с указанной позицией"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT * FROM users WHERE position = ?
                """, (position,))
                users = cursor.fetchall()
                if users:
                    return random.choice(users)  # Возвращаем случайного пользователя
                else:
                    return None  # Если нет пользователей с такой позицией
            except Error as e:
                error=str(e)
                LOGGER.error(DB_RANDOM_USER_ERROR).format(error=error)
                return None

    def create_task(self, message_id: int, assigned_to: str):
        """Создает новую задачу"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO tasks 
                    (message_id, assigned_to, status, taken_at)
                    VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
                """, (message_id, assigned_to))
                self.conn.commit()
                return cursor.lastrowid
            except Error as e:
                error=str(e)
                LOGGER.error(DB_CREATE_TASK_ERROR).format(error=error)
                return None

    def update_task_status(self, task_id: int, status: str):
        """Обновляет статус задачи"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                if status == 'completed':
                    cursor.execute("""
                        UPDATE tasks 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, task_id))
                else:
                    cursor.execute("""
                        UPDATE tasks 
                        SET status = ?
                        WHERE id = ?
                    """, (status, task_id))
                self.conn.commit()
                return cursor.rowcount > 0
            except Error as e:
                error=str(e)
                LOGGER.error(DB_UPDATE_TASK_ERROR).format(error=error)
                return False
    
    def get_user_by_email(self, email: str):
        """Проверяет, существует ли пользователь с таким email"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT user_id, username, first_name, last_name, position, time_zone FROM users WHERE email = ?", (email,))
            return cursor.fetchone()
        except Error as e:
            error=str(e)
            LOGGER.error(DB_GET_USER_EMAIL_ERROR).format(error=error)
            return None

    def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            self.conn.close()
