# coding: utf-8
import os, json
from datetime import datetime
from flask import Flask, request, render_template, jsonify
from random import random, choice

app = Flask(__name__)

#---------------------------
#   Load Model
#---------------------------
import tensorflow as tf
from lib import data_utils
from lib.config import params_setup
from lib.seq2seq_model_utils import create_model, get_predicted_sentence


class ChatBot(object):

    def __init__(self, args, debug=False):
        start_time = datetime.now()

        # flow ctrl
        self.args = args
        self.debug = debug
        self.fbm_processed = []
        gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=args.gpu_usage)
        self.sess = tf.InteractiveSession(config=tf.ConfigProto(gpu_options=gpu_options))

        # Create model and load parameters.
        self.args.batch_size = 1  # We decode one sentence at a time.
        self.model = create_model(self.sess, self.args)

        # Load vocabularies.
        self.vocab_path = os.path.join(self.args.data_dir, "vocab%d.in" % self.args.vocab_size)
        self.vocab, self.rev_vocab = data_utils.initialize_vocabulary(self.vocab_path)
        print("[ChatBot] model initialize, cost %i secs" % (datetime.now() - start_time).seconds)


    def gen_response(self, sent, max_cand=10):
        sent = " ".join([w.lower() for w in sent.split(' ') if w not in [' ']])
        # if self.debug: return sent
        raw = get_predicted_sentence(self.args, sent, self.vocab, self.rev_vocab, self.model, self.sess, debug=False)
        # find bests candidates
        cands = sorted(raw, key=lambda v: v['prob'], reverse=True)[:max_cand]
        return cands

@app.route('/reply', methods=['GET'])
def chat():
    context = request.args.get('context')
    if context is None:
        return jsonify({'message': 'Context cannot be empty'}), 400
    res = chatbot.gen_response(context, 5)
    return jsonify(res), 200


#---------------------------
#   Start Server
#---------------------------
if __name__ == '__main__':
    args = params_setup()
    chatbot = ChatBot(args, debug=False)
    app.run(host='0.0.0.0', debug=False)

