import requests
import random
import threading


class BotBrain:
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

    # For examples of bot, user, chat look at dialog_tracker/api_wrappers/ dir
    # text_and_qa - dict(qas: array, text: string). Store text and q&as for text
    def __init__(self, bot, user=None, chat=None, text_and_qa=None):
        self._bot = bot
        self._user = user
        self._chat = chat
        self._text_and_qa = text_and_qa

        # When user is silent cntr and threads are being used
        self._too_long_waiting_cntr = 0
        self._threads = []

        self._last_user_message = None

        self._init_factoid_qas_and_text()
        self._dialog_context = []

        # For answer checking skill - it goes to hint mode if this is True
        self._is_first_incorrect = True
        # To prevent recursion call, need to figure out if we still need it
        self._is_chitchat_replica_is_answer = False

        self._setup_topics_info()

    def _init_factoid_qas_and_text(self):
        # list of all questions and answers
        self._factoid_qas = self._text_and_qa['qas']
        self._text = self._text_and_qa['text']

        self._question_asked = False
        # last asked factoid qas
        self._last_factoid_qas = None

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

    def _get_topics_response(self):
        return random.sample(self._best_additionals, k=1)[0]

    def start(self):
        self._cancel_timer_threads(presereve_cntr=False, reset_question=False, reset_seq2seq_context=False, reset_topic=False)

        def _ask_question_if_user_inactive():
            # If user not type after dialog start then ask question
            if not self._last_user_message:
                self.ask_question()

        t = threading.Timer(config.WAIT_TIME, _ask_question_if_user_inactive)
        t.start()
        self._threads.append(t)

    def ask_question():
        self._cancel_timer_threads(reset_question=False, presereve_cntr=True)

        def _too_long_waiting_if_user_inactive():
            if self.is_asked():
                self.long_wait()

        if self._get_factoid_question() is not None:
            self._send_message(self._filter_seq2seq_output(self._last_factoid_qas['question']))
        else:
            self._send_message(random.sample(BotBrain.wait_messages, 1)[0])
            self.return_to_wait()

        t = threading.Timer(config.WAIT_TOO_LONG, _too_long_waiting_if_user_inactive)
        t.start()
        self._threads.append(t)
