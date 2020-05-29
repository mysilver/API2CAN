import inspect
import sys

from nltk import WordNetLemmatizer

from swagger.param_sampling import ParamValueSampler
from swagger.resource_extractor import extract_resources
from swagger.swagger_utils import ParamUtils
from utils.text import is_singular, singular, is_verb
from swagger.entities import Operation, Resource, UNKNOWN_RESOURCE, COLLECTION, SINGLETON, \
    ATTRIBUTE_RESOURCE, ACTION_RESOURCE, COUNT_RESOURCE, SEARCH_RESOURCE, FILE_EXTENSION_RESOURCE, \
    AUTH_RESOURCE, SWAGGER_RESOURCE, Param, FILTER_RESOURCE, IntentCanonical

from canonical.post_edits import finalize_utterance, to_parameters_postfix

param_sampler = ParamValueSampler()
lemmatizer = WordNetLemmatizer()


class RuleBasedCanonicalGenerator:
    def __init__(self, translators=list(), load_all_translators=True) -> None:
        self.translators = translators
        if load_all_translators:
            self.translators = [obj for name, obj in inspect.getmembers(sys.modules[__name__])
                                if inspect.isfunction(obj) and "translate" in name]

    def translate(self, operation, sample_values=True, ignore_non_path_params=False):
        method = operation.verb
        resources = extract_resources(operation)

        if len(resources) == 0:
            return None

        for translator in self.translators:
            canonical = translator(method, resources, sample_values)
            if canonical:
                canonical = finalize_utterance(canonical)
                entity_params = list(filter(ParamUtils.is_entity_parameter, operation.params))
                path_params = list(filter(lambda p: p.location == 'path', entity_params))
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

        return None


def translate_collection(method, resources, sample_values):
    if method not in ['get', 'post', 'delete']:
        return None

    if len(resources) != 1:
        return None

        # if ':' in resources[0].name:
        # //v1/{name}:setDefault
        # return None

    if resources[0].resource_type == ACTION_RESOURCE:
        ret = ParamUtils.normalize(resources[0].name)

        for w in ret.split():
            if not ParamUtils.is_necessary_param(w):
                return None

        if not ret or not is_verb(ret.split()[0]) or ret.endswith('ing') or ret.endswith('s'):
            return None

        return ret

    if resources[0].resource_type != COLLECTION:
        return None

    resource = ParamUtils.normalize(resources[0].name)

    for key in ["get ", "set ", "create ", "put ", "delete "]:
        if resource.startswith(key):
            resource = resource[len(key):]

    if is_singular(resource) or ' ' in resource:
        ret = 'get the {}'
    else:
        ret = 'get the list of {}'

    if method == 'post':
        resource = singular(resource)
        ret = 'create a {}'
    elif method == 'delete':
        ret = 'delete all {}'

    return ret.format(resource)


def translate_collection_adjective(method, resources, sample_values):
    if method not in ['get', 'delete']:
        return None

    if len(resources) != 2:
        return None

    if resources[0].resource_type != ATTRIBUTE_RESOURCE or resources[1].resource_type != COLLECTION:
        return None

    adjective = ParamUtils.normalize(resources[0].name)
    resource = ParamUtils.normalize(resources[1].name)

    for key in ["get ", "set ", "create ", "put ", "delete "]:
        if resource.startswith(key):
            resource = resource[len(key):]

    if is_singular(resource) or ' ' in resource:
        ret = 'get the {} {}'
    else:
        ret = 'get the list of {} {}'

    if method == 'delete':
        ret = 'delete all {} {}'

    return ret.format(adjective, resource)


def translate_collection_verb(method, resources, sample_values):
    if method not in ['get', 'post', 'delete']:
        return None

    if len(resources) != 2:
        return None

    if resources[0].resource_type != ACTION_RESOURCE or resources[1].resource_type != COLLECTION:
        return None

    verb = ParamUtils.normalize(resources[0].name)
    resource = ParamUtils.normalize(resources[1].name)

    return '{} the {}'.format(verb, resource)


