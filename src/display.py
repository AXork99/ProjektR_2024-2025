
import matplotlib.pyplot as plt
import networkx as nx
from my_utils import GROUP_KEY, GEOMETRY_KEY, LONGITUDE, LATITUDE, NODE_ATTR
import generator as gen
import numpy as np

def display(
    G: nx.Graph | list[dict], 
    label: str = NODE_ATTR, 
    color: bool = True,
    hatch: bool | list = None,
    num_colors: int = None,
    draw: str = 'all',
    figsize = None
):    
    draw_points = not isinstance(G, nx.Graph) or draw == 'points'
    draw_dual = not draw_points and draw == 'all' or draw == 'dual'
    draw_voronoi = not draw_points and draw == 'all' or draw == 'voronoi'
    
    if not isinstance(G, nx.Graph):
        tmp = nx.Graph()
        tmp.add_nodes_from(enumerate(G))
        print('yikes')
        G = tmp
    
    # check_planarity returns (bool, graph) where graph is either a planar embedding or a kuratowski subgraph
    assert nx.check_planarity(G)[0], "Graph is not planar!"
    
    plt.figure(figsize=figsize or (10, 8))
    
    nx.draw(
        G, pos = {n : (data[LONGITUDE], data[LATITUDE]) for n, data in G.nodes(data=True)},
        node_color="red", 
        node_size = 10 if draw_dual or draw_points else 0, 
        edge_color = (0, 0, 0, 0.5 if draw_dual else 0),
        with_labels = label is not None and (draw_points or draw_dual), 
        labels = {n: d.get(label if label is not None else n) for n, d in G.nodes(data=True)}
    )
    
    if draw_voronoi:
        N = len(G.nodes)  
        
        if color or num_colors:
            color_map = gen.get_color_map((num_colors or N) + 1, pattern=hatch)  
        
        for n, region in G.nodes(data=True):
            if color or num_colors:
                color = color_map[int((region.get(GROUP_KEY)) or n) % N]
                if color and len(color) == 2:
                    color, hatch = color
                else:
                    color, hatch = color, None
            else:
                color, hatch = None, None
            
            poly_coords = list(region[GEOMETRY_KEY].exterior.coords)
            
            plt.gca().add_patch(
                plt.Polygon(
                    poly_coords, 
                    facecolor=color or 'white',
                    edgecolor=color or 'blue', 
                    hatch=hatch, 
                    alpha=0.3, fill=True,
                )
            )
            if label:
                centroid = np.mean(poly_coords, axis=0)
                plt.text(
                    centroid[0], centroid[1], 
                    region.get(label),
                    ha='center', va='center',
                    fontsize=8,
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1)
                )
    
    plt.show()
 