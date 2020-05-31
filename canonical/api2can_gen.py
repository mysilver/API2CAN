import re
import traceback
from os import walk
import sys

from bs4 import BeautifulSoup
from nltk import CFG
from nltk.corpus.reader import VERB, json
from nltk.parse.generate import generate
from nltk.stem import WordNetLemmatizer
from tqdm import tqdm

from canonical.post_edits import finalize_utterance, entity_phrase, to_parameters_postfix, to_entities
from canonical.rule_based import RuleBasedCanonicalGenerator
from swagger.entities import Operation, IntentCanonical
from swagger.resource_extractor import extract_resources
from swagger.swagger_analysis import SwaggerAnalyser
from swagger.swagger_utils import ParamUtils
import corenlp as nlp
from utils.text import replace_last, to_sentences

common_verbs = {'get', 'create', 'delete', 'remove', 'eliminate', 'update', 'replace', 'return', 'check', 'set', 'list'}
common_sverbs = {v + 's' for v in common_verbs}
lemmatizer = WordNetLemmatizer()


def replace_hyperlinks(text):
    p = re.compile('\[[^\[\]()]*\]\s*\([^\[\]()]*\)')
    links = p.findall(text)
    for link in links:
        l = re.compile('\[[^\[\]()]*\]').findall(link)[0][1:-1]
        # txt = re.compile('\([^\[\]()]*\)').findall(link)[0][1:-1]
        text = text.replace(link, l)

    return text


# print(replace_hyperlinks(
#     "this is [/my/otherEndpoint](#/tagName/myOtherEndpointId) just a test [/my/2](#/tagName/dd) dfdfd"))
#

