#!/usr/bin/env python3

from collections import defaultdict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.graphs import *
import json
import geopandas as gpd

metis = MetisFormat()
        
dir = "../Nikola/spatial files"
voronoi_data : gpd.GeoDataFrame = gpd.read_file(f"{dir}/country_Voronoi_clip.geojson")
from shapely import unary_union, MultiPolygon, Polygon

def reduce(poly):
    if isinstance(poly, MultiPolygon):
        poly = unary_union(poly.geoms)
    if isinstance(poly, MultiPolygon):
        poly = max(poly.geoms, key = lambda p : p.area)
    return poly
    
voronoi_data[GEOMETRY_KEY] = voronoi_data[GEOMETRY_KEY].apply(reduce)

# "properties": {
#     "Rbr IJ": 8,
#     "Naziv izborne jedinice": "VIII. IZBORNA JEDINICA",

#     "Rbr.županije": 18,
#     "Županija": "ISTARSKA ŽUPANIJA",

ZUP_id = "Rbr.županije"
ZUP_map = {
    "Županija" : "name",    
}

#     "Latitude": 45.4523108,
#     "Longitude": 13.5390361,
#     "ID_global": 5126,
#     "Ukupno birača": 928,

BM_map = {
    "Latitude" : LATITUDE,
    "Longitude" : LONGITUDE,
    "ID_global" : PRIMARY_KEY,
    "Ukupno birača" : NODE_ATTR,
    "geometry" : GEOMETRY_KEY,
    "" : "data"
}

#     "ID_u_zupaniji": 145,
#     "Oznaka Gr/Op/Dr": "grad",
#     "Grad/općina/država": "UMAG - UMAGO",
#     "Rbr BM": 6,
#     "Naziv BM": "MURINE-MORNO",
#     "Lokacija BM": "PODRUČNA ŠKOLA MURINE",
#     "Adresa BM": "PRVA ULICA 3",
#     "Glasovalo birača": 515,
#     "Glasovalo birača (po listićima)": 514,
#     "Važeći listići": 507,
#     "Nevažeći listići": 7,
# },

zups = defaultdict(lambda : {
    "meta" : {},
    "BMs" :  {key : [] for key in BM_map.values()}
})

for id, row in voronoi_data.iterrows():
    data = row.to_dict()
    
    zup_id = data[ZUP_id]
    extras = {}
    
    for key, val in data.items():
        if key in BM_map.keys():
            zups[zup_id]["BMs"][BM_map[key]].append(val)
        elif key in ZUP_map.keys():
            zups[zup_id]["meta"][ZUP_map[key]] = val
        else:
            extras[key] = val
            
    zups[zup_id]["BMs"]["data"].append(extras)

for id, zup in zups.items():
    data = gpd.GeoDataFrame(zup["BMs"], crs="EPSG:3765")
    data.to_file(f'parsed/zupanija_{id}.geojson', driver='GeoJSON')
    with open(f"parsed/zupanija_{id}.json", 'w', encoding="utf-8") as f:
        json.dump(zup["meta"], f, ensure_ascii=False, indent=2)