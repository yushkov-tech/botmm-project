MESSAGE_QUEUE_MAXSIZE = 100
RESPONSE_CHECK_TIMEOUT = 3600
MATTERMOST_POST_ID_LENGTH = 26
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@skbkontur.ru$'
MM_POST_URL_TEMPLATE = "{server_url}/kontur/pl/{post_id}"
MM_DIRECT_MESSAGE_URL_TEMPLATE = "https://chat.skbkontur.ru/kontur/messages/@{username}"
STAFF_PROFILE_URL_TEMPLATE = "https://staff.skbkontur.ru/profile/{username}"
HTTP_SUCCESS = 200
HTTP_CREATED = 201
MAX_REMINDERS = 3 
REMINDER_TIME = 7

WORK_TIME = {'start': 9, 'end': 16}


# Ошибки базы данных
DB_INIT_ERROR = "Ошибка инициализации базы данных: {error}"
DB_ADD_MESSAGE_ERROR = "Ошибка добавления сообщения: {error}"
DB_GET_MESSAGE_ERROR = "Ошибка получения сообщения: {error}"
DB_UPDATE_RESPONSE_ERROR = "Ошибка обновления ответа на сообщение: {error}"
DB_USER_UPDATE_ERROR = "Ошибка добавления/обновления пользователя: {error}"
DB_GET_USER_ERROR = "Ошибка получения информации о пользователе: {error}"
DB_GET_USERS_TZ_ERROR = "Ошибка получения пользователей с часовыми поясами: {error}"
DB_RANDOM_USER_ERROR = "Ошибка получения случайного пользователя по должности: {error}"
DB_CREATE_TASK_ERROR = "Ошибка создания задачи: {error}"
DB_UPDATE_TASK_ERROR = "Ошибка обновления статуса задачи: {error}"
DB_GET_USER_EMAIL_ERROR = "Ошибка получения пользователя по email: {error}"

# Ошибки Mattermost
MM_POLL_ERROR = "Ошибка поллинга Mattermost: {error}"
MM_POLL_EXCEPTION = "Исключение при поллинге Mattermost: {error}"
MM_SEND_ERROR = "Ошибка отправки в Mattermost: {error}"
MM_USER_INFO_ERROR = "Ошибка получения информации о пользователе: {error}"

# Ошибки Telegram
TG_SEND_ERROR = "Ошибка отправки в Telegram: {error}"

# Общие ошибки
WEBHOOK_SERVER_ERROR = "Ошибка вебхук сервера: {error}"
FATAL_ERROR = "Критическая ошибка: {error}"
SHUTDOWN_MESSAGE = "Завершение работы..."

POSITION = 'Менеджер проектов по внедрению'