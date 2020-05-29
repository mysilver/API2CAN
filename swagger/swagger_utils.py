import os
import re

import wordninja
from nltk.stem import WordNetLemmatizer
from pandas import read_csv
from tabulate import tabulate

from swagger.entities import Param
from utils.preprocess import remove_stopword
from utils.language_tool import LanguageChecker
from utils.text import is_singular

lemmatizer = WordNetLemmatizer()
sch = LanguageChecker()
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
params_file = os.path.join(__location__, "files/parameters.tsv")
entity_file = os.path.join(__location__, "files/entity-list.txt")


class ParamUtils:
    def __init__(self, params_tsv=params_file, entity_file=entity_file) -> None:

        self.df_params = read_csv(params_tsv, sep='\t')
        self.df_params = self.df_params[self.df_params.is_auth_param == False]  # Remove authentication parameters
        self.df_params['name'] = self.df_params['name'].apply(ParamUtils.normalize)
        self.values = {}
        self.pattern_values = {}
        self.entities = set()

        with open(entity_file) as f:
            for entity in set(f.readlines()):
                self.entities.add(ParamUtils.normalize(entity, lemmatize=True))

        for index, row in self.df_params.iterrows():
            name, pattern, example, typ, count = row['name'], row['pattern'], row['example'], row['type'], row['count']

            if example == 'None':
                continue

            if (name, typ) not in self.values:
                self.values[(name, typ)] = {example: count}
            else:
                if example not in self.values[(name, typ)]:
                    self.values[(name, typ)][example] = 0
                    self.values[(name, typ)][example] += count

            if pattern == 'None':
                continue

            if pattern not in self.pattern_values:
                self.pattern_values[pattern] = {example: count}
            else:
                if example not in self.pattern_values[pattern]:
                    self.pattern_values[pattern][example] = 0
                self.pattern_values[pattern][example] += count

    @staticmethod
    def is_param(text: str):
        if not text:
            return False

        if text.startswith('{') and text.endswith('}'):
            return True
        return False

    @staticmethod
    def normalize(text, lowercase=True, lemmatize=False, remove_punct=True, rm_stopwords=False):
        if not isinstance(text, str):
            return

        if text.lower() == 'api':
            return 'API'

        if rm_stopwords:
            text = remove_stopword(text)

        if text.startswith("x-"):
            t = text.replace("x-", "")
        else:
            t = text
        for ch in ['X-Amz-', 'x-amz-', '$', '_', '-', '.']:
            t = t.replace(ch, " ")

        if lemmatize:
            lt = ""
            for w in text.strip().lower().split():
                lt += lemmatizer.lemmatize(w) + " "
            t = lt.strip()

        if t == t.upper() and ' ' not in t:
            return t

        t = t.replace('’', "'")
        if remove_punct:
            t = re.sub(r"(\w)([A-Z])", r"\1 \2", t)

        m = ''
        for w in t.split():
            if w in {"<<", ">>"}:
                m += " " + w
                continue

            parts = wordninja.split(w)
            current = " ".join(parts)
            for p in parts:
                if len(p) == 1:
                    current = w
            m += " " + current
        t = m

        if lowercase:
            t = t.lower()

        t = re.sub('\s+', ' ', t).strip()
        return t

    @staticmethod
    def is_entity_parameter(param: Param):
        """
        Shows if a parameter should be present in a canonical expression or not.
        For example, it returns `False` for header params, and parameters related to authentication and API versioning 
        :param param: 
        :return: 
        """

        if param.location in {'header', 'file'}:
            return False

        if param.is_auth_param or ParamUtils.is_version(param.name):
            return False

        if param.name in {'username'}:
            return False

        return True

    @staticmethod
    def human_readable_name(param: Param):
        threshold = 20
        name = ParamUtils.normalize(param.name)
        desc = ParamUtils.normalize(param.desc)

        if not sch.misspellings(name):
            return name

        if desc and len(desc) > threshold:
            return sch.spelling_corector(name)

        if desc and not sch.misspellings(desc):
            return desc

        return name

    @staticmethod
    def is_authentication(param_name: str):
        param_name = ParamUtils.normalize(param_name)
        terms = set(param_name.split())
        for t in ['token', 'api key', 'key', "api token", 'x-aio-key', 'aio-key', 'x-aio-signature', 'accesstoken']:
            if t in terms:
                return True

        return False

    @staticmethod
    def is_necessary_param(param_name: str, auth=True):
        """
        if a parameter should be appeared in the canonical sentence
        :param param_name: 
        :return: 
        """

        if ParamUtils.is_version(param_name) or (ParamUtils.is_authentication(param_name) and auth):
            return False

        if param_name in {'username', 'user', 'account', 'user_name'}:
            return False

        return True

    @staticmethod
    def is_version(param_name: str):

        if not param_name:
            return False

        if param_name.startswith("v1") or param_name.startswith("v2"):
            return True

        param_name = ParamUtils.normalize(param_name)
        terms = set(param_name.split())
        for t in ['version', 'versions', 'v', 'v0', 'ver', 'v1', 'v2', 'v3', 'v4', 'v5']:
            if t in terms or param_name.startswith(t + ".") or param_name.startswith(t + "_") or param_name.startswith(
                            t + "-"):
                return True
        return False

    @staticmethod
    def is_identifier(param_name: str, auth=False, version=False):
        param_name = ParamUtils.normalize(param_name)
        if auth and ParamUtils.is_authentication(param_name):
            return True
        if version and ParamUtils.is_version(param_name):
            return True

        param_name = ParamUtils.normalize(param_name, lemmatize=True)
        terms = set(param_name.split())
        for id in {'id', 'key', 'identifier', 'ids', 'sid', 'token', 'credential', 'credentials', 'guid', 'uuid',
                   'code', 'serial'}:
            if id in terms:
                return True
        if param_name.endswith("id"):
            return True

        return False

    def is_named_entity(self, param_name):

        param_name = ParamUtils.normalize(param_name, lemmatize=True)
        terms = set(param_name.split())
        for t in terms:
            if t in self.entities:
                return True

        return False

    def stats(self):
        print("—————————————————— params.tsv ———————————————————————")
        print("#Unique Parameters : ", self.df_params.shape[0])
        # print("—————————————————————————————————————————————————————")
        # name	type	required	pattern 	count
        g = self.df_params.groupby(['type']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Parameters({}) by Types:".format(total))
        print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")
        g = self.df_params.groupby(['required']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Parameters by Required:".format(total))
        print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")
        g = self.df_params.groupby(['location']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Parameters Request Location:".format(total))
        print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")
        g = self.df_params['desc'].apply(lambda a: a != 'None')
        self.df_params['desc'] = g
        g = self.df_params.groupby(['desc']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Parameters by Desc:")
        print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")
        g = self.df_params['pattern'].apply(lambda a: a != 'None')
        self.df_params['pattern'] = g
        g = self.df_params.groupby(['pattern']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Parameters by Patterns:")
        print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")
        g = self.df_params['example'].apply(lambda a: a != 'None')
        self.df_params['example'] = g
        g = self.df_params.groupby(['example']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Parameters by Example:")
        print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")
        # g = df_params.groupby(['is_auth_param']).sum()
        # total = g['count'].sum()
        # g['percent'] = g['count'] / total * 100
        # print("Authentication Parameters:")
        # print(tabulate(g, headers='keys', tablefmt='psql'))

        # print("—————————————————————————————————————————————————————")[, 'key', 'identifier', 'ids']
        self.df_params['identifier'] = self.df_params['name'].apply(ParamUtils.is_identifier)
        g = self.df_params.groupby(['identifier']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Identifier Parameters:")
        print(tabulate(g, headers='keys', tablefmt='psql'))
        self.df_params.drop(columns=['identifier'], inplace=True)

        # print("—————————————————————————————————————————————————————")[, 'key', 'identifier', 'ids']
        self.df_params['entity'] = self.df_params['name'].apply(self.is_named_entity)
        g = self.df_params.groupby(['entity']).sum()
        total = g['count'].sum()
        g['percent'] = g['count'] / total * 100
        print("Entity Parameters:")
        print(tabulate(g, headers='keys', tablefmt='psql'))
        self.df_params.drop(columns=['entity'], inplace=True)


class PathUtils:
    @staticmethod
    def filter_redundant_url_segments(parts):
        ret = []
        previous = None
        for word in parts:

            if not word:
                previous = word
                continue

            if previous and ParamUtils.normalize(word[1:-1]) == ParamUtils.normalize(previous) and is_singular(
                    word[1:-1]):
                '''remove cases like: /countries/country_code/{country_code}'''
                ret = ret[:-1]
                ret.append(word)
                continue

            if word in []:
                '''ignore common URL prefixes like search/filter/...'''
                previous = word
                continue

            # tagged = nlp.pos_tag(word)
            # if tagged:
            #     '''Ignore cases like /items/latest'''
            #     if tagged[0][1].startswith('JJ'):
            #         previous = word
            #         continue

            previous = word
            ret.append(word)

        return ret

    @staticmethod
    def x(segments):
        if not segments:
            return None

        for i in range(len(segments)):
            if ParamUtils.is_necessary_param(segments[i]):
                break

        return segments[i:]

    @staticmethod
    def remove_non_informative_segments(url, base_path):
        """"
        Removes non informative segments of the given URL
        """

        if "?" in url:
            url = url[:url.index("?")]

        if base_path:
            parts = base_path.split('/')

            prev = None
            for i, p in enumerate(parts):
                if "{" in p and "}" in p or not is_singular(p) or p in ["search", "query", "count"] \
                        or ParamUtils.is_version(prev):
                    base_path = base_path[:base_path.index(p)]
                    break
                prev = p

        if base_path and base_path != '/':
            url = url.replace(base_path, "/")

        url = url.replace('http://', '/').replace('https://', '/')
        url = url.replace("{", "/{")
        url = url.replace("}", "}/")
        url = url.replace("//", "/")

        return url, base_path

    @staticmethod
    def extract_segments(url):
        parts = re.compile("[./:]").split(url)

        parts = PathUtils.filter_redundant_url_segments(parts)

        i = 0
        for i in range(len(parts)):
            if ParamUtils.is_necessary_param(parts[i]):
                break

        parts = parts[i:]
        ret = []
        for p in parts:
            if "}{" in p:  # //{dataset}{format}
                ret.append(p[:p.index("}{") + 1])
                ret.append(p[p.index("}{") + 1:])
            else:
                ret.append(p)

        ret = list(filter(lambda p: ParamUtils.normalize(p), ret))
        return ret


if __name__ == "__main__":
    print(PathUtils.extract_segments("/{url}/hello.json/{dataset}{format}"))
