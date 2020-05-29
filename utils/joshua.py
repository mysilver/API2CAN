import requests
from artemis.fileman.disk_memoize import memoize_to_disk


@memoize_to_disk
def joshua_paraphrase(sentence, paraphrase_count):
    data = requests.get("http://localhost:5674/translate?q=" + sentence)

    try:
        return [p['hyp'] for p in data.json()['data']['translations'][0]['raw_nbest']][:paraphrase_count]
    except:
        return []


