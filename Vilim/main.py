import os
import graphs as g

G1 = g.get_map(os.getcwd() + "/Juraj/dual_graph/dual.graphml")

p = "Ukupno birača"
l = "length"
k = 144

edgecut, blocks, err = g.bisect(
    G1, 
    nkey = p, ekey = l, 
    nblocks = k, 
    imbalance = 0.005, 
    mode = 1
)

print("err:", max(err))

with open("partition", 'w') as f:
        for b in blocks:
            f.write(str(b) + "\n")