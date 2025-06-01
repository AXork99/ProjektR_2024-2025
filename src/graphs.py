import networkx as nx
import numpy as np

NODE_ATTR = "population"
GROUP_KEY = "IJ"
PRIMARY_KEY = "BM"
GEOMETRY_KEY = "geometry"
LONGITUDE = 'longitude'
LATITUDE = 'latitude'

EDGE_ATTR = "weight"
EDGE_ID = "id"

class KaHIP:
    def __init__(self, kahip_dir: str = "KaHIP"):
        from pathlib import Path
        
        self.kahip_dir = Path(kahip_dir) 
        self.deploy_dir = self.kahip_dir / "deploy"
    
    def list_binaries(self) -> list[str]:
        import os
        return [f.name for f in self.deploy_dir.iterdir() if f.is_file() and os.access(f, os.X_OK)]
    
    def run_binary(
        self, binary_name: str,
        args: list[str] = None,
        kwargs: dict[str, str] = None,
        timeout: float = None,
        capture_output: bool = False
    ):
        import subprocess
        import os
        from my_utils import cmd_format
        
        binary_path = self.deploy_dir / binary_name
        if not binary_path.exists():
            raise FileNotFoundError(f"Binary {binary_name} not found in {self.deploy_dir}")
        
        if not os.access(binary_path, os.X_OK):
            raise PermissionError(f"Binary {binary_name} is not executable")
        
        cmd = [f"{binary_path}"]
        cmd += cmd_format(*args, **kwargs)
        
        print(cmd)
        
        try:
            return subprocess.run(
                cmd,
                timeout=timeout,
                check=True,
                capture_output=capture_output,
                text=True
            )
        except subprocess.TimeoutExpired as e:
            print(f"Command timed out after {timeout} seconds")
            raise e
        except subprocess.CalledProcessError as e:
            print(f"Command {e.cmd} returned code {e.returncode}\nstderr: {e.stdout}\nstdout: {e.stderr}")
            raise e

METIS_FLAGS = 11

class MetisFormat:
    from my_utils import PLACEHOLDER
    
    def __init__(
        self, 
        flags: int = METIS_FLAGS,
        node_attr: str = NODE_ATTR,
        edge_attr: str = EDGE_ATTR,
        id: str = PRIMARY_KEY,
        default_name: str = PLACEHOLDER
    ):
        self.flags = flags
        self.node_attr = node_attr
        self.edge_attr = edge_attr
        self.id = id
        self.default_name = default_name
        self.extentions = {
            '.geojson', 
            '.graph'
        }
        self.G = None
        self.data = None
    
    def read(self, filename: str = None):
        import re
        import geopandas as gpd
        
        if not filename:
            filename = self.default_name
        
        if not re.search(r'\.[a-zA-Z]*$', filename):
            filename = [filename + ext for ext in self.extentions]
        else:
            filename = [filename]
        
        for file in filename:
            if file.endswith(".geojson"):
                self.data = gpd.read_file(file).set_index(self.id)
            
            elif file.endswith(".graph"):
                with open(file, 'r') as f:
                    f.readline()
                    G = nx.Graph()
                    
                    i = 1
                    while (line := f.readline()):
                        line = line.split()
                        G.add_node(i, **{self.node_attr: int(line[0])})
                        
                        for it in np.arange(1, len(line), 2):
                            j, w = int(line[it]), int(line[it + 1])
                            G.add_edge(i, j, **{self.edge_attr: w})

                        i += 1
                    
                    self.G = G
            else:
                raise TypeError(
                    f"Unrecogised file extension: .{file.split('.').pop()}\n \
                        Allowed extensions are: {self.extentions}"
                )
                
        return self
    
    def embed(self):
        if self.G is None or self.data is None:
            raise ValueError("No data or graph defined!")
        
        for n, data in self.G.nodes(data=True):
            for col in self.data:
                data[col] = self.data.loc[n, col]
                
        self.data = None 
        return self
    
    def flush(self):
        if self.G is None:
            raise ValueError("No graph defined!")
        
        G = self.G.copy()
        self.G = None
        
        if self.data is None:
            return G
        
        data = self.data.copy()
        self.data = None
        
        return G, data
        
    def write(self, G: nx.Graph, filename: str = None, data = True):
        import geopandas as gpd
        
        if not filename:
            filename = self.default_name
            
        with open(filename + '.graph', 'w') as f:
            f.write(f"{G.number_of_nodes()} {G.number_of_edges()} {self.flags}\n")
            
            for n1, data in sorted(G.nodes(data=True)):
                f.write(
                    f"{data[self.node_attr]} { \
                        " ".join([f"{n2} {G[n1][n2][self.edge_attr]}" \
                        for n2 in G.neighbors(n1)]) \
                    }\n"
                )
        
        if data:
            node_data = [
                {**attrs, self.id : node} for node, attrs in sorted(G.nodes(data=True))
            ]
            gdf = gpd.GeoDataFrame(node_data, geometry=GEOMETRY_KEY)
            gdf = gdf.set_crs(epsg=3765)
            gdf.to_file(filename + ".geojson", driver="GeoJSON")

