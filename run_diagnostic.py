#!/usr/bin/env python3

from src import *

metis = graphs.MetisFormat()

G = metis.read().embed().flush()

# for n, d in G.nodes(data=True):
#     print (n, d.keys())

def attr(obj, name):
    return lambda x: obj[x].get(name)

def nodes(f, key):
    return f(map(attr(G.nodes, key), G.nodes))

def edges(f, key):
    return f(map(attr(G.edges, key), G.edges))

print(f"max_population: {nodes(max, NODE_ATTR)}")
print(f"min_population: {nodes(min, NODE_ATTR)}")

display(G, label=NODE_ATTR)
