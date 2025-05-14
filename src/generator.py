#!/usr/bin/env python3
import argparse

import numpy as np
from numpy.random import Generator
import networkx as nx

from shapely.geometry import Polygon, Point
from collections import defaultdict

from my_utils import NODE_ATTR, EDGE_ATTR, GEOMETRY_KEY, LONGITUDE, LATITUDE, seeded

def get_color_map(num_colors, pattern: bool | list = None):    
    import distinctipy
    from itertools import cycle
    
    if pattern == True:
        pattern = ['/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*']

    colors = distinctipy.get_colors(num_colors, pastel_factor=0.0)  # Disable pastel tones for higher contrast

    hatches = cycle(pattern) if pattern else None
    
    return list(zip(colors, hatches)) if hatches else colors

@seeded
def get_random_points(num: int, boundary: Polygon | tuple = None, rng: Generator = None, seed: int = None):
    minx, maxx, miny, maxy = \
        boundary.bounds if isinstance(boundary, Polygon) else \
        boundary if boundary else np.array((-1, 1, -1, 1)) * num / 2
        
    points = set()
    while len(points) < num:
        random_point = tuple(rng.uniform(low=[minx, miny], high=[maxx, maxy], size=2))
        if not isinstance(boundary, Polygon) or boundary.contains(random_point):
            points.add(random_point)
    
    print(f"Generated {num} points (seed: {seed})")
    return list(points)

@seeded
def make_delunay(points: int | list, seed: int = None):
    from scipy.spatial import Delaunay
    
    if isinstance(points, int):
        points = get_random_points(points, seed=seed)
    
    simplices = Delaunay(points).simplices
    
    G_dual = nx.Graph()
    
    G_dual.add_nodes_from(
        (i + 1, {
            LONGITUDE : (center := np.mean(poly, axis=0))[0],
            LATITUDE : center[1],
            GEOMETRY_KEY : Polygon(poly)
        })
        for i, poly in enumerate(points[simplices])
    )
    
    edge_map = defaultdict(list)
    
    edges = np.sort(simplices[:,[0,1,1,2,2,0]].reshape(-1,2), axis=1)
    for i, edge in enumerate(edges):
        edge_map[tuple(edge)].append(i // 3)  # Integer division maps edges back to simplices
    
    G_dual.add_edges_from(
        (pair[0], pair[1], {EDGE_ATTR: np.linalg.norm(points[p1] - points[p2])})
        for (p1, p2), pair in edge_map.items()
        if len(pair) == 2
    )
    
    return G_dual

@seeded
def make_voronoi(points = int | list[Point], boundary: Polygon = None, seed: int = None):
    from my_utils import make_convex, get_midpoint
    from scipy.spatial import Voronoi
    from shapely import box
    
    if isinstance(points, int):
        points = get_random_points(points, boundary=boundary, seed=seed)
    
    points = np.asarray(points)
        
    if not boundary:
        min_coords = np.min(points, axis=0)
        max_coords = np.max(points, axis=0)
        
        MAX = np.max(max_coords-min_coords, axis=0)
        PAD =  MAX / 20  # Bounding box padding
        LINE = MAX * 20  # Length for extending infinite edges
        
        boundary = box(min_coords[0]-PAD, min_coords[1]-PAD,
                max_coords[0]+PAD, max_coords[1]+PAD)

    vor = Voronoi(points)
    G_dual = nx.Graph()
    
    MID = Point(np.average(points, axis=0))
    
    # Step 1: Handle infinite ridges
    infinite = defaultdict(list)
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        if v1 == -1 or v2 == -1:
            midpoints = get_midpoint(vor.points[p1], vor.points[p2], LINE)
            mid = max(midpoints, key=lambda p: Point(p).distance(MID)) 
            infinite[vor.point_region[p1]].append(mid)
            infinite[vor.point_region[p2]].append(mid)
    
    # Step 2: Create valid polygons for each cell
    for i in range(len(points)):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        
        if not region:
            raise ValueError(f'Invalid region {i + 1}')
        
        # Case 1: Finite Voronoi cell
        if -1 not in region:
            cell_poly = Polygon(vor.vertices[region])
        # Case 2: Infinite Voronoi cell
        else:
            finite_verts = [vor.vertices[v] for v in region if v != -1]
            # print(i)
            cell_poly = make_convex(finite_verts + infinite[region_idx]) or Polygon(finite_verts)
        
        # Final validation and clipping
        if cell_poly and cell_poly.is_valid:
            clipped = cell_poly.intersection(boundary)
            if not clipped.is_empty:
                if clipped.geom_type == 'MultiPolygon':
                    clipped = max(clipped.geoms, key=lambda p: p.area)
                
                if clipped.geom_type == 'Polygon':
                    cell_poly = clipped
        else:
            print('Bad region:', region)
        
        center = cell_poly.centroid
        G_dual.add_node(
            i + 1,
            **{
                LONGITUDE : center.x,
                LATITUDE : center.y,
                GEOMETRY_KEY : cell_poly
            }
        )
    
    def dist(p1, p2):
        if not p1 or not p2:
            return None
        
        poly1 : Polygon = G_dual.nodes[p1][GEOMETRY_KEY]
        poly2 : Polygon = G_dual.nodes[p2][GEOMETRY_KEY]
        
        intersection = poly1.boundary.intersection(poly2.boundary)
        
        if intersection.is_empty:
            return None
        
        if intersection.geom_type == "MultiLineString":
            return sum(linestring.length for linestring in intersection.geoms)
        else:
            return intersection.length
    
    try:
        G_dual.add_edges_from(
            (p1 + 1, p2 + 1, {EDGE_ATTR: int(d * 1000)})
            for p1, p2 in vor.ridge_points if (d := dist(p1 + 1, p2 + 1)) is not None
        )
    except:
        for n, data in G_dual.nodes(data=True):
            print(n, ':', data)
    
    return G_dual

@seeded
def populate(G: nx.Graph, max: int = 10000, min: int = 1, rng: Generator = None, seed: int = None):
    for n, data in G.nodes(data=True):
        data[NODE_ATTR] = rng.integers(min, max) 
        
    print(f"Populated graph (seed: {seed})")

if __name__ == "__main__":
    
    ALGORITHM = {
        "voronoi": make_voronoi,
        "delunay": make_delunay
    }    
    
    def init():
        parser = argparse.ArgumentParser(description='Geometry generator')

        # Positional arguments
        parser.add_argument('algorithm', choices = ALGORITHM.keys(),
                        metavar='algorithm',
                        help='Type of geometry to generate (choices: %(choices)s)')
        parser.add_argument('n', type=int,
                        help='Number of faces (for voronoi) or nodes (for delaunay)')

        # Optional arguments
        parser.add_argument('-W', '--width', type=float, default=10.0,
                        help='Width of the space (default: %(default)s)')
        parser.add_argument('-H', '--height', type=float, default=10.0,
                        help='Height of the space (default: %(default)s)')
        parser.add_argument('-P', '--max_population', type=int, default=100000,
                        help='Max population for single node (default: %(default)s)')
        parser.add_argument('-s', '--seed', type=int,
                        help='Generation seed')
        
        parser.add_argument('-q', '--quiet', action='store_true',
                        help='Supress graph output')
        parser.add_argument('-c', '--color', action='store_true',
                        help='Color graph')
        parser.add_argument('-F', '--fancy', action='store_true',
                        help='Add hatches to graph')
        parser.add_argument('-L', '--label', type=str,
                        help='Label graph feature')
        parser.add_argument('-o', '--output',
                        help='Output filename')
        
        return parser.parse_args()
    
    args = init()
    
    seed = args.seed or np.random.SeedSequence().entropy
    print('Seed used:', seed)
    
    G = ALGORITHM[args.algorithm](
        get_random_points(
            args.n, 
            boundary=(
                -args.width/2, 
                args.width/2, 
                -args.height/2, 
                args.height/2
            ),
            seed=seed
        )
    )
    populate(G, seed=seed)

    from my_utils import MetisFormat
    MetisFormat().write(G, args.output)
    
    if not args.quiet:
        from display import display
        display(G, label = args.label, pattern = args.color and args.fancy)