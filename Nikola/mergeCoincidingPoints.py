import json
import os
import pandas as pd

DIR = os.path.dirname(__file__)
POINTS_XLSX = "../Mislav/geocoded/02_all_geocoded.xlsx"
VORONOI_GEOJSON = "./spatial files/hr_susjedi.geojson"
OUT_GEOJSON = "./spatial files/hr_susjedi_spojeno.geojson"

in_geojson = open(os.path.join(DIR,VORONOI_GEOJSON), "r", encoding="UTF8")
out_geojson = open(os.path.join(DIR,OUT_GEOJSON), "w", encoding="UTF8")
BM_list = pd.read_excel(os.path.join(DIR, POINTS_XLSX))
voronoi_list = json.load(in_geojson)["features"]
print(BM_list)