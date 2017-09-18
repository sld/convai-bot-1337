import pickle
import torch
import torch.utils.data
import torch.nn as nn
from torch.autograd import Variable
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score
from collections import Counter


class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()
        # Bx50
        self.word_embeddings = nn.Embedding(11000, 50, padding_idx=0)
        # Bx10
        self.user_bot_embeddings = nn.Embedding(5, 10, padding_idx=0)
        self.cur_embeddings = nn.Embedding(3, 10, padding_idx=0)
        self.rnn = nn.GRU(70, 128, 1, batch_first=True)
        self.linear = nn.Linear(128, 3)
        self.softmax = nn.LogSoftmax()

    def init_hidden(self, batch_size):
        return Variable(torch.zeros(50, batch_size, 128))

    # input => Bx2xN, B - sentence len
    def forward(self, input, calc_softmax=False):
        word_emb = self.word_embeddings(input[:, 0, :])
        user_bot_emb = self.user_bot_embeddings(input[:, 1, :])
        cur_emb = self.cur_embeddings(input[:, 2, :])

        input_combined = torch.cat((word_emb, user_bot_emb, cur_emb), 2)

        rnn_out, self.hidden = self.rnn(input_combined, self.hidden)
        output = self.linear(self.hidden).view(-1, 3)

        if calc_softmax:
            probs = self.softmax(output)
            return self.hidden, probs
        else:
            return self.hidden, output

    def save(self, path='data/models/sentence/model.pytorch'):
        torch.save(self, path)
        return True

    @staticmethod
    def load(self, path='data/models/sentence/model.pytorch'):
        return torch.load(path)


def load_dialogs_and_labels(filename):
    with open(filename, 'rb') as f:
        X_train, X_test, y_train, y_test = pickle.load(f)

    # X_train = X_train[:100]
    # X_test = X_test[:100]
    # y_train = y_train[:100]
    # y_test = y_test[:100]

    X_train = torch.LongTensor(X_train)
    y_train = torch.LongTensor(y_train)
    train_dataset = torch.utils.data.TensorDataset(X_train, y_train)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=16, shuffle=True)

    X_test = torch.LongTensor(X_test)
    y_test = torch.LongTensor(y_test)
    test_dataset = torch.utils.data.TensorDataset(X_test, y_test)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=16)

    return train_loader, test_loader


def load_sent_labels(filename):
    with open(filename, 'rb') as f:
        labels = pickle.load(f)

    return labels


def measure_model_quality(model, loss_function, test_loader, prev_best_f1=0):
    avg_loss = 0
    y_pred = []
    for batch_idx, (data, target) in tqdm(enumerate(test_loader)):
        data, target = Variable(data), Variable(target)
        model.zero_grad()
        model.hidden = model.init_hidden(target.size()[0])
        hidden, out = model(data, True)
        loss = loss_function(out, target)
        avg_loss += loss.data[0]

        top_n, top_i = out.data.topk(1)
        y_pred += top_i.resize_(top_i.size()[0]).tolist()

    print("Test loss: {}".format(avg_loss / len(test_loader.dataset)))
    f1 = f1_score(y_test, y_pred, average='weighted')
    print("Test F1: {}".format(f1))

    y_test = test_loader.dataset.target_tensor.tolist()
    print(classification_report(y_test, y_pred))

    if f1 >= prev_best_f1:
        prev_best_f1 = f1
        model.save()

    return prev_best_f1


def main():
    train_loader, test_loader = load_dialogs_and_labels('data/sent_data.pickle')

    model = Model()
    loss_function = nn.NLLLoss()
    optimizer = torch.optim.Adam(model.parameters())
    prev_best_f1 = 0
    for epoch in range(10):
        avg_loss = 0
        for batch_idx, (data, target) in tqdm(enumerate(train_loader)):
            data, target = Variable(data), Variable(target)
            model.zero_grad()
            model.hidden = model.init_hidden(target.size()[0])
            hidden, out = model(data, True)

            loss = loss_function(out, target)
            avg_loss += loss.data[0]
            loss.backward()
            optimizer.step()
        print("Loss: {}".format(avg_loss / len(train_loader.dataset)))

        prev_best_f1 = measure_model_quality(model, loss_function, test_loader, prev_best_f1)


if __name__ == '__main__':
    main()