class TrainingExprGenerator:
    def __init__(self):
        self.paramUtils = ParamUtils()
        # self.param_sampler = param_sampler

    def populate_canonicals(self, Operations, ignore_non_path_params=True):
        for e in Operations:
            e.canonical_expr = self.to_canonical(e, ignore_non_path_params)

        return Operations

    def to_canonical(self, operation, ignore_non_path_params):

        entity_params = list(filter(ParamUtils.is_entity_parameter, operation.params))
        path_params = list(filter(lambda p: p.location == 'path', entity_params))
        # non_path_params = list(filter(lambda p: p.location != 'path', entity_params))

        path_params, intent = self.to_intent(operation, path_params)
        if not intent:
            return None
        canonical = finalize_utterance(intent)

        if path_params:
            canonical += ' for ' + to_entities(path_params)

        ic = IntentCanonical(operation.intent, canonical, path_params)

        if ignore_non_path_params:
            return [ic]

        rest_params = []
        for p in entity_params:
            if p.location != "path":
                rest_params.append(p)

        ret = [ic]
        if rest_params:
            for p in rest_params:
                params = [p]
                params.extend(path_params)
                ret.append(IntentCanonical(operation.intent,
                                           canonical + to_parameters_postfix([p]),
                                           params))

        return ret

    def to_intent(self, operation, path_params):
        """
        returns the intent of the Operation and path_params which have not been used in the intent
        :return: path_params, intent
        """

        intent = self.extract_intent(operation.summary)
        if not intent:
            intent = self.extract_intent(operation.desc)

        # if not intent:
        #     intent = get_intent(Operation.response_desc)
        if not intent or len(intent) < 8:
            return path_params, None

        # todo: remove unnecessary words
        if intent.endswith('.'):
            intent = intent[:-1]

        for verb in ['return', 'retrieve', "read", "fetch"]:
            if intent.startswith(verb):
                intent = 'get' + intent[len(verb):]

        for verb in ['add']:
            if intent.startswith(verb):
                intent = 'create' + intent[len(verb):]

        for verb in ['remove']:
            if intent.startswith(verb):
                intent = 'delete' + intent[len(verb):]

        for i in range(2):
            intent = ParamUtils.normalize(intent)
        # TODO: more robost approaches to defeat misppelling

        path_params, intent = self.replace_path_params(intent, operation, path_params)
        return path_params, intent

    @staticmethod
    def extract_intent(text):

        if not text or text == 'None':
            return None

        # remove links in swagger []()
        if "](" in text or "] (" in text:
            text = replace_hyperlinks(text)

        text = BeautifulSoup(text, "lxml").text

        if ':' in text:
            text = text[:text.index(':')]

        if '(' in text:
            text = re.sub(r"\(.*\)", '', text)

        expr = None
        for sent in to_sentences(text):

            if len(sent) > 120:
                continue

            sent = sent.lower()

            tagged_sent = nlp.pos_tag(sent)

            count = 0
            for w, t in tagged_sent:
                if t in {'VB', 'VBZ'}:
                    count += 1

            if count > 1 and len(sent) > 80:
                # print("More than one verb: ", sent)
                continue

            if tagged_sent[0][1] == 'VB' or tagged_sent[0][0] in common_verbs or \
                    (tagged_sent[0][1] == 'RB' and tagged_sent[1][1] == 'VB'):
                expr = sent
            elif tagged_sent[0][1] == 'VBZ' or tagged_sent[0][0] in common_sverbs or \
                    (tagged_sent[0][1] == 'RB' and tagged_sent[1][1] == 'VB'):
                if tagged_sent[0][1] == 'RB' and tagged_sent[1][1] == 'VB':
                    verb = tagged_sent[1][0]
                else:
                    verb = tagged_sent[0][0]
                old_verb = verb
                if verb not in {"was", "is", "has"}:
                    verb = lemmatizer.lemmatize(verb, pos=VERB)

                expr = sent.replace(old_verb, verb)

            if expr and 'http' in expr:
                continue

            if expr and 'see' in expr and (':' in expr or 'please' in expr or 'href' in expr):
                continue

            if expr and ('<' in expr and '>' in expr or '<p>' in expr):
                continue

            if expr:
                expr = finalize_utterance(expr)
                if " by " in expr:
                    expr = expr[:expr.index(" by ")]
                return expr

        return None

    @staticmethod
    def __cfg_list_to_str(lst):
        lst = [x for x in lst if x]
        lst = ["'{}'".format(i) for i in lst]
        return "|".join(lst)

    def replace_path_params(self, intent, e: Operation, path_params):

        def find_resource(param, resources):

            if resources:
                for r in resources:
                    if r.is_param and r.param.name == param:
                        return r

            return None

        ret_path_params = []
        resources = extract_resources(e)
        for p in path_params:

            pname = p.name
            res = find_resource(pname, resources)

            if not res:
                ret_path_params.append(p)
                continue

            rname = res.name
            rname_normalized = ParamUtils.normalize(rname)
            pname_normalized = ParamUtils.normalize(pname)

            try:
                regex_str = "{} by(.+){}".format(rname, pname)
                regex = re.compile(regex_str)

                matched_1 = regex.search(intent)
                if matched_1:
                    matched_1 = matched_1.group(0)
                    matched_1 = matched_1.replace(rname + " by ", "")
                else:
                    matched_1 = ' '
            except:
                matched_1 = ' '

            try:
                regex_str_2 = "{} by(.+){}".format(ParamUtils.normalize(rname, lemmatize=True),
                                                   ParamUtils.normalize(pname, lemmatize=True))
                regex2 = re.compile(regex_str_2)
                matched_2 = regex2.search(intent)
                if matched_2:
                    matched_2 = matched_2.group(0)
                    matched_2 = matched_2.replace(ParamUtils.normalize(rname, lemmatize=True) + " by ", "")
                else:
                    matched_2 = ' '
            except:
                matched_2 = ' '

            if not rname:
                rname = pname
            if not rname_normalized:
                rname_normalized = pname_normalized

            R1 = self.__cfg_list_to_str({" ", matched_1, matched_2, rname, " ".join(rname_normalized.split()),
                                         " ".join(ParamUtils.normalize(rname, lemmatize=True).split())})

            R2 = self.__cfg_list_to_str({' ', pname, pname_normalized, ParamUtils.normalize(pname, lemmatize=True),
                                         " ".join(pname_normalized.split()), " ".join(pname_normalized.split()),
                                         " ".join(ParamUtils.normalize(pname, lemmatize=True).split()),
                                         "id", "name", "type", "resource", "item"})

            Plst = {' ', 'by', "via", "with", "based on", "with specific", "based on", "with specific", "matching",
                    "with a given", "with given", "given", "given a"}
            P = self.__cfg_list_to_str(Plst)

            grammar = """S -> R1 P R2\nR1 -> {}\nR2 -> {}\nP  -> {}""".format(R1, R2, P)
            grammar = CFG.fromstring(grammar)

            possible_phrases = []
            for phr in generate(grammar):
                phr = " ".join(phr).strip()

                if not phr or phr in Plst:
                    continue

                possible_phrases.append(phr)
                possible_phrases.append(ParamUtils.normalize(phr))

            possible_phrases.sort(key=len, reverse=True)
            possible_phrases = list(filter(lambda a: len(a) > 2, possible_phrases))

            found = False
            intent += " "  # important do not remove
            for phrase in possible_phrases:
                if " {} ".format(phrase) in intent or intent.endswith(phrase):
                    replacement = entity_phrase(p)

                    # if phrase in replacement:
                    replacement = phrase + " by " + replacement

                    # if not phrase.endswith(" with"):
                    #     phrase += " with "
                    # replacement = phrase + replacement

                    if phrase + "'s" in intent or phrase + " of " in intent:
                        intent = intent + " with " + entity_phrase(p)
                        break

                    intent = replace_last(intent, phrase + " ", replacement + " ")
                    found = True
                    break

            if not found:
                ret_path_params.append(p)

        regex = re.compile('(by|based|based on|via|with) (id|specific id|given id|the given id|a specific id)$',
                           re.IGNORECASE)
        intent = regex.sub('', intent)

        return ret_path_params, intent


