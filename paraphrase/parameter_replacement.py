import warnings

from swagger.param_sampling import ParamValueSampler


class ParamValParaphraser:
    def __init__(self, param_sampler: ParamValueSampler) -> None:
        self.param_sampler = param_sampler

    def paraphrase(self, paraphrases: list, params: list, n: int) -> list:
        valid_uttrs = []

        if not params:
            return paraphrases

        cparams = [p.clone() for p in params]
        ret = []
        for paraph in paraphrases:
            all_params = True

            if "<<" not in paraph.paraphrase and not params:
                ret.append(paraph)
                continue

            for p in cparams:
                if "<< {} >>".format(p.name) not in paraph.paraphrase:
                    all_params = False
                    break
            if all_params:
                valid_uttrs.append(paraph)

        for p in params:
            values = self.param_sampler.sample(p, n)
            pname = "<< {} >>".format(p.name)
            new_utter = []

            if not values:
                warnings.warn("Unable to sample value: {}".format(p.to_json()))
                continue

            for v in values:
                for paraph in valid_uttrs:
                    paraph = paraph.clone()
                    paraph.paraphrase = paraph.paraphrase.replace(pname, str(v))
                    for c in paraph.entities:
                        if c.name == p.name:
                            c.example = v
                        else:
                            continue

                    new_utter.append(paraph)
            valid_uttrs = new_utter
            # ret.extend(new_utter)
        ret.extend(valid_uttrs)
        return ret
