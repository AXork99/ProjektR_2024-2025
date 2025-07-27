#!/usr/bin/env python3

from collections import defaultdict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.graphs import *
from src.utils import reduce_polygon
import geopandas as gpd

metis = MetisFormat()

dir = "../Nikola/spatial files"
voronoi_data : gpd.GeoDataFrame = gpd.read_file(f"{dir}/country_Voronoi_clip.geojson")
from shapely import MultiPolygon, Polygon
    
voronoi_data[GEOMETRY_KEY] = voronoi_data[GEOMETRY_KEY].apply(reduce_polygon)

# "properties": {
#     "Rbr IJ": 8,
#     "Naziv izborne jedinice": "VIII. IZBORNA JEDINICA",
#     "ID_u_zupaniji": 145,

banned = {"ID_u_zupaniji", "Rbr IJ", "Naziv izborne jedinice", "Rbr.županije", "Županija"}

#     "Latitude": 45.4523108,
#     "Longitude": 13.5390361,
#     "Ukupno birača": 928,

common = {
    "Latitude" : LATITUDE,
    "Longitude" : LONGITUDE,
    "Ukupno birača" : NODE_ATTR,
    "geometry" : GEOMETRY_KEY,
}

#     "Rbr.županije": 18,
#     "Županija": "ISTARSKA ŽUPANIJA",

ZUP_id = "Rbr.županije"
ZUP_map = {
    "Županija" : "name",   
    **common
}

#     "ID_global": 5126,

BM_map = {
    "ID_global" : PRIMARY_KEY,
    "" : "data",
    **common
}

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

total_population = 0

for id, row in voronoi_data.iterrows():
    data = row.to_dict()
    
    zup_id = data[ZUP_id]
    extras = {}
    
    for key, val in data.items():
        if key in BM_map.keys():
            zups[zup_id]["BMs"][BM_map[key]].append(val)
        elif key not in banned:
            extras[key] = val
        
        if key in ZUP_map.keys():
            if isinstance(val, str):
                name : str = zups[zup_id]["meta"].get(ZUP_map[key])
                if name and name != val:
                    raise ValueError("Same ID %d different names! : %s and %s".format(zup_id, name, val))
                zups[zup_id]["meta"][ZUP_map[key]] = val
            elif isinstance(val, Polygon):
                poly : list = zups[zup_id]["meta"].get(ZUP_map[key], [])
                poly.append(val)
                zups[zup_id]["meta"][ZUP_map[key]] = poly
            else:
                num = zups[zup_id]["meta"].get(ZUP_map[key], 0)
                zups[zup_id]["meta"][ZUP_map[key]] = num + val
        
    zups[zup_id]["BMs"]["data"].append(extras)
    total_population += data["Ukupno birača"]

for id, zup in zups.items():
    if len(sys.argv) < 2 or id == int(sys.argv[1]):
        print(id)
        data = gpd.GeoDataFrame(zup["BMs"], crs="EPSG:3765")
        data.to_file(f'parsed/zupanija_{id}.geojson', driver='GeoJSON')
        
        zup["meta"][GEOMETRY_KEY] = [reduce_polygon(MultiPolygon(zup["meta"][GEOMETRY_KEY]))]
        
        metadata = gpd.GeoDataFrame(zup["meta"], crs="EPSG:3765")
        metadata[NODE_ATTR] = metadata[NODE_ATTR].apply(lambda x: x / total_population)
        
        metadata.to_file(f'parsed/zupanija_{id}_meta.geojson', driver='GeoJSON', encoding="utf-8")

        from src.generator import make_voronoi
        dual = make_voronoi(data.to_dict('records'))
        
        metis.write(dual, f"parsed/zupanija_{id}", data=False)
