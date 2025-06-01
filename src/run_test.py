#!/usr/bin/env python3

from my_utils import PLACEHOLDER
from graphs import GROUP_KEY, NODE_ATTR, MetisFormat, Coloring

def init():
    import argparse
    parser = argparse.ArgumentParser(description='Geometry generator')
    # parser.add_argument('k', nargs='?', default=0, type=int,
    #                 help='Number of clusters, by default only displays previous partition')
    # parser.add_argument('-s', '--seed', type=int,
    #                 help='Graph gen and/or partition seed')
    # parser.add_argument('-n', '--new', type=int,
    #                     help='Make new graph with n nodes')
    # parser.add_argument('-t', '--timeout', type=int, default=3,
    #                     help='Timeout (default: %(default)s)')
    # parser.add_argument('-C', '--config', type=str, default='eco',
    #                     help='Run configuration {eco, fast, strong} (default: %(default)s)')
    # parser.add_argument('-i', '--imbalance', type=float, default=5,
    #                     help='Allowed imbalance (default: %(default)s)')
    parser.add_argument('-L', '--label', type=str,
                        help='Label clusters')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph')
    
    return parser.parse_args()

args = init()

G = MetisFormat().read(PLACEHOLDER).embed().flush()

def show():
    _, ax = plt.subplots(figsize=(8, 6))
    display(
        G, 
        num_colors=max(part),
        label=NODE_ATTR, 
        draw='voronoi',
        ax=ax
    )
    display(coloring.C, color=False, draw='all', label=NODE_ATTR, ax=ax)

def log():
    print()
    print(f"ERR LOG")
    print(errs := coloring.get_imbalance())
    maxerr = max(errs, key=lambda x: x[1], default=None)
    print(f"IMBALANCE: {maxerr}" if maxerr else "BALANCED")
    print()

from kaffpa import read_partition
part = read_partition()

coloring = Coloring(G, {n+1 : c for n, c in enumerate(part)})

import matplotlib.pyplot as plt
from display import display

if coloring.inferiors:
    coloring.disolve_inferiors()

show()
plt.show()
log()

n = 100
for i in range(n):
    if coloring.rebalance():
        break

show()
plt.show()
log()