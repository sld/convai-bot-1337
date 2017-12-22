import itertools
import logging
import random
import re
import subprocess
import threading

import config
import requests
from skills.qa import QuestionAndAnswer
from from_opennmt_chitchat.get_reply import normalize, detokenize
from fuzzywuzzy import fuzz
from nltk import word_tokenize
from nltk.corpus import stopwords
from transitions.extensions import LockedMachine as Machine

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

logger_bot = logging.getLogger('bot')
bot_file_handler = logging.FileHandler("bot.log")
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
    # hello_messages_2 = ["Let's discuss this awesome text!",
    #     "I'm coming up with a question about the text...",
    #     "Would you mind to ask me some factual question about the text? Maybe I'll do it first..." ]
    hello_messages_2 = [""]

    greet_messages = [hello_messages_1, hello_messages_2]
    msg = combinate_and_return_answer(greet_messages)
    bot.send_message(chat_id=chat_id, text=msg)


class BotBrain:
    states = [
      'init', 'started', 'asked', 'waiting', 'classifying', 'ending', 'checking_answer',
      'correct_answer', 'incorrect_answer', 'bot_answering_question', 'bot_answering_replica',
      'bot_correct_answer', 'bot_incorrect_answer'
    ]
    wait_messages = [
        "What do you feel about the text?", "Do you like this text?",
        "Do you know familiar texts?", "Can you write similar text?",
        "Do you like to chat with me?", "Are you a scientist?",
        "What do you think about ConvAI competition?",
        "Do you like to be an assessor?",
        "What is your job?"
    ]

    CHITCHAT_URL = 'tcp://opennmtchitchat:5556'
    FB_CHITCHAT_URL = 'tcp://opennmtfbpost:5556'
    SUMMARIZER_URL = 'tcp://opennmtsummary:5556'
    BIGARTM_URL = 'http://bigartm:3000'

    CLASSIFY_ANSWER = 'ca'
    CLASSIFY_QUESTION = 'cq'
    CLASSIFY_REPLICA = 'cr'
    CLASSIFY_FB = 'cf'
    CLASSIFY_ASK_QUESTION = 'caq'
    CLASSIFY_ALICE = "calice"
    CLASSIFY_SUMMARY = "csummary"
    CLASSIFY_TOPIC = "ctopic"

    MESSAGE_CLASSIFIER_MODEL = "model_all_labels.ftz"

    ASK_QUESTION_ON_WAIT_PROB = 0.5
    MAX_WAIT_TURNS = 4


    def __init__(self, bot, user=None, chat=None, text_and_qa=None):
        self.machine = Machine(model=self, states=BotBrain.states, initial='init')

        # Start part
        self.machine.add_transition('start', 'init', 'started', after='wait_for_user_typing')
        self.machine.add_transition('start_convai', 'init', 'started', after='wait_for_user_typing_convai')

        # Universal states
        self.machine.add_transition('return_to_start', '*', 'started', after='wait_for_user_typing')
        self.machine.add_transition('return_to_wait', '*', 'waiting', after='say_user_about_long_waiting')
        self.machine.add_transition('return_to_init', '*', 'init', after='clear_all')

        # Classify user utterance part
        self.machine.add_transition('classify', '*', 'classifying', after='get_class_of_user_message')

        # Answer to user replica part - using different skills like fb, alice, q&a
        self.machine.add_transition('answer_to_user_question', 'classifying', 'bot_answering_question', after='answer_to_user_question_')
        self.machine.add_transition('answer_to_user_replica', 'classifying', 'bot_answering_replica', after='answer_to_user_replica_')
        self.machine.add_transition('answer_to_user_replica_with_fb', 'classifying', 'bot_answering_replica', after='answer_to_user_replica_with_fb_')
        self.machine.add_transition('answer_to_user_replica_with_alice', 'classifying', 'bot_answering_replica', after='answer_to_user_replica_with_alice_')
        self.machine.add_transition('answer_to_user_with_summary', 'classifying', 'bot_answering_replica', after='answer_to_user_with_summary_')
        self.machine.add_transition('answer_to_user_with_topic', 'classifying', 'bot_answering_replica', after='answer_to_user_with_topic_')

        # Too long wait part
        self.machine.add_transition('user_off', 'waiting', 'init', after='propose_conversation_ending')

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

        self._setup_topics_info()

    def _init_factoid_qas_and_text(self):
        # list of all questions and answers
        self._qa_skill = QuestionAndAnswer(self._text_and_qa['qas'], self._user)
        self._factoid_qas = self._text_and_qa['qas']
        self._text = self._text_and_qa['text']

        self._question_asked = False
        # last asked factoid qas
        self._last_factoid_qas = None

    def _get_topics_response(self):
        return random.sample(self._best_additionals, k=1)[0]

    def _setup_topics_info(self):
        def _send_additional():
            response = self._get_topics_response()
            print(["topic additinonal", response])
            self._send_message(response)

        if self._text:
            r = requests.post(BotBrain.BIGARTM_URL + '/respond', json={'text': self._text})
            self._topics_info = r.json()['result']
            print("Topics result: {}".format(self._topics_info))
            self._best_additionals = self._topics_info[0]['responses']

            self._topic_thread = threading.Timer(1, _send_additional)
            self._topic_thread.start()

    def set_text_and_qa(self, text_and_qa):
        self._text_and_qa = text_and_qa
        self._init_factoid_qas_and_text()
        self._setup_topics_info()

    def wait_for_user_typing(self):
        self._cancel_timer_threads(presereve_cntr=False, reset_question=False, reset_seq2seq_context=False, reset_topic=False)

        def _ask_question_if_user_inactive():
            if self.is_started():
                question = self._qa_skill.ask_question()
                self._post_process_and_send_skill_sent(question)
                self.return_to_wait()

        t = threading.Timer(config.WAIT_TIME, _ask_question_if_user_inactive)
        t.start()
        self._threads.append(t)

    def _post_process_and_send_skill_sent(self, sent):
        if sent is not None:
            self._send_message(self._filter_seq2seq_output(sent))
        else:
            self._send_message(random.sample(BotBrain.wait_messages, 1)[0])
            self.return_to_wait()

    def generate_suggestions(self):
        # Блин, нужен колоссальный рефакторинг, сделаем после 12 ноября
        # ЧТобы было так: for each skill: generate
        #
        # Waiting* - BotBrain.wait_messages, ask factoid question
        # ------------------------------------------------------------
        # greet_user - NOT possible, clf type required (BotBrain.ClassifyGreeting)
        #
        # _get_factoid_question (CLASSIFY_ASK_QUESTION, waiting)
        # checking_user_answer (CLASSIFY_ANSWER, is_asked)
        # _get_answer_to_factoid_question (answer_to_user_question_) (CLASSIFY_QUESTION)
        # _get_opennmt_fb_reply (answer_to_user_replica_with_fb_) (CLASSIFY_FB)
        # _get_opennmt_chitchat_reply (answer_to_user_replica_) (CLASSIFY_REPLICA)
        # _select_from_common_responses (_get_best_response) (BAD! or NOT? CLASSIFY_FB AND CLASSIFY_REPLICA)
        # _classify_user_response_to_bot_answer (ANSWER_CORRECT, ANSWER_INCORRECT)
        # ------------------------------------------------------------

        # При этом надо все таки знать какой ответ был бы при том или ином выборе!

        def process_tsv(tsv):
            payload = []
            for line in tsv.split('\n'):
                _, resp, score = line.split('\t')
                score = float(score)
                payload.append((resp, score))
            payload = sorted(payload, key=lambda x: x[1], reverse=True)[:3]
            return payload

        answer = None
        if self._last_factoid_qas and self._last_factoid_qas.get('answer'):
            answer = self._last_factoid_qas.get('answer')

        qa = self._qa_skill._last_factoid_qas

        class_to_string = {
            BotBrain.CLASSIFY_ASK_QUESTION: 'Factoid question',
            BotBrain.CLASSIFY_ANSWER: 'Answer to Factoid question',
            BotBrain.CLASSIFY_QUESTION: 'Factoid question from user',
            BotBrain.CLASSIFY_FB: 'Facebook seq2seq',
            BotBrain.CLASSIFY_REPLICA: 'OpenSubtitles seq2seq',
            BotBrain.CLASSIFY_ALICE: 'Alice',
            BotBrain.CLASSIFY_SUMMARY: 'Summary'
        }

        fb_replicas = process_tsv(self._get_opennmt_fb_reply(with_heuristic=False))
        opensubtitle_replicas = process_tsv(self._get_opennmt_chitchat_reply(with_heuristic=False))
        alice_replicas = [self._get_alice_reply()]
        summaries = self._get_summaries()

        result = [
            (class_to_string[BotBrain.CLASSIFY_ASK_QUESTION], [qa]),
            (class_to_string[BotBrain.CLASSIFY_ANSWER], [answer]),
            (class_to_string[BotBrain.CLASSIFY_QUESTION], [None]),
            (class_to_string[BotBrain.CLASSIFY_FB], fb_replicas),
            (class_to_string[BotBrain.CLASSIFY_REPLICA], opensubtitle_replicas),
            (class_to_string[BotBrain.CLASSIFY_ALICE], alice_replicas),
            (class_to_string[BotBrain.CLASSIFY_SUMMARY], [summaries]),
            ('Common Responses', [self._select_from_common_responses()]),
            ('Topic Modelling', self._topics_info)
        ]
        return result

    def _get_alice_reply(self):
        alice_url = 'http://alice:3000'
        user_sentences = [e[0] for e in self._dialog_context]
        if self._dialog_context and self._dialog_context[-1][0] != self._last_user_message:
            user_sentences += [self._last_user_message]
        elif not self._dialog_context:
            user_sentences = [self._last_user_message]
        print("Alice input {}".format(user_sentences))
        url = alice_url + '/respond'
        r = requests.post(url, json={'sentences': user_sentences})
        print("Alice output: {}".format(r.json()))
        msg = self._filter_seq2seq_output(r.json()['message'])
        return msg

    def say_user_about_long_waiting(self):
        self._cancel_timer_threads(reset_question=False, presereve_cntr=True, reset_seq2seq_context=False)

        def _too_long_waiting_if_user_inactive():
            if self.is_waiting() and self._too_long_waiting_cntr < BotBrain.MAX_WAIT_TURNS:
                if random.random() > BotBrain.ASK_QUESTION_ON_WAIT_PROB:
                    question = self._qa_skill.ask_question()
                    self._post_process_and_send_skill_sent(question)
                else:
                    self._send_message(random.sample(BotBrain.wait_messages, 1)[0])
                self.return_to_wait()
            elif self.is_waiting() and self._too_long_waiting_cntr > BotBrain.MAX_WAIT_TURNS:
                self.user_off()
                self._too_long_waiting_cntr = 0
            else:
                self._too_long_waiting_cntr = 0

        self._too_long_waiting_cntr += 1

        t = threading.Timer(config.WAIT_TOO_LONG, _too_long_waiting_if_user_inactive)
        t.start()
        self._threads.append(t)


    def propose_conversation_ending(self):
        self._cancel_timer_threads()

        self._send_message(("Seems you went to the real life."
                            "Type /start to replay."))

    def _classify(self, text):
        text = normalize(text)
        cmd = "echo \"{}\" | /fasttext/fasttext predict /src/data/{} -".format(text, BotBrain.MESSAGE_CLASSIFIER_MODEL)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info(res)

        intent = self._get_intent(text)
        if intent is not None:
            return intent

        if res == '__label__0':
            return BotBrain.CLASSIFY_REPLICA
        elif res == '__label__1':
            return BotBrain.CLASSIFY_QUESTION
        elif res == '__label__2':
            return BotBrain.CLASSIFY_FB
        elif res == '__label__3':
            return BotBrain.CLASSIFY_ANSWER
        elif res == '__label__4':
            return BotBrain.CLASSIFY_ALICE

    def get_class_of_user_message(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        message_class = self._classify(self._last_user_message)
        self._last_classify_label = message_class
        self._classify_user_utterance(message_class)

    def _classify_user_utterance(self, clf_type):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)

        if clf_type == BotBrain.CLASSIFY_ANSWER:
            msg = self._qa_skill.check_user_answer(self._last_user_message)
            self._post_process_and_send_skill_sent(msg)
            self.return_to_wait()
        elif clf_type == BotBrain.CLASSIFY_QUESTION:
            self.answer_to_user_question()
        elif clf_type == BotBrain.CLASSIFY_REPLICA:
            self.answer_to_user_replica()
        elif clf_type == BotBrain.CLASSIFY_FB:
            self.answer_to_user_replica_with_fb()
        elif clf_type == BotBrain.CLASSIFY_ASK_QUESTION:
            question = self._qa_skill.ask_question()
            self._post_process_and_send_skill_sent(question)
            self.return_to_wait()
        elif clf_type == BotBrain.CLASSIFY_ALICE:
            self.answer_to_user_replica_with_alice()
        elif clf_type == BotBrain.CLASSIFY_SUMMARY:
            self.answer_to_user_with_summary()
        elif clf_type == BotBrain.CLASSIFY_TOPIC:
            self.answer_to_user_with_topic()

    def answer_to_user_question_(self):
        self._cancel_timer_threads()

        answer = self._filter_seq2seq_output(self._get_answer_to_factoid_question())

        msg1 = ["I think that", "It seems that", "I'd like to say that"]
        msg2 = ["correct answer", "answer", "true answer"]
        msg3 = ["is: {}".format(detokenize(normalize(answer))).lower()]
        total_msg = [msg1, msg2, msg3]

        msg = combinate_and_return_answer(total_msg)

        self._send_message(msg)
        self.return_to_wait()

    def _get_answer_to_factoid_question(self):
        out = subprocess.check_output(
            ["python3", "from_factoid_question_answerer/get_answer.py",
             "--paragraph", self._text, "--question", self._last_user_message])
        return str(out, "utf-8").strip()

    def answer_to_user_replica_(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)
        bots_answer = self._get_opennmt_chitchat_reply()
        self._send_message(bots_answer)
        self.return_to_wait()

    def answer_to_user_replica_with_fb_(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)
        bots_answer = self._get_opennmt_fb_reply()
        self._send_message(bots_answer)
        self.return_to_wait()

    def answer_to_user_replica_with_alice_(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)
        bots_answer = self._get_alice_reply()
        self._send_message(bots_answer)
        self.return_to_wait()

    def answer_to_user_with_summary_(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)
        bots_answer = self._get_summaries()
        self._send_message(bots_answer)
        self.return_to_wait()

    def answer_to_user_with_topic_(self):
        self._cancel_timer_threads(reset_question=False, reset_seq2seq_context=False)
        bots_answer = self._get_topics_response()
        self._send_message(bots_answer)
        self.return_to_wait()

    def _get_last_bot_reply(self):
        if len(self._dialog_context):
            return self._dialog_context[-1][1]
        return ""

    def _get_opennmt_chitchat_reply(self, with_heuristic=True):
        # feed_context = "{} {}".format(self._get_last_bot_reply(), self._last_user_message)
        sentence = self._last_user_message
        sentence_with_context = None
        user_sent = None
        if len(self._dialog_context) > 0:
            sentence_with_context = " _EOS_ ".join([self._dialog_context[-1][1], self._last_user_message])
            user_sent = " ".join([self._dialog_context[-1][0], self._last_user_message])

        to_echo = sentence
        if sentence_with_context:
            to_echo = "{}\n{}".format(to_echo, sentence_with_context)

        if user_sent:
            to_echo = "{}\n{}".format(to_echo, user_sent)

        logger.info("Send to opennmt chitchat: {}".format(to_echo))
        cmd = "echo \"{}\" | python from_opennmt_chitchat/get_reply.py {}".format(to_echo, BotBrain.CHITCHAT_URL)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from opennmt chitchat: {}".format(res))

        if with_heuristic:
            return self._get_best_response(res)
        else:
            return res

    def _get_best_response(self, tsv):
        candidates = []
        for line in tsv.split('\n'):
            _, resp, score = line.split('\t')
            words_cnt = len(word_tokenize(resp))
            print(resp, words_cnt, self._get_stopwords_count(resp), self._is_bad_resp(resp))
            if words_cnt >= 1 and self._get_stopwords_count(resp) / words_cnt <= 0.75 and not self._is_bad_resp(resp):
                candidates.append(resp)
        print('candidates:', candidates)
        if len(candidates) > 0:
            return random.choice(candidates)
        return self._get_alice_reply()

    def _is_bad_resp(self, resp):
        if len(self._dialog_context) > 1:
            if (self._dialog_context[-2][1] == self._dialog_context[-1][1]):
                return True
            if (self._dialog_context[-1][1] == self._last_user_message):
                return True

        words = word_tokenize(resp)
        unique_words = set(words)
        if len(words) > 10 and len(unique_words) / len(words) < 0.5:
            return True

        if '<unk>' in resp or re.match('\w', resp) is None or ('youtube' in resp and 'www' in resp and 'watch' in resp):
            return True
        else:
            return False

    def _get_stopwords_count(self, resp):
        return len(list(filter(lambda x: x.lower() in stopwords.words('english'), word_tokenize(resp))))

    def _get_summaries(self, with_heuristic=True):
        text = self._text
        logger.info("Send to opennmt summary: {}".format(text))
        cmd = "echo \"{}\" | python from_opennmt_summary/get_reply.py {}".format(text, BotBrain.SUMMARIZER_URL)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from opennmt summary: {}".format(res))
        # now lets select one best response
        candidates = []
        for line in res.split('\n'):
            _, resp, score = line.split('\t')
            words_cnt = len(word_tokenize(resp))
            print(resp, words_cnt, self._get_stopwords_count(resp))
            if words_cnt >= 2 and self._get_stopwords_count(resp) / words_cnt < 0.5 and '<unk>' not in resp:
                candidates.append(resp)
        if len(candidates) > 0:
            summary = random.choice(candidates)
            msg1 = ['I think this', 'I suppose that this', 'Maybe this']
            msg2 = ['article', 'text', 'paragraph']
            msg3 = ['can be described as:', 'can be summarized as:', 'main idea is:', 'in a nutshell is:']
            msg4 = [summary]
            msg5 = ['.', '...', '?', '..?']
            msg = [msg1, msg2, msg3, msg4, msg5]
            return combinate_and_return_answer(msg)
        return self._get_alice_reply()


    def _select_from_common_responses(self):
        msg1 = ['Do you know what?', '', "I don't understand :(", '¯\_(ツ)_/¯']
        msg2 = ["I can't answer", "Its beyond my possibilities"]
        msg3 = [':(', '.', '!', ';(']
        msg4 = ["Let's talk about", "I would like to talk about", "I would like to discuss"]
        msg5 = ["movies", "politics", "news", "you", "myself", "cats", "..."]
        msg6 = ['.', '', '!', ':)']
        total_msg = [msg1, msg2, msg3, msg4, msg5, msg6]
        msg = combinate_and_return_answer(total_msg)
        return msg

    def _get_opennmt_fb_reply(self, with_heuristic=True):
        # feed_context = "{} {}".format(self._get_last_bot_reply(), self._last_user_message)
        sentence = self._last_user_message
        sentence_with_context = None
        user_sent = None
        if len(self._dialog_context) > 0:
            sentence_with_context = " ".join([self._dialog_context[-1][1], self._last_user_message])
            user_sent = " ".join([self._dialog_context[-1][0], self._last_user_message])

        text_with_sent = "{} {}".format(self._text, self._last_user_message)
        to_echo = "{}\n{}".format(sentence, text_with_sent)
        if sentence_with_context:
            to_echo = "{}\n{}".format(to_echo, sentence_with_context)
        if user_sent:
            to_echo = "{}\n{}".format(to_echo, user_sent)

        logger.info("Send to fb chitchat: {}".format(to_echo))
        cmd = "echo \"{}\" | python from_opennmt_chitchat/get_reply.py {}".format(to_echo, BotBrain.FB_CHITCHAT_URL)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from fb chitchat: {}".format(res))

        if with_heuristic:
            return self._get_best_response(res)
        else:
            return res

    def _get_intent(self, text):
        url = 'http://intent_classifier:3000/get_intent'
        r = requests.post(url, json={'text': text})

        intent = r.json()['intent']
        score = r.json()['score']

        if score and score > 0.85:
            return intent
        return None

    def _send_message(self, text, reply_markup=None):
        text = text.strip()
        logger_bot.info("BOT[_send_message]: {}".format(text))

        self._bot.send_message(
            chat_id=self._chat.id,
            text=text,
            reply_markup=reply_markup
        )
        if self._last_user_message is None:
            self._last_user_message = ""
        text = text.replace('"', " ").replace("`", " ").replace("'", " ")
        self._dialog_context.append((self._last_user_message, text))

    def _cancel_timer_threads(self, presereve_cntr=False, reset_question=True, reset_seq2seq_context=True, reset_topic=True):
        if not presereve_cntr:
            self._too_long_waiting_cntr = 0

        if reset_question:
            self._question_asked = False

        if reset_topic:
            self._topic_thread.cancel()

        [t.cancel() for t in self._threads]

    def _filter_seq2seq_output(self, s):
        s = normalize(str(s))
        s = detokenize(s)
        return s

    def clear_all(self):
        self._cancel_timer_threads(reset_topic=False)
