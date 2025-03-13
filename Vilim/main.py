import os
import graphs as g

G1 = g.get_map(os.getcwd() + "/Juraj/dual_graph/dual.graphml")

edgecut, blocks = g.bisect(G1, "Ukupno birača", 144)

with open("partition", 'w') as f:
        for b in blocks:
            f.write(str(b) + "\n")