# Команды бота
BOT_COMMAND_START = "/start"
BOT_COMMAND_HELP = "/help"
BOT_COMMAND_INFO = "/info"
BOT_COMMAND_FAIR = "/yarmarka"

# Приветственные сообщения
WELCOME_MESSAGE = "Добро пожаловать! Я бот Валера.\nЯ помогу вам держать контакт между телеграмом и маттермостом."
HELP_MESSAGE = (
    "Доступные команды:\n"
    "/start - Начать взаимодействие с ботом\n"
    "/help - Получить список доступных команд\n"
    "/info - Получить информацию о боте\n"
    "/yarmarka - ЯРМАРКА!"
)

INFO_MESSAGE = (
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

# Кнопки и callback данные
BUTTON_INTRODUCE = "Познакомиться"
BUTTON_TAKE_WORK = "Взять в работу"
BUTTON_GO_TO_MM = "Перейти к сообщению в Mattermost"
BUTTON_GO_TO_DM = "Перейти к сообщению в лс Mattermost"
CALLBACK_INTRODUCE = "introduce"
CALLBACK_TAKE_WORK = "take_work"

# Email регистрация
EMAIL_PROMPT = "📧 Пожалуйста, ответьте на это сообщение вашей корпоративную почту:"
EMAIL_VALIDATION_ERROR = "❌ Пожалуйста, введите корректный email адрес(@skbkontur.ru)."
EMAIL_UPDATE_SUCCESS = "✅ Информация обновлена!\nEmail: {email}\nТеперь вы связаны с этим аккаунтом."
EMAIL_SAVE_SUCCESS = "✅ Отлично! Ваш email сохранен: {email}\n"
EMAIL_SAVE_ERROR = "❌ Ошибка при сохранении email."
EMAIL_UPDATE_ERROR = "❌ Ошибка при обновлении информации."

# Часовой пояс
TIMEZONE_PROMPT = "🌏 Пожалуйста, ответьте на это сообщение вашим часовым поясом (Мск/Екб)"
TIMEZONE_SAVE_SUCCESS = "✅ Ваш часовой пояс сохранен: {time_zone}\n"
TIMEZONE_SAVE_ERROR = "❌ Ошибка при обновлении часового пояса."
USER_NOT_FOUND_ERROR = "❌ Пользователь не найден в базе данных."

# Новые сообщения
MESSAGE_TEMPLATE = (
    "{status}\n\n"
    "От: {position}:<a href='{profile_url}'><b> {first_name} {last_name}</b></a>\n\n"
    "Сообщение: {message}\n"
)

NEW_MESSAGE = ("🚨 Новое сообщение! 🚨")
REMINDER_MESSAGE = ("🔔 *Напоминание #{reminder_number}*")
NO_RESPONSE_MESSAGE= ("⚠️ Никто не ответил на обращение ⚠️\n\n")


ATTENTION_PREFIX = "Внимание: "

# Ответы и подтверждения
RESPONSE_SENT_CONFIRMATION = "Ваш ответ отправлен в Mattermost!"
TASK_TAKEN_CONFIRMATION = "Задача взята в работу, исполнитель {user_name}"
TASK_GIVEN_AWAY_CONFIRMATION = "Задача вновь ищет исполнителя"

# Информация о пользователях
SPECIALIST_INFO_TEMPLATE = (
    "Случайный специалист по внедрению:\n"
    "Имя: {first_name}\n"
    "Фамилия: {last_name}\n"
    "Email: {email}\n"
    "Telegram: {telegram}"
)
NO_SPECIALISTS_ERROR = "❌ Нет специалистов по внедрению."

FAIR_GIF_URL = "https://i.pinimg.com/originals/7d/a9/f0/7da9f09c8b61866d87a5c0db8e4957db.gif"
