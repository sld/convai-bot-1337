from intent_classifier import IntentClassifier


if __name__ == '__main__':
    c = IntentClassifier()
    print(c.get_scores('What is this text about?'))
    print(c.get_scores('I want text summary'))
    print(c.get_scores('I want you to ask me a question'))