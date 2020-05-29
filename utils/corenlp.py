from time import sleep

from stanfordcorenlp import StanfordCoreNLP

import requests

from subprocess import getoutput
try :
    url = "http://localhost:9000/shutdown?"
    shutdown_key = getoutput("cat /tmp/corenlp.shutdown")
    r = requests.post(url, data="", params={"key": shutdown_key})
    print(r.json())
except Exception as e:
    print(e)


try:
    sleep(3)
    print("Loading CoreNLP")
    nlp = StanfordCoreNLP("/media/may/Data/servers/stanford-corenlp-full-2018-10-05", port=9000)
    print("CoreNLP loaded")
except Exception as e:
    print("Unable to run CoreNLP", e)
    nlp = None