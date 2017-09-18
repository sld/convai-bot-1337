import requests
import json
from sys import argv


def dialog_quality_test(url):
    data = {
        'thread': [
            {'text': 'Hi!', 'userId': 'Bot'},
            {'text': 'Hey! How are you?', 'userId': 'Human'}
        ]
    }

    r = requests.get(url, json=data)
    assert r.json()['quality'] > 0


def utterance_quality_test(url):
    data = {
        'thread': [
            {'text': 'Hi!', 'userId': 'Bot'},
            {'text': 'Hey! How are you?', 'userId': 'Human'}
        ],
        'current': {'text': 'I am fine, thx.', 'userId': 'Bot'}
    }

    r = requests.get(url, json=data)
    assert r.json()['quality'] > 0


if __name__ == '__main__':
    base_url = argv[1]
    dialog_quality_test(base_url + 'dialog_quality')
    utterance_quality_test(base_url + 'dialog_quality')
