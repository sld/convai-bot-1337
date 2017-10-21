import csv
import random
from sys import argv


topic_map = {
    "topic_0": "Politics",
    "topic_1": "Country1",
    "topic_2": "Military",
    "topic_3": "Media",
    "topic_4": "Games",
    "topic_5": "Biology",
    "topic_6": "Transports (mechanics)",
    "topic_7": "Town (education)",
    "topic_8": "Sports",
    "topic_9": "Research",
    "topic_10": "Films",
    "topic_11": "Country3",
    "topic_12": "Business",
    "topic_13": "Nature (city)",
    "topic_14": "English",
    "noise_0": "Noise1",
    "noise_1": "Noise2",
    "noise_2": "Music"
}


def generate_response(topic_with_score, only_good):
    if only_good is True and not is_good_topic(topic_with_score):
        return ""

    topic = topic_map[topic_with_score[0]]
    responses = [
        "I like {}. And you?".format(topic),
        "{} it is so about me!".format(topic),
        "I guess this text about {}".format(topic),
        "Let's talk about {}".format(topic),
        "What do you think about {}?".format(topic)
    ]
    return random.sample(responses, k=1)[0]


def is_good_topic(topic_with_score):
    if topic_with_score[1] > 0.25:
        return True
    return False


def get_top3_topics(filename):
    with open(filename, 'r') as f:
        row = list(csv.DictReader(f, delimiter=';'))[0]

    sorted_items = sorted(row.items(), key=lambda x: x[1])
    top3 = list(reversed(sorted_items[-4:-1]))
    top3 = [(k, float(v)) for k, v in top3]
    return top3


def print_top3_scores(filename):
    top3 = get_top3_topics(filename)
    for k, v in top3:
        print("{}\t{}\t{}".format(topic_map[k], k, v))


def print_good_response(filename):
    top3 = get_top3_topics(filename)
    top1 = top3[0]
    print(generate_response(top1, True))


if __name__ == '__main__':
    mode = argv[1]
    filename = argv[2]
    if mode == 'top3_scores':
        print_top3_scores(filename)
    elif mode == 'good_response':
        print_good_response(filename)
