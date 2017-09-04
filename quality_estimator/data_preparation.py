import json
import pickle
from nltk import word_tokenize


def get_label(val):
    if val < 3:
        return 0
    elif val == 3:
        return 1
    elif val > 3:
        return 2


def preserve_good_data(dialogs):
    filtered = []
    for d in dialogs:
        eval1 = d['evaluation'][0]['quality']
        eval2 = d['evaluation'][1]['quality']
        if len(d['thread']) < 4 and (eval1 > 3 or eval2 > 3):
            pass
        elif d['users'][0]['userType'] == 'Human' and d['users'][1]['userType'] == 'Human':
            pass
        elif len(d['thread']) == 0:
            pass
        else:
            filtered.append(d)
    return filtered


def create_dataset(filtered):
    dialogs = []
    labels = []
    for d in filtered:
        context = d['context']
        user_replicas = []
        bot_replicas = []
        if d['users'][0]['userType'] == 'Human' and d['users'][1]['userType'] == 'Bot':
            user = d['users'][0]['id']
            bot = d['users'][1]['id']
        else:
            user = d['users'][1]['id']
            bot = d['users'][0]['id']

        if d['evaluation'][0]['userId'] == bot:
            label = get_label(d['evaluation'][0]['quality'])
        else:
            label = get_label(d['evaluation'][1]['quality'])

        dialog = [('<SOD>', ['<SOD>'])]
        for r in d['thread']:
            words = [w.lower() for w in word_tokenize(r['text'])]
            if r['userId'] == user:
                dialog.append(('user', words))
            else:
                dialog.append(('bot', words))
        dialog.append(('<EOD>', ['<EOD>']))
        dialogs.append(dialog)
        labels.append(label)
    return dialogs, labels


def make_word_ix(dialogs):
    word_ix = {}
    vocab = set()
    for d in dialogs:
        for sent in d:
            for w in sent[1]:
                vocab.add(w)
    ix = 0
    for w in vocab:
        word_ix[w] = ix
        ix += 1
    return word_ix


def make_vectored_dialogs(dialogs, word_ix, user_bot_ix):
    dialogs_vecs = []
    for d in dialogs:
        d_vecs = []
        for sent in d:
            sent_bot_ix = []
            sent_word_ix = []
            for w in sent[1]:
                sent_word_ix.append(word_ix[w])
                sent_bot_ix.append(user_bot_ix[sent[0]])
            if sent_bot_ix:
                sent_vec = [sent_word_ix, sent_bot_ix]
                d_vecs.append([sent_vec])
        dialogs_vecs.append(d_vecs)
    return dialogs_vecs


def main():
    with open("data/train_full.json") as f:
        dialogs = json.load(f)

    filtered = preserve_good_data(dialogs)

    dialogs, labels = create_dataset(filtered)

    user_bot_ix = {'user': 0, 'bot': 1, '<SOD>': 2, '<EOD>': 3}
    word_ix = make_word_ix(dialogs)

    dialogs_vectored = make_vectored_dialogs(dialogs, word_ix, user_bot_ix)

    with open('data/dilogs_and_labels.pickle', 'wb') as f:
        pickle.dump([dialogs_vectored, labels], f)


if __name__ == '__main__':
    main()

