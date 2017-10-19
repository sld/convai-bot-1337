import csv
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

def main(filename):
    with open(filename, 'r') as f:
        row = list(csv.DictReader(f, delimiter=';'))[0]

    sorted_items = sorted(row.items(), key=lambda x: x[1])
    top3 = reversed(sorted_items[-4:-1])
    for k, v in top3:
        print("{}\t{}\t{}".format(topic_map[k], k, v))

if __name__ == '__main__':
    main(argv[1])
