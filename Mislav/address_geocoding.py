import pandas as pd
import time
import googlemaps
import glob

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

def geocode_csv(input_csv, output_csv, api_key):
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=api_key)
    
    # Load CSV file
    try:
        df = pd.read_csv(input_csv, sep=';', encoding='windows-1250')
    except UnicodeDecodeError:
        print(f"Error: Unable to decode CSV file {input_csv} with windows-1250 encoding.")
        return
    
    # Add columns for coordinates if they don't exist
    if 'Latitude' not in df.columns:
        df['Latitude'] = None
    if 'Longitude' not in df.columns:
        df['Longitude'] = None
    
    # Process each row
    for index, row in df.iterrows():
        # Skip if already has coordinates
        if pd.notna(df.at[index, 'Latitude']) and pd.notna(df.at[index, 'Longitude']):
            continue
            
        # Combine address components
        address = f"{row['Adresa BM']}, {row['Grad/općina/država']}, Croatia"
        
        print(f"Geocoding address: {address}")
        lat, lon = geocode_address(gmaps, address)
        
        # Save valid coordinates
        if lat and lon:
            df.at[index, 'Latitude'] = lat
            df.at[index, 'Longitude'] = lon
            print(f"Success: {lat}, {lon}")
        else:
            print(f"Unable to geocode: {address}")
        
        # Delay to respect API limits
        time.sleep(0.1)  # 100ms delay between requests
    
    # Save results
    df.to_csv(output_csv, sep=';', index=False, encoding='windows-1250')
    print(f"Geocoded CSV saved to {output_csv}")

# Process multiple files
api_key = 'REPLACE_WITH_YOUR_API_KEY'  # Replace with your actual API key

# Get all input files
input_files = glob.glob('02_*.csv')

# Process each file
for input_file in input_files:
    output_file = input_file.replace('.csv', '_geocoded.csv')
    print(f"\nProcessing {input_file}...")
    geocode_csv(input_file, output_file, api_key)
