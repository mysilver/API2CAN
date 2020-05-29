import json

import editdistance

from swagger.entities import Operation, Resource, UNKNOWN_RESOURCE, COLLECTION, SINGLETON, \
    ATTRIBUTE_RESOURCE, ACTION_RESOURCE, COUNT_RESOURCE, SEARCH_RESOURCE, FILE_EXTENSION_RESOURCE, \
    AUTH_RESOURCE, SWAGGER_RESOURCE, FILTER_RESOURCE, ALL_RESOURCE, UNKNOWN_PARAM_RESOURCE, \
    VERSION_RESOURCE, BASE_VERB_RESOURCE, BASE_NOUN_RESOURCE, METHOD_NAME_RESOURCE
from swagger.swagger_utils import ParamUtils, PathUtils
from utils.corenlp import nlp
from utils.text import is_verb, is_singular, singular, is_adjective, is_noun, is_plural


def __find_param(name, params):
    if params:
        for p in params:
            if p.name == name:
                return p

    return None


def __resource_type(previous, segment, current_tag, url):
    """
    :return: is singleton, Collection, sub-Collection
    """

    current = segment
    is_param = ParamUtils.is_param(current)
    if is_param:
        current = current[1:-1]
    current = ParamUtils.normalize(current)

    if not is_param:
        if current.startswith("by"):
            return FILTER_RESOURCE
        if current.startswith("search") or current.endswith("search") or current.startswith(
                "query") or current.endswith("query"):
            return SEARCH_RESOURCE
        if "count" == current:
            return COUNT_RESOURCE
        if "all" == current:
            return ALL_RESOURCE
        if ParamUtils.is_authentication(current):
            return AUTH_RESOURCE
        if current in {"swagger", "yaml"}:
            return SWAGGER_RESOURCE
        if current in {'pdf', 'json', 'xml', 'txt', 'doc', 'docx', 'jpeg', 'jpg', 'gif', 'png', 'xls', 'tsv', 'csv',
                       'fmw'}:
            return FILE_EXTENSION_RESOURCE

    if is_param and current in {"format"}:
        return FILE_EXTENSION_RESOURCE

    if is_param and previous:

        if current in previous:
            return SINGLETON

        if (current_tag.startswith('NNS') or is_plural(previous)) and ParamUtils.is_identifier(current):
            return SINGLETON

        if (current.endswith('name') or current.endswith('type')) and "{}.".format(segment) not in url:
            return SINGLETON

        if singular(previous) in current:
            return SINGLETON

        if editdistance.eval(current, previous) / (len(current) + len(previous)) < 0.4:
            return SINGLETON

    if current_tag.startswith('NNS') or is_plural(current):
        return COLLECTION

    if current_tag.startswith('jj') or is_adjective(current) or \
            current.endswith('ed') or (current_tag.startswith('VB') and current.startswith('is')):
        return ATTRIBUTE_RESOURCE

    if (current_tag.startswith('VB') or is_verb(current)) and not is_param:
        return ACTION_RESOURCE

    words = current.split()
    if len(words) > 1 and is_verb(words[0]) and not is_param:
        return METHOD_NAME_RESOURCE

    if is_param:
        return UNKNOWN_PARAM_RESOURCE

    if ParamUtils.is_version(current):
        return VERSION_RESOURCE

    return UNKNOWN_RESOURCE


def extract_resources(e: Operation):
    """
    returns a dictionary containing pairs of resources and their ids
    :param e: 
    :return: 

    """

    url, base_path = PathUtils.remove_non_informative_segments(e.url, e.base_path)
    segments = PathUtils.extract_segments(url)

    skip = False
    ret = []
    for i in reversed(range(0, len(segments))):
        if skip:
            skip = False
            continue

        current, previous = segments[i], None if i == 0 else segments[i - 1]
        resource = Resource(name=current, resource_type=UNKNOWN_RESOURCE)

        tagged = nlp.pos_tag(resource.name)
        resource.resource_type = __resource_type(previous, current, tagged[0][1], e.url)
        resource.is_param = ParamUtils.is_param(current)

        if resource.is_param:
            resource.param = __find_param(current[1:-1], e.params)

        if resource.resource_type == SINGLETON:
            resource.name = previous
            skip = True
        elif resource.is_param:
            resource.name = current[1:-1]

        ret.append(resource)

    reversed(ret)

    for seg in base_path.split('/'):
        if seg:
            if is_noun(seg):
                ret.append(Resource(name=seg, resource_type=BASE_NOUN_RESOURCE))
            elif is_verb(seg):
                ret.append(Resource(name=seg, resource_type=BASE_VERB_RESOURCE))

    return ret


if __name__ == "__main__":

    dataset = list(filter(lambda e: e["canonical_expr"], json.load(open("../api2expr/dataset/API2Can-test.json", "r"))))

    for e in dataset:
        e = Operation.from_json(e)
        print("{}\n{}\n".format(e.url,  [r.resource_type for r in extract_resources(e)]))
    #
    # Operations = [
    #     Operation("get", "/api/v2/customers/{id}", params=[Param(name="id", location="path")], base_path="/api/v2"),
    #     Operation("get", "/api/v2/customers/{id}/accounts.pdf", params=[Param(name="id", location="path")],
    #              base_path="/api/v2"),
    #
    # ]
    #
    # for e in Operations:
    #     print("----------------------{}------------------------".format(e.url))
    #     resources = extract_resources(e)
    #     print(json.dumps([r.to_json() for r in resources], indent=4))
