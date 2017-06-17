import logging
import threading
import telegram
import random

from transitions.extensions import LockedMachine as Machine
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class FSM:
    states = ['init', 'started', 'asked', 'waiting', 'classifying', 'ending',
      'checking_answer', 'correct_answer', 'incorrect_answer']
    wait_messages = ["Why you're not answering? Am I bother you?(",
     "Please, answer to me.", "Why so silence?",
     "Please, answer to me. It gives me an energy to live"]

    CLASSIFY_ANSWER = 'a'
    CLASSIFY_QUESTION = 'q'
    CLASSIFY_REPLICA = 'r'
    WAIT_TIME = 10
    WAIT_TOO_LONG = 15

    def __init__(self, bot, user=None, chat=None):
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
        self.machine.add_transition('return_to_start', 'correct_answer', 'started', after='wait_for_user_typing')
        self.machine.add_transition('return_to_wait', 'incorrect_answer', 'waiting', after='say_user_about_long_waiting')

        self.machine.add_transition('answer_to_user_question', 'classifying', 'bot_answering_question')
        self.machine.add_transition('answer_to_user_replica', 'classifying', 'bot_answering_replica')

        self.machine.add_transition('long_wait', 'asked', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('too_long_wait', 'waiting', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('user_off', 'waiting', 'init', after='propose_conversation_ending')

        self._bot = bot
        self._user = user
        self._chat = chat
        self._too_long_waiting_cntr = 0
        self.__last_user_message = None
        self._threads = []

    def wait_for_user_typing(self):
        self._cancel_timer_threads()

        def _ask_question_if_user_inactive():
            if self.is_started():
                self.ask_question()

        t = threading.Timer(FSM.WAIT_TIME, _ask_question_if_user_inactive)
        t.start()
        self._threads.append(t)

    def ask_question_to_user(self):
        self._cancel_timer_threads()

        def _too_long_waiting_if_user_inactive():
            if self.is_asked():
                self.long_wait()
        self._bot.send_message(self._chat.id, "I'm working!! And asking you a question...")
        self._bot.send_message(self._chat.id, "How are you?")

        t = threading.Timer(FSM.WAIT_TOO_LONG, _too_long_waiting_if_user_inactive)
        t.start()
        self._threads.append(t)

    def say_user_about_long_waiting(self):
        self._cancel_timer_threads(presereve_cntr=True)

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
        self._cancel_timer_threads()

        self._bot.send_message(self._chat.id, ("I'm trying to classify your message"
                                               " to give correct answer"))
        keyboard = [
            [telegram.InlineKeyboardButton("Answer to my question", callback_data=FSM.CLASSIFY_ANSWER),
             telegram.InlineKeyboardButton("Question to me", callback_data=FSM.CLASSIFY_QUESTION),
             telegram.InlineKeyboardButton("Just chit-chatting", callback_data=FSM.CLASSIFY_REPLICA)]
        ]

        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        self._bot.send_message(
            chat_id=self._chat.id,
            text="Your last sentence \"{}\" was?".format(self._last_user_message),
            reply_markup=reply_markup
        )

    def classify_user_utterance(self, clf_type):
        self._cancel_timer_threads()

        if clf_type == FSM.CLASSIFY_ANSWER:
            self.check_user_answer()
        elif clf_type == FSM.CLASSIFY_QUESTION:
            self.answer_to_user_question()
            self._bot.send_message(chat_id=self._chat.id, text="42?")
        elif clf_type == FSM.CLASSIFY_REPLICA:
            self.answer_to_user_replica()
            self._bot.send_message(
                chat_id=self._chat.id,
                text="How are you, {}?".format(self._user.first_name)
            )

    def checking_user_answer(self):
        self._cancel_timer_threads()

        if self._last_user_message == 'Right answer':
            self._send_message("And its right answer!!!")
            self._send_message("You're very smart")
            self._send_message("Try to ask me something else or I will ask you")

            self.correct_user_answer()
            self.return_to_start()
        else:
            self._send_message("Ehh its incorrect(")
            self._send_message("{}, try again, please!".format(self._user.first_name))

            self.incorrect_user_answer()
            self.return_to_wait()

    def _send_message(self, text):
        self._bot.send_message(
            chat_id=self._chat.id,
            text=text
        )

    def _cancel_timer_threads(self, presereve_cntr=False):
        if not presereve_cntr:
            self._too_long_waiting_cntr = 0
        [t.cancel() for t in self._threads]

