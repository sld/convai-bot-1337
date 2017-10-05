import logging
import threading
import telegram
import itertools
import random
import subprocess
import requests
import re
import config

from fuzzywuzzy import fuzz
from nltk import word_tokenize
from from_opennmt_chitchat.get_reply import normalize, detokenize
from transitions.extensions import LockedMachine as Machine
from telegram.utils import request


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

logger_bot = logging.getLogger('bot_revisited')
bot_file_handler = logging.FileHandler("bot_revisited.log")
bot_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot_file_handler.setFormatter(bot_log_formatter)
if not logger_bot.handlers:
    logger_bot.addHandler(bot_file_handler)


def combinate_and_return_answer(arr):
        messages_product = list(itertools.product(*arr))
        msg_arr = random.sample(messages_product, 1)[0]
        msg = detokenize(" ".join(msg_arr))
        return msg


# NOTE: Оставил тут, т.к. непонятно как добавлять в fsm.
# Может быть так, что юзер у нас что-то спросил, а мы его только поприветствовали
# Как бы это решить? В голову приходит только многопоточка и асинхронное программирование
def greet_user(bot, chat_id):
    hello_messages_1 = ['Well hello there!', 'How’s it going?', 'What’s up?',
                        'Yo!', 'Alright mate?', 'Whazzup?', 'Hiya!',
                        'Nice to see you!', 'Good to see you!']
    hello_messages_2 = ["Let's discuss this awesome text!",
        "I'm coming up with a question about the text...",
        "Would you mind to ask me some factual question about the text? Maybe I'll do it first..." ]

    greet_messages = [hello_messages_1, hello_messages_2]
    msg = combinate_and_return_answer(greet_messages)
    bot.send_message(chat_id=chat_id, text=msg)


class BotBrainRevisited:
    def __init__(self, bot, user=None, chat=None, text_and_qa=None):
        self._bot = bot
        self._user = user
        self._chat = chat
        self._text_and_qa = text_and_qa
        self._too_long_waiting_cntr = 0
        self._last_user_message = None
        self._threads = []
        self._init_factoid_qas_and_text()
        self._dialog_context = []
        self._is_first_incorrect = True
        # to prevent recursion call
        self._is_chitchat_replica_is_answer = False


    def reply(self, dialog_context, sentence, metadata):
        # if metadata is greet then greet
        # elif user is not reponding for a long time then common skill
        # else classify user utterance


    def get_klass_of_user_message(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        klass = self._classify(self._last_user_message)
        self._classify_user_utterance(klass)

    def _classify_user_utterance(self, clf_type):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        self._is_chitchat_replica_is_answer = False
        if clf_type == BotBrain.CLASSIFY_ANSWER and self._question_asked:
            self._is_chitchat_replica_is_answer = True
            self.check_user_answer()
        elif clf_type == BotBrain.CLASSIFY_ANSWER and not self._question_asked:
            self._send_message(("I did not ask you a question. Then why do you think"
                " it has the answer type? My last sentence is a rhetorical question 😋"))
            self.return_to_start()
        elif clf_type == BotBrain.CLASSIFY_QUESTION:
            self.answer_to_user_question()
        elif clf_type == BotBrain.CLASSIFY_REPLICA:
            self.answer_to_user_replica()
        elif clf_type == BotBrain.CLASSIFY_FB:
            self.answer_to_user_replica_with_fb()
        elif clf_type == BotBrain.CLASSIFY_ASK_QUESTION:
            self.ask_question_after_classifying()
