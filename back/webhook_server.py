from flask import Flask, request, jsonify
import time
from threading import Event

from back.database import *

from back.message_processor import *
from back.config import *

from massage_varibles import *
from varibles import *

class WebhookServer:
    """Сервер для обработки вебхуков"""
    def __init__(self, config: Config, processor: MessageProcessor):
        self.app = Flask(__name__)
        self.config = config
        self.processor = processor
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.route('/mattermost_webhook', methods=['POST'])
        def webhook():
            data = request.json
            if data:
                post = data.get('post', {})
                if post and post.get('user_id') != self.config.bot_user_id:
                    self.processor.process_message(
                        post['message'],
                        data['channel_id'],
                        post['id'],
                        post['user_id']
                    )
            return jsonify({'status': 'ok'})
    
    def run(self, stop_event: Event):
        """Запускает сервер"""
        while not stop_event.is_set():
            try:
                self.app.run(port=5000, threaded=True)
            except Exception as e:
                error=str(e)
                LOGGER.error(WEBHOOK_SERVER_ERROR)
                time.sleep(5)
