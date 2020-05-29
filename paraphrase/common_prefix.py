import json
import os

from artemis.fileman.disk_memoize import memoize_to_disk
from nltk import ngrams
from collections import Counter

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
params_file = os.path.join(__location__, "prefix.txt")


class PrefixParaphraser:
    def __init__(self, prefix_file=params_file) -> None:
        self.prefixes = []
        with open(prefix_file, "rt") as f:
            for l in f.readlines():
                self.prefixes.append(l.strip())

    def paraphrase(self, canonical_utterance, n: int) -> list:
        ret = []
        for p in self.prefixes:
            ret.append("{} {}".format(p, canonical_utterance))
            if len(p) == n:
                break

        return ret


def print_prefixes():
    data = json.loads(open("Para-Quality.json", "rt").read())

    prefixes = Counter()
    for l in data:
        for p in [p['paraphrase'].lower() for p in l['paraphrases']]:
            phrase = p.split()[:5]
            for i in range(2, len(phrase)):
                for ngram in ngrams(phrase, i):
                    ngram = " ".join(ngram)
                    prefixes.update((ngram, 1))

    prefixes = prefixes.most_common(1000)
    for p in prefixes:
        print(p)


if __name__ == "__main__":
    for i in PrefixParaphraser().paraphrase("get a list of customers"):
        print(i)
