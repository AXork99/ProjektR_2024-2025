#!/usr/bin/env python3

from src import *
import geopandas as gpd
import os
from pathlib import Path
import importlib

def init():
    import argparse
    parser = argparse.ArgumentParser(description='Geometry generator')
    
    parser.add_argument('input_file', nargs='?', type=str, default=PLACEHOLDER,
                    help='Graph input path, (default: %(default)s)')
    # parser.add_argument('-s', '--single', action='store_true',
    #                 help='Only run single test case')
    
    parser.add_argument('-k', default=0, type=int,
                    help='Number of partitions, if 0 just reads saved partition, (default: %(default)s)')
    
    # Volotile parameters, may break kaffpa if configured
    parser.add_argument('-t', '--timeout', type=int, default=0, 
                        help='Runtime for KaHIP'),
    parser.add_argument('-i', '--imbalance', type=float, default=5,
                        help='Allowed imbalance (default: %(default)s)')
    
    parser.add_argument('-D', '--debug', action='store_true',
                        help='debug info'),
    parser.add_argument('-L', '--label', type=str, default="False",
                        help='Label clusters (default: %(default)s)')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph'),
    parser.add_argument('-P', '--paramaters', nargs=4, type=float, default=[1.5, 1, 2, 2, 1],
                        help='Hyperparamaters of rebalancing algorithm')
    
    return parser.parse_args()
args = init()

DEBUG = True if args.debug else False

def show(coloring : graphs.Coloring, ax=None):
    if not ax:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    if not args.minimal:
        display(
            coloring.G,
            # num_colors=len(coloring.clusters),
            label=False,
            draw='voronoi',
            ax=ax
        )
    display(
        coloring.C, 
        # color=False if not args.minimal else True, 
        color=True,
        num_colors=len(coloring.clusters),
        draw='all', 
        edgecolor='red',
        label=True if args.label is None else args.label, 
        ax=ax
    )
    
    return ax

def log(coloring : graphs.Coloring):
    maxerr = max(coloring.get_imbalance(), key=lambda x: x[1], default=None)
    if not DEBUG:
        print()
        print(f"ERR LOG")
        print()
        print(f"IMBALANCE: {maxerr}" if maxerr else "BALANCED")
        print()
    return maxerr

metis = graphs.MetisFormat()

input_file = Path(args.input_file)
output_file : Path = input_file.parent.parent / (input_file.name + f"_{args.k}.part")
num_regions = len(os.listdir(input_file.parent)) // 3
# num_regions = 1

from src.generator import get_color_map
patterns = get_color_map(num_regions, pattern=True)

regions = []
surplus = args.k
total = 0
for i in range(num_regions):
    meta_info : dict = gpd.read_file(str(input_file) + f"_{i + 1}_meta.geojson").to_dict('records')[0]
    total += meta_info[NODE_ATTR]
    
    meta_info[NODE_ATTR] = (reduced := int(population := meta_info[NODE_ATTR] * args.k))
    regions.append((i, meta_info, population - reduced))
    
    surplus -= meta_info[NODE_ATTR]

# print("totality check: ", total)
regions.sort(key=lambda x: x[-1], reverse=True)

for i in range(surplus):
    regions[i][1][NODE_ATTR] += 1

fig, ax = plt.subplots()
with open(output_file, 'w') as file:
    for i, region, _ in regions:
        G = metis.read(str(input_file) + f"_{i + 1}").embed().flush()
        metis.write(G)

        import run_diagnostic
        get_dimensions = importlib.reload(run_diagnostic).get_dimensions
        scale = max(get_dimensions())

        K = region[NODE_ATTR]
        name = region["name"]
        
        from shapely import Polygon, MultiLineString
        border : Polygon = region[GEOMETRY_KEY]

        if args.k:
            print(f"Region {i} \"{name}\" of scale {scale} partitions into {K} units")
            part = kaffpa(
                k=K,
                imbalance=args.imbalance,
                tl=args.timeout
            )
        else:
            part = read_partition()
        
        if DEBUG:
            display(G, label=False)

        imbalanced = True
        max_iterations = 10
        mid = 1
        while imbalanced and max_iterations:
            coloring = graphs.Coloring(
                G, 
                initial = {n+1 : c for n, c in enumerate(part)}, 
                balance = (args.imbalance - 0.5) / 100, # continuity correction
                debug=DEBUG
            )

            if coloring.inferiors:
                coloring.disolve_inferiors()

            maxx = coloring.expected_error() * 2
            maxy = scale

            print("expected_error: ", maxx/2)

            from src.utils.functions import *
            
            def cost(n=1.5, r=1, s=2 / (scale / maxx), norm=2, mid=mid):
                return cost_func(
                    x = compose(offset(POW(n)), RELU(maxx/2 * mid)), 
                    y = extend_odd(ROOT(r)),
                    xactivation = CONSTANT(1),
                    yactivation = CONSTANT(s),
                    norm=SIGNEDLNORM(norm)
                )

            # plot2d(cost(0.01)(err), minx=-maxy, maxx=maxy)
            # plot2d(cost(0.01)(err/2), minx=-maxy, maxx=maxy)
            # plot2d(cost(0.01)(err*3/2), minx=-maxy, maxx=maxy)

            if DEBUG:
                plot3d(
                    cost(), 
                    name="cost function", 
                    maxx=maxx, 
                    maxy=maxy,
                    miny=-maxy
                )

            if K != 1:
                for _ in range(100):
                    if coloring.rebalance(cost()):
                        break
                    # log(coloring)
                    # print("iteretion:", i)
                    for c1, c2 in coloring.tournament.priority:
                        if not coloring.C.has_edge(c1, c2):
                            raise KeyError(f"Tournament contains nonexistent edge {c1, c2}")

            imbalanced = log(coloring)
            max_iterations -= 1
            mid *= 2/3
        
        print(f"{'PASSED' if not imbalanced else f"IMBALANCE: {imbalanced}"}")
        if DEBUG:
            show(coloring)
            plt.show()
        
        ax = show(coloring, ax)
        
        from src.utils import reduce_polygon
        bounds = reduce_polygon(border)
        
        for bound in bounds:
            ax.add_patch(plt.Polygon(bound.coords, hatch=patterns[i][1], facecolor='none', edgecolor=patterns[i][0], alpha=0.5))
        
        for n, data in coloring.G.nodes(data=True):
            file.write(f"{data[PRIMARY_KEY]} : {int(data[GROUP_KEY])}\n")

plt.show()
fig.savefig(f"data/partition_{args.k}.svg", format='svg', bbox_inches='tight')