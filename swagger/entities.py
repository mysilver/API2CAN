import json
from collections import namedtuple, OrderedDict


class Paraphrase:
    def __init__(self, paraphrase, entities, score=None, method=None):
        self.entities = entities
        self.paraphrase = paraphrase
        self.score = score
        self.method = method

    def to_json(self):
        ret = self.__dict__

        ret['entities'] = [p.to_json() if isinstance(p, Param) else p for p in ret['entities']]

        ret = {k: v for k, v in ret.items() if v}
        return OrderedDict(ret)

    @staticmethod
    def from_json(d: dict):

        empty_sample = Paraphrase(None, None).__dict__
        for key in empty_sample:
            if key not in d:
                d[key] = empty_sample[key]

        ret = Paraphrase(**d)
        entities = []
        if ret.entities:
            for p in ret.entities:
                entities.append(Param.from_json(p))

        ret.entities = entities

        return ret

    def clone(self):
        return Paraphrase(self.paraphrase, [p.clone() for p in self.entities], self.score, self.method)

    def __hash__(self) -> int:
        return json.dumps(self.to_json()).__hash__()


class IntentCanonical:
    def __init__(self, intent, canonical, entities, **keys):

        self.entities = entities
        self.intent = intent
        self.canonical = canonical
        for key in keys:
            setattr(self, key, keys[key])

    def to_json(self):
        ret = self.__dict__

        ret['entities'] = [p.to_json() for p in ret['entities']]

        if 'paraphrases' in ret:
            ret['paraphrases'] = [p.to_json() for p in ret['paraphrases']]

        ret = {k: v for k, v in ret.items() if v}
        return OrderedDict(ret)

    @staticmethod
    def from_json(d: dict):

        empty_sample = IntentCanonical(None, None, None).__dict__
        for key in empty_sample:
            if key not in d:
                d[key] = empty_sample[key]

        ret = IntentCanonical(**d)
        entities = []
        if ret.entities:
            for p in ret.entities:
                entities.append(Param.from_json(p))

        # paraphrases = []
        # if ret.paraphrases:
        #     for p in ret.entities:
        #         entities.append(Param.from_json(p))

        ret.entities = entities

        return ret


class Param:
    def __init__(self, name=None, required=None, is_auth_param=None, location=None, type=None, pattern=None,
                 example=None,
                 desc=None):

        self.required = required
        self.desc = desc
        self.location = location
        self.is_auth_param = is_auth_param
        self.name = name
        self.pattern = pattern
        self.example = example
        self.type = type

    @staticmethod
    def from_tuple(param_tuple: tuple):
        name, required, is_auth_param, location, type, pattern, example, desc = param_tuple
        return Param(name, required, is_auth_param, location, type, pattern, example, desc)

    @staticmethod
    def from_swagger(param_obj, parents=None, parent_in=None, required=set(), auth_tokens=set(),
                     body_parameter=True):

        global_auth_keys = {'token', 'api_key', 'oAuth', 'OAuth', 'Authentication', 'authentication'}
        if not parents:
            parents = [""]
        if isinstance(parents, str):
            parents = [parents]

        if parents[0] == '' or parents[0] == 'body' and len(parents) > 1:
            parents = parents[1:]

        p = Param()
        if parents:
            if param_obj.get('name'):
                p.name = ".".join(parents) + '.' + param_obj.get('name')
            else:
                p.name = ".".join(parents)
        else:
            p.name = param_obj.get('name', '')

        p.pattern = param_obj.get('pattern', param_obj.get('x-pattern'))
        p.location = param_obj.get('in', parent_in)
        p.type = Param.get_type(param_obj)
        p.is_auth_param = p.name in auth_tokens or p.name in global_auth_keys
        p.example = param_obj.get('example',
                                  param_obj.get('default', param_obj.get('minimum', param_obj.get('x-example'))))

        if p.type and 'enum' in p.type:
            if len(param_obj['enum']) > 0:
                p.example = param_obj['enum'][0]

        if isinstance(p.example, list) or isinstance(p.example, dict):
            p.example = json.dumps(p.example)

        if isinstance(p.example, str):
            p.example = p.example.replace('\n', '---').replace('\t', '---').replace('\r', '---')

        p.desc = param_obj.get('description')
        if p.desc:
            p.desc = p.desc.replace('\n', '---').replace('\t', '---').replace('\r', '---')

        if p.location == 'path':
            p.required = True
        elif not body_parameter:
            p.required = param_obj.get('required', False)
        else:
            p.required = p.name in required

        if not p.required:
            req = False
            for pr in parents:
                if pr in required:
                    req = True
                    break
            p.required = req

        return p

    def to_tuple(self):
        return self.name, self.required, self.is_auth_param, self.location, self.type, self.pattern, self.example, self.desc

    @staticmethod
    def get_type(obj):
        if "type" in obj:
            return obj.get("type")
        if "enum" in obj:
            return "enum"

        if len(obj) == 0:
            return 'object'

        for key in {'oneOf', 'anyOf', 'allOf', 'not'}:
            if key in obj:
                o = obj.get(key)
                if isinstance(o, list) and len(o) > 0:
                    return Param.get_type(o[0])
        # obj.get("x-type")
        return None

    def clone(self):
        return Param(self.name, self.required, self.is_auth_param, self.location, self.type, self.pattern, self.example,
                     self.desc)

    def to_json(self):
        ret = self.__dict__
        ret = {k: v for k, v in ret.items() if v is not None}
        return ret

    @staticmethod
    def from_json(d: dict):

        empty_sample = Param(None, None).__dict__
        for key in empty_sample:
            if key not in d:
                d[key] = empty_sample[key]

        ret = Param(**d)
        return ret


