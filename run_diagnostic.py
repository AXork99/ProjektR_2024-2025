#!/usr/bin/env python3

from src import *
from src.utils import avg, attr

compose = functions.compose

metis = graphs.MetisFormat()

G = metis.read().embed().flush()

def nodes(fs, key):
    return [f(list(map(attr(G.nodes, key), G.nodes))) for f in fs]

def edges(fs, key):
    return [f(list(map(attr(G.edges, key), G.edges))) for f in fs]

def get_dimensions():
    W, E, S, N = *nodes([min, max], LATITUDE), *nodes([min, max], LONGITUDE)
    return (E - W) * (10 ** PERCISION), (N - S) * (10 ** PERCISION)

if __name__ == "__main__":
    
    for name, f in (NODE_ATTR, nodes), (EDGE_ATTR, edges):
        print(
            "avg_{v} : {0:.2f}\n \
            min_{v} : {1:d}\n \
            max_{v} : {2:d}\n" \
            .format(*f([avg, min, max], name), v=name)
        )

    print(f"zero_weights : {edges([compose(sum, lambda arr : map(lambda x: 1 if x == 0 else 0, arr))], EDGE_ATTR)}")

    print("total_width : {1:.2f}\ntotal_height : {1:.2f}".format(*get_dimensions()))

    display(G)
