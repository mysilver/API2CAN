# import requests
# from artemis.fileman.disk_memoize import memoize_to_disk
#
# techniques = {
#     "Sent2Vec": 4011,
#     "InferSent": 4012,
#     "UniversalSentenceEncoder": 4013,
#     "XlingSentEmbedding": 4014,
# }
#
#
# def vectorize(sentence, technique=None):
#     """
#     :param sentence:  in English
#     :param technique: "Sent2Vec", "InferSent", "UniversalSentenceEncoder", "XlingSentEmbedding"
#     :return:
#     """
#     if technique in techniques:
#         port = techniques[technique]
#     else:
#         port = techniques['Sent2Vec']
#
#     resp = requests.post("http://localhost:" + str(port) + "/vector", json={'sentence': sentence})
#
#     return resp.json()
#
#
# @memoize_to_disk
# def similarity(sentence1, sentence2, technique=None):
#     """
#     :param sentence1:  in English
#     :param sentence2:  in English
#     :param technique: "Sent2Vec", "InferSent", "UniversalSentenceEncoder", "XlingSentEmbedding"
#     :return:
#     """
#     try:
#         if technique in techniques:
#             port = techniques[technique]
#         else:
#             port = techniques['Sent2Vec']
#
#         resp = requests.post("http://localhost:" + str(port) + "/similarity",
#                              json={'seq_1': sentence1, 'seq_2': sentence2})
#         return resp.json()["cosine_similarity"]
#     except Exception as e:
#         print("Error in similarity method:", sentence1, sentence2)
#         raise e
#
#     pass
