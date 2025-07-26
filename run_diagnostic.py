#!/usr/bin/env python3

from src import *
from src.utils import avg, attr

compose = functions.compose

import sys

metis = graphs.MetisFormat()

G = metis.read(sys.argv[1] if len(sys.argv) >= 2 else PLACEHOLDER).embed().flush()
if len(sys.argv) >= 2:
    metis.write(G)

def nodes(fs, key):
    return [f(list(map(attr(G.nodes, key), G.nodes))) for f in fs]

def edges(fs, key):
    return [f(list(map(attr(G.edges, key), G.edges))) for f in fs]

for name, f in (NODE_ATTR, nodes), (EDGE_ATTR, edges):
    print(
        "avg_{v} : {0:.2f}\n \
        min_{v} : {1:d}\n \
        max_{v} : {2:d}\n" \
        .format(*f([avg, min, max], name), v=name)
    )

W, E, S, N = *nodes([min, max], LATITUDE), *nodes([min, max], LONGITUDE)

print(f"zero_weights : {edges([compose(sum, lambda arr : map(lambda x: 1 if x == 0 else 0, arr))], EDGE_ATTR)}")

print(f"total_width : {(E - W) * (10 ** PERCISION):.2f} ")
print(f"total_height : {(N - S) * (10 ** PERCISION):.2f}")


# display(G, label=False)
