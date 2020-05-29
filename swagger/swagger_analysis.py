import re
import traceback
from collections import Counter
from os import walk

from swagger.entities import Param, Operation, API
from swagger.swagger_parser import SwaggerParser
from swagger.swagger_utils import ParamUtils


class SwaggerAnalyser:
    def __init__(self, swagger_path=None, swagger=None, debug=False):

        if debug:
            print("Parsing {}".format(swagger_path))

        self.debug = debug
        if swagger:
            self.doc = SwaggerParser(swagger_yaml=swagger)
        else:
            self.doc = SwaggerParser(swagger_path)

        self.auth_tokens = self.auth_keys()
        self.operations = []

    def process_parameters(self, params, auth_tokens):
        ret = []
        for p in params:
            param = Param.from_swagger(params[p], auth_tokens=auth_tokens, body_parameter=False)
            if param.location != 'body':
                ret.append(param)
        return ret

    def process_body_parameters(self, url, method, auth_tokens):

        def get_def(name, sdoc):
            name = name.replace("#/definitions/", "")
            defs = sdoc.specification['definitions']
            return defs.get(name)

        try:
            data = self.doc.get_send_request_correct_body(url, method)
            if data:
                ps = self.doc.paths[url][method]['parameters']
                for p in ps:
                    if ps[p].get("in") == 'body':
                        schema = ps[p].get('schema')
                        param = ps[p]
                        if '$ref' in schema:
                            schema = get_def(schema.get('$ref'), self.doc)
                            param = {**schema, **param}
                        return self.extract_body_parameters(schema, param, auth_tokens)

        except KeyError as ke:
            # error in swagger definition (cannot be parsed for)
            m = self.doc.paths[url][method]
            for p in m.get('parameters'):
                param = m.get('parameters')[p]
                if param['in'] == 'body':
                    if not param['schema'].get('type'):
                        # if not tried fixing the doc, change the schema and try again
                        param['schema']['type'] = 'object'
                        return self.process_body_parameters(url, method, auth_tokens)
                    else:
                        print(ke)

        except Exception as e:
            # print("Error file={}, method={} {}".format(f, method, url))
            raise e
        return []

    def extract_body_parameters(self, schema, param, auth_tokens):

        def traverse(obj, parent_keys=list(), required=set(), auth_tokens=set(), params=list()):

            if obj.get('readOnly', False):
                # get rid of readonly parameters
                return

            is_enum = False
            if 'pattern' in obj:
                if '|' in obj['pattern'] and len(obj['pattern']) > 2 and re.match("\([A-Za-z0-9\s\-_|]*\)",
                                                                                  obj['pattern']):
                    is_enum = True

            if is_enum:
                # for the time that pattern shows a fix number of options like (yes|no)
                param = Param.from_swagger(obj, parents=parent_keys, parent_in='body', required=required,
                                           auth_tokens=auth_tokens)
                param.type = "enum_pattern"
                vals = obj.get('pattern')
                param.example = vals[1:"".rindex('|')]
                params.append(param)
            elif "enum" in obj:
                param = Param.from_swagger(obj, parents=parent_keys, parent_in='body', required=required,
                                           auth_tokens=auth_tokens)
                param.type = "enum " + param.type
                params.append(param)
            elif SwaggerAnalyser.is_object(obj):
                ps = obj.get("properties")
                name = obj.get('name')
                pkeys = list(parent_keys)
                if name:
                    pkeys.append(name)

                if ps is not None:
                    return traverse(ps, pkeys, required, auth_tokens, params)

                for key in obj.keys():

                    if isinstance(obj[key], dict):
                        pkeys = list(parent_keys)
                        pkeys.append(key)
                        traverse(obj[key], pkeys, required, auth_tokens, params)
                    else:
                        param = Param.from_swagger(obj, parents=parent_keys, parent_in='body', required=required,
                                                   auth_tokens=auth_tokens)
                        # (parent_key, get_type(obj), 'body', parent_key in required or key in required, None)
                        params.append(param)
                        return
            elif obj.get("type") == "array" and "items" in obj:
                ps = obj.get("items")
                name = obj.get('name')
                pkeys = list(parent_keys)
                if name:
                    pkeys.append(name)
                if ps.get('type') != 'object' and ps.get('type') != 'array':
                    param = Param.from_swagger(obj, parents=pkeys, parent_in='body', required=required,
                                               auth_tokens=auth_tokens)
                    # param.type = ps.get('type', 'array')
                    # key = obj.get('name', parent_key)
                    # (key, ps.get('type', 'array'), 'body', key in required, None)
                    params.append(param)

                traverse(ps, pkeys, required, auth_tokens, params)
            else:
                for key in obj:
                    if not isinstance(obj.get(key), dict):
                        param = Param.from_swagger(obj, parents=parent_keys, parent_in='body', required=required,
                                                   auth_tokens=auth_tokens)
                        params.append(param)
                        # paramCounter.update(
                        #     [(parent_key, get_type(obj), 'body', parent_key in required, obj.get('pattern'))])
                        return
                    pkeys = list(parent_keys)
                    pkeys.append(key)
                    if SwaggerAnalyser.is_leaf(obj.get(key)):
                        # obj['name'] = key

                        param = Param.from_swagger(obj.get(key), parents=pkeys, parent_in='body', required=required,
                                                   auth_tokens=auth_tokens)
                        params.append(param)

                        # type = get_type(obj.get(key))
                        # paramCounter.update(
                        #     [(key, type, 'body', key in required or parent_key in required, obj.get(key).get('pattern'))])
                    else:
                        traverse(obj.get(key), pkeys, required, auth_tokens, params)

        # print(schema)
        required = schema.get("required", [])
        params = []
        traverse(schema, [param.get('name')], required, auth_tokens, params)
        return params

    @staticmethod
    def is_object(obj):

        if obj.get("type") == "array" and "items" in obj:
            return False

        if obj.get("type") == "object":
            return True

        if "properties" in obj and "required" in obj and len(obj.keys()) < 5:
            return True

        if "properties" in obj and "description" in obj and len(obj.keys()) < 5:
            return True

        return False

    @staticmethod
    def is_leaf(obj):
        # if 'type' in obj and 'properties' not in obj and 'items' not in obj:
        #     return True
        # return False
        leaf = True
        for key in obj:
            if isinstance(obj[key], dict) and key not in ["allOf", "anyOf", "oneOf", "additionalProperties"]:
                leaf = False

        return leaf

    def auth_keys(self):
        auth_tokens = {}
        for key in self.doc.specification.get('securityDefinitions', []):
            name = self.doc.specification['securityDefinitions'][key].get('name')
            ptype = self.doc.specification['securityDefinitions'][key].get('type')
            in_ = self.doc.specification['securityDefinitions'][key].get('in')
            auth_tokens[name] = (ptype, in_)
        return auth_tokens.keys()

    def analyse(self):
        for url in sorted(self.doc.paths):
            title = self.doc.specification['info']['title']
            api_url = self.doc.specification['host'] + self.doc.specification['basePath']
            protocols = self.doc.specification['schemes']
            api = API(title, api_url, protocols, self.operations)
            path = self.doc.paths[url]
            for m in sorted(path.keys()):
                if m in ['get', 'post', 'put', 'delete', 'patch']:
                    method = path[m]
                    params = self.process_parameters(method.get('parameters'), auth_tokens=self.auth_tokens)
                    summary = method.get('summary')
                    desc = method.get('description')
                    ok_response = method.get("responses")
                    operation_id = method.get("operationId")
                    response_desc = ""
                    # if ok_response:
                    #     response_desc = method.get('responses').get("200", {}).get("description", "")

                    if m != 'get':
                        params.extend(self.process_body_parameters(url, m, auth_tokens=self.auth_tokens))

                    # if len(url) > 2 and url.endswith('\\') and url.startswith('\\'):
                    #     url = url.replace(self.doc.base_path, '')
                    op = Operation(m, url, summary, desc, response_desc, params, operation_id=operation_id,
                                   base_path=self.base_path())

                    operation_id = ParamUtils.normalize(operation_id)
                    if operation_id:
                        op.intent = operation_id.replace(" ", "_")
                    else:
                        op.intent = m + "_" + url.replace("/", " ").replace(" ", "_").replace("{", "").replace("}", "")
                    self.operations.append(op)

        return api

    def base_path(self):
        return self.doc.base_path


if __name__ == "__main__":
    count = 0
    operations = []
    paramCounter = Counter()
    for (dirpath, dirnames, filenames) in walk("./_APIs"):
        total = len(filenames)
        count = 0
        for f in filenames:
            if f.endswith('.yaml'):
                try:
                    param_analyser = SwaggerAnalyser(dirpath + "/" + f)
                    results = param_analyser.analyse()
                    operations.extend(results)
                    for e in results:
                        for p in e.params:
                            paramCounter.update([p.to_tuple()])
                except ValueError:
                    continue
                except Exception as e:
                    traceback.print_exc()

            count += 1
            print(count, count * 100 / total)

    with open("out/operations.tsv", "wt") as f:
        f.write("verb\tpath\tsummary\tdesc\tresponse_desc\n")
        for p in operations:
            f.write("{}\t{}\t{}\t{}\t{}"
                    .format(str(p.verb).replace("\t", " "), str(p.url).replace("\t", " "),
                            str(p.summary).replace("\t", " "),
                            str(p.desc).replace("\t", " "), str(p.response_desc).replace("\t", " "))
                    .replace('"', "''").replace("\n", "---").replace("\r", "---") + "\n")

    with open("./out/parameters.tsv", "wt") as f:
        f.write("name\trequired\tis_auth_param\tlocation\ttype\tpattern\texample\tdesc\tcount\n")
        for p, c in paramCounter.most_common(len(paramCounter)):
            f.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n"
                    .format(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], c).replace('"', "''"))
