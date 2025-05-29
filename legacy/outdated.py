import networkx as nx

import matplotlib.pyplot as plt
import os
import random
import KaHIP.deploy.kahip as kahip # type: ignore
import distinctipy as distinct

def bisect(
    G, nkey: str, ekey: str, 
    nblocks: int, 
    imbalance: float = 0.03, 
    seed: int = 0, 
    supress_output: int = 0, 
    mode: str = "ECO"
):
    
    N = len(G.nodes)
    M = sum(map(lambda g: len(g[1]), G.adjacency()))

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
        adjncy[xadj[n1] : p], adjcwgt[xadj[n1] : p] = zip(*[(int(n2), int(args[ekey] * 1000000)) for n2, args in neighbors.items()])
        vwgt[n1] = G.nodes[node][nkey]

    # print(xadj[N])

    edgecut, blocks = kahip.kaffpa(vwgt, xadj, adjcwgt, 
                                adjncy,  nblocks, imbalance, 
                                supress_output, seed, mode)

    # partition_graph(G, nblocks, blocks)
    
    partition = [0] * nblocks

    for n, data in G.nodes(data = True):
        partition[blocks[int(n)]] += data[nkey]

    avg = sum(map(lambda d: d[1][nkey], G.nodes(data = True))) / nblocks
    # print(avg)
    
    err = list(map(lambda n: abs(partition[n] - avg) / avg * 100, range(nblocks)))
    
    return (edgecut, blocks, err)

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

if __name__ == "__main__":

    G1 = get_map(os.getcwd() + "/Juraj/dual_graph/dual.graphml")

    p = "Ukupno birača"
    l = "length"
    k = 144

    edgecut, blocks, err = bisect(
        G1, 
        nkey = p, ekey = l, 
        nblocks = k, 
        imbalance = 0.005, 
        mode = 1
    )

    print("err:", max(err))

    with open("partition", 'w') as f:
            for b in blocks:
                f.write(str(b) + "\n")       
        
@seeded
def make_delunay(points: int | list, seed = None, attrs = None):
    from scipy.spatial import Delaunay
    
    if isinstance(points, int):
        points = get_random_points(points, attrs=attrs, seed=seed)
    
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

# @seeded
# def populate(G: nx.Graph, max: int = 10000, min: int = 1, rng: Generator = None, seed: int = None):
#     for n, data in G.nodes(data=True):
#         data[NODE_ATTR] = rng.integers(min, max) 
        
#     print(f"Populated graph (seed: {seed})")