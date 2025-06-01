#!/usr/bin/env python3

from my_utils import PLACEHOLDER

def init():
    import argparse
    parser = argparse.ArgumentParser(description='Geometry generator')
    parser.add_argument('input_file', nargs='?', type=str, default=PLACEHOLDER,
                    help='Graph input path, (default: %(default)s)')
    parser.add_argument('-k', default=0, type=int,
                    help='Number of partitions, if 0 just reads saved partition, (default: %(default)s)')
    parser.add_argument('-t', '--timeout', type=int, default=3,
                        help='Runtime for KAhIP'),
    parser.add_argument('-i', '--imbalance', type=float, default=5,
                        help='Allowed imbalance (default: %(default)s)')
    parser.add_argument('-L', '--label', type=str,
                        help='Label clusters')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph'),
    parser.add_argument('-P', '--paramaters', nargs=4, type=float, default=[0.01, 1.4, 1.8, 4],
                        help='Hyperparamaters of rebalancing algorithm')
    return parser.parse_args()

args = init()

from graphs import MetisFormat
metis = MetisFormat()

G = metis.read(args.input_file).embed().flush()
metis.write(G, data=True)

from kaffpa import kaffpa, read_partition
if args.k:
    part = kaffpa(
        k=args.k,
        imbalance=args.imbalance,
        tl=args.timeout,
    )
else:
    part = read_partition()

from graphs import Coloring
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