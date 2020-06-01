import re

from swagger.entities import RESOURCE_TYPES, SINGLETON, COLLECTION, COUNT_RESOURCE, \
    SEARCH_RESOURCE, UNKNOWN_RESOURCE, COLLECTION, SINGLETON, ATTRIBUTE_RESOURCE, ACTION_RESOURCE, \
    COUNT_RESOURCE, SEARCH_RESOURCE, FILE_EXTENSION_RESOURCE, AUTH_RESOURCE, SWAGGER_RESOURCE, \
    FILTER_RESOURCE, ALL_RESOURCE, VERSION_RESOURCE, BASE_NOUN_RESOURCE, BASE_VERB_RESOURCE, \
    Resource, UNKNOWN_PARAM_RESOURCE, Operation
from swagger.resource_extractor import extract_resources
from swagger.swagger_utils import ParamUtils
from utils.language_tool import LanguageChecker
from utils.text import singular, is_singular, is_plural, is_verb

langtool = LanguageChecker()


class Templatetizer:
    @staticmethod
    def __replacements(resource):

        ret = []
        ids = resource.ids
        r_name = resource.name

        if len(ids) == 1:
            pairs = [(r_name, ids[0])]
        else:
            pairs = [(r_name, ids[0]), (resource.param.name, ids[1]),
                     (resource.param.name.replace(singular(r_name), ""), ids[1])]

        if resource.resource_type == COUNT_RESOURCE:
            pairs.append(("count", COUNT_RESOURCE))
        elif resource.resource_type == SEARCH_RESOURCE:
            pairs.append(("search", SEARCH_RESOURCE))
            pairs.append(("query", SEARCH_RESOURCE))

        for name, id in pairs:
            if not name:
                continue
            names = set()
            for n in [name, name.replace('get', '').replace('create', '').replace('remove', '')]:
                names.add(n)
                names.add(n.lower())
                names.add(n.replace("_", " ").lower())
                names.add(ParamUtils.normalize(n))
                names.add(ParamUtils.normalize(ParamUtils.normalize(n), lemmatize=True))
                names.add(ParamUtils.normalize(n, lemmatize=True))
                for str in combinations(ParamUtils.normalize(n).split()):
                    names.add(str)
                for str in combinations(ParamUtils.normalize(n, lemmatize=True).split()):
                    names.add(str)

            names = list(names)
            names.sort(key=lambda s: len(s), reverse=True)
            for name in names:
                ret.append((name, id))

        return ret

    @staticmethod
    def generate_template(e: Operation, resources: dict):

        if not resources:
            return e.canonical_expr

        replst = list()
        if e.operation_id:
            e.operation_id = e.operation_id.replace("post", "")
            e.operation_id = ParamUtils.normalize(e.operation_id)
            if " by " in e.operation_id:
                e.operation_id = e.operation_id[: e.operation_id.index(" by ")]
            words = e.operation_id.split()
            if len(words) > 1 and is_verb(words[0]):
                e.operation_id = ParamUtils.normalize(e.operation_id)
                if e.operation_id.startswith("add") and "new" not in e.operation_id:
                    e.operation_id = "add a new" + e.operation_id[3:]
                replst.append((e.operation_id.strip(), "OperationID"))
        # if len(resources) == 1:
        #     res = resources[0]
        #     if res.resource_type not in [COLLECTION, SINGLETON] and not res.is_param:
        #         replst.append((ParamUtils.normalize(res.name), "SingleResource"))

        can_expr = e.canonical_expr.lower()
        for r in resources:
            for rpl in Templatetizer.__replacements(r):
                replst.append((rpl[0], rpl[1]))

        replst.sort(key=lambda s: len(s[0]), reverse=True)

        can_expr = " {} ".format(can_expr.lower())
        for rpl in replst:
            if " {} ".format(rpl[0]) in can_expr:
                can_expr = can_expr.replace(" {} ".format(rpl[0]), " {} ".format(rpl[1]))

        return re.sub(r'\s+', ' ', can_expr).strip()  # Remove extra spaces

    @staticmethod
    def url_to_resource_sequence(e: Operation, resources: list):

        counter = dict()
        for r in RESOURCE_TYPES:
            counter[r] = 1

        # Remove unknown resources from the beginning of the url
        if resources:
            to_remove = []
            for i, r in enumerate(reversed(resources)):

                if r.resource_type in [UNKNOWN_PARAM_RESOURCE] and i + 1 != len(resources) \
                        and (not r.is_param or not ParamUtils.is_necessary_param(r.name)):
                    to_remove.append(r)
                else:
                    break
            for r in to_remove:
                resources.remove(r)

        # Remove unwanted resources
        resources = list(filter(lambda r: r.resource_type not in [VERSION_RESOURCE, ALL_RESOURCE], resources))

        ret = [e.verb]

        if e.operation_id:
            e.operation_id = e.operation_id.replace("post", "")
            e.operation_id = ParamUtils.normalize(e.operation_id)
            if " by " in e.operation_id:
                e.operation_id = e.operation_id[: e.operation_id.index(" by ")]
            words = e.operation_id.split()
            if len(words) > 1 and is_verb(words[0]):
                ret.append("OperationID")

        # ret.append(str("|"))
        for rs in resources:

            if rs.resource_type == SINGLETON:
                rs_coll_id = '{}_{}'.format(COLLECTION, counter[COLLECTION])
                rs_id = '{}_{}'.format(SINGLETON, counter[SINGLETON])
                counter[COLLECTION] += 1
                ret.append(rs_coll_id)
                ret.append(rs_id)
                rs.ids = [rs_coll_id, rs_id]
            else:
                id = '{}_{}'.format(rs.resource_type, counter[rs.resource_type])
                ret.append(id)
                rs.ids = [id]

            counter[rs.resource_type] += 1

        if len(ret) == 1:
            return None, resources

        ret = [str(i) for i in ret]
        return " ".join(ret), resources

    @staticmethod
    def to_expression(e: Operation, templates: list, post_editing=False):
        resources = extract_resources(e)
        _, resources = Templatetizer.url_to_resource_sequence(e, resources)

        template = Templatetizer.__best_template(templates, resources)

        if e.operation_id:
            words = ParamUtils.normalize(e.operation_id).split()
            if len(words) > 1 and is_verb(words[0]):
                template = template.replace("OperationID", ParamUtils.normalize(e.operation_id))

        # if len(resources) == 1 and "SingleResource" in template:
        #     template = template.replace("SingleResource", ParamUtils.normalize(resources[0].name))

        for rs in resources:
            if len(rs.ids) > 1:
                rs_coll_id = rs.ids[0]
                rs_id = rs.ids[1]
                if rs_coll_id:
                    template = template.replace(rs_coll_id, str(rs.name))
                if rs_id:
                    template = template.replace(rs_id, str(rs.param.name))
            else:
                rs_id = rs.ids
                template = template.replace(rs_id[0], rs.name)

        tokens = template.replace(" << ", " <<").replace(" >>", ">>").split(" ")
        ret = []
        for t in tokens:
            if not t.startswith("<<") and not Resource.is_resource_identifier(t):
                ret.append(ParamUtils.normalize(t))
            else:
                ret.append(t)

        ret = " ".join(ret).replace("<<", "<< ").replace(">>", " >>").strip()

        if post_editing:
            ret = remove_extra_params(ret)
            ret = remove_dangling_words(ret)
            ret = edit_grammar(ret)
            ret = append_parameters(ret, resources)

        return ret.replace(" get ", " ")

    @staticmethod
    def __best_template(templates, resources):

        # Sort templates
        types = [r.resource_type for r in resources]

        for rtype in [UNKNOWN_RESOURCE, SINGLETON, COLLECTION]:
            if rtype in types:
                templates.sort(key=lambda a: rtype + "_" in a, reverse=True)

        template = None
        for t in templates:

            if t.count("<<") != t.count(">>"):
                continue

            if Templatetizer.__has_unknown_tags(t, resources):
                continue

            template = t
            break

        if not template:
            template = templates[0]

        return template

    @staticmethod
    def __has_unknown_tags(template, resources):

        valid_ids = set()
        for item in resources:
            valid_ids = valid_ids.union(item.ids)

        for token in template.split():
            for tag in RESOURCE_TYPES:
                if token.startswith(tag) and token not in valid_ids:
                    return True

        return False


def remove_extra_params(ret):
    for i in range(1, 4):
        phrase = "Singleton_{} being << Singleton_{} >>".format(i, i)
        ret = ret.replace(phrase, "")
        phrase = "Unknown_{} being << Unknown_{} >>".format(i, i)
        ret = ret.replace(phrase, "")

    return ret


def remove_dangling_words(ret):
    ret = ret.strip()
    for word in {" for", " with"}:
        if ret.endswith(word):
            ret = ret[:-len(word)]

    return ret.strip()


def edit_grammar(text):
    ret = []
    words = text.split()
    prev = None
    sndPre = None
    for t in words:

        if prev == t:
            continue
        # size = len(ret)
        if sndPre in {'a', 'an'} and is_plural(t):
            ret.append(singular(t))
        elif prev in {'a', 'an'} and is_plural(t):
            ret.append(singular(t))
        elif prev == 'a' and t[0].lower() in {'a', 'e', 'i', 'o'}:
            ret = ret[:-1]
            ret.append('an')
            ret.append(singular(t))
        elif prev == 'an' and t[0].lower() not in {'a', 'e', 'i', 'o'}:
            ret = ret[:-1]
            ret.append('a')
            ret.append(singular(t))
        elif t == 's':
            ret = ret[:-1]
            ret.append(langtool.singleWordCorrection(prev + "s"))
        elif t == "'s":
            ret = ret[:-2]
            ret.append(langtool.singleWordCorrection(prev + "'s"))
        else:
            ret.append(t)

        sndPre = prev
        prev = t

    return " ".join(ret)


def append_parameters(text, resources):
    for r in resources:
        if r.resource_type in [ATTRIBUTE_RESOURCE, COUNT_RESOURCE, SEARCH_RESOURCE,
                               FILE_EXTENSION_RESOURCE, AUTH_RESOURCE, SWAGGER_RESOURCE, FILTER_RESOURCE, ALL_RESOURCE,
                               VERSION_RESOURCE, BASE_VERB_RESOURCE, BASE_NOUN_RESOURCE]:
            continue

        param = r.param
        if param and param.name:
            if "<< " + param.name + " >>" in text:
                continue
            else:
                text += " by {} being << {} >>".format(ParamUtils.human_readable_name(param), param.name)

    return text


def combinations(strs):
    if len(strs) <= 1:
        return strs

    news = combinations(strs[1:])
    ret = []
    ret.extend([strs[0] + r for r in news])
    ret.extend([strs[0] + " " + r for r in news])
    return list(set(ret))

# print(combinations(["A", "B", "C", "D", "E"]))
