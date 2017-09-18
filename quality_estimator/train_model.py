import pickle
import torch
import torch.nn as nn
from torch.autograd import Variable
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score
from collections import Counter
from models import DialogModel


def load_dialogs_and_labels(filename):
    with open(filename, 'rb') as f:
        X_train, X_test, y_train, y_test = pickle.load(f)

    # X_train = X_train[:100]
    # X_test = X_test[:100]
    # y_train = y_train[:100]
    # y_test = y_test[:100]

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


def measure_model_quality(model, loss_function, X_test, y_test, prev_best_f1=0):
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
    f1 = f1_score(y_test, y_pred, average='weighted')
    print("Test F1: {}".format(f1))

    print(classification_report(y_test, y_pred))

    if f1 >= prev_best_f1:
        prev_best_f1 = f1
        model.save()

    return prev_best_f1


def main():
    X_train, X_test, y_train, y_test = load_dialogs_and_labels('data/dialogs_and_labels.pickle')

    y_train = Variable(torch.LongTensor(y_train))

    model = DialogModel()
    loss_function = nn.NLLLoss()
    optimizer = torch.optim.Adam(model.parameters())
    prev_best_f1 = 0

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

        prev_best_f1 = measure_model_quality(model, loss_function, X_test, y_test, prev_best_f1)


if __name__ == '__main__':
    main()
