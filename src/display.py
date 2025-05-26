
from typing import Iterable
import matplotlib.pyplot as plt
import networkx as nx
from shapely import MultiPolygon, Polygon
from my_utils import GROUP_KEY, GEOMETRY_KEY, LONGITUDE, LATITUDE
import generator as gen
import numpy as np
from shapely.ops import unary_union

def display(
    G: nx.Graph | list[dict], 
    label: str | bool = True, 
    color: bool = True,
    hatch: bool | list = None,
    num_colors: int = None,
    draw: str = 'all',
    ax = None
):    
    draw_points = not isinstance(G, nx.Graph) or draw == 'points'
    draw_dual = not draw_points and draw == 'all' or draw == 'dual'
    draw_voronoi = not draw_points and draw == 'all' or draw == 'voronoi'
    
    if not isinstance(G, nx.Graph):
        tmp = nx.Graph()
        tmp.add_nodes_from(enumerate(G))
        G = tmp
    
    # check_planarity returns (bool, graph) where graph is either a planar embedding or a kuratowski subgraph
    assert nx.check_planarity(G)[0], "Graph is not planar!"
    
    if not ax:
        fig, ax = plt.subplots(figsize=(10, 8))

    nx.draw(
        G, pos = {n : (data[LONGITUDE], data[LATITUDE]) for n, data in G.nodes(data=True)},
        node_color="red", 
        node_size = 10 if draw_dual or draw_points else 0, 
        edge_color = (0, 0, 0, 0.5 if draw_dual else 0),
        with_labels = label != False and not draw_voronoi, 
        labels = {n: lbl if (lbl := d.get(label)) is not None else str(n) for n, d in G.nodes(data=True)},
        ax=ax
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
            
            poly = unary_union(list(p) if isinstance(p := region[GEOMETRY_KEY], Iterable) else [p])
            
            ax.add_patch(
                plt.Polygon(
                    poly.boundary.coords, 
                    facecolor=color or 'white',
                    edgecolor=color or 'blue', 
                    hatch=hatch, 
                    alpha=0.3, fill=True,
                )
            )
            if label != False:
                centroid = poly.centroid
                ax.text(
                    centroid.x, centroid.y, 
                    region.get(label) or str(n),
                    ha='center', va='center',
                    fontsize=8,
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1)
                )
 