if __name__ == "__main__":

    expr_gen = TrainingExprGenerator()
    rule_gen = RuleBasedCanonicalGenerator()
    swaggers_directory = sys.argv[1]
    out_directory = sys.argv[2]
    for (dirpath, dirnames, filenames) in walk(swaggers_directory):

        with tqdm(total=len(filenames)) as bar:
            with open("./dataset/expert-canonicals-test-data.json", "r") as f:
                expert_canonicals = json.load(f)

            files = {
                "train": filenames[: int(0.9 * len(filenames))],
                "validation": filenames[int(0.9 * len(filenames)): int(0.95 * len(filenames))],
                "test": filenames[int(0.95 * len(filenames)):]
            }

            single_file_dataset = dict()
            for stage in ["test", "validation", "train"]:
                single_file_dataset = []
                for f in files[stage]:
                    if f.endswith('.yaml'):
                        try:
                            param_analyser = SwaggerAnalyser(dirpath + "/" + f)

                            Operations = param_analyser.analyse()
                            Operations = expr_gen.populate_canonicals(Operations, ignore_non_path_params=True)
                            for e in Operations:
                                if e.verb + e.url in expert_canonicals:
                                    e.canonical_expr = expert_canonicals[e.verb + e.url]
                                can = rule_gen.translate(e, False, True)
                                if can:
                                    e.canonical_expr = can

                                e.api = f
                                single_file_dataset.append(e.to_json())

                        except ValueError:
                            print("Unable to parse: {}".format(f))
                            # traceback.print_exc()
                            continue
                        except Exception as e:
                            print("Unable to parse: {}".format(f))
                            traceback.print_exc()
                        finally:
                            bar.update(1)

                with open("{}/API2Can-{}.json".format(out_directory,stage), "wt") as f:
                    f.write(json.dumps(single_file_dataset, indent=4))
