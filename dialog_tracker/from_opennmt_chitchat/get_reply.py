# -*- coding: utf-8 -*-
import zmq, sys, json
from signal import signal, SIGPIPE, SIG_DFL


class ConnectionHandler:
    def __init__(self):
        signal(SIGPIPE, SIG_DFL)
        self.sock = zmq.Context().socket(zmq.REQ)
        self.sock.connect("tcp://opennmtchitchat:5556")

    def __call__(self, data):
        self.sock.send_string(json.dumps(data))
        recieved = json.loads(str(self.sock.recv(), "utf-8"), encoding='utf-8', strict=False)
        recieved = [(row[0]['tgt'], row[0]['pred_score'], row[0]['src']) for row in recieved]
        return recieved


if __name__ == '__main__':
    fin = sys.stdin
    data = [{"src": line} for line in fin]

    connect = ConnectionHandler()
    received = connect(data)

    for dst, score, src in sorted(received, key=lambda x: x[2], reverse=True):
        print("{}\t{}\t{}".format(src, dst, score))
