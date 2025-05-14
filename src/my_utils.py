from typing import List, Dict, Optional

from pathlib import Path
import os
import subprocess

import numpy as np
import networkx as nx
import geopandas as gpd

from shapely.geometry import Polygon, Point  

NODE_ATTR = "population"
EDGE_ATTR = "weight"

GROUP_KEY = "IJ"
PRIMARY_KEY = "BM"
GEOMETRY_KEY = "geometry"
LONGITUDE = 'longitude'
LATITUDE = 'latitude'

PLACEHOLDER = 'a'

METIS_FLAGS = 11

def noExtension(path: str):
    return path.split('.')[0]

def cmd_format(*args, **kwargs):
    cmd = []
    if args:
        cmd.extend(str(arg) for arg in args)
    
    if kwargs:
        for key, value in kwargs.items():
            if not key[0] == '-':
                if len(key) == 1:
                    prefix = "-"
                else:
                    prefix = "--"
            else: 
                prefix = ''
            
            if value is True:
                cmd.append(f"{prefix}{key}")
            else:
                cmd.append(f"{prefix}{key}={value}")
    return cmd

class KaHIP:
    def __init__(self, kahip_dir: str = "KaHIP"):
        self.kahip_dir = Path(kahip_dir) 
        self.deploy_dir = self.kahip_dir / "deploy"
    
    def list_binaries(self) -> List[str]:
        return [f.name for f in self.deploy_dir.iterdir() if f.is_file() and os.access(f, os.X_OK)]
    
    def run_binary(
        self, binary_name: str,
        args: List[str] = None,
        kwargs: Dict[str, str] = None,
        timeout: Optional[float] = None,
        capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        
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

def is_connected(G, key: str=GROUP_KEY):
    color_groups = {}
    
    for node, attrs in G.nodes(data=True):
        color = attrs.get(key)
        if not color:
            raise KeyError(f"Graph isn't colored in {node}")
        if color not in color_groups:
            color_groups[color] = []
        color_groups[color].append(node)
    
    color_connectivity = {}
    
    for color, nodes in color_groups.items():
        color_connectivity[color] = nx.is_connected(G.subgraph(nodes))
    
    return 0 if all(color_connectivity.values()) else color_connectivity

def get_midpoint(p1, p2, offset=None):
    """Calculate midpoint with optional perpendicular offset"""
    p1 = np.array([p1.x, p1.y]) if isinstance(p1, Point) else np.array(p1)
    p2 = np.array([p2.x, p2.y]) if isinstance(p2, Point) else np.array(p2)
    
    midpoint = (p1 + p2) / 2
    
    if not offset:
        return [tuple(midpoint)]
    
    direction = p2 - p1
    perp_direction = np.array([-direction[1], direction[0]])
    perp_direction_norm = perp_direction / np.linalg.norm(perp_direction)
    dir = offset * perp_direction_norm
    
    return [tuple(midpoint - dir), tuple(midpoint + dir)]

def is_convex(points):
    from scipy.spatial import ConvexHull   
    
    points = np.asarray(points)
    
    if len(points) < 3:
        return False
    
    try:
        hull = ConvexHull(points)
        return len(hull.vertices) == len(points)
    except:
        return False
    
def make_convex(points):
    from scipy.spatial import ConvexHull   
    
    points = np.asarray(points)
    
    if len(points) < 3:
        return None
    
    try:
        hull = ConvexHull(points)
        
        if len(hull.vertices) == len(points):
            hull_vertices = np.vstack([
                points[hull.vertices],
                points[hull.vertices[0]] 
            ])
            return Polygon(hull_vertices)
        
        return None
    
    except:
        return None

class MetisFormat:
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
        if not filename:
            filename = self.default_name
        
        if not re.search(r'\..*$', filename):
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

def seeded(func):
    from functools import wraps
    from inspect import signature, Parameter
    from numpy.random import Generator, PCG64
    
    sig = signature(func)
    params = list(sig.parameters.values())
    
    if 'seed' not in sig.parameters:
        params.append(
            Parameter('seed', Parameter.KEYWORD_ONLY, default=None)
        )
    
    if 'rng' not in sig.parameters:
        params.append(
            Parameter('rng', Parameter.KEYWORD_ONLY, default=None)
        )
    
    sig = sig.replace(parameters=params)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        seed = bound.arguments.get('seed')
        rng = bound.arguments.get('rng')
        
        if seed is None:
            seed = np.random.SeedSequence().entropy
            bound.arguments['seed'] = seed
            
        if rng is None:
            rng = Generator(PCG64(seed))
            bound.arguments['rng'] = rng
        
        if 'seed' not in func.__code__.co_varnames:
            bound.arguments.pop('seed', None)
            
        if 'rng' not in func.__code__.co_varnames:
            bound.arguments.pop('rng', None)
        
        return func(*bound.args, **bound.kwargs)
    
    wrapper.__signature__ = sig
    
    return wrapper

if __name__ == "__main__":
    pass