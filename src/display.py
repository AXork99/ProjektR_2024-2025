
import matplotlib.pyplot as plt
import networkx as nx
from my_utils import GROUP_KEY, GEOMETRY_KEY, LONGITUDE, LATITUDE, PRIMARY_KEY
import generator as gen
import numpy as np

def display(
    G: nx.Graph, 
    label: str = PRIMARY_KEY, 
    pattern: bool | list = True, 
    num_colors: int = None,
    draw: str = 'all',
    figsize = None
):    
    # check_planarity returns (bool, graph) where graph is either a planar embedding or a kuratowski subgraph
    assert nx.check_planarity(G)[0], "Graph is not planar!"
    
    draw_dual = draw == 'all' or draw == 'dual'
    draw_voronoi = draw == 'all' or draw == 'voronoi'
    
    N = len(G.nodes)  
    
    plt.figure(figsize=figsize or (10, 8))
    
    nx.draw(
        G, pos = {n : (data[LONGITUDE], data[LATITUDE]) for n, data in G.nodes(data=True)},
        node_color="red", 
        node_size = 10 if draw_dual else 0, 
        edge_color = (0, 0, 0, 0.5 if draw_dual else 0)
    )
    
    if draw_voronoi:
        if pattern:
            color_map = gen.get_color_map((num_colors or N) + 1, pattern=pattern)  
        
        for n, region in G.nodes(data=True):
            if pattern and (pattern := color_map[int((region.get(GROUP_KEY)) or n) % N]) and len(pattern) == 2:
                color, hatch = pattern
            else:
                color, hatch = pattern, None
            
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
 