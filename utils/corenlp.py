from time import sleep

from stanfordcorenlp import StanfordCoreNLP
import os

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
    if 'CORENLP_HOME' not in os.environ:
        print("CORENLP_HOME is not set; set it as an  environment variable.")
        exit(0)
    sleep(3)
    print("Loading CoreNLP")
    nlp = StanfordCoreNLP(os.environ['CORENLP_HOME'], port=9000)
    print("CoreNLP loaded")
except Exception as e:
    print("Unable to run CoreNLP", e)
    exit(0)