def translate_singleton(method, resources, sample_values):
    if method not in ['get', 'patch', 'delete', 'put']:
        return None

    if len(resources) != 1:
        return None

        # if ':' in resources[0].name:
        # //v1/{name}:setDefault
        # return None

    if resources[0].resource_type != SINGLETON:
        return None

    resource = ParamUtils.normalize(resources[0].name)
    resource = singular(resource)
    # print(resources)
    # print(resource)
    if sample_values:
        vals = param_sampler.sample(resources[0].param, 1)
        val = vals[0] if vals else resources[0].param.name
    else:
        val = resources[0].param.name

    parameter_value = '<< {} >>'.format(val)
    ret = 'get a {} with {} being {}'
    if method == 'patch':
        ret = 'update a {} with {} being {}'
    elif method == 'delete':
        ret = 'delete a {} with {} being {}'
    elif method == 'put':
        ret = 'replace a {} with {} being {}'

    return ret.format(resource, ParamUtils.normalize(resources[0].param.name), parameter_value)


def translate_singleton_action(method, resources, sample_values):
    if method not in ['get', 'patch', 'delete', 'put']:
        return None

    if len(resources) != 2:
        return None

    if ACTION_RESOURCE not in resources[0].resource_type or resources[1].resource_type != SINGLETON:
        return None

    resource = ParamUtils.normalize(resources[1].name)
    resource = singular(resource)

    if sample_values:
        vals = param_sampler.sample(resources[1].param.name, 1)
        val = vals[0] if vals else resources[1].param.name
    else:
        val = resources[1].param.name

    parameter_value = '<< {} >>'.format(val)

    verb = ParamUtils.normalize(resources[0].name)
    if verb.endswith('ed'):
        verb = verb[:-1]

    ret = '{} a {} with {} being {}'
    # if method == 'patch':
    #     ret = 'update the {} with {} being {}'
    # elif method == 'delete':
    #     ret = 'delete the {} with {} being {}'
    # elif method == 'put':
    #     ret = 'replace the {} with {} being {}'

    return ret.format(verb, resource, ParamUtils.normalize(resources[1].param.name), parameter_value)


def translate_singleton_collection(method, resources, sample_values):
    if method not in ['get', 'post', 'delete']:
        return None

    if len(resources) != 2:
        return None

        # if ':' in resources[0].name:
        # //v1/{name}:setDefault
        # return None

    if resources[0].resource_type != COLLECTION or resources[1].resource_type != SINGLETON:
        return None

    resource = ParamUtils.normalize(singular(resources[1].name))
    resource2 = ParamUtils.normalize(resources[0].name)

    if sample_values:
        vals = param_sampler.sample(resources[1].param, 1)
        val = vals[0] if vals else resources[1].param.name
    else:
        val = resources[1].param.name

    param_value = '<< {} >>'.format(val)

    # param_value = '<<{}>>'.format(resources[1].param.name)

    if is_singular(resource2):
        ret = 'get the {} of a {} with {} being {}'
    else:
        ret = 'get the list of {} of a {} with {} being {}'

    if method == 'post':
        resource = singular(resource)
        resource2 = singular(resource2)
        ret = 'create a {} for a {} with {} being {}'
    elif method == 'delete':
        resource = singular(resource)
        ret = 'delete the {} of a {} with {} being {}'

    return ret.format(resource2, resource, ParamUtils.normalize(resources[1].param.name), param_value)


def translate_singleton_collection_action(method, resources, sample_values):
    if method not in ['get', 'post', 'delete']:
        return None

    if len(resources) != 3:
        return None

    if resources[2].resource_type != SINGLETON or resources[1].resource_type != COLLECTION or \
                    resources[0].resource_type != ACTION_RESOURCE:
        return None

    resource = ParamUtils.normalize(singular(resources[2].name))
    resource2 = ParamUtils.normalize(resources[1].name)
    # param_value = '<<{}>>'.format(resources[2][1]['val'])

    if sample_values:
        vals = param_sampler.sample(resources[2].param.name, 1)
        val = vals[0] if vals else resources[2].param.name
    else:
        val = resources[2].param.name

    param_value = '<< {} >>'.format(val)

    verb = ParamUtils.normalize(resources[0].name)

    ret = '{} all {} of a {} with {} being {}'

    # if method == 'post':
    #     resource = singular(resource)
    #     resource2 = singular(resource2)
    #     ret = '{} a {} for the {} with {} being {}'
    # elif method == 'delete':
    #     resource = singular(resource)
    #     ret = '{} the {} of the {} with {} being {}'

    return ret.format(verb, resource2, resource, ParamUtils.normalize(resources[2].name), param_value)


def translate_singleton_collection_adjective(method, resources, sample_values):
    if method not in ['get', 'post', 'delete']:
        return None

    if len(resources) != 3:
        return None

    if resources[2].resource_type != SINGLETON or resources[1].resource_type != COLLECTION or \
                    resources[0].resource_type != ATTRIBUTE_RESOURCE:
        return None

    resource = ParamUtils.normalize(singular(resources[2].name))
    resource2 = ParamUtils.normalize(resources[1].name)
    # param_value = '<<{}>>'.format(resources[2][1]['val'])

    if sample_values:
        vals = param_sampler.sample(resources[2].param.name, 1)
        val = vals[0] if vals else resources[2].param.name
    else:
        val = resources[2].param.name

    param_value = '<< {} >>'.format(val)

    adjective = ParamUtils.normalize(resources[0].name)

    # ret = '{} the {} of the {} with {} being {}'

    # if method == 'post':
    #     resource = singular(resource)
    #     resource2 = singular(resource2)
    #     ret = '{} a {} for the {} with {} being {}'
    # elif method == 'delete':
    #     resource = singular(resource)
    #     ret = '{} the {} of the {} with {} being {}'

    if is_singular(resource2):
        ret = 'get the {} {} of a {} with {} being {}'
    else:
        ret = 'get the list of {} {} of a {} with {} being {}'

    if method == 'post':
        resource = singular(resource)
        resource2 = singular(resource2)
        ret = 'create all {} {} for a {} with {} being {}'
    elif method == 'delete':
        resource = singular(resource)
        ret = 'delete all {} {} of a {} with {} being {}'

    return ret.format(adjective, resource2, resource, ParamUtils.normalize(resources[2].param.name), param_value)


def translate_singleton_singleton(method, resources, sample_values):
    if method not in ['get', 'patch', 'delete', 'put']:
        return None

    if len(resources) != 2:
        return None

        # if ':' in resources[0].name:
        # //v1/{name}:setDefault
        # return None

    if resources[1].resource_type != SINGLETON or resources[0].resource_type != SINGLETON:
        return None

    resource2 = ParamUtils.normalize(singular(resources[1].name))
    resource1 = ParamUtils.normalize(singular(resources[0].name))

    if sample_values:
        vals = param_sampler.sample(resources[0].param.name, 1)
        val = vals[0] if vals else resources[0].param.name
    else:
        val = resources[0].param.name

    parameter_value1 = '<< {} >>'.format(val)

    if sample_values:
        vals = param_sampler.sample(resources[1].param.name, 1)
        val = vals[0] if vals else resources[1].param.name
    else:
        val = resources[1].param.name

    parameter_value2 = '<< {} >>'.format(val)

    ret = 'get a {} with {} being {} for a {} with {} being {}'
    if method == 'patch':
        ret = 'update a {} with {} being {} for a {} with {} being {}'
    elif method == 'delete':
        ret = 'delete a {} with {} being {} for a {} with {} being {}'
    elif method == 'put':
        ret = 'replace a {} with {} being {} for a {} with {} being {}'

    return ret.format(resource1, ParamUtils.normalize(resources[0].param.name), parameter_value1,
                      resource2, ParamUtils.normalize(resources[1].param.name), parameter_value2)


def translate_singleton_singleton_action(method, resources, sample_values):
    if method not in ['get', 'patch', 'delete', 'put']:
        return None

    if len(resources) != 3:
        return None

    if resources[2].resource_type != SINGLETON or resources[1].resource_type != SINGLETON \
            or "Controller" not in resources[0].resource_type:
        return None

    resource2 = ParamUtils.normalize(singular(resources[2].name))
    resource1 = ParamUtils.normalize(singular(resources[1].name))

    if sample_values:
        vals = param_sampler.sample(resources[1].param.name, 1)
        val = vals[0] if vals else resources[1].param.name
    else:
        val = resources[1].param.name

    parameter_value1 = '<< {} >>'.format(val)

    if sample_values:
        vals = param_sampler.sample(resources[2].param.name, 1)
        val = vals[0] if vals else resources[2].param.name
    else:
        val = resources[2].param.name

    parameter_value2 = '<< {} >>'.format(val)

    verb = ParamUtils.normalize(resources[1].name)
    if verb.endswith('ed'):
        verb = verb[:-1]

    ret = '{} a {} with {} being {} for a {} with {} being {}'

    return ret.format(verb, resource1, ParamUtils.normalize(resources[1].param.name), parameter_value1,
                      resource2, ParamUtils.normalize(resources[1].param.name), parameter_value2)

