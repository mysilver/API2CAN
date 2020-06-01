# API2CAN
API2CAN consists of the following parts:
- A dataset to train machine translation models for translation REST operations to Natural Language Sentences
- A service to extract resources from an operations
- A service implementing the resource-based delexicalization
- A service to translate a REST operation into a canonical utterance
API
This API can be also used for 
## Datasets
API2Can offers three datasets: test, train, and validation datasets.
Each dataset is a list of operations (API methods from various APIs) in which canonical utterance is shown by the "canonical_expr" field:

```json
# sample operation in the datasets
{
        "verb": "get",
        "params": [
            {
                "example": null,
                "type": "string",
                "required": true,
                "pattern": null,
                "for_auth": false,
                "desc": "all | full-time | part-time | [reviewer-name]------Specify all to get all Times reviewers, or specify full-time or part-time to get that subset. Specify a reviewer's name to get details about a particular reviewer.---",
                "location": "path",
                "name": "resource-type"
            }
        ],
        "response_desc": "An array of Movie Critics",
        "url": "/svc/movies/v2/critics/{resource-type}.json",
        "desc": null,
        "operation_id": null,
        "summary": null,
        "api": "nytimes.com__movie_reviews__2.0.0.yaml",
        "canonical_expr": "get the list of movie critics by resource type being << resource-type >>",
        "base_path": "/svc/movies/v2"
    }
```
It is also possible to generate the dataset for any set of swagger files. 
To do so, you need to create a directory of yaml files (swagger documentations), and run the following command:

```shell script
pip3 install -r requirements.txt
python3 canonical/api2can_gen.py [SWAGGER_DIRECTORY] [OUTPUT_DIRECTORY]
```
## Automatic Canonical Utterance Generation

- You can run "canonical utterance generator" as a service:
```shell script
pip3 install -r requirements.txt
python3 rest/restapi.py 8080
```
- Next browse http://localhost:8080/ for swagger documentation of the API
- Invoke "/operations/extract" to extract the operations of the given YAML file
- Invoke "/operations/generate-canonicals" to generate canonical utterances for each operation. The payload of the request is a list of operations extracted by the "/operations/extract" operation.
```json
# Here is a sample payload  
[
      {
        "base_path": "/forex-quotes",
        "desc": "Get quotes",
        "intent": "get__forex-quotes_quotes",
        "summary": "Get quotes for all symbols",
        "url": "/forex-quotes/quotes",
        "verb": "get"
      },
      {
        "base_path": "/forex-quotes",
        "desc": "Symbol List",
        "intent": "get__forex-quotes_symbols",
        "summary": "Get a list of symbols for which we provide real-time quotes",
        "url": "/forex-quotes/symbols",
        "verb": "get"
      }
  ]
```
## Resource-based Delexiclization
- To extract resources (& delexicalize an operation) in an operation use the "/resources/delexicalize" operation with an operation in the payload:
 ```json
POST /resources/delexicalize
     {
        "base_path": "/forex-quotes",
        "desc": "Get quotes",
        "intent": "get__forex-quotes_quotes",
        "summary": "Get quotes for all symbols",
        "url": "/forex-quotes/quotes",
        "verb": "get"
     }
```
- To convet back a delexicalized sentence, you can invoke "/resources/delexicalize?delexicalized_text=" operation with an operation in the payload and the sentence in a query parameter:
 ```json
POST /resources/delexicalize?delexicalized_text=get Collection_1
     {
        "base_path": "/forex-quotes",
        "desc": "Get quotes",
        "intent": "get__forex-quotes_quotes",
        "summary": "Get quotes for all symbols",
        "url": "/forex-quotes/quotes",
        "verb": "get"
     }
```
## More information
For more information please refer to the following papars:
```sh
@inproceedings{api2can_edbt_2020,
  title={Automatic Canonical Utterance Generation for Task-OrientedBots from API Specifications},
  author={Yaghoubzadeh, Mohammadali and Benatallah, Boualem, and Zamanirad, Shayan},
  booktitle={Advances in Database Technology-23rd International Conference on Extending Database Technology (EDBT)},
  year={2020}
}

@inproceedings{rest2bot_www_2020,
    author = {Yaghoub-Zadeh-Fard, Mohammad-Ali and Zamanirad, Shayan and Benatallah, Boualem and Casati, Fabio},
    title = {REST2Bot: Bridging the Gap between Bot Platforms and REST APIs},
    year = {2020},
    isbn = {9781450370240},
    publisher = {Association for Computing Machinery},
    address = {New York, NY, USA},
    url = {https://doi.org/10.1145/3366424.3383551},
    doi = {10.1145/3366424.3383551},
    booktitle = {Companion Proceedings of the Web Conference 2020},
    pages = {245–248},
    numpages = {4},
    keywords = {Paraphrasing, Chatbots, Automated Bot Development, REST APIs},
    location = {Taipei, Taiwan},
    series = {WWW ’20}
}
```
