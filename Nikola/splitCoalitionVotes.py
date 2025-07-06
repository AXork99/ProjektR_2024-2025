from math import inf

class SplitCoalitionVotes:
    def __init__(self, components):
        self.components = list(components)
        self.party_component_map = {}
        for i, comp in enumerate(components):
            for party in comp:
                if self.party_component_map.get(party) is not None:
                    raise Exception(f"Party {party} appeared multiple times. Components must be disjunct and have no duplicates.")
                self.party_component_map[party] = i
        self.rules = []

    @classmethod 
    def from_file(path, sep = ","):
        f = open(path, "r")
        components = [frozenset(line[:-1].split(sep)) for line in f]
        return SplitCoalitionVotes(components)

    def add_rules(self, rules):
        try: # lista
            self.rules.extend(rules)
        except: # jedno pravilo
            self.rules.append(rules)

    def __call__(self, coalition):
        comps = set()
        for party in coalition:
            comps.add(self.components[self.party_component_map[party]])
        comps = list(comps)
        result = None
        for rule in self.rules:
            result = rule(comps)
            if result is not None: break
        return result
    

class LargestPartyComponentRule:
    def __init__(self, parties_by_size):
        self.parties_by_size = parties_by_size

    @classmethod
    def from_file(cls, path):
        f = open(path, "r", encoding="UTF-8")
        return LargestPartyComponentRule([line[:-1] for line in f])
    
    def __call__(self, comps):
        minComp = None; minPos = inf
        for c in comps:
            for party in c:
                # print(party)
                pos = self.parties_by_size.index(party)
                if pos < minPos and pos >= 0:
                    minComp = c
        if minComp is not None:
            return {minComp: 1}
        return None


class ProportionalToWeightRule:
    def __init__(self, party_weights):
        self.party_weights = party_weights

    @classmethod
    def from_file(path, sep = ","):
        f = open(path, "r")
        l = [line[:-1].split(sep) for line in f.readlines()]
        for i in l: l[1] = float(l[1])            
        return ProportionalToWeightRule(dict(l))
    
    def __call__(self, comps):
        total = 0
        res = {}
        for c in comps:
            res[c] = 0
            for party in c: res[c] += self.party_weights.get(party, 0)
            total += res[c]
        if total == 0:
            return None
        for c in res.keys(): res[c] /= total
        return res

class EqualRule:
    def __call__(self, comps):
        return dict.fromkeys(comps, 1 / len(comps))