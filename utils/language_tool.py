"""
nohup java -cp /media/may/Data/servers/languagetool/languagetool-standalone/target/LanguageTool-4.2-SNAPSHOT/LanguageTool-4.2-SNAPSHOT/languagetool-server.jar org.languagetool.server.HTTPServer --port 5004 &

for categories:
https://community.languagetool.org/rule/list?offset=0&max=10&lang=en&filter=&categoryFilter=Misused+terms+in+EU+publications+%28Gardner%29&_action_list=Filter
"""
import requests


class GrammarError:
    def __init__(self, message, short_message, replacements, offset, length, rule):
        self.replacements = replacements
        self.offset = offset
        self.length = length
        self.rule = rule
        self.short_message = short_message
        self.message = message


class Client(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.headers = {
            'content-type': 'application/json'
        }

    def _get_url(self, path):
        return "http://{0}:{1}{2}".format(self.host, self.port, path)

    def check(self, sentence):

        url = self._get_url('/v2/check')
        response = requests.post(url, headers=self.headers, data=('text=' + sentence + '&language=' + 'en-US').encode('utf-8'))

        if not response.ok:
            print("Warning", str(response.status_code) + ": " + response.text)
            return []

        matches = response.json().get('matches')

        return [GrammarError(message=i.get('message'),
                             replacements=i.get('replacements'),
                             offset=i.get('offset'),
                             length=i.get('length'),
                             rule=i.get('rule'),
                             short_message=i.get('shortMessage')) for i in matches]


class LanguageChecker:
    def __init__(self, host='localhost', port=5004):
        self.client = Client(host, port)

    def check(self, sentence, categories=None, excludes_ids=None):
        if not categories and not excludes_ids:
            return self.client.check(sentence)

        ret = []
        for error in self.client.check(sentence):
            if error.rule['category']['id'] in categories and (excludes_ids is None or error.rule['id'] not in excludes_ids):
                ret.append(error)

        return ret

    def misspellings(self, sentence):
        """
        :return: list of spelling errors 
        """
        resplacments = self.check(sentence, ['TYPOS'])
        ret = set()
        # corrections = set()
        for r in resplacments:
            ret.add(sentence[r.offset: r.offset + r.length])
            # if len(r.replacements) > 0:
            #     corrections.add(r.replacements[0]['value'])

        return ret

    def spelling_corector(self, sentence):
        resplacments = self.check(sentence, ['TYPOS'])
        for r in resplacments:
            ms = sentence[r.offset: r.offset + r.length]
            if len(r.replacements) > 0:
                sentence = sentence.replace(ms, r.replacements[0]['value'])

        return sentence

    def grammar_corector(self, sentence, categories=['MISC', 'GRAMMAR', "TYPOS"]):

        resplacments = self.check(sentence, categories=categories)

        while len(resplacments) > 0:
            r = resplacments[0]
            if not r.replacements:
                break

            sentence = sentence[:r.offset] + r.replacements[0]['value'] + sentence[r.offset + r.length:]
            resplacments = self.check(sentence, categories=['MISC', 'GRAMMAR', 'TYPOS'])
            # ms = sentence[r.offset: r.offset + r.length]
            # if len(r.replacements) > 0:
            #     sentence = sentence.replace(ms, )

        return sentence

    def singleWordCorrection(self, word):

        for p in self.check(word.replace('_', ' ')):
            if p.rule['issueType'] == 'misspelling':
                for r in p.replacements:
                    if word in r['value']:
                        # print(word, "->",r['value'])
                        return r['value'].replace(' ', '_')
                if p.replacements:
                    # print(word, "->", p.replacements[0]['value'])
                    return p.replacements[0]['value'].replace(' ', '_')
        return word



# p = LanguageChecker().singleWordCorrection('creat')
# print(LanguageChecker().grammar_corector("get hotels with hotel id being << hotelid >>"))

# err = LanguageChecker().check("Get a airport")
# p = SpellChecker().singleWordCorrection('in_vicinity_of')
# p = LanguageChecker().check("she have a bookks", ['GRAMMAR'])
# for i in p:
#     print(i)