class Operation:
    def __init__(self, verb, url, summary=None, desc=None, response_desc=None, params=None, canonicals=None,
                 operation_id=None, base_path=None, **keys):
        self.canonicals = canonicals
        self.params = params
        self.verb = verb
        self.url = url
        self.summary = summary
        self.desc = desc
        # self.response_desc = response_desc
        self.operation_id = operation_id
        self.base_path = base_path
        self.intent = None
        for key in keys:
            setattr(self, key, keys[key])

    def to_json(self):
        ret = self.__dict__

        ret['params'] = [p.to_json() for p in ret['params']]
        if ret['canonicals']:
            ret['canonicals'] = [p.to_json() for p in ret['canonicals']]

        ret = {k: v for k, v in ret.items() if v}
        return OrderedDict(ret)

    @staticmethod
    def from_json(d: dict):

        empty_sample = Operation(None, None).__dict__
        for key in empty_sample:
            if key not in d:
                d[key] = empty_sample[key]

        ret = Operation(**d)
        params = []
        if ret.params:
            for p in ret.params:
                params.append(Param.from_json(p))
        ret.params = params

        canonicals = []
        if ret.canonicals:
            for p in ret.canonicals:
                canonicals.append(IntentCanonical.from_json(p))

        ret.canonicals = canonicals

        return ret


class API:
    def __init__(self, title, url, protocols, operations, **keys):

        self.url = url
        self.protocols = protocols
        self.operations = operations
        self.title = title
        for key in keys:
            setattr(self, key, keys[key])

    def to_json(self):
        ret = self.__dict__

        ret['operations'] = [p.to_json() for p in ret['operations']]

        ret = {k: v for k, v in ret.items() if v}
        return OrderedDict(ret)

    @staticmethod
    def from_json(d: dict):

        empty_sample = API(None, None, None, None).__dict__
        for key in empty_sample:
            if key not in d:
                d[key] = empty_sample[key]

        ret = API(**d)
        operations = []
        if ret.operations:
            for p in ret.operations:
                operations.append(Operation.from_json(p))

        ret.operations = operations

        return ret


UNKNOWN_RESOURCE = "Unknown"
UNKNOWN_PARAM_RESOURCE = "Unknown_Param"
COLLECTION = "Collection"
SINGLETON = "Singleton"
ATTRIBUTE_RESOURCE = "Attribute_Controller"
ACTION_RESOURCE = "Action_Controller"
METHOD_NAME_RESOURCE = "Method_Name_Controller"
COUNT_RESOURCE = "Count_Key"
FILTER_RESOURCE = "Filter_Key"
SEARCH_RESOURCE = "Search_Key"
AUTH_RESOURCE = "Auth_Key"
FILE_EXTENSION_RESOURCE = "File_Extension_Key"
SWAGGER_RESOURCE = "Swagger_Key"
ALL_RESOURCE = "ALL_KEY"
VERSION_RESOURCE = "VERSION_KEY"
BASE_NOUN_RESOURCE = "BASE_NOUN_RESOURCE"
BASE_VERB_RESOURCE = "BASE_VERB_RESOURCE"
RESOURCE_TYPES = [UNKNOWN_RESOURCE, COLLECTION, SINGLETON, ATTRIBUTE_RESOURCE, ACTION_RESOURCE,
                  COUNT_RESOURCE,
                  SEARCH_RESOURCE, FILE_EXTENSION_RESOURCE, AUTH_RESOURCE, SWAGGER_RESOURCE,
                  FILTER_RESOURCE, ALL_RESOURCE, UNKNOWN_PARAM_RESOURCE, VERSION_RESOURCE,
                  BASE_VERB_RESOURCE, BASE_NOUN_RESOURCE, METHOD_NAME_RESOURCE]


class Resource:
    @staticmethod
    def is_resource_identifier(term):
        for t in RESOURCE_TYPES:
            if term.startswith("{}_".format(t)):
                return True

        return False

    def __init__(self, name, resource_type=None, param=None, is_param=False):
        self.name = name
        self.resource_type = resource_type
        self.param = param
        self.is_param = is_param

    def to_json(self):
        ret = self.__dict__
        # if ret['param']:
        #     ret['param'] = ret['param'].to_json()
        return OrderedDict(ret)

    @staticmethod
    def from_json(d: dict):

        empty_sample = Resource(None).__dict__
        for key in empty_sample:
            if key not in d:
                d[key] = empty_sample[key]

        ret = Resource(**d)

        # if ret.param:
        #     ret.param = Param.from_json(ret.param)

        return ret

#
# print(Endpoint.from_json({"url": "/dsdsd/", "params": [{"name": "test"}]}))
# print(Endpoint.from_json({"url": "/dsdsd/", "params": [{"name": "test"}]}))
