import torch
from torch.autograd import Variable

from flask import Flask, jsonify, request
from data_preparation import normalize_words_in_text, base_main, make_vectored_dialogs

from train_model import convert_to_torch_format, forward_pass
# NOTE: Ugly hack, because pytorch can load only this way
from models import DialogModel
dialog_model = DialogModel.load('data/models/dialog/model.pytorch')

from models import UtteranceModel as Model
utterance_model = Model.load('data/models/sentence/model_56.pytorch')


print(dialog_model)
print(utterance_model)


app = Flask(__name__)
user_bot_ix, current_ix, word_ix, _, _ = base_main()


@app.route('/dialog_quality')
def dialog_quality():
    data = request.json

    dialogs = convert_to_dialog_quality_format(data, word_ix, user_bot_ix)
    dialogs = convert_to_torch_format(dialogs)

    assert len(dialogs) == 1

    dialog = dialogs[0]
    print(dialog)
    out = forward_pass(dialog_model, dialog)
    _, top_i = out.data.topk(1)
    label = top_i[0][0]
    return jsonify(quality_label=label)


@app.route('/utterance_quality')
def utterance_quality():
    data = request.json

    sents = [('<SOD>', ['<SOD>'])]
    for row in data['thread']:
        normalized = normalize_words_in_text(row['text'])
        sents.append((row['userId'], normalized))

    sent_context = sents[-5:]
    cur_sent = normalize_words_in_text(data['current']['text'])
    cur_user = data['current']['userId']
    sent = (cur_user, cur_sent)

    sent_row = (sent_context, sent)
    print(sent_row)
    return jsonify(message='ok utterance', quality=0)


def convert_to_dialog_quality_format(data, word_ix, user_bot_ix):
    sents = [('<SOD>', ['<SOD>'])]
    for row in data['thread']:
        normalized = normalize_words_in_text(row['text'])
        sents.append((row['userId'], normalized))
    sents.append(('<EOD>', ['<EOD>']))
    print(sents)
    return make_vectored_dialogs([sents], word_ix, user_bot_ix)


def convert_to_utterance_quality_format(data, word_ix, user_bot_ix, cur_ix):
    pass


if __name__ == '__main__':
    app.run(debug=True)
