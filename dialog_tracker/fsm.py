import logging
import threading
import telegram
import random
import subprocess
import requests

from fuzzywuzzy import fuzz
from from_opennmt_chitchat.get_reply import normalize
from transitions.extensions import LockedMachine as Machine
from telegram.utils import request


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

logger_bot = logging.getLogger('bot')
bot_file_handler = logging.FileHandler("bot.log")
bot_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot_file_handler.setFormatter(bot_log_formatter)
if not logger_bot.handlers:
    logger_bot.addHandler(bot_file_handler)


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
    CLASSIFY_FB = 'cf'
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

        self.machine.add_transition('check_user_answer_on_asked', 'asked', 'checking_answer', after='checking_user_answer')
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
        self.machine.add_transition('answer_to_user_replica_with_fb', 'classifying', 'bot_answering_replica', after='answer_to_user_replica_with_fb_')

        self.machine.add_transition('long_wait', 'asked', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('too_long_wait', 'waiting', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('user_off', 'waiting', 'init', after='propose_conversation_ending')

        self._bot = bot
        self._user = user
        self._chat = chat
        self._text_and_qa = text_and_qa
        self._too_long_waiting_cntr = 0
        self.__last_user_message = None
        self._threads = []
        self._init_factoid_qas_and_text()
        self._dialog_context = []

    def _init_factoid_qas_and_text(self):
        self._factoid_qas = self._text_and_qa['qas']
        self._text = self._text_and_qa['text']

        self._question_asked = False
        self._qa_ind = -1

    def set_text_and_qa(self, text_and_qa):
        self._text_and_qa = text_and_qa
        self._init_factoid_qas_and_text()

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
        self._send_message(self._filter_seq2seq_output(self._factoid_qas[self._qa_ind]['question']))

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
                self._send_message(random.sample(FSM.wait_messages, 1)[0])
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

        self._send_message(("Seems you went to the real life."
                            "Type /start to replay."))

    def _classify(self, text):
        text = normalize(text)
        cmd = "echo \"{}\" | /fasttext/fasttext predict /src/data/fact_vs_fb_vs_os.bin -".format(text)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info(res)
        if self.is_asked():
            return FSM.CLASSIFY_ANSWER
        if res == '__label__0':
            return FSM.CLASSIFY_REPLICA
        elif res == '__label__1':
            return FSM.CLASSIFY_QUESTION
        elif res == '__label__2':
            return FSM.CLASSIFY_FB

    def get_klass_of_user_message(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        klass = self._classify(self._last_user_message)
        self._classify_user_utterance(klass)

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
        elif clf_type == FSM.CLASSIFY_FB:
            self.answer_to_user_replica_with_fb()

    def checking_user_answer(self):
        self._cancel_timer_threads(reset_question=False)

        true_answer = self._factoid_qas[self._qa_ind]['answer']
        sim = fuzz.ratio(true_answer, self._last_user_message)
        if sim == 100:
            self._send_message("And its right answer!!! You're very smart. Try to ask me something else or relax and wait my question 🌈")
            self.correct_user_answer()
            self.return_to_start()
        elif sim >= 90:
            self._send_message("I think you mean: \"{}\". If you really mean what I think then my congratulations! Try to ask me something else or relax and wait my question 🌈".format(true_answer))
            self.correct_user_answer()
            self.return_to_start()
        else:
            self._send_message("Ehh its incorrect. Hint: first 3 answer letters is \"{}\" ".format(true_answer[:3]))
            self.incorrect_user_answer()
            self.return_to_wait()

    def answer_to_user_question_(self):
        self._cancel_timer_threads()

        answer = self._filter_seq2seq_output(self._get_answer_to_factoid_question())
        self._send_message("My answer is: \"{}\"".format(answer))

    def _get_answer_to_factoid_question(self):
        out = subprocess.check_output(
            ["python3", "from_factoid_question_answerer/get_answer.py",
             "--paragraph", self._text, "--question", self._last_user_message])
        return str(out, "utf-8").strip()

    def answer_to_user_replica_(self):
        self._cancel_timer_threads(reset_seq2seq_context=False)
        bots_answer = self._get_opennmt_chitchat_reply()
        self._send_message(bots_answer)
        self.return_to_wait()

    def answer_to_user_replica_with_fb_(self):
        self._cancel_timer_threads(reset_seq2seq_context=False)
        bots_answer = self._get_opennmt_fb_reply()
        self._send_message(bots_answer)
        self.return_to_wait()

    def _get_last_bot_reply(self):
        if len(self._dialog_context):
            return self._dialog_context[-1][1]
        return ""

    def _get_opennmt_chitchat_reply(self):
        # feed_context = "{} {}".format(self._get_last_bot_reply(), self._last_user_message)
        feed_context = self._last_user_message

        logger.info("Send to opennmt chitchat: {}".format(feed_context))
        cmd = "echo \"{}\" | python from_opennmt_chitchat/get_reply.py tcp://opennmtchitchat:5556".format(feed_context)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from opennmt chitchat: {}".format(res))
        return res.split('\t')[1]

    def _get_opennmt_fb_reply(self):
        # feed_context = "{} {}".format(self._get_last_bot_reply(), self._last_user_message)
        feed_context = "{} _EOP_ {}".format(self._text, self._last_user_message)

        logger.info("Send to fb chitchat: {}".format(feed_context))
        cmd = "echo \"{}\" | python from_opennmt_chitchat/get_reply.py tcp://opennmtfb:5556".format(feed_context)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from fb chitchat: {}".format(res))
        return res.split('\t')[1]

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
        logger_bot.info("BOT[_send_message]: {}".format(text))

        self._bot.send_message(
            chat_id=self._chat.id,
            text=text,
            reply_markup=reply_markup
        )
        if self._last_user_message is None:
            self._last_user_message = ""
        self._dialog_context.append((self._last_user_message, text))

    def _cancel_timer_threads(self, presereve_cntr=False, reset_question=True, reset_seq2seq_context=True):
        if not presereve_cntr:
            self._too_long_waiting_cntr = 0

        if reset_question:
            self._question_asked = False

        [t.cancel() for t in self._threads]

    def _filter_seq2seq_output(self, s):
        s = "{}{}".format(s[0].upper(), s[1:])
        s = "'".join([w.strip() for w in s.split("'")])
        return s

    def clear_all(self):
        self._cancel_timer_threads()
