import unicodedata
import re
import nltk
from nltk.corpus import stopwords

import nltk
import pyphen
from nltk import ngrams
from nltk.tokenize import TweetTokenizer

tknzr = TweetTokenizer()
pyphen_dic = pyphen.Pyphen(lang='en')
stop_words = set(stopwords.words('english'))


def syllables(text):
    return pyphen_dic.inserted(text).split('-')


def tokenize(text, dictionary=None, ngrams_sizes=(3, 2), normilize_text=True):

    if not text:
        return []

    if normilize_text:
        text = normalize(text)

    if dictionary and ngrams_sizes:
        for i in ngrams_sizes:
            # join ngrams with '_'
            tokens = tknzr.tokenize(text)
            ngs = ngrams(tokens, i)
            for ng in ngs:
                phrs = "_".join(ng)
                if phrs in dictionary:
                    text = text.replace(" ".join(ng), phrs)

    tokens = tknzr.tokenize(text)
    return tokens


def pos_tag(tokenized_text):
    return nltk.pos_tag(tokenized_text)


def unicode_to_ascii(s):
    if not s:
        return s

    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def normalize(s):
    if not s:
        return s
    s = unicode_to_ascii(s.lower().strip())
    s = re.sub(r"([.!?])", r" \1", s)
    s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
    s = s.strip()
    return s


def remove_marks(s):
    if not s:
        return s

    s = unicode_to_ascii(s.lower().strip())
    s = re.sub(r"([.!?'\"])", r" ", s)
    s = s.strip()
    return s


def remove_stopword(text):
    filtered_sentence = []

    for w in tokenize(text):
        if w not in stop_words:
            filtered_sentence.append(w)

    return " ".join(filtered_sentence)
