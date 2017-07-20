import json
import logging
import requests
import os
from uuid import uuid4

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_URL = "https://ipavlov.mipt.ru/nipsrouter/F0690A4D-B999-46F0-AD14-C65C13F09C40"


class ConvApiBot:
    def send_message(self, chat_id, text, reply_markup=None):
        data = {'text': text, 'evaluation': 0}
        message = {'chat_id': chat_id, 'text': json.dumps(data)}

        res = requests.post(
            os.path.join(BOT_URL, 'sendMessage'),
            json=message,
            headers={'Content-Type': 'application/json'}
        )
        if res.status_code != 200:
            logger.warn(res.text)


class ConvUpdate:
    def __init__(self, message):
        print('DEBUG', message)
        text = message['message']['text']
        self.effective_chat = ConvChat(message['message']['chat']['id'])
        self.message = ConvMessage(message['message']['text'])
        self.effective_user = ConvUser()


class ConvChat:
    def __init__(self, id_):
        self.id = id_


class ConvMessage:
    def __init__(self, text):
        self.text = text


class ConvUser:
    def __init__(self):
        self.first_name = 'Anonym'
        self.id = str(uuid4())
