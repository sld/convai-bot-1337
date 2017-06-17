import logging
import threading
import telegram
import random

from transitions.extensions import LockedMachine as Machine
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class FSM:
    states = [
      'init', 'started', 'asked', 'waiting', 'classifying', 'ending', 'checking_answer',
      'correct_answer', 'incorrect_answer', 'bot_answering_question', 'bot_answering_replica',
      'bot_correct_answer', 'bot_incorrect_answer'
    ]
    wait_messages = ["Why you're not speaking? Am I bother you?(",
     "Please, speak with me.", "Why you're not typing anything?",
     "Please, speak with me. It gives me energy to live"]

    CLASSIFY_ANSWER = 'ca'
    CLASSIFY_QUESTION = 'cq'
    CLASSIFY_REPLICA = 'cr'
    ANSWER_CORRECT = 'ac'
    ANSWER_INCORRECT = 'ai'

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
        self.machine.add_transition('return_to_start', '*', 'started', after='wait_for_user_typing')
        self.machine.add_transition('return_to_wait', '*', 'waiting', after='say_user_about_long_waiting')

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

    def _classify_user_utterance(self, clf_type):
        self._cancel_timer_threads()

        if clf_type == FSM.CLASSIFY_ANSWER:
            self.check_user_answer()
        elif clf_type == FSM.CLASSIFY_QUESTION:
            self.answer_to_user_question()
        elif clf_type == FSM.CLASSIFY_REPLICA:
            self.answer_to_user_replica()

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

    def answer_to_user_question_(self):
        self._cancel_timer_threads()

        keyboard = [
            [telegram.InlineKeyboardButton("Correct", callback_data=FSM.ANSWER_CORRECT),
             telegram.InlineKeyboardButton("Incorrect", callback_data=FSM.ANSWER_INCORRECT)]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        if self._last_user_message == 'How are you?':
            ans = "I'm fine thanks!"
        else:
            ans = "43"
        self._send_message("My answer is: \"{}\"".format(ans), reply_markup=reply_markup)

    def answer_to_user_replica_(self):
        self._cancel_timer_threads()
        self._send_message("Blah blah blah...")
        self.return_to_wait()

    def go_from_choices(self, query_data):
        self._cancel_timer_threads()

        assert query_data[0] in ['c', 'a']

        if query_data[0] == 'c':
            self._classify_user_utterance(query_data)
        elif query_data[0] == 'a':
            self._classify_user_response_to_bot_answer(query_data)

    def _classify_user_response_to_bot_answer(self, clf_type):
        self._cancel_timer_threads()

        if clf_type == FSM.ANSWER_CORRECT:
            self.answer_to_user_question_correct()
            self._send_message("Hooray! I'm smart!")
        elif clf_type == FSM.ANSWER_INCORRECT:
            self.answer_to_user_question_incorrect()
            self._send_message(("Maybe 42? Sorry, I don't know the answer :(\n"
                                "I hope my master will make me smarter."))
        self.return_to_start()

    def _send_message(self, text, reply_markup=None):
        self._bot.send_message(
            chat_id=self._chat.id,
            text=text,
            reply_markup=reply_markup
        )

    def _cancel_timer_threads(self, presereve_cntr=False):
        if not presereve_cntr:
            self._too_long_waiting_cntr = 0
        [t.cancel() for t in self._threads]

