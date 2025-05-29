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

def coords(node, G: nx.Graph):
    return np.array((
        G.nodes[node][LONGITUDE], 
        G.nodes[node][LATITUDE]
    ))

def dist(n1, n2, G: nx.Graph, norm = 2):
    from functions import LNORM
    return LNORM(norm)(coords(n1, G), coords(n2, G))

class Coloring:
    from my_utils import Identifiable
    
    class Cluster(Identifiable):
        def __init__(self, G: nx.graph, C: nx.Graph, id, initial = set()):
            self.G : nx.Graph = G
            self.C : nx.Graph = C
            
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
        
        def get_perimeter(self, other):
            def f(other: Coloring.Cluster):
                return {(n1, n2) for n1, n2 in self.perimeter if n2 in other.nodes}
            return f(other)
        
        def add(self, node: int):
            from typing import Iterable
            
            if isinstance(node, Iterable):
                for n in node:
                    self.add(n)
            else:
                self.dirty = True
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
        
        def remove(self, node):
            pass
        
        def is_separated_by(self, node, max_iterations = 10):
            removed = node
            nodes = {n for n in self.G.neighbors(removed) if n in self.nodes}
    
            curr = nodes.pop()
            
            while max_iterations and nodes:
                curr = min(
                    filter(
                        lambda node: node in self.nodes and node != removed, 
                        self.G.neighbors(curr)
                    ), 
                    key = lambda node: min({dist(node, n, self.G) for n in nodes})
                )
                if curr in nodes:
                    nodes.remove(curr)
                
                max_iterations -= 1
                    
            return len(nodes) != 0
        
        def __repr__(self):
            return f"Cluster {self.id}"
        
        def __int__(self):
            return int(self.C.nodes[self][GROUP_KEY])
        
        def __iter__(self):
            return iter(self.nodes)
    
    def __init__(self, G: nx.Graph, initial: dict, balance = 0.05):
        from collections import defaultdict
        
        self.G: nx.Graph = G
        self.C = nx.Graph()
        
        self.clusters = defaultdict(set)
        self.inferiors = set()
        
        self.total_population = 0
        self.balance = balance
        
        self.tournament = None
        
        for node, data in G.nodes(data=True):
            self.total_population += data[NODE_ATTR]
            data[GROUP_KEY] = (c := Coloring.Cluster(G, self.C, id=node, initial={node}))
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
        
        avg = self.total_population / len(self.clusters)
        err = {list(self.clusters[col])[0] : float((sum(map(lambda x: x.population, c)) - avg) / avg) for col, c in self.clusters.items()}

        print('BASE ERR:')
        print([(c, val) for c, val in err.items() if abs(val) > balance])
        print(max(err.items(), key=lambda x: abs(x[1])))

        for col, clusters in sorted(self.clusters.items(), key=lambda c: -len(c[1])):
            clusters : set[Coloring.Cluster] = clusters
            
            dominant = max(clusters, key=lambda c: c.population)
            clusters.remove(dominant)
            
            self.inferiors.update(clusters)
            self.clusters[col] = dominant
        
        self.update_attrs()
        
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
        self.clusters[self.get_attr(c1)].remove(c2)
        
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
            n1, n2 = queue.pop()
            if n1 in g.keys():
                c1, c2 = self.get_cluster(n1, n2)
                if c1 != c2:
                    self.C.add_edge(c1, c2)
                continue
            
            g[n1] = g[n2] + self.G.nodes[n1][NODE_ATTR]
            self.get_cluster(n2).add(n1)
            
            for n in self.G.neighbors(n1):
                if g.get(n) != g[n1]:
                    queue.push((n, n1))
        
        self.C.remove_node(cluster)
    
    def disolve_inferiors(self):
        while len(self.inferiors):
            self.disolve(self.inferiors.pop())
    
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
    
    def rebalance(self):
        from functions import SIGMOID, IDENTITY, YTRANSLATED, RELU, YSCALED, COMPOSE, OFFSETLOG, L1NORM, NROOT
        from my_utils import Tournament
        
        expected_error = self.balance * self.get_avg()
        
        def cost_func(
            activation = SIGMOID(m = expected_error, s = 0.1), 
            x = YTRANSLATED(expected_error, IDENTITY), 
            y = COMPOSE(YSCALED(expected_error * 3/2, RELU(w=1000)), NROOT(2)),
            norm = L1NORM
        ):
            def f(p, e):
                return norm(x(p) * activation(p), y(e) * (1 - activation(p)))
            return f
        
        def perimeter_weight():
            def f(edge: tuple[Coloring.Cluster, Coloring.Cluster]):
                p = self.C.edges[edge][EDGE_ATTR]
                e = abs(edge[0].population - edge[1].population)
                
                return cost_func()(p, e)
            
            return f
        
        if not self.tournament:
            self.tournament = Tournament(key=perimeter_weight())
            for edge in self.C.edges:
                self.C.edges[edge][EDGE_ATTR] = edge[0].get_perimeter(edge[1])
                self.C.edges[edge][EDGE_ID] = self.tournament.append(edge)
        
        c11, c22 = self.tournament.top()
        c1 : Coloring.Cluster = min(c11, c22, lambda x: x.population)
        c2 : Coloring.Cluster = max(c11, c22, lambda x: x.population)
        
        equilibrium = (c1.population + c2.population) / 2
        
        def edge_weight(s = 0.05):
            def f(edge):
                n1, n2 = edge
                if c2.is_separated_by(n2):
                    return -1
                
                population_gain = abs(equilibrium - c1.population - self.get_node_attr(n2)) * 2
                
                edge_gain = 0
                for n in self.G.neighbors(n2):
                    if self.get_cluster(n) == c1:
                        edge_gain -= self.G[n1][n2][EDGE_ATTR]
                    else:
                        edge_gain += self.G[n1][n2][EDGE_ATTR]

                return cost_func(activation = SIGMOID(m = expected_error, s = s))(population_gain, edge_gain)
            
            return f
        
        _, n2 = min(c1.get_perimeter(c2), key=edge_weight())
        
        c1.add(n2)
        c2.remove(n2)
        
        for c in c1, c2:
            for n in self.C.neighbors(c):
                self.tournament.update(self.C[c][n][EDGE_ID])
        
    def __iter__(self):
        return iter(self.C.nodes)
    
    def __repr__(self):
        return f"Coloring:\n{'\n'.join(map(str, self))}"
