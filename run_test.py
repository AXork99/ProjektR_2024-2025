#!/usr/bin/env python3

from src import *

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
    
    parser.add_argument('-L', '--label', type=str, default="False",
                        help='Label clusters (default: %(default)s)')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph'),
    parser.add_argument('-P', '--paramaters', nargs=4, type=float, default=[1.5, 1.2, 50, 3],
                        help='Hyperparamaters of rebalancing algorithm')
    
    return parser.parse_args()

args = init()

metis = graphs.MetisFormat()

G = metis.read(args.input_file).embed().flush()
if args.input_file != PLACEHOLDER:
    metis.write(G)

# display(G, label=args.label)

if args.k:
    part = kaffpa(
        k=args.k,
        imbalance=args.imbalance,
        tl=args.timeout,
    )
else:
    part = read_partition()

coloring = graphs.Coloring(
    G, 
    initial = {n+1 : c for n, c in enumerate(part)}, 
    balance = args.imbalance / 100
)

def show():
    _, ax = plt.subplots(figsize=(8, 6))
    display(
        coloring.G, 
        num_colors=max(part),
        label=False if args.label is None else args.label, 
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

if coloring.inferiors:
    coloring.disolve_inferiors()

show()
log()
plt.show()

maxx = coloring.expected_error() * 2
maxy = 1000

from src.utils.functions import *

def cost(n=1.5, r=1.2, s=50, norm=3):
    return cost_func(
        x = compose(offset(POW(n)), RELU(maxx / 2)), 
        y = extend_odd(ROOT(r)),
        xactivation = CONSTANT(1),
        yactivation = CONSTANT(s),
        norm=SIGNEDLNORM(norm)
    )

# plot2d(cost(0.01)(err), minx=-maxy, maxx=maxy)
# plot2d(cost(0.01)(err/2), minx=-maxy, maxx=maxy)
# plot2d(cost(0.01)(err*3/2), minx=-maxy, maxx=maxy)

plot3d(
    cost(), 
    name="cost function", 
    maxx=maxx, 
    maxy=maxy,
    miny=-maxy
)

n = 100
for i in range(n):
    if coloring.rebalance(cost()):
        break
    print("iteretion:", i)
    for c1, c2 in coloring.tournament.priority:
        if not coloring.C.has_edge(c1, c2):
            raise KeyError(f"Tournament contains nonexistent edge {c1, c2}")

show()
log()
plt.show()