import os
from collections import Counter

from faker import Faker
from pandas import read_csv
from pymantic import sparql
from random import randint
from swagger.entities import Param
from swagger.swagger_utils import ParamUtils

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
params_file = os.path.join(__location__.replace("/value_sampling", "/swagger"), "files/parameters.tsv")


class ParamValueSampler:
    def __init__(self, params_tsv=params_file, return_param_name=False) -> None:

        self.df_params = read_csv(params_tsv, sep='\t')
        self.df_params = self.df_params[self.df_params.is_auth_param == False]  # Remove authentication parameters
        self.df_params['name'] = self.df_params['name'].apply(ParamUtils.normalize)
        self.values = {}
        self.pattern_values = {}
        self.wikidata_server = sparql.SPARQLServer('http://localhost:9999/bigdata/namespace/wdq/sparql')
        self.return_param_name = return_param_name

        for index, row in self.df_params.iterrows():
            name, pattern, example, typ, count = row['name'], row['pattern'], row['example'], row['type'], row['count']

            if example == 'None':
                continue

            if (name, typ) not in self.values:
                self.values[(name, typ)] = Counter()
            self.values[(name, typ)].update({example: count})

            if pattern == 'None':
                continue

            if pattern not in self.pattern_values:
                self.pattern_values[pattern] = Counter()
            self.pattern_values[pattern].update({example: count})

    def sample(self, param: Param, n: int):

        if self.return_param_name and n == 1:
            return ["<< " + param.name.upper() + " >>"]

        values = []
        if param.example:
            values.append(param.example)

        if len(values) < n:
            values.extend(self.common_param_sampler(param, n))

        if len(values) < n:
            values.extend(self.pattern_sampler(param, n))

        if len(values) < n:
            values.extend(self.swagger_sampler(param, n))

        try:
            if len(values) < n:
                values.extend(self.wikidata_sampler(param, n))
        except:
            return values

        return values[:n]

    def pattern_sampler(self, param: Param, n: int):

        if param.pattern in self.pattern_values:
            vals = self.pattern_values[param.pattern]
            return vals.most_common(n)

        return []

    @staticmethod
    def common_param_sampler(param: Param, n: int):
        gold_values = {
            'email': 'user{}@company.com',
            'username': 'my_username{}',
        }

        values = []
        if gold_values.get(param.name):
            p = gold_values.get(param.name)
            for i in range(1, n + 1):
                values.append(p.format(i))

        if ParamUtils.is_identifier(param.name):
            for i in range(1, n + 1):
                values.append(i)

        fake = Faker()
        if 'date' in param.name:
            for i in range(1, n + 1):
                values.append(fake.date_between(start_date='today', end_date='+1y'))

            values = [str(v) for v in values]

        if param.type in {'integer', 'number'}:
            s = randint(0, 2000)
            values = [str(i) for i in range(s, n + s)]

        if param.type == 'boolean':
            values = ['false', 'true']

        return set(values)

    def swagger_sampler(self, param: Param, n: int):

        p = (ParamUtils.normalize(param.name), param.type)
        if p not in self.values:
            return []

        examples = self.values[p]
        return [a[0] for a in examples.most_common(n)]

    def wikidata_sampler(self, param: Param, n: int):

        values = []
        result = self.wikidata_server.query(
            'SELECT ?item WHERE {?item rdfs:label "' + ParamUtils.normalize(param.name, lemmatize=True) + '"@en}')

        for item in result['results']['bindings']:
            qid = item['item']['value'].replace('http://www.wikidata.org/entity/', '')
            q = 'SELECT ?itemLabel WHERE {  ?item wdt:P31 wd:' + qid + '.  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}'
            result = self.wikidata_server.query(q)
            for item2 in result['results']['bindings']:
                if item2['itemLabel']['type'] == 'literal':
                    values.append(item2['itemLabel']['value'])
        return values

# print(ParamValueSampler().wikidata_sampler(param=Param(name="city"), n=2))
