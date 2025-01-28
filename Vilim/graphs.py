import networkx as nx
import pymetis as pm
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import random

sample = nx.read_graphml("sample_map.graphml")

def get_map(name: str) -> nx.Graph:
    return nx.read_graphml(name + ".graphml")

def create_sample_map(num_bm: int, max_population: int = 2000, min_population: int = 10, name: str = "sample_map"):
    def _create_sample_map_r(num_nodes: int) -> nx.Graph:
        if num_nodes <= 3:
            G = nx.complete_graph(num_nodes)
            for n in G.nodes:
                G.nodes[n]['population'] = random.randint(min_population, max_population)
            return G
        
        G1 = _create_sample_map_r(num_nodes // 2)
        G2 = _create_sample_map_r(num_nodes - num_nodes // 2)
        N1 = len(G1.nodes)
        N2 = len(G2.nodes)
        
        G2 = nx.relabel_nodes(G2, {i: i + N1 for i in range(N2)})
        G = nx.compose(G1, G2)
        
        for i in range(min(N1, N2)):
            n2 = i + N1
            n1 = i
            G.add_edge(n1, n2)
            if not nx.check_planarity(G)[0]:
                G.remove_edge(n1, n2)
        return G
    
    sample_map = _create_sample_map_r(num_bm)
    nx.write_graphml(sample_map, name + ".graphml")

def print_map(G, label = None, color: str | dict = "color", layout = nx.planar_layout):
    labels = {node: f"{G.nodes[node]["part"]}:{G.nodes[node][label]}" for node in G.nodes} if label else None
    pos = layout(G)
    
    node_colors = None
    if isinstance(color, str):
        node_colors = [G.nodes[node][color] for node in G.nodes]
    elif isinstance(color, dict):
        node_colors = [color[G.nodes[node]] for node in G.nodes]
    
    nx.draw(G, pos, node_size=150, node_color=node_colors)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    
    plt.show()
    
def init_partition(G: nx.Graph, parts: int, by: str, colormap = cm.tab20) -> nx.Graph:
    node_map = {node: idx for idx, node in enumerate(G.nodes)}
    adjacency_list = [list(map(node_map.get, G.neighbors(node))) for node in G.nodes]
    weights = [G.nodes[node][by] for node in G.nodes]

    (_, initial_partition) = pm.part_graph(parts, adjacency=adjacency_list, vweights=weights)
    
    colors = [colormap(i / parts) for i in range(parts)] if colormap else None
    
    for node in G.nodes:
        G.nodes[node]['part'] = initial_partition[node_map[node]]
        if (colors): 
            G.nodes[node]['color'] = colors[initial_partition[node_map[node]]]

    return G

create_sample_map(17)