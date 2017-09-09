import pickle
import torch
import torch.nn as nn
from torch.autograd import Variable
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import Counter


class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

        # Bx50
        self.word_embeddings = nn.Embedding(10037, 50)
        # Bx10
        self.user_bot_embeddings = nn.Embedding(4, 10)
        self.rnn = nn.GRU(60, 128, 1)
        self.linear = nn.Linear(128, 3)
        self.softmax = nn.LogSoftmax()

        self.hidden = self.init_hidden()

    def init_hidden(self):
        return Variable(torch.zeros(1, 1, 128))

    # input => Bx2xN, B - sentence len
    def forward(self, input, calc_softmax=False):
        word_emb = self.word_embeddings(input[:, 0, :])
        user_bot_emb = self.user_bot_embeddings(input[:, 1, :])
        input_combined = torch.cat((word_emb, user_bot_emb), 2)
        input_combined = input_combined.view(input_combined.size()[1], 1, input_combined.size()[-1])

        rnn_out, self.hidden = self.rnn(input_combined, self.hidden)
        output = self.linear(self.hidden).view(1, 3)

        if calc_softmax:
            probs = self.softmax(output)
            return self.hidden, probs
        else:
            return self.hidden, output


def load_dialogs_and_labels(filename):
    with open(filename, 'rb') as f:
        X_train, X_test, y_train, y_test = pickle.load(f)

    train_dialogs = []
    test_dialogs = []
    for dialog_vec in X_train:
        dialog = []
        for sent_vec in dialog_vec:
            dialog.append(torch.LongTensor(sent_vec).view(1, 2, -1))
        train_dialogs.append(dialog)

    for dialog_vec in X_test:
        dialog = []
        for sent_vec in dialog_vec:
            dialog.append(torch.LongTensor(sent_vec).view(1, 2, -1))
        test_dialogs.append(dialog)

    return train_dialogs, test_dialogs, y_train, y_test


def load_sent_labels(filename):
    with open(filename, 'rb') as f:
        labels = pickle.load(f)

    return labels


def measure_model_quality(model, loss_function, X_test, y_test):
    avg_loss = 0
    y_pred = []
    y_test_for_loss = Variable(torch.LongTensor(y_test))
    for ind, dialog in tqdm(enumerate(X_test)):
        model.zero_grad()
        model.hidden = model.init_hidden()
        for sent in dialog[:-1]:
            input = Variable(torch.LongTensor(sent))
            hidden, out = model(input)
        input = Variable(torch.LongTensor(dialog[-1]))
        hidden, out = model(input, True)

        top_n, top_i = out.data.topk(1)
        y_pred.append(top_i[0][0])

        loss = loss_function(out, y_test_for_loss[ind])

        avg_loss += loss.data[0]
    avg_loss = avg_loss / len(X_test)
    print("Test loss: {}".format(avg_loss))

    print(classification_report(y_test, y_pred))


def main():
    X_train, X_test, y_train, y_test = load_dialogs_and_labels('data/dilogs_and_labels.pickle')

    y_train = Variable(torch.LongTensor(y_train))

    model = Model()
    loss_function = nn.NLLLoss()
    optimizer = torch.optim.Adam(model.parameters())

    for epoch in range(10):
        avg_loss = 0
        for ind, dialog in tqdm(enumerate(X_train)):
            model.zero_grad()
            model.hidden = model.init_hidden()

            for j, sent in enumerate(dialog[:-1]):
                model.zero_grad()
                input = Variable(torch.LongTensor(sent))
                hidden, out = model(input)

            input = Variable(torch.LongTensor(dialog[-1]))
            hidden, out = model(input, True)

            loss = loss_function(out, y_train[ind])
            avg_loss += loss.data[0]
            loss.backward()
            optimizer.step()
        print("Loss: {}".format(avg_loss / len(X_train)))

        measure_model_quality(model, loss_function, X_test, y_test)


if __name__ == '__main__':
    main()