from my_utils import unordered

def coords(node, G: nx.Graph):
    return np.array((
        G.nodes[node][LONGITUDE], 
        G.nodes[node][LATITUDE]
    ))

def dist(n1, n2, G: nx.Graph, norm = 2):
    from functions import LNORM
    return LNORM(norm)(*(coords(n1, G) - coords(n2, G)))

class Coloring:
    from my_utils import Identifiable
    
    class Cluster(Identifiable):
        def __init__(self, parent : 'Coloring', id, initial = set()):
            self.parent = parent
            self.C = parent.C
            self.G = parent.G
            self.get_node_attr = self.parent.get_node_attr
            self.get_cluster = self.parent.get_cluster
            
            self.id = id
            self.inferior = False
            
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
        
        def get_perimeter(self, other: 'Coloring.Cluster'):
            return {(n1, n2) for n1, n2 in self.perimeter if n2 in other.nodes}
        
        def add(self, node: int):
            from typing import Iterable
            if isinstance(node, Iterable):
                for n in node:
                    self.add(n)
            else:
                self.take(node)
                
        def take(self, node, other: 'Coloring.Cluster' = None, force = False):
            if other:
                if not force:
                    if other.is_separated_by(node):
                        raise ValueError(f"Node {node} is an articulation point of cluster {other}!")
                    
                    if node not in other.inner_perimeter() or not self.C.has_edge(self, other):
                        raise ValueError(f"Node {node} not on perimeter between {self} and {other}!")  
                
                other.dirty = True
                other.population -= self.get_node_attr(node)
                
                other.center -= coords(node, self.G)
                
                other.geometry.remove(self.get_node_attr(node, GEOMETRY_KEY))
                other.nodes.remove(node)       
            
            if node in self.nodes:
                print(f"WARNING: re-adding node {node}!")
                return
            
            self.G.nodes[node][GROUP_KEY] = self
            
            self.dirty = True
            self.population += self.get_node_attr(node)
                
            self.center += coords(node, self.G)
            
            self.geometry.add(self.get_node_attr(node, GEOMETRY_KEY))
            self.nodes.add(node)    

            for n in self.G.neighbors(node):
                if n in self.nodes:
                    self.perimeter.remove((n, node))
                else:
                    self.perimeter.add((node, n))
                
                if other:
                    if n in other.nodes:
                        other.perimeter.add((n, node))
                    else:
                        other.perimeter.remove((node, n))    
                    
                    c = self.parent.get_cluster(n)
                    
                    if c != self and c != other:
                        if not self.C.has_edge(self, c):
                            self.C.add_edge(self, c)                    
                            if self.parent.tournament:
                                self.parent.tournament.add(unordered(self, c))
                        
                        if not other.get_perimeter(c):
                            self.C.remove_edge(other, c)
                            if self.parent.tournament:
                                self.parent.tournament.remove(unordered(other, c))
                    
                    # if c == self:
                    #     self.parent.add_edge(other, self, -e)
                    # elif c == other:
                    #     self.parent.add_edge(other, self, e)
                    # else:
                    #     self.parent.add_edge(self, c, e)
                    #     self.parent.add_edge(other, c, -e)
                        
                    #     if not self.parent.edge_weight(c, other):
                    #         self.parent.remove_edge(c, other)
        
        def give(self, node, other: 'Coloring.Cluster'):
            other.take(node, self)
        
        def is_separated_by(self, node, max_iterations = None):
            if len(self.nodes) == 1:
                return True
            
            removed = node
            nodes = {n for n in self.G.neighbors(removed) if n in self.nodes}
            if not nodes:
                return False
            
            curr = nodes.pop()
            if not max_iterations:
                max_iterations = len(nodes) * 2
            
            while curr and max_iterations and len(nodes) > 0:
                curr = min(
                    filter(
                        lambda node: node in self.nodes and node != removed, 
                        self.G.neighbors(curr)
                    ), 
                    key = lambda node: min({dist(node, n, self.G) for n in nodes}),
                    default=None
                )
                if curr in nodes:
                    nodes.remove(curr)
                
                max_iterations -= 1
                    
            return len(nodes) != 0
        
        def __repr__(self):
            return f"Cluster {self.C.nodes[self][GROUP_KEY]}"
        
        def __int__(self):
            return int(self.C.nodes[self][GROUP_KEY])
        
        def __iter__(self):
            return iter(self.nodes)
        
        def __gt__(self, other: 'Coloring.Cluster'):
            return self.id > other.id
    
    def __init__(self, G: nx.Graph, initial: dict, balance = 0.05):
        from collections import defaultdict
        
        self.G: nx.Graph = G
        self.C = nx.Graph()
        
        self.clusters : dict[int, Coloring.Cluster] = defaultdict(set)
        self.inferiors = set()
        
        self.total_population = 0
        self.balance = balance
        
        self.tournament = None
        
        for node, data in G.nodes(data=True):
            self.total_population += data[NODE_ATTR]
            
            data[GROUP_KEY] = (c := Coloring.Cluster(self, id=node, initial={node}))
            self.clusters[initial.get(node)].add(c)

        self.C.add_nodes_from([
            (self.get_cluster(node), { 
                GROUP_KEY: initial.get(node)
            })
            for node in G.nodes
        ])
        
        for n1, n2, data in G.edges(data=True):
            c1, c2 = self.get_cluster(n1, n2)
            if c1 == c2:
                continue
            
            if self.get_attr(c1) != self.get_attr(c2):
                self.C.add_edge(c1, c2)
            else:
                if c1.population > c2.population:
                    self.collapse(c1, c2)
                else:
                    self.collapse(c2, c1)

        for col, clusters in sorted(self.clusters.items(), key=lambda c: -len(c[1])):
            clusters : set[Coloring.Cluster] = clusters
            
            dominant = max(clusters, key=lambda c: c.population)
            clusters.remove(dominant)
            
            self.inferiors.update(clusters)
            self.clusters[col] = dominant
        
        self.update_attrs()
    
    def edge_attr(self, c1, c2):
        return self.C[c1][c2][EDGE_ATTR] if isinstance(c1, Coloring.Cluster) else self.G[c1][c2][EDGE_ATTR]
    
    # def add_edge(self, c1, c2):
    #     if not self.C.has_edge(c1, c2):
    #         self.C.add_edge(c1, c2)
    #         if self.tournament:
    #             self.tournament.add(unordered(c1, c2))
        
    #     if self.tournament:
    #         self.tournament.update(unordered(c1, c2))
    
    # def remove_edge(self, c1, c2):
    #     if w := self.edge_attr(c1, c2):
    #         raise ValueError(f"Attempting to remove edge with positive weight: {c1}-{c2} (weight: {w})")
        
    #     if self.tournament:
    #         self.tournament.remove(unordered(c1, c2))
        
    #     self.C.remove_edge(c1, c2)
        
    def get_avg(self):
        if self.inferiors:
            print("WARNING: Inferiors not disolved before calling get_avg!")
        return float(self.total_population / len(self.C.nodes))
    
    def get_cluster(self, *node):
        def f(n) -> Coloring.Cluster:
            return self.G.nodes[n][GROUP_KEY]
        if len(node) > 1:
            return list(map(f, node))
        return f(node[0])
    
    def get_attr(self, obj, attr = GROUP_KEY):
        if not isinstance(obj, Coloring.Cluster):
            obj = self.get_cluster(obj)
        if attr != GROUP_KEY:
            self.update_attrs(obj)
        return self.C.nodes[obj][attr]
    
    def get_node_attr(self, node, attr = NODE_ATTR):
        return self.G.nodes[node][attr]
    
    def update_attrs(self, c: 'Coloring.Cluster' = None):
        if c is None:
            for c in self.C.nodes:
                self.update_attrs(c)
        elif c.dirty:
            self.C.nodes[c].update({
                NODE_ATTR: c.population, 
                LONGITUDE: c.center[0] / len(c.nodes), 
                LATITUDE: c.center[1] / len(c.nodes), 
                GEOMETRY_KEY: c.geometry
            })
            c.dirty = False

    def collapse(self, c1: 'Coloring.Cluster', c2: 'Coloring.Cluster', force = False):
        if not force and not self.C.has_edge(c1, c2) and not c1.get_perimeter(c2):
            raise KeyError(f"{c1} and {c2} aren't incident!")
        
        c1.add(c2)
        
        clusters = self.clusters[col := self.get_attr(c1)]
        
        if isinstance(clusters, set):
            clusters.remove(c2)
        else:
            self.clusters.pop(col)
        
        nx.contracted_nodes(self.C, c1, c2, self_loops=False, copy=False)
        
    def disolve(self, cluster: 'Coloring.Cluster'):
        from my_utils import pqueue
        
        print(f"Disolving ({cluster}) into neighbors: {set(self.C.neighbors(cluster))}")
        
        g = {n : self.get_cluster(n).population for n in cluster.outer_perimeter()}
        queue = pqueue(
            {e for e in cluster.perimeter if self.get_cluster(e[1]) not in self.inferiors},
            lambda edge: g[edge[1]] + self.G.nodes[edge[0]][NODE_ATTR]
        )
        
        while not queue.empty():
            # print("Checking disolve: ")
            # self.edge_check()
            
            n1, n2 = queue.pop()
            if n1 in g.keys():
                continue
            
            g[n1] = g[n2] + self.G.nodes[n1][NODE_ATTR]
            self.get_cluster(n2).take(n1, cluster, force=True)
            
            for n in self.G.neighbors(n1):
                if g.get(n) != g[n1]:
                    queue.push((n, n1))
         
        self.C.remove_node(cluster)
        
    def disolve_inferiors(self):
        while len(self.inferiors):
            self.disolve(self.inferiors.pop())
        self.update_attrs()
    
    def get_imbalance(self, *cluster):
        if len(cluster) > 1:
            return list(map(self.get_imbalance, cluster))
        elif len(cluster) == 0:
            return list(
                filter(
                    lambda x : x[1] > self.balance, 
                    [(c, self.get_imbalance(c)) for c in self.clusters.values()]
                )
            )
        
        cluster : Coloring.Cluster = cluster[0]
        return float((cluster.population - self.get_avg()) / self.get_avg())
    
    def expected_error(self):
        return self.balance * self.get_avg()
    
    def rebalance(self):
        from functions import SIGMOID, OFFSETROOT, extend_odd, SIGNEDLNORM, CONSTANT, cost_func
        from my_utils import Tournament
        
        def ordered(edge: tuple[Coloring.Cluster, Coloring.Cluster]) -> tuple[Coloring.Cluster, Coloring.Cluster]:
            if edge is None:
                return None
            return min(edge, key=lambda x: x.population), max(edge, key=lambda x: x.population)
               
        def cost(s, root1, root2, norm):
            return cost_func(
                x = OFFSETROOT(root1),
                y = extend_odd(OFFSETROOT(root2)),
                xactivation = SIGMOID(m = self.expected_error() * 2, s=s),
                yactivation = CONSTANT(1),
                norm=SIGNEDLNORM(norm)
            )
            
        def perimeter_weight(edge: tuple[Coloring.Cluster, Coloring.Cluster]):
            edge = unordered(*edge)
            
            if not self.C.has_edge(*edge):
                raise ValueError(f"EDGE {edge} not in Graph!")
                # self.tournament.remove(edge)
                # return -1
            
            c1, c2 = ordered(edge)
            equilibrium = (c1.population + c2.population) / 2
            
            def edge_weight(edge):
                n1, n2 = edge
                if c2.is_separated_by(n2):
                    return -1
                
                population_diff_before = abs(equilibrium - c1.population) * 2
                population_diff_after = abs(equilibrium - c1.population - self.get_node_attr(n2)) * 2
                
                edge_gain = 0
                for n in self.G.neighbors(n2):
                    if self.get_cluster(n) == c1:
                        edge_gain -= self.edge_attr(n1, n2)
                    elif self.get_cluster(n) == c2:
                        edge_gain += self.edge_attr(n1, n2)

                # define hyperparameters
                C = cost(s=0.01, root1=1, root2=2, norm=4)
                
                return C(population_diff_before)(0) - C(population_diff_after)(edge_gain)

            E, P = max({(e, edge_weight(e)) for e in c1.get_perimeter(c2)}, key=lambda e: e[1], default=(None, -1))
            
            if E is None:
                raise ValueError(f"EDGE {edge} is empty!!")
                # self.C.remove_edge(edge)
                # self.tournament.remove(edge)
            else:
                self.C.edges[edge][EDGE_ATTR] = E
            
            return P
        
        if not self.tournament:
            self.tournament = Tournament(key=perimeter_weight)
            for edge in self.C.edges:
                self.tournament.add(unordered(*edge))
        
        c1, c2 = ordered(self.tournament.top())
        n1, n2 = self.edge_attr(c1, c2)
        
        c = self.tournament.priority[unordered(c1, c2)]
        if c < 0:
            print("UNABLE TO FIND IMPROVEMENTS!")
            print(self.tournament.priority)
            return 1
        
        print(f"Moved {n2} from {c2} into {c1} COST: {c}")
        c1.take(n2, c2, force = False)
            
        for c in c1, c2:
            for n in self.C.neighbors(c):
                self.tournament.update(unordered(c, n))
        
        self.update_attrs()
        return 0
        
    def __iter__(self):
        return iter(self.C.nodes)
    
    def __repr__(self):
        return f"Coloring:\n{'\n'.join(map(str, self))}"

    # def edge_check(self):
    #     for c1, c2 in self.C.edges:
    #         s1 = sum(map(lambda e: self.edge_attr(*e), c1.get_perimeter(c2)))
    #         s2 = self.edge_attr(c1, c2)
    #         if s1 != s2:
    #             print(c1, c2, s1, s2) 