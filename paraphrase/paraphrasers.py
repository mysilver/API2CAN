# from artemis.fileman.disk_memoize import memoize_to_disk
#
# from paraphrase.common_prefix import PrefixParaphraser
# from paraphrase.parameter_replacement import ParamValParaphraser
# from swagger.entities import Param, Paraphrase
# from swagger.param_sampling import ParamValueSampler
# from utils.joshua import joshua_paraphrase
# # from utils.sentence_embeddings import similarity
#
# PARAPHRASERS = [
#     'COMMON_PREFIX',
#     'APACHE_JOSHUA',
#     'NEMATUS'
# ]
#
#
# def similarity_score(utterance, ps):
#     for p in ps:
#         p.score = similarity(utterance, p.paraphrase, "UniversalSentenceEncoder")
#     ps = sorted(ps, key=lambda p: - p.score)
#     return ps
#
#
# class Paraphraser:
#     def __init__(self) -> None:
#         self.cp = PrefixParaphraser()
#         self.param_sampler = ParamValueSampler()
#         self.nematus = nematus_paraphraser
#         self.paramValParaphraser = ParamValParaphraser(param_sampler=self.param_sampler)
#
#     def paraphrase(self, utterance, params: list, paraphrase_count=10, num_of_sampled_params=10, paraphrasers=PARAPHRASERS, score=True):
#
#         ps = []
#         if not paraphrasers or 'COMMON_PREFIX' in paraphrasers:
#             ps.extend(createParaphrase(self.cp.paraphrase(utterance, paraphrase_count), params, 'COMMON_PREFIX'))
#
#         if not paraphrasers or 'APACHE_JOSHUA' in paraphrasers:
#             ps.extend(createParaphrase(joshua_paraphrase(utterance, paraphrase_count), params, 'APACHE_JOSHUA'))
#
#         if not paraphrasers or 'NEMATUS' in paraphrasers:
#             ps.extend(createParaphrase(nematus_paraphrase(utterance, paraphrase_count), params, 'NEMATUS'))
#
#         ps = ps[:paraphrase_count]
#         ps = self.paramValParaphraser.paraphrase(ps, params, num_of_sampled_params)
#
#         if score:
#             ps = similarity_score(utterance, ps)
#         ps = list(filter(lambda p: p.paraphrase.lower() != utterance.lower() and "<<" not in p.paraphrase, ps))
#         return set(ps)
#
#
# def createParaphrase(paraphrases, entities, method):
#     ret = []
#
#     for p in paraphrases:
#         p = Paraphrase(p, entities)
#         p.score = 0
#         p.method = method
#         ret.append(p)
#
#     return ret
#
#
# if __name__ == "__main__":
#     for p in Paraphraser().paraphrase("get a customer with id 1", [Param("id", example=1)]):
#         print(p)
