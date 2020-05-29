import logging
import traceback
import warnings
import sys
import werkzeug
from flask import Flask, jsonify, request
from flask_restx import Api, Resource, reqparse, abort, fields, inputs, Model

from canonical.api2can_gen import TrainingExprGenerator
from canonical.rule_based import RuleBasedCanonicalGenerator, param_sampler
# from paraphrase.paraphrasers import Paraphraser, PARAPHRASERS
from swagger.entities import Operation, Param, IntentCanonical, API
from swagger.swagger_analysis import SwaggerAnalyser
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
api = Api(app,
          default="APIs",
          title="REST2Bot APIs",
          description="A collection of APIs to automate bot development")

param_model = api.model('Parameter', {
    "name": fields.String,
    "value": fields.String,
    "type": fields.String,
    "desc": fields.String,
    "example": fields.String,
    "required": fields.Boolean,
    "start": fields.Integer,
    "end": fields.Integer,
    "is_auth_param": fields.Boolean,
})

paraphrase_model = api.model('Paraphrase', {
    "text": fields.String,
    "method": fields.String,
    "score": fields.Integer,
    "entities": fields.List(fields.Nested(param_model)),
})

canonical_paraphrase_model = api.model('Canonical Paraphrases', {
    "intent": fields.String,
    "canonical": fields.String,
    # "entities": fields.List(fields.Nested(param_model)),
    "paraphrases": fields.List(fields.Nested(paraphrase_model)),

})

canonical_model = api.model('IntentCanonicals', {
    "intent": fields.String,
    "canonical": fields.String,
    "entities": fields.List(fields.Nested(param_model)),
    # "paraphrases": fields.List(fields.Nested(paraphrase_model)),
})
expression_model = api.model('Expression', {
    "text": fields.String,
    "method": fields.String,
    "score": fields.Integer,
    "entities": fields.List(fields.Nested(param_model)),
})
operation_model = api.model('Operation', {
    "base_path": fields.String,
    "verb": fields.String,
    "url": fields.String,
    "intent": fields.String,
    "summary": fields.String,
    "desc": fields.String,
    "canonicals": fields.List(fields.Nested(canonical_model)),
    "params": fields.List(fields.Nested(param_model)),
    "expressions": fields.List(fields.Nested(expression_model))
})

api_model = api.model('API', {
    "title": fields.String,
    "url": fields.String,
    "protocols": fields.List(fields.String),
    "operations": fields.List(fields.Nested(operation_model)),
})

expr_gen = TrainingExprGenerator()
rule_gen = RuleBasedCanonicalGenerator()
# paraphraser = Paraphraser()

yaml_parser = reqparse.RequestParser()
yaml_parser.add_argument('yaml', type=werkzeug.datastructures.FileStorage, location='files', required=True)

query_parser = reqparse.RequestParser()
query_parser.add_argument('n', type=int, help="number of sampled values for the given entity")

# paraphraser_parser = reqparse.RequestParser()
# paraphraser_parser.add_argument('params', type=int, help="number of sampled values for each entities", location='args')
# paraphraser_parser.add_argument('count', type=int, help="number of paraphrases", location='args')
# paraphraser_parser.add_argument('score', type=inputs.boolean, default=False, help="score generated paraphrases",
#                                 location='args')
# paraphraser_parser.add_argument('paraphrasers', type=str, action="append", location='args',
#                                 help='Pick from: {}'.format(", ".join(PARAPHRASERS)))

TRANSLATORS = {
    "RULE",
    "SUMMARY",
    "NEURAL"
}
canonical_parser = reqparse.RequestParser()
canonical_parser.add_argument('translators', type=str, action="append", location='args',
                              help='Pick from: {}'.format(", ".join(TRANSLATORS)))


#
# platform_parser = reqparse.RequestParser()
# platform_parser.add_argument('platform', choices=["Wit.ai"],
#                               help='Pick from: {}'.format(", ".join(["Wit.ai"])))


@api.route("/extract-operations")
class Specs(Resource):
    @api.expect(yaml_parser)
    @api.response(200, "Success", [api_model])
    def post(self):
        """
        extracts operations of a given swagger specs
        """
        files = list(request.files.values())
        if not files:
            abort(401, message="file is missing")
        try:
            ret = []
            for file in files:
                yaml = file.stream.read().decode("utf-8")
                doc = SwaggerAnalyser(swagger=yaml).analyse()
                ret.append(doc.to_json())

            # ret = {
            #     "apis": ret,
            #     # "size": len(ret),
            #     "success": True,
            # }
            return jsonify(ret)
        except Exception as e:
            abort(501, message="Server is not able to process the request; {}".format(e))
            traceback.print_stack()


@api.route("/generate-canonicals")
class Canonicals(Resource):
    @api.expect(canonical_parser, [operation_model])
    @api.response(200, "Success", [canonical_model])
    def post(self):
        """
        generates canonical sentences for a list of operations
        """
        try:
            ret = []
            args = canonical_parser.parse_args()
            translators = args.get("translators", TRANSLATORS)
            lst = request.json

            for api in lst:
                api = API.from_json(api)
                for operation in api.operations:
                    operation.canonicals = []
                    # operation = Operation.from_json(o)
                    if not translators or "SUMMARY" in translators:
                        canonicals = expr_gen.to_canonical(operation, ignore_non_path_params=False)

                        if canonicals:
                            operation.canonicals = canonicals

                    if not translators or "RULE" in translators:
                        canonicals = rule_gen.translate(operation, sample_values=False, ignore_non_path_params=False)
                        if canonicals:
                            operation.canonicals.extend(canonicals)
                ret.append(api)
            return jsonify([a.to_json() for a in ret])
        except Exception as e:
            abort(400, message=e)
            traceback.print_stack()


@api.route("/entities/suggest-values")
class EntityValues(Resource):
    @api.expect(param_model, query_parser)
    def post(self):
        """
        generates sample values for the given parameter
        """
        try:
            args = query_parser.parse_args()
            n = args.get("n")
            if not n:
                n = 10
            param = Param.from_json(request.json)

            ret = param_sampler.sample(param, n)
            return jsonify(ret)

        except Exception as e:
            print(e)
            abort(400, message=e)


def convert_api(api):
    def to_entity(param, utterance):
        return {
            "entity": param["name"],
            "value": param["example"],
            "start": utterance.index(str(param["example"])),
            "end": utterance.index(str(param["example"])) + len(str(param["example"])) - 1,
            "type": param["type"]
        }

    def to_expressions(operation):
        expressions, entities = [], {}
        for c in operation.canonicals:
            if not hasattr(c, 'paraphrases'):
                warnings.warn("No paraphrases for the canonical:{}".format(c.to_json()))
                continue
            for p in c.paraphrases:
                expressions.append({
                    "text": p['paraphrase'],
                    "entities": [to_entity(e, p['paraphrase']) for e in p['entities']] if 'entities' in p else []
                })
                if 'entities' in p:
                    for e in p['entities']:
                        if e['name'] not in entities:
                            entities[e['name']] = []
                        # if 'example' in e:
                        entities[e['name']].append(e['example'])
        entities2 = []
        for e in entities:
            entities2.append({
                "entity": e,
                "values": entities[e]
            })
        return expressions, entities2

    def convert_method(operation):

        expressions, entities = to_expressions(operation)
        return {
            "intent_name": operation.intent,
            "method_path": operation.url,
            "type": operation.verb,
            "parameters": [p.to_json() for p in operation.params],
            "expressions": expressions,
            "entities": entities,
        }

    return {
        "api_title": api.title,
        "api_url": api.url,
        "api_protocol": api.protocols,
        "api_methods": [convert_method(o) for o in api.operations]
    }


if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    LOGGER = logging.getLogger("artemis.fileman.disk_memoize")
    LOGGER.setLevel(logging.WARN)
    app.run("0.0.0.0", port=port)
