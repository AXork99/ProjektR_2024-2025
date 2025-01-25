import pandas as pd
import folium
import glob

# Read all geocoded Excel files
geocoded_files = glob.glob('geocoded/02_*_geocoded.xlsx')
dfs = []

for file in geocoded_files:
    df = pd.read_excel(file)
    dfs.append(df)

# Combine all dataframes
df = pd.concat(dfs, ignore_index=True)

# Print initial count
total_rows = len(df)
print(f"\nTotal number of rows before filtering: {total_rows}")

# Filter out rows with NaN coordinates and print stats
df_filtered = df.dropna(subset=['Latitude', 'Longitude'])
rows_removed = total_rows - len(df_filtered)
print(f"Rows removed due to missing coordinates: {rows_removed}")
print(f"Remaining rows: {len(df_filtered)}")
print(f"Percentage of rows with coordinates: {(len(df_filtered)/total_rows*100):.1f}%")

# Update df with filtered version
df = df_filtered

# Group by coordinates and sum the voting data
grouped_df = df.groupby(['Latitude', 'Longitude']).agg({
    'Ukupno birača': 'sum',
    'Glasovalo birača': 'sum',
    'Važeći listići': 'sum',
    'Nevažeći listići': 'sum',
    'Naziv BM': lambda x: ' | '.join(str(val) for val in x if pd.notna(val) and str(val) not in ['0', '1']),
    'Adresa BM': lambda x: next((str(val) for val in x if pd.notna(val) and str(val) != '0'), ''),
    'Grad/općina/država': lambda x: next((str(val) for val in x if pd.notna(val) and str(val) not in ['0', '1', '2', '29']), ''),
    'Naziv izborne jedinice': lambda x: next((str(val) for val in x if pd.notna(val) and str(val) != '1432'), '')
}).reset_index()

# Find and print duplicate coordinates
duplicate_coords = df[df.duplicated(subset=['Latitude', 'Longitude'], keep=False)]
print(f"\nNumber of locations with duplicate coordinates: {len(duplicate_coords)//2}")
print("\nAddresses with identical coordinates:")
for _, row in duplicate_coords.iterrows():
    print(f"\nCoordinates ({row['Latitude']}, {row['Longitude']})")
    print(f"Location: {row['Naziv BM']}")
    print(f"Address: {row['Adresa BM']}")
    print(f"City/Municipality: {row['Grad/općina/država']}")

# Create the map
center_lat = df['Latitude'].mean()
center_lon = df['Longitude'].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

# Add markers with different colors for duplicates
for idx, row in grouped_df.iterrows():
    is_duplicate = ((df['Latitude'] == row['Latitude']) & 
                   (df['Longitude'] == row['Longitude'])).sum() > 1
    
    # Calculate turnout percentage safely
    try:
        turnout = row['Glasovalo birača'] / row['Ukupno birača'] * 100 if row['Ukupno birača'] > 0 else 0
        turnout_str = f"{turnout:.1f}%"
    except:
        turnout_str = "N/A"
    
    # Create a more detailed popup with voting information
    popup_html = f"""
        <b>Location(s):</b> {row['Naziv BM']}<br>
        <b>Address:</b> {row['Adresa BM']}<br>
        <b>City:</b> {row['Grad/općina/država']}<br>
        <b>Electoral Unit:</b> {row['Naziv izborne jedinice']}<br>
        <hr>
        <b>Total Voters:</b> {row['Ukupno birača']}<br>
        <b>Votes Cast:</b> {row['Glasovalo birača']}<br>
        <b>Valid Ballots:</b> {row['Važeći listići']}<br>
        <b>Invalid Ballots:</b> {row['Nevažeći listići']}<br>
        <b>Turnout:</b> {turnout_str}
    """
    
    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=row['Naziv BM'],
        icon=folium.Icon(color='red' if is_duplicate else 'blue')
    ).add_to(m)

m.save('all_polling_locations_map.html')