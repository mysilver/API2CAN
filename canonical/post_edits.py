import re
from string import digits

from swagger.entities import Param, SINGLETON
from swagger.swagger_utils import ParamUtils
from utils.preprocess import tokenize
from utils.language_tool import LanguageChecker
from utils.text import is_singular, singular


def finalize_utterance(text, trim_sentences=True):
    canonical = text
    if not canonical:
        return None

    if trim_sentences:

        if canonical.startswith("will "):
            canonical = canonical[5:]

        for fnt in [" pdf", " json", " swagger", " html", " xhtml", " csv", " tsv", " doc", " txt", " docx",
                    " tif", " xml", " xls", " fmw", " yaml"]:
            canonical = canonical.replace(fnt, ' ')

        for key in [' details of', " details", " specified", " available", " selected", " to database",
                    " for current user", " one or more", " an existing"]:
            canonical = canonical.replace(key, ' ')

        for key in ["matching", "filtered by", "that match", "within the", "by setting the values", "for that",
                    "for this", "for which", "which", "using the provided", "using the", "for a given",
                    "that", "by specifying", "identified in", "by this account", "identified by", "having",
                    "for the currently logged", "for the currently authenticated user", "for a user", "given a",
                    "given an", "for the given", "in the given", "for the authenticated user", "for a specific"]:

            if key in canonical:
                canonical = canonical[:canonical.index(key)]

    for key in [" me ", " you ", " your "]:
        canonical = canonical.replace(key, " my ")

    canonical = canonical.replace(" the current user", " me")

    if canonical.startswith("list") and not canonical.startswith("list of"):
        canonical = "get the list of" + canonical[4:]
    elif canonical.startswith("list of"):
        canonical = "get the " + canonical

    if "a list of" in canonical:
        canonical = canonical.replace("a list of", "the list of")

    if " all " in canonical and "the list of all" not in canonical:
        canonical = canonical.replace(" all ", " the list of ")

    canonical = canonical.replace("get the list of all ", "get the list of ")
    canonical = canonical.replace("get search ", "search ")

    if canonical.startswith("create a ") and not canonical.startswith("create a new "):
        canonical = canonical.replace("create a ", "create a new ")

    for key in ["create", "replace", "delete", "remove", "update"]:
        if canonical.startswith(key) and not canonical.startswith("{} a ".format(key)):
            canonical = canonical.replace("{} ".format(key), "{} a ".format(key))

    canonical = canonical.translate({ord(k): None for k in digits})

    canonical = re.sub("\s+", " ", canonical).strip()
    return canonical


def plural_to_singular_edit(canonical, resources=None):
    """
    corrects plural noun grammatical errors
    """

    for resource in resources:
        rname = resource.name
        if resource.resource_type != SINGLETON:
            continue

        canonical = canonical.replace(rname, "a {}".format(singular(rname)))
        canonical = canonical.replace(" the a ", " a ")
        canonical = canonical.replace(" a a ", " a ")
        canonical = canonical.replace(" an a ", " a ")
        canonical = canonical.replace(" a an ", " a ")

    canonical = LanguageChecker().grammar_corector(canonical, categories=['MISC']).lower()
    tokens = tokenize(canonical, normilize_text=False)

    ret = []
    seen_article = -20
    for token in tokens:

        if token in {"a", "an"}:
            seen_article = 0

        if 3 > seen_article > 0:
            if not is_singular(token):
                ret.append(singular(token))
                seen_article = 0
                continue

        ret.append(token)
        seen_article += 1

    tokens = []
    prev = False
    for token in reversed(ret):
        if not is_singular(token):
            if prev:
                token = singular(token)
            prev = True
        tokens.append(token)

    ret = reversed(tokens)

    return " ".join(ret).replace("< <", "<<").replace("> >", ">>")


def to_parameters_postfix(params):
    if not params:
        return ""

    entity_params = list(filter(ParamUtils.is_entity_parameter, params))
    non_path_params = list(filter(lambda p: p.location != 'path', entity_params))

    if not non_path_params:
        return ""
    return ' with ' + to_entities(non_path_params)


def to_entities(params):
    pt = ''
    for i, p in enumerate(params, 1):
        sep = ''
        if len(params) > 1:
            sep = ', '
            if i == len(params) - 1:
                if len(params) == 2:
                    sep = " and "
                else:
                    sep = ", and "
            elif i == len(params):
                sep = ''
        pt += entity_phrase(p) + sep

    return pt


def entity_phrase(param: Param):
    # value = self.param_sampler.sample(param, 1)
    # value = value[0] if value else "---"
    name = ParamUtils.human_readable_name(param)
    # todo : shorten when value is too lengthy
    # todo : not using = when it is possible (verb, boolean)
    return "{} being << {} >>".format(name, str(param.name))
