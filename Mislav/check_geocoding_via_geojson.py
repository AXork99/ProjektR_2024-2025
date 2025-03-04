import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import glob
import os

def normalize_county_name(name: str) -> str:
    """Normalize county name for comparison"""
    name = name.upper().strip()
    name = name.replace("ŽUPANIJA", "").strip()
    return name

# Load counties from geojson and filter for admin_level 6 (counties)
counties = gpd.read_file('zupanije.geojson')
counties = counties[counties['admin_level'] == 6]  # Filter only counties

# Get all matching Excel files
excel_files = glob.glob('geocoded/02_*_geocoded.xlsx')

total_locations = 0
total_correct = 0
all_mismatches = []

for excel_file in excel_files:
    print(f"\nProcessing {excel_file}...")
    
    # Load polling stations from Excel
    df = pd.read_excel(excel_file)
    df_filtered = df.dropna(subset=['Latitude', 'Longitude', 'Županija'])
    
    correct_count = 0
    file_mismatches = []
    
    for idx, row in df_filtered.iterrows():
        point = Point(row['Longitude'], row['Latitude'])
        found = False
        
        for _, county in counties.iterrows():
            if county['geometry'].contains(point):
                excel_county = normalize_county_name(row['Županija'])
                geojson_county = normalize_county_name(county['local_name'])
                
                if excel_county == geojson_county:
                    correct_count += 1
                else:
                    file_mismatches.append({
                        'File': os.path.basename(excel_file),
                        'City': row.get('Naziv BM', 'N/A'),
                        'Address': row.get('Adresa BM', 'N/A'),
                        'Expected': row['Županija'],
                        'Found': county['local_name'],
                        'Coordinates': f"({row['Latitude']}, {row['Longitude']})"
                    })
                found = True
                break
                
        if not found:
            file_mismatches.append({
                'File': os.path.basename(excel_file),
                'City': row.get('Naziv BM', 'N/A'),
                'Address': row.get('Adresa BM', 'N/A'),
                'Expected': row['Županija'],
                'Found': 'Not in any county',
                'Coordinates': f"({row['Latitude']}, {row['Longitude']})"
            })
    
    total_locations += len(df_filtered)
    total_correct += correct_count
    all_mismatches.extend(file_mismatches)
    
    print(f"File results:")
    print(f"Locations checked: {len(df_filtered)}")
    print(f"Correctly geocoded: {correct_count}")
    print(f"Mismatches found: {len(file_mismatches)}")

print("\nFinal Summary:")
print(f"Total locations checked: {total_locations}")
print(f"Total correctly geocoded: {total_correct}")
print(f"Total mismatches found: {len(all_mismatches)}")

if all_mismatches:
    print("\nList of mismatched locations:")
    for i, m in enumerate(all_mismatches, 1):
        print(f"\n{i}. File: {m['File']}")
        print(f"   Address: {m['Address']}")
        print(f"   City: {m['City']}")
        print(f"   Expected: {m['Expected']}")
        print(f"   Found: {m['Found']}")
        print(f"   Coordinates: {m['Coordinates']}")
