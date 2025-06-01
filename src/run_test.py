#!/usr/bin/env python3

from graphs import GROUP_KEY, NODE_ATTR, MetisFormat, Coloring

def init():
    import argparse
    parser = argparse.ArgumentParser(description='Geometry generator')
    # parser.add_argument('k', nargs='?', default=0, type=int,
    #                 help='Graph gen and/or partition seed')
    # parser.add_argument('-n', '--new', type=int,
    #                     help='Make new graph with n nodes')
    # parser.add_argument('-t', '--timeout', type=int, default=3,
    parser.add_argument('-i', '--imbalance', type=float, default=5,
                        help='Allowed imbalance (default: %(default)s)')
    parser.add_argument('-L', '--label', type=str,
                        help='Label clusters')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph')
    parser.add_argument('-P', '--paramaters', nargs=4, type=float, default=[0.01, 1, 1, 1])
    
    return parser.parse_args()

args = init()

G = MetisFormat().read().embed().flush()

from kaffpa import read_partition
part = read_partition()

coloring = Coloring(
    G, 
    initial = {n+1 : c for n, c in enumerate(part)}, 
    balance = args.imbalance / 100
)

def show():
    _, ax = plt.subplots(figsize=(8, 6))
    display(
        coloring.G, 
        num_colors=max(part),
        label=True if args.label is None else args.label, 
        draw='voronoi',
        ax=ax
    )
    display(
        coloring.C, 
        color=False, 
        draw='all' if not args.minimal else 'voronoi', 
        label=True if args.label is None else args.label, 
        ax=ax
    )

def log():
    print()
    print(f"ERR LOG")
    print(errs := coloring.get_imbalance())
    maxerr = max(errs, key=lambda x: x[1], default=None)
    print(f"IMBALANCE: {maxerr}" if maxerr else "BALANCED")
    print()

import matplotlib.pyplot as plt
from display import display

if coloring.inferiors:
    coloring.disolve_inferiors()

show()
log()
plt.show()

n = 100
for i in range(n):
    if coloring.rebalance(*args.paramaters):
        break
    print("iteretion:", i)
    for c1, c2 in coloring.tournament.priority:
        if not coloring.C.has_edge(c1, c2):
            raise KeyError(f"Tournament contains nonexistent edge {c1, c2}")

show()
log()
plt.show()