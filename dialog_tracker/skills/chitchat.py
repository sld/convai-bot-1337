import random
import subprocess
import logging
import re
import requests
from skills.utils import get_stopwords_count
from nltk import word_tokenize


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseChitChatSkill:
    ALICE_URL = 'http://alice:3000'

    def __init__(self, chitchat_url):
        self._chitchat_url = chitchat_url

    def predict(self, current_sentence, dialog_context):
        raise NotImplementedError

    def _get_best_response(self, tsv, is_bad_response):
        candidates = []
        for line in tsv.split('\n'):
            _, resp, score = line.split('\t')
            words_cnt = len(word_tokenize(resp))
            print(resp, words_cnt, get_stopwords_count(resp), is_bad_response)
            good_stopwords_ratio = get_stopwords_count(resp) / words_cnt <= 0.75
            is_good_response = words_cnt >= 1 and good_stopwords_ratio and not is_bad_response
            if is_good_response:
                candidates.append(resp)
        print('candidates:', candidates)
        if len(candidates) > 0:
            return random.choice(candidates)
        return None

    def _is_bad_resp(self, resp, current_sentence, dialog_context):
        if len(dialog_context) > 1:
            if (dialog_context[-2][1] == dialog_context[-1][1]):
                return True
            if (dialog_context[-1][1] == current_sentence):
                return True

        words = word_tokenize(resp)
        unique_words = set(words)
        if len(words) > 10 and len(unique_words) / len(words) < 0.5:
            return True

        if '<unk>' in resp or re.match('\w', resp) is None or ('youtube' in resp and 'www' in resp and 'watch' in resp):
            return True
        else:
            return False


class AliceChitChatSkill(BaseChitChatSkill):
    def predict(self, current_sentence, dialog_context, *args):
        return self._get_alice_reply(current_sentence, dialog_context)

    def _get_alice_reply(self, current_sentence, dialog_context):
        # TODO: remove it from here, use as argument, and move alice reply to other place
        alice_url = BaseChitChatSkill.ALICE_URL
        user_sentences = [e[0] for e in dialog_context]
        if dialog_context and dialog_context[-1][0] != current_sentence:
            user_sentences += [current_sentence]
        elif not dialog_context:
            user_sentences = [current_sentence]
        print("Alice input {}".format(user_sentences))
        url = alice_url + '/respond'
        r = requests.post(url, json={'sentences': user_sentences})
        print("Alice output: {}".format(r.json()))
        msg = r.json()['message']
        return msg


class OpenSubtitlesChitChatSkill(BaseChitChatSkill):
    def predict(self, current_sentence, dialog_context):
        bots_answer = self._get_opennmt_chitchat_reply(current_sentence, dialog_context)
        return bots_answer

    def _get_opennmt_chitchat_reply(self, current_sentence, dialog_context, with_heuristic=True):
        sentence_with_context = None
        user_sent = None
        if len(dialog_context) > 0:
            sentence_with_context = " _EOS_ ".join([dialog_context[-1][1], current_sentence])
            user_sent = " ".join([dialog_context[-1][0], current_sentence])

        to_echo = current_sentence
        if sentence_with_context:
            to_echo = "{}\n{}".format(to_echo, sentence_with_context)

        if user_sent:
            to_echo = "{}\n{}".format(to_echo, user_sent)

        logger.info("Send to opennmt chitchat: {}".format(to_echo))
        cmd = "echo \"{}\" | python from_opennmt_chitchat/get_reply.py {}".format(to_echo, self._chitchat_url)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from opennmt chitchat: {}".format(res))

        if with_heuristic:
            is_bad_response = self._is_bad_resp(res, current_sentence, dialog_context)
            return self._get_best_response(res, is_bad_response)
        else:
            return res


class FbChitChatSkill(BaseChitChatSkill):
    def predict(self, current_sentence, dialog_context, text):
        bots_answer = self._get_opennmt_fb_reply(current_sentence, dialog_context, text)
        return bots_answer

    def _get_opennmt_fb_reply(self, current_sentence, dialog_context, text, with_heuristic=True):
        # feed_context = "{} {}".format(self._get_last_bot_reply(), current_sentence)
        sentence = current_sentence
        sentence_with_context = None
        user_sent = None
        if len(dialog_context) > 0:
            sentence_with_context = " ".join([dialog_context[-1][1], current_sentence])
            user_sent = " ".join([dialog_context[-1][0], current_sentence])

        text_with_sent = "{} {}".format(text, current_sentence)
        to_echo = "{}\n{}".format(sentence, text_with_sent)
        if sentence_with_context:
            to_echo = "{}\n{}".format(to_echo, sentence_with_context)
        if user_sent:
            to_echo = "{}\n{}".format(to_echo, user_sent)

        logger.info("Send to fb chitchat: {}".format(to_echo))
        cmd = "echo \"{}\" | python from_opennmt_chitchat/get_reply.py {}".format(to_echo, self._chitchat_url)
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0]
        res = str(output, "utf-8").strip()
        logger.info("Got from fb chitchat: {}".format(res))

        if with_heuristic:
            is_bad_response = self._is_bad_resp(res, current_sentence, dialog_context)
            return self._get_best_response(res, is_bad_response)
        else:
            return res
