import networkx as nx
from shapely import MultiLineString

from ..graphs.constants import *
from . import plt

def display(
    G: nx.Graph | list[dict], 
    label: str | bool = True, 
    color: bool = False,
    hatch: bool | list = None,
    num_colors: int = None,
    draw: str = 'all',
    ax = None
):    
    from shapely.ops import unary_union
    from typing import Iterable

    if label == "False":
        label = False
    if label == "True":
        label = True
        
    draw_points = not isinstance(G, nx.Graph) or draw == 'points'
    draw_dual = not draw_points and draw == 'all' or draw == 'dual'
    draw_voronoi = not draw_points and draw == 'all' or draw == 'voronoi'
    
    if not isinstance(G, nx.Graph):
        tmp = nx.Graph()
        tmp.add_nodes_from(enumerate(G))
        G = tmp
    
    assert nx.check_planarity(G)[0], f"Graph is not planar!"
    
    display_immediate = False
    if not ax:
        display_immediate = True
        _, ax = plt.subplots(figsize=(10, 8))
    
    nx.draw(
        G, pos = {n : (data[LONGITUDE], data[LATITUDE]) for n, data in G.nodes(data=True)},
        node_color="red", 
        node_size = 10 if draw_dual or draw_points else 0, 
        edge_color = (0, 0, 0, 0.5 if draw_dual else 0),
        with_labels = label != False and not draw_voronoi, 
        labels = {n: str(n) + (f":{lbl}" if (lbl := d.get(label)) is not None else '') for n, d in G.nodes(data=True)},
        ax=ax
    )
    
    if draw_voronoi:
        N = len(G.nodes)  
        
        if color or num_colors:
            from ..generator import get_color_map
            color_map = get_color_map((num_colors or N) + 1, pattern=hatch)  
        
        for n, region in G.nodes(data=True):
            if color or num_colors:
                color = color_map[int(region.get(GROUP_KEY, n)) % N]
                if color and len(color) == 2:
                    color, hatch = color
                else:
                    color, hatch = color, None
            else:
                color, hatch = None, None
            
            from ..utils import reduce_polygon
            poly = unary_union(list(p) if isinstance(p := region[GEOMETRY_KEY], Iterable) else [p])
            
            bound = poly.boundary
            if isinstance(bound, MultiLineString):
                bound = bound.geoms[0]
            
            ax.add_patch(
                plt.Polygon(
                    bound.coords, 
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
                    str(n) + (f":{lbl}" if (lbl := region.get(label)) is not None else ''),
                    ha='center', va='center',
                    fontsize=8,
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1)
                )
                
    if display_immediate:
        plt.show()
