import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import random
import KaHIP.deploy.kahip as kahip # type: ignore
import subprocess
import distinctipy as distinct
import os

def partition_graph(G: nx.Graph, k: int, partition: list[int] | str, label: str = "part", colormap = None):
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

def get_map(name: str) -> nx.Graph:
    return nx.read_graphml(name)

def save_map(G: nx.Graph, name: str = "map"):
    nx.write_graphml(G, name + ".graphml")

def print_map(G, label = None, color: str | dict = None, layout = nx.planar_layout):
    labels = {node: f"{G.nodes[node]['part']}:{G.nodes[node][label]}" for node in G.nodes} if label else None
    pos = layout(G)
    
    node_colors = None
    if isinstance(color, str):
        node_colors = [G.nodes[node][color] for node in G.nodes]
    elif isinstance(color, dict):
        node_colors = [color[G.nodes[node]] for node in G.nodes]
    
    nx.draw(G, pos, node_size=150, node_color=node_colors)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    
    plt.show()

def bisect(G, key: str, nblocks: int, imbalance: float = 0.03, seed: int = 0, supress_output: int = 0, mode: int = 1):
    
    N = len(G.nodes)
    M = sum(map(lambda g: len(g[1]), G.adjacency()))

    # print(N, M)
    
    # # set mode 
    # # const int FAST          = 0;
    # #const int ECO            = 1;
    # #const int STRONG         = 2;

    xadj           = [0] * (N + 1)
    adjncy         = [0] * M
    vwgt           = [0] * N
    adjcwgt        = [0] * M

    if not nx.is_connected(G):
        raise ValueError("The graph must be connected")

    p = 0
    input = sorted(G.adjacency(), key = lambda x: int(x[0]))

    for node, neighbors in input:
        # print(node)
        n1 = int(node)
        xadj[n1] = p
        p += len(neighbors)
        xadj[n1 + 1] = p
        adjncy[xadj[n1] : p], adjcwgt[xadj[n1] : p] = zip(*[(int(n2), int(args["length"]*1000000)) for n2, args in neighbors.items()])
        vwgt[n1] = G.nodes[node][key]

    # print(xadj[N])

    edgecut, blocks = kahip.kaffpa(vwgt, xadj, adjcwgt, 
                                adjncy,  nblocks, imbalance, 
                                supress_output, seed, mode)

    # partition_graph(G, nblocks, blocks)
    
    partition = [0] * nblocks

    for n, data in G.nodes(data = True):
        partition[blocks[int(n)]] += data[key]

    avg = sum(map(lambda d: d[1][key], G.nodes(data = True))) / nblocks
    # print(avg)
    
    err = list(map(lambda n: abs(partition[n] - avg) / avg * 100, range(nblocks)))

    # print(edgecut)
    # print(blocks)

    # g.print_map(G1, color="color", label=key)
    
    return (edgecut, blocks, err)


# DEPRECATED:

# cwd = os.path.dirname(os.path.dirname(__file__))

# KaHIP_dir = cwd + "/Vilim/KaHIP/"

# def export_graph_to_KaHIP(G, filename, key):
#     if not nx.is_connected(G):
#         raise ValueError("The graph must be connected")

#     node_map = {node: idx + 1 for idx, node in enumerate(G.nodes())}
    
#     with open(KaHIP_dir + filename, "w") as f:
#         num_nodes = G.number_of_nodes()
#         num_edges = G.number_of_edges()

#         f.write(f"{num_nodes} {num_edges} 11\n")

#         for node, data in G.nodes(data = True):
#             neighbors = [node_map[n] for n in G.neighbors(node)]
#             f.write(f"{data[key]} {' '.join(map(str, neighbors))}\n")

#     print(f"Graph successfully exported")

# def KaHIP(command: str, *args: str, **kwargs: str):
    
#     for key, value in kwargs.items():
#         args += (f"--{key}={value}",)
    
#     full_command = f"./{command} {' '.join(args)}"
#     print(f"Running command: {full_command}")
    
#     try:
#         result = subprocess.run(
#             full_command, 
#             cwd=KaHIP_dir,
#             capture_output=True,
#             text=True,
#             shell=True,
#             timeout=60,
#             errors=""
#         )
#         print(f"Command output: {result.stdout}")
#         return result
#     except subprocess.TimeoutExpired:
#         print("The command timed out.")
#         return ""

# def KaFFPa(G: nx.Graph, key: str, k: int, check_format: bool = True, name: str = "graph.graph", config: str = "eco", imbalance: int = 5) -> nx.Graph:
#     print(cwd)
#     out = cwd + "/Vilim/partition.txt"
    
#     export_graph_to_KaHIP(G, name, key)
    
#     if (check_format):
#         print("Checking Graph format...")
#         print(KaHIP("graphchecker", name).stdout)

#     print(
#         KaHIP(
#             "kaffpa", 
#             name, 
#             k=k, 
#             preconfiguration=config, 
#             imbalance=imbalance,
#             output_filename = out
#         )
#         .stdout
#     )
    
#     partition_graph(G, k, out)
    
#     return G