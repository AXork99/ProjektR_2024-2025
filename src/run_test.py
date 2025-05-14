#!/usr/bin/env python3

import geopandas as gpd
import generator as gen

import argparse

from my_utils import MetisFormat, KaHIP, GROUP_KEY, PLACEHOLDER, NODE_ATTR, noExtension
import generator as gen

from pathlib import Path
import os

from display import display
from kaffpa import kaffpa, read_partition

metis = MetisFormat()

def init():
    parser = argparse.ArgumentParser(description='Geometry generator')

    parser.add_argument('k', nargs='?', default=0, type=int,
                    help='Number of clusters, by default only displays previous partition')
    parser.add_argument('-s', '--seed', type=int,
                    help='Graph gen and/or partition seed')
    parser.add_argument('-n', '--new', type=int,
                        help='Make new graph with n nodes')
    parser.add_argument('-t', '--timeout', type=int, default=3,
                        help='Timeout (default: %(default)s)')
    parser.add_argument('-C', '--config', type=str, default='eco',
                        help='Run configuration {eco, fast, strong} (default: %(default)s)')
    parser.add_argument('-i', '--imbalance', type=float, default=5,
                        help='Allowed imbalance (default: %(default)s)')
    parser.add_argument('-L', '--label', action='store_true',
                        help='Label clusters')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph')
    
    return parser.parse_known_args()

args, fwd = init()

if (not args.new):
    G = metis.read(PLACEHOLDER).embed().flush()
else:
    G = gen.make_voronoi(args.new, seed=args.seed)
    gen.populate(G, seed=args.seed)
    metis.write(G)

if args.k:
    part = kaffpa(
        k=args.k, 
        seed=args.seed,
        config = args.config,
        imbalance=args.imbalance,
        tl=args.timeout
        # partition='a.part' if not args.new else None,
    )
else:
    part = read_partition()

for bm, ij in enumerate(part):
    G.nodes[bm + 1][GROUP_KEY] = ij

display(
    G, 
    num_colors=args.k or max(part), 
    label=GROUP_KEY if args.label else None, 
    draw='voronoi' if args.minimal else 'all'
)