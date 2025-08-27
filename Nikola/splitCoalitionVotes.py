from math import inf

class SplitCoalitionVotes:
    def __init__(self, components):
        self.components = list(components)
        self.party_component_map = {}
        for i, comp in enumerate(components):
            for party in comp:
                if self.party_component_map.get(party) is not None:
                    raise Exception(f"Party {party} appeared multiple times. Components must be disjunct and have no duplicates within a component.")
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
        # primijeni prvo pravilo u listi koje daje rezultat
        for rule in self.rules:
            result = rule(comps)
            if result is not None: break
        return result
    
# Pravila vraćaju dict {komponenta koalicije: udio glasova}. Zbroj udjela je 1, nesadržane komponente imaju udio 0

# Pridjeljuje sve glasove komponenti koja sadrži najveću stranku u koaliciji
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
                try: 
                    pos = self.parties_by_size.index(party)
                    if pos < minPos and pos >= 0:
                        minComp = c
                except: pass
        if minComp is not None:
            return {minComp: 1}
        return None

# Komponente dobivaju težine proporcionalne zbroju postotaka birača koji podržavaju pojedinu stranku po svim strankama u komponenti. 
# Udjele većih stranaka može se dobiti iz predizbornih anketa (npr. IPSOS Crobarometar), a nepoznati udjeli se broje kao 0

class ProportionalToWeightRule:
    def __init__(self, party_weights):
        self.party_weights = party_weights

    @classmethod
    def from_file(cls, path, sep = ","):
        f = open(path, "r")
        l = [line[:-1].split(sep) for line in f.readlines()]
        for i in l: i[1] = float(i[1])  
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

# sve komponente u koaliciji dobiju jednak udio glasova 
# korišteno za koalicije malih stranki s koje imaju približno jednake potpore birača ili o njima nema pouzdanih podataka
class EqualRule:
    def __call__(self, comps):
        return dict.fromkeys(comps, 1 / len(comps))