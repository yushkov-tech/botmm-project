MATTERMOSTTIMEOUT = 20
MASSAGETIMEOUT = 10
USERTIMEOUT = 15
MESSAGE_QUEUE_MAXSIZE = 100 
RESPONSE_CHECK_TIMEOUT = 360
POLLING_INTERVAL = 10
ERROR_RETRY_INTERVAL = 15
MATTERMOST_POST_ID_LENGTH = 26
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@skbkontur.ru$'
MM_POST_URL_TEMPLATE = "{server_url}/kontur/pl/{post_id}"
MM_DIRECT_MESSAGE_URL_TEMPLATE = "https://chat.skbkontur.ru/kontur/messages/@{username}"
STAFF_PROFILE_URL_TEMPLATE = "https://staff.skbkontur.ru/profile/{username}"
HTTP_SUCCESS = 200
HTTP_CREATED = 201
MAX_REMINDERS = 3 
REMINDER_TIME = 7

WORK_TIME = {'start': 9, 'end': 18}


# Ошибки базы данных
DB_INIT_ERROR = "Database initialization error: {error}"
DB_ADD_MESSAGE_ERROR = "Error adding message: {error}"
DB_GET_MESSAGE_ERROR = "Error getting message: {error}"
DB_UPDATE_RESPONSE_ERROR = "Error updating message response: {error}"
DB_USER_UPDATE_ERROR = "Error adding/updating user: {error}"
DB_GET_USER_ERROR = "Error getting user info: {error}"
DB_GET_USERS_TZ_ERROR = "Error fetching users with time zone: {error}"
DB_RANDOM_USER_ERROR = "Error getting random user by position: {error}"
DB_CREATE_TASK_ERROR = "Error creating task: {error}"
DB_UPDATE_TASK_ERROR = "Error updating task status: {error}"
DB_GET_USER_EMAIL_ERROR = "Error getting user by email: {error}"

# Ошибки Mattermost
MM_POLL_ERROR = "Mattermost poll error: {error}"
MM_POLL_EXCEPTION = "Mattermost poll exception: {error}"
MM_SEND_ERROR = "Mattermost send error: {error}"
MM_USER_INFO_ERROR = "Ошибка получения информации о пользователе: {error}"

# Ошибки Telegram
TG_SEND_ERROR = "Ошибка отправки в Telegram: {error}"

# Общие ошибки
WEBHOOK_SERVER_ERROR = "Webhook server error: {error}"
FATAL_ERROR = "Fatal error: {error}"
SHUTDOWN_MESSAGE = "Shutting down..."

POSITION='Менеджер проектов по внедрению'