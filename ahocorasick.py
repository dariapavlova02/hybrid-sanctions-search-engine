class Automaton:
    def __init__(self):
        self._patterns = []

    def add_word(self, word, value):
        self._patterns.append((word, value))

    def make_automaton(self):
        pass

    def iter(self, text):
        for word, value in self._patterns:
            start = text.find(word)
            if start != -1:
                end_idx = start + len(word) - 1
                yield end_idx, value
