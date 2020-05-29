from nltk import sent_tokenize, tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
import inflect
from nltk.corpus import wordnet as wn
from utils.corenlp import nlp
from nltk.corpus import wordnet as wn

inflect_engine = inflect.engine()

lemmatizer = WordNetLemmatizer()


def mlcs(strings):
    """Return a long common subsequence of the strings.
    """

    def check(string, seq):
        i = 0
        j = 0
        while i < len(string) and j < len(seq):
            if string[i] == seq[j]:
                j += 1
            i += 1
        return len(seq) - j

    def checkall(strings, seq):
        for x in strings:
            a = check(x, seq)
            if not a == 0:
                print(x, seq, a)
                return False
        return True

    if not strings:
        raise ValueError("mlcs() argument is an empty sequence")
    strings = list(set(strings))  # deduplicate
    alphabet = set.intersection(*(set(s) for s in strings))

    # indexes[letter][i] is list of indexes of letter in strings[i].
    indexes = {letter: [[] for _ in strings] for letter in alphabet}
    for i, s in enumerate(strings):
        for j, letter in enumerate(s):
            if letter in alphabet:
                indexes[letter][i].append(j)

    # Generate candidate positions for next step in search.
    def candidates():
        for letter, letter_indexes in indexes.items():
            candidate = []
            for ind in letter_indexes:
                if len(ind) < 1:
                    break
                q = ind[0]
                candidate.append(q)
            else:
                yield candidate

    result = []
    while True:
        try:
            # Choose the closest candidate position, if any.
            pos = None
            for c in candidates():
                if not pos or sum(c) < sum(pos):
                    pos = c
            letter = strings[0][pos[0]]
        except TypeError:
            return ''.join(result)
        for let, letter_indexes in indexes.items():
            for k, ind in enumerate(letter_indexes):
                ind = [i for i in ind if i > pos[k]]
                letter_indexes[k] = ind
        result.append(letter)


def lcs(source, target):
    m = len(source)
    n = len(target)
    counter = [[0] * (n + 1) for x in range(m + 1)]
    longest = 0
    lcs_set = set()
    for i in range(m):
        for j in range(n):
            if source[i] == target[j]:
                c = counter[i][j] + 1
                counter[i + 1][j + 1] = c
                if c > longest:
                    lcs_set = set()
                    longest = c
                    lcs_set.add(source[i - c + 1:i + 1])
                elif c == longest:
                    lcs_set.add(source[i - c + 1:i + 1])

    return lcs_set


def replace_last(text: str, find: str, replacement: str):
    k = text.rfind(find)
    return text[:k] + replacement + text[k + len(find):]


def to_sentences(text):
    if not isinstance(text, str):
        print("Warning given text is not string = ", text)
        return []
    text = text.replace("---", "\n")
    sents = sent_tokenize(text)
    ret = []
    for sent in sents:
        for s in sent.split('\n'):
            s = s.strip()
            if s:
                ret.append(s)
    return ret


def lemmatize(text):
    ret = []
    for t in tokenize.word_tokenize(text):
        ret.append(lemmatizer.lemmatize(t))
        # ret.append(PorterStemmer().stem(t))
    return " ".join(ret)


def singular(word):
    """
    Makes a plural name singular
    :param word: 
    :return: 
    """
    try:
        sing = inflect_engine.singular_noun(word)
        if sing:
            return sing
    except:
        return word
    return word


def plural(word):
    """
    Makes a plural name singular
    :param word: 
    :return: 
    """
    try:
        sing = inflect_engine.plural_noun(word)
        if sing:
            return sing
    except:
        return word
    return word


def is_singular(word: str) -> bool:
    if not is_noun(word):
        return False

    if word == singular(word):
        return True
    return False


def is_plural(word: str):
    if not is_noun(word):
        return False

    if word == plural(word):
        return True

    return False


def is_question(text):
    text = text.lower()
    q1 = text.endswith('?')
    q2 = text.startswith("wh")

    q3 = False
    if not (q1 or q2):
        for w in {'could', 'can', 'is', 'any', 'are', 'do', 'does', "would", 'might', 'may', "should", "shall", "will",
                  "must", "had", "have", "did", "how", "i am wondering", "i wonder", "i'm wondering"}:
            if text.startswith(w):
                q3 = True
                break

    return q1 or q2 or q3


def is_response(text):
    text = text.lower()
    for ph in ["you can", "you must", "i suggest", "i know", "these are", "this is", "i can", "that is", "those are",
               "i do not", "i don't", "there you go", "no ", 'i have']:
        if text.startswith(ph):
            return True

    # if " is " in text or ' are ':
    #     return True

    return False


def is_imperative(text):
    text = text.lower()
    if "please" in text or 'pls' in text:
        return True

    for ph in ["i need", "i want"]:
        if text.startswith(ph):
            return True

    sent = text.lower()

    tagged_sent = nlp.pos_tag(sent)

    for w, t in tagged_sent:
        if t == 'VB':
            return True
        elif t not in ["please", "kindly", "you", ","]:
            break

    return False


def is_verb(text):
    if wn.synsets(text, wn.VERB):
        return True

    return False


def is_noun(text):
    if wn.synsets(text, wn.NOUN):
        return True

    return False


def is_adjective(word: str):
    if wn.synsets(word, wn.ADJ):
        return True

    return False

    # p1 = "The weather on Friday is OK"
    # p2 = "The weather on Friday is acceptable"
    # p3 = "The weather on Friday is adequate"
    # print(mlcs([p1,p2,p3]))
