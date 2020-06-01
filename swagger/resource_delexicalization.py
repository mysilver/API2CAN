import json

from swagger.entities import Operation, RESOURCE_TYPES
from swagger.resource_extractor import extract_resources


def delexicalize(e: Operation):
    resources = extract_resources(e)
    counter = {}
    for r in RESOURCE_TYPES:
        counter[r] = 1

    # Remove unknown resources from the end

    if resources:
        to_remove = []
        for i, r in enumerate(reversed(resources)):
            if r.resource_type == 'Unknown' and i + 1 != len(resources):
                to_remove.append(r)
            else:
                break
        for r in to_remove:
            resources.pop(r)

    ret = [e.verb]
    ret_res = []
    for r in resources:
        rs = r.to_json()

        if rs['resource_type'] == 'Singleton':
            rs_coll_id = 'Collection_{}'.format(counter['Collection'])
            rs_id = 'Singleton_{}'.format(counter[rs['resource_type']])
            counter["Collection"] += 1
            ret.append(rs_coll_id)
            ret.append(rs_id)
            rs['ids'] = [rs_coll_id, rs_id]
        else:
            id = '{}_{}'.format(rs['resource_type'], counter[rs['resource_type']])
            ret.append(id)
            rs['ids'] = [id]
        ret_res.append(rs)
        counter[rs['resource_type']] += 1

    if len(ret) == 1:
        return None, ret_res

    return " ".join(ret), ret_res


def lexicalize(delexicalize_text, e: Operation):
    _, resources = delexicalize(e)

    return ret

print(delexicalize(Operation.from_json(json.loads('{"base_path": "/forex-quotes",\
        "desc": "Get quotes",\
        "intent": "get__forex-quotes_quotes",\
        "summary": "Get quotes for all symbols",\
        "url": "/forex-quotes/quotes",\
        "verb": "get"}'))))