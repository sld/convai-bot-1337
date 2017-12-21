class QuestionAndAnswer:
    def __init__(self, qas, user):
        self._user = user
        self._factoid_qas = qas
        self._question_asked = False
        # last asked factoid qas
        self._last_factoid_qas = None

    def get_question(self):
        if len(self._factoid_qas) == 0:
            return None
        # takes one question from list and removes it
        self._question_asked = True
        self._last_factoid_qas = self._factoid_qas[0]
        self._factoid_qas = self._factoid_qas[1:]
