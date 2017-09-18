from flask import Flask, jsonify
from data_preparation import normalize_words_in_text

# NOTE: Ugly hack, because pytorch can load only this way
from models import DialogModel as Model
dialog_model = Model.load('data/models/dialog/model_28.pytorch')

from models import UtteranceModel as Model
utterance_model = Model.load('data/models/sentence/model_56.pytorch')

print(dialog_model)
print(utterance_model)


app = Flask(__name__)


@app.route('/dialog_quality')
def dialog_quality():
    return jsonify(message='ok dialog', quality=0)


@app.route('/utterance_quality')
def utterance_quality():
    return jsonify(message='ok utterance', quality=0)


def convert_to_dialog_quality_format(data, user_bot_ix):
    sents = [('<SOD>', ['<SOD>'])]
    for row in data['thread']:
        normalized = normalize_words_in_text(row['text'])
        sents.append((row['userId'], normalized))
    return make_vectored_dialogs(sents, word_ix, user_bot_ix)


if __name__ == '__main__':
    app.run(debug=True)
