import logging
import threading
import telegram
import random
import subprocess
import requests

from fuzzywuzzy import fuzz
from transitions.extensions import LockedMachine as Machine
from telegram.utils import request


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class FSM:
    states = [
      'init', 'started', 'asked', 'waiting', 'classifying', 'ending', 'checking_answer',
      'correct_answer', 'incorrect_answer', 'bot_answering_question', 'bot_answering_replica',
      'bot_correct_answer', 'bot_incorrect_answer'
    ]
    wait_messages = ["Why you're not speaking? Am I bother you? {}".format(telegram.Emoji.FACE_WITH_COLD_SWEAT),
     "Please, speak with me.", "Why you're not typing anything?",
     "Please, speak with me. It gives me energy to live"]

    CLASSIFY_ANSWER = 'ca'
    CLASSIFY_QUESTION = 'cq'
    CLASSIFY_REPLICA = 'cr'
    ANSWER_CORRECT = 'ac'
    ANSWER_INCORRECT = 'ai'

    WAIT_TIME = 45
    WAIT_TOO_LONG = 120

    def __init__(self, bot, user=None, chat=None, text_and_qa=None):
        self.machine = Machine(model=self, states=FSM.states, initial='init')

        self.machine.add_transition('start', 'init', 'started', after='wait_for_user_typing')
        self.machine.add_transition('ask_question', 'started', 'asked', after='ask_question_to_user')

        self.machine.add_transition('classify', 'started', 'classifying', after='get_klass_of_user_message')
        self.machine.add_transition('classify', 'asked', 'classifying', after='get_klass_of_user_message')
        self.machine.add_transition('classify', 'waiting', 'classifying', after='get_klass_of_user_message')
        self.machine.add_transition('classify', 'classifying', 'classifying', after='get_klass_of_user_message')

        self.machine.add_transition('check_user_answer', 'classifying', 'checking_answer', after='checking_user_answer')
        self.machine.add_transition('correct_user_answer', 'checking_answer', 'correct_answer')
        self.machine.add_transition('incorrect_user_answer', 'checking_answer', 'incorrect_answer')
        self.machine.add_transition('return_to_start', '*', 'started', after='wait_for_user_typing')
        self.machine.add_transition('return_to_wait', '*', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('return_to_init', '*', 'init', after='clear_all')

        self.machine.add_transition('answer_to_user_question', 'classifying', 'bot_answering_question', after='answer_to_user_question_')
        self.machine.add_transition('classify', 'bot_answering_question', 'classifying', after='get_klass_of_user_message')
        self.machine.add_transition('answer_to_user_question_correct', 'bot_answering_question', 'bot_correct_answer')
        self.machine.add_transition('answer_to_user_question_incorrect', 'bot_answering_question', 'bot_incorrect_answer')

        self.machine.add_transition('answer_to_user_replica', 'classifying', 'bot_answering_replica', after='answer_to_user_replica_')

        self.machine.add_transition('long_wait', 'asked', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('too_long_wait', 'waiting', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('user_off', 'waiting', 'init', after='propose_conversation_ending')

        self._bot = bot
        self._user = user
        self._chat = chat
        self._text_and_qa = text_and_qa
        self._text = self._text_and_qa['text']
        self._too_long_waiting_cntr = 0
        self.__last_user_message = None
        self._threads = []
        self._init_factoid_qas()
        self._seq2seq_context = []

    def _init_factoid_qas(self):
        self._factoid_qas = self._text_and_qa['qas']

        self._question_asked = False
        self._qa_ind = -1

    def wait_for_user_typing(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        def _ask_question_if_user_inactive():
            if self.is_started():
                self.ask_question()

        t = threading.Timer(FSM.WAIT_TIME, _ask_question_if_user_inactive)
        t.start()
        self._threads.append(t)

    def ask_question_to_user(self):
        self._cancel_timer_threads(reset_question=False)

        def _too_long_waiting_if_user_inactive():
            if self.is_asked():
                self.long_wait()
        self._get_factoid_question()
        self._bot.send_message(self._chat.id, self._filter_seq2seq_output(self._factoid_qas[self._qa_ind]['question']))

        t = threading.Timer(FSM.WAIT_TOO_LONG, _too_long_waiting_if_user_inactive)
        t.start()
        self._threads.append(t)

    def _get_factoid_question(self):
        self._question_asked = True
        self._qa_ind = (self._qa_ind + 1) % len(self._factoid_qas)

    def say_user_about_long_waiting(self):
        self._cancel_timer_threads(reset_question=False, presereve_cntr=True, reset_seq2seq_context=False)

        def _too_long_waiting_if_user_inactive():
            if self.is_waiting() and self._too_long_waiting_cntr < 4:
                self._bot.send_message(self._chat.id, random.sample(FSM.wait_messages, 1)[0])
                self.too_long_wait()
            elif self.is_waiting() and self._too_long_waiting_cntr > 3:
                self.user_off()
                self._too_long_waiting_cntr = 0
            else:
                self._too_long_waiting_cntr = 0

        self._too_long_waiting_cntr += 1

        t = threading.Timer(FSM.WAIT_TOO_LONG, _too_long_waiting_if_user_inactive)
        t.start()
        self._threads.append(t)

    def propose_conversation_ending(self):
        self._cancel_timer_threads()

        self._bot.send_message(self._chat.id, ("Seems you went to the real life."
                                               "Type /start to replay."))

    def get_klass_of_user_message(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        self._bot.send_message(self._chat.id, ("Help me to understand the type of your sentence."))
        keyboard = [
            [telegram.InlineKeyboardButton("Factoid question to me", callback_data=FSM.CLASSIFY_QUESTION),
             telegram.InlineKeyboardButton("Chit-chat", callback_data=FSM.CLASSIFY_REPLICA),
             telegram.InlineKeyboardButton("Answer to my factoid question", callback_data=FSM.CLASSIFY_ANSWER)]
        ]

        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        self._bot.send_message(
            chat_id=self._chat.id,
            text="Your last sentence \"{}\" was?".format(self._last_user_message),
            reply_markup=reply_markup
        )

    def _classify_user_utterance(self, clf_type):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        if clf_type == FSM.CLASSIFY_ANSWER and self._question_asked:
            self.check_user_answer()
        elif clf_type == FSM.CLASSIFY_ANSWER and not self._question_asked:
            self._send_message(("I did not ask you a question. Then why do you think"
                " it has the answer type? My last sentence is a rhetorical question 😋"))
            self.return_to_start()
        elif clf_type == FSM.CLASSIFY_QUESTION:
            self.answer_to_user_question()
        elif clf_type == FSM.CLASSIFY_REPLICA:
            self.answer_to_user_replica()

    def checking_user_answer(self):
        self._cancel_timer_threads(reset_question=False)

        true_answer = self._factoid_qas[self._qa_ind]['answer']
        sim = fuzz.ratio(true_answer, self._last_user_message)
        if sim == 100:
            self._send_message("And its right answer!!!")
            self._send_message("You're very smart {}".format(telegram.Emoji.GRADUATION_CAP))
            self._send_message("Try to ask me something else or relax and wait my question 🌈")

            self.correct_user_answer()
            self.return_to_start()
        elif sim >= 90:
            self._send_message("I think you mean: \"{}\"".format(true_answer))
            self._send_message("If you really mean what I think then my congratulations!")
            self._send_message("Try to ask me something else or relax and wait my question 🌈")

            self.correct_user_answer()
            self.return_to_start()
        else:
            self._send_message("Ehh its incorrect {}".format(telegram.Emoji.DISAPPOINTED_BUT_RELIEVED_FACE))
            self._send_message("Hint: first 3 answer letters {}".format(true_answer[:3]))
            self._send_message("{}, try again, please!".format(self._user.first_name))

            self.incorrect_user_answer()
            self.return_to_wait()

    def answer_to_user_question_(self):
        self._cancel_timer_threads()

        keyboard = [
            [telegram.InlineKeyboardButton("Correct", callback_data=FSM.ANSWER_CORRECT),
             telegram.InlineKeyboardButton("Incorrect", callback_data=FSM.ANSWER_INCORRECT)]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        answer = self._filter_seq2seq_output(self._get_answer_to_factoid_question())
        self._send_message("My answer is: \"{}\"".format(answer), reply_markup=reply_markup)

    def _get_answer_to_factoid_question(self):
        out = subprocess.check_output(
            ["python3", "from_factoid_question_answerer/get_answer.py",
             "--paragraph", self._text, "--question", self._last_user_message])
        return str(out, "utf-8").strip()

    def answer_to_user_replica_(self):
        self._cancel_timer_threads(reset_seq2seq_context=False)
        self._seq2seq_context.append(self._last_user_message)
        bots_answer = self._get_seq2seq_reply()
        self._seq2seq_context.append(bots_answer)
        self._send_message(bots_answer)
        self.return_to_wait()

    def _get_seq2seq_reply(self):
        words = [word for word in self._last_user_message.split(' ')]
        context = " ".join(words[-29:])
        r = requests.get(
            'http://tf_chatbot:5000/reply',
            params={'context': context}
        )
        res = self._filter_seq2seq_output(r.json()[0]['dec_inp'])
        return res

    def go_from_choices(self, query_data):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        assert query_data[0] in ['c', 'a']

        if query_data[0] == 'c':
            self._classify_user_utterance(query_data)
        elif query_data[0] == 'a':
            self._classify_user_response_to_bot_answer(query_data)

    def _classify_user_response_to_bot_answer(self, clf_type):
        self._cancel_timer_threads()

        if clf_type == FSM.ANSWER_CORRECT:
            self.answer_to_user_question_correct()
            self._send_message("Hooray! I'm smart {}".format(telegram.Emoji.SMILING_FACE_WITH_SUNGLASSES))
        elif clf_type == FSM.ANSWER_INCORRECT:
            self.answer_to_user_question_incorrect()
            self._send_message(("Maybe 42? Sorry, I don't know the answer 🤔\n"
                                " I hope my master will make me smarter."))
        self.return_to_start()

    def _send_message(self, text, reply_markup=None):
        self._bot.send_message(
            chat_id=self._chat.id,
            text=text,
            reply_markup=reply_markup
        )

    def _cancel_timer_threads(self, presereve_cntr=False, reset_question=True, reset_seq2seq_context=True):
        if not presereve_cntr:
            self._too_long_waiting_cntr = 0

        if reset_question:
            self._question_asked = False

        if reset_seq2seq_context:
            self._seq2seq_context = []
        [t.cancel() for t in self._threads]

    def _filter_seq2seq_output(self, s):
        s = "{}{}".format(s[0].upper(), s[1:])
        s = "'".join([w.strip() for w in s.split("'")])
        return s

    def clear_all(self):
        self._cancel_timer_threads()
