import random


class ByeSkill:
    def __init__(self):
        self._bye_messages = [
            "Peace!", "Catch you later!", "It was nice seeing you!",
            "I look forward to our next meeting!", "Bye bye!"
        ]

    def predict(self, arg=None):
        return random.sample(self._bye_messages, 1)[0]
