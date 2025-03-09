import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import random
import subprocess
import distinctipy as distinct
import time
import os
from utils import get_dir

# KaHIP:

KaHIP_dir = os.getcwd() + "/Vilim/KaHIP/"

def export_graph_to_KaHIP(G, filename):
    if not nx.is_connected(G):
        raise ValueError("The graph must be connected")

    node_map = {node: idx + 1 for idx, node in enumerate(G.nodes())}
    
    with open(KaHIP_dir + filename, "w") as f:
        num_nodes = G.number_of_nodes()
        num_edges = G.number_of_edges()

        # First line: Number of nodes and number of edges
        f.write(f"{num_nodes} {num_edges} 10\n")

        # Write adjacency list
        for node, data in G.nodes(data = True):
            neighbors = [node_map[n] for n in G.neighbors(node)]  # Convert to 1-based indexing
            f.write(f"{data['population']} {' '.join(map(str, neighbors))}\n")

    print(f"Graph successfully exported")

def KaHIP(command: str, *args: str, **kwargs: str):
    
    for key, value in kwargs.items():
        args += (f"--{key}={value}",)
    
    full_command = f"./{command} {' '.join(args)}"
    print(f"Running command: {full_command}")
    
    try:
        result = subprocess.run(
            full_command, 
            cwd=KaHIP_dir,
            capture_output=True,
            text=True,
            shell=True,
            timeout=60,
            errors=""
        )
        print(f"Command output: {result.stdout}")
        return result
    except subprocess.TimeoutExpired:
        print("The command timed out.")
        return ""

def partition_graph(G: nx.Graph, k: int, partition: list[int] | str, label: str = "k", colormap = None):
    if (isinstance(partition, str)):
        parts = []
        with open(partition, "r") as f:
            parts = [int(x) for x in f.readlines()]    
        partition = parts
    
    
    colors = [colormap(i / (k-1)) for i in random.shuffle(range(k))] if colormap else distinct.get_colors(k)
    
    for i, node in enumerate(G.nodes):
        G.nodes[node][label] = partition[i]
        if (colors): 
            G.nodes[node]['color'] = colors[partition[i]]

    return G
   
def KaFFPa(G: nx.Graph, k: int, check_format: bool = True, name: str = "graph.graph", config: str = "eco", imbalance: int = 5) -> nx.Graph:
    out = "../../" + "partition.txt"
    name = "graph.graph"
    
    export_graph_to_KaHIP(G, name)
    
    if (check_format):
        print("Checking Graph format...")
        print(KaHIP("graphchecker", name).stdout)

    print(
        KaHIP(
            "kaffpa", 
            name, 
            k=k, 
            preconfiguration=config, 
            imbalance=imbalance,
            output_filename = out
        )
        .stdout
    )
    
    partition_graph(G, k, out)
    
    return G

# General:

def get_map(name: str) -> nx.Graph:
    return nx.read_graphml(name)

def save_map(G: nx.Graph, name: str = "map"):
    nx.write_graphml(G, name + ".graphml")

def print_map(G, label = None, color: str | dict = None, layout = nx.planar_layout):
    labels = {node: f"{G.nodes[node]['k']}:{G.nodes[node][label]}" for node in G.nodes} if label else None
    pos = layout(G)
    
    node_colors = None
    if isinstance(color, str):
        node_colors = [G.nodes[node][color] for node in G.nodes]
    elif isinstance(color, dict):
        node_colors = [color[G.nodes[node]] for node in G.nodes]
    
    nx.draw(G, pos, node_size=150, node_color=node_colors)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    
    plt.show()
