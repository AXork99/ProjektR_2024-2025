#!/usr/bin/env python3

from collections import defaultdict
from queue import PriorityQueue as pqueue
from typing import Iterable
import generator as gen
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

import argparse

from my_utils import MetisFormat, Identifiable, GROUP_KEY, PLACEHOLDER, NODE_ATTR, EDGE_ATTR, LONGITUDE, LATITUDE, GEOMETRY_KEY
import generator as gen

from display import display
from kaffpa import kaffpa, read_partition

class Tournament:
    class Node(Identifiable):
        def __init__(self, data = None, children = set()):
            self.data = data
            self.children : set[Tournament.Node] = children
            for child in children:
                self.add_child(child)
            self.parent : Tournament.Node = None
        
        def add_child(self, child):
            self.children.add(child)
            child.parent = self
            
    def __init__(self, sequence = [], key = lambda x: x):
        self.key = key
        self.bottom : list[Tournament.Node] = []
        self.top = None
        for s in sequence:
            self.add(s)
    
    def add(self, s):
        other = self.bottom[-1].parent
        me = Tournament.Node(s)
        self.bottom.append(me)
        while len(other.children) > 1:
            other = other.parent
            me = Tournament.Node(s, children={me})
            if other.parent is None:
                other = Tournament.Node(children={other})
                self.top = other
        other.children.add(me)
        self.update(other)
    
    def update(self, node, val = None):
        def f(node: Tournament.Node):
            if val is not None and node not in self.bottom:
                raise IndexError(f"Node {node} cannot be changed directly!")
            node.data = val if val else max(node.children, key=self.key).data
            self.update(node.parent)
        if node:
            f(node)
            
    def get(self):
        return self.top.data

class Coloring:
    class Cluster(Identifiable):
        def __init__(self, G: nx.graph, C: nx.DiGraph, id, initial = set()):
            self.G : nx.Graph = G
            self.C : nx.DiGraph = C
            self.id = id
            
            self.center = np.zeros(2)
            self.population = 0
            self.geometry = set()
            
            self.nodes = set()
            self.perimeter = set()
            
            self.add(initial)
        
        def outer_perimeter(self):
            return {n for _, n in self.perimeter}
        
        def inner_perimeter(self):
            return {n for n, _ in self.perimeter}
        
        def get_perimeter(self, other):
            def f(other: Coloring.Cluster):
                return {(n1, n2) for n1, n2 in self.perimeter if n2 in other.nodes}
            return f(other)
        
        def add(self, node: Iterable | int):
            if isinstance(node, Iterable):
                for n in node:
                    self.add(n)
            else:
                self.G.nodes[node][GROUP_KEY] = self
                
                self.population += self.G.nodes[node][NODE_ATTR]
                self.center += np.array([
                    self.G.nodes[node][LONGITUDE], 
                    self.G.nodes[node][LATITUDE]
                ])
                self.geometry.add(self.G.nodes[node][GEOMETRY_KEY])
                self.nodes.add(node)
                
                for n in self.G.neighbors(node):
                    if n in self.nodes:
                        self.perimeter.remove((n, node))
                    else:
                        self.perimeter.add((node, n))
        
        def __repr__(self):
            return f"Cluster {self.id}"
        
        def __int__(self):
            return int(self.C.nodes[self][GROUP_KEY])
        
        def __iter__(self):
            return iter(self.nodes)
    
    def __init__(self, G: nx.Graph, initial: dict):
        self.G: nx.Graph = G
        self.C = nx.DiGraph()
        for node, data in G.nodes(data=True):
            data[GROUP_KEY] = Coloring.Cluster(G, self.C, id=node, initial={node})
        
        self.C.add_nodes_from([
            (self.get_cluster(node), { 
                GROUP_KEY: initial.get(node),
                NODE_ATTR: self.G.nodes[node][NODE_ATTR], 
                LONGITUDE: self.G.nodes[node][LONGITUDE], 
                LATITUDE: self.G.nodes[node][LATITUDE], 
                GEOMETRY_KEY: { self.G.nodes[node][GEOMETRY_KEY] }
            })
            for node in G.nodes
        ])
        
        for n1, n2, data in G.edges(data=True):
            c1, c2 = self.get_cluster(n1, n2)
            if c1 == c2:
                continue
            if self.get_attr(c1, GROUP_KEY) != self.get_attr(c2, GROUP_KEY):
                self.add_edge(n1, n2)
            else:
                if c1.population > c2.population:
                    self.collapse(c1, c2)
                else:
                    self.collapse(c2, c1)
    
    def get_cluster(self, *node):
        if len(node) > 1:
            return [self.get_cluster(n) for n in node]
        def f() -> Coloring.Cluster:
            return self.G.nodes[node[0]][GROUP_KEY]
        return f()
    
    def get_attr(self, obj, attr):
        if not isinstance(obj, Coloring.Cluster):
            obj = self.get_cluster(obj)
        return self.C.nodes[obj][attr]
    
    def update(self, c):
        def f(c: Coloring.Cluster):
            self.C.nodes[c].update({
                NODE_ATTR: c.population, 
                LONGITUDE: c.center[0] / len(c.nodes), 
                LATITUDE: c.center[1] / len(c.nodes), 
                GEOMETRY_KEY: c.geometry
            })
        f(c)
    
    def add_edge(self, n1, n2):
        c1, c2 = self.get_cluster(n1, n2)
        if not (self.C.has_edge(c1, c2)):
            self.C.add_edge(c1, c2, **{EDGE_ATTR : set()})
            self.C.add_edge(c2, c1, **{EDGE_ATTR : set()})
        
        self.C[c1][c2][EDGE_ATTR].add((n1, n2))
        self.C[c2][c1][EDGE_ATTR].add((n2, n1))
    
    def collapse(self, c1, c2, force = False):
        def f(c1: Coloring.Cluster, c2: Coloring.Cluster):
            if not force and not self.C.has_edge(c1, c2) and not c1.get_perimeter(c2):
                raise KeyError(f"{c1} and {c2} aren't incident!")
            neighbors = set(self.C.neighbors(c1)).intersection(self.C.neighbors(c2))
            for n in neighbors:
                self.C[c1][n][EDGE_ATTR].update(self.C[c2][n][EDGE_ATTR])
                self.C[n][c1][EDGE_ATTR].update(self.C[n][c2][EDGE_ATTR])
            c1.add(c2)
            nx.contracted_nodes(self.C, c1, c2, self_loops=False, copy=False)
            self.update(c1)    
        f(c1, c2)
    
    def __iter__(self):
        return iter(self.C.nodes)
    
    def __repr__(self):
        return f"Neighborhood:\n{'\n'.join(map(str, self))}"

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
    parser.add_argument('-L', '--label', type=str,
                        help='Label clusters')
    parser.add_argument('-M', '--minimal', action='store_true',
                        help='Only draw voronoi graph')
    
    return parser.parse_known_args()

args, fwd = init()

G = metis.read(PLACEHOLDER).embed().flush()

# FIXIT
# else:
#     G = gen.make_voronoi(args.new, seed=args.seed)
#     metis.write(G)

if args.k:
    part = kaffpa(
        k=args.k,
        seed=args.seed,
        config = args.config,
        imbalance=args.imbalance,
        tl=args.timeout
    )
else:
    part = read_partition()

coloring = Coloring(G, {n+1 : c for n, c in enumerate(part)})

fig, ax = plt.subplots(figsize=(8, 6))

display(
    G, 
    num_colors=args.k or max(part),
    label=True if args.label is None else args.label, 
    draw='voronoi',
    ax=ax
)

def cleanup(coloring: Coloring, ax = ax):
    C = coloring.C
    G = coloring.G
    for c1, c2, data in C.edges(data=True):
        print(f"\nperimeter between: {c1} {c2}:")
        perim = data[EDGE_ATTR]
        for n1, n2 in perim:
            l = G[n1][n2][EDGE_ATTR]
            print(f"({n1} {n2})", end='; ')
        # print(f"\nREAL perimeter between: {c1} {c2}:")
        # for n1, n2 in c1.get_perimeter(c2):
        #     print(f"({n1} {n2})", end='; ')
    
    
cleanup(coloring)

print(coloring.C.nodes)

display(coloring.C, color=False, ax=ax)

plt.show()
