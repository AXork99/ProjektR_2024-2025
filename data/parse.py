#!/usr/bin/env python3

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.graphs import *
import json
from shapely.geometry import shape
import geopandas as gpd

metis = MetisFormat()

def get_coordinates_from_json(file_path, index):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)["features"]
        feature = data[index]
        coordinates = feature['geometry']['coordinates']
        return tuple(coordinates)
        
dir = "dual_po_zupaniji"
voronoi_data : gpd.GeoDataFrame = gpd.read_file(f"{dir}/voronoi.geojson").set_index("id")

for i in range(20 + 1):
    G : nx.Graph = nx.read_graphml(f"{dir}/" + (name := f"zupanija_graph_{i}") + ".graphml")
    
    for n, data in G.nodes(data=True):
        data[GEOMETRY_KEY] = (shp := shape(voronoi_data.at[data["id"] - 1, GEOMETRY_KEY]))
        data[PRIMARY_KEY] = data["id"]
        data[LONGITUDE], data[LATITUDE] = shp.centroid.x, shp.centroid.y
        data[NODE_ATTR] = data["Ukupno birača"]
        
        del data["id"]
        del data["zupanija"]
        del data["path"]
        del data["layer"]
        del data["Ukupno birača"]
        del data["Naziv izborne jedinice"]
        del data["Rbr IJ"]
    
    G = nx.relabel_nodes(G, {f"{i}": i + 1 for i in range(G.number_of_nodes())})
    
    for e1, e2, data in G.edges(data=True):
        data[EDGE_ATTR] = max(int(data["length"] * 1000), 1) # pretpostavka da je daljina u kilometrima
        del data["length"]
            
    metis.write(G, "parsed/" + name)