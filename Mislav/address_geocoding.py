import pandas as pd
import time
import googlemaps
import glob
from datetime import datetime

def validate_row(row):
    # Check if address or city are numeric or empty
    address = str(row['Adresa BM']).strip()
    city = str(row['Grad/općina/država']).strip()
    
    issues = []
    if address.isdigit() or not address:
        issues.append(f"Invalid address: {address}")
    if city.isdigit() or not city:
        issues.append(f"Invalid city: {city}")
        
    return len(issues) == 0, issues

def geocode_address(gmaps, address):
    try:
        # Geocode the address
        result = gmaps.geocode(address)
        if result:
            location = result[0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"No results found for address: {address}")
            return None, None
    except Exception as e:
        print(f"Error geocoding address {address}: {e}")
        return None, None

def geocode_excel(input_excel, output_excel, api_key):
    gmaps = googlemaps.Client(key=api_key)
    
    try:
        # Read Excel file (first sheet)
        excel_file = pd.ExcelFile(input_excel)
        print(f"Using first sheet: {excel_file.sheet_names[0]}")
        
        df = pd.read_excel(input_excel, sheet_name=0)
        print(f"Processing {len(df)} rows...")
    except Exception as e:
        print(f"Error: Unable to read Excel file {input_excel}. Error: {e}")
        return

    if 'Latitude' not in df.columns:
        df['Latitude'] = None
    if 'Longitude' not in df.columns:
        df['Longitude'] = None
    
    problematic_rows = []
    
    for index, row in df.iterrows():
        if pd.notna(df.at[index, 'Latitude']) and pd.notna(df.at[index, 'Longitude']):
            continue
            
        is_valid, issues = validate_row(row)
        if not is_valid:
            row_data = row.to_dict()
            row_data['Issues'] = ', '.join(issues)
            row_data['Source File'] = input_excel
            problematic_rows.append(row_data)
            continue
            
        address = f"{row['Adresa BM']}, {row['Grad/općina/država']}, Croatia"
        print(f"Geocoding address: {address}")
        lat, lon = geocode_address(gmaps, address)
        
        if lat and lon:
            df.at[index, 'Latitude'] = lat
            df.at[index, 'Longitude'] = lon
            print(f"Success: {lat}, {lon}")
        else:
            row_data = row.to_dict()
            row_data['Issues'] = 'Failed to geocode'
            row_data['Source File'] = input_excel
            problematic_rows.append(row_data)
        
        time.sleep(0.1)
    
    # Save geocoded results
    df.to_excel(output_excel, index=False)
    print(f"Geocoded Excel saved to {output_excel}")
    
    return problematic_rows

# Process multiple files
api_key = 'YOUR_API_KEY'
input_files = glob.glob('XLSX_data/02_*.xlsx')

# Create a list to store all problematic rows
all_problematic_rows = []

# Process each file
for input_file in input_files:
    output_file = input_file.replace('.xlsx', '_geocoded.xlsx')
    print(f"\nProcessing {input_file}...")
    problematic_rows = geocode_excel(input_file, output_file, api_key)
    if problematic_rows:
        all_problematic_rows.extend(problematic_rows)

# Save problematic rows to a separate Excel file if any were found
if all_problematic_rows:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    problems_file = f'problematic_rows_{timestamp}.xlsx'
    pd.DataFrame(all_problematic_rows).to_excel(problems_file, index=False)
    print(f"\nProblematic rows saved to {problems_file}")
    print(f"Total problematic rows: {len(all_problematic_rows)}")
