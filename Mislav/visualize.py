import pandas as pd
import folium
import glob

# Read all geocoded CSV files
geocoded_files = glob.glob('02_*_geocoded.csv')
dfs = []

for file in geocoded_files:
    df = pd.read_csv(file, delimiter=';', encoding='windows-1250')
    dfs.append(df)

# Combine all dataframes
df = pd.concat(dfs, ignore_index=True)

# Filter out rows with NaN coordinates
df = df.dropna(subset=['Latitude', 'Longitude'])

# Group by coordinates and sum the voting data
grouped_df = df.groupby(['Latitude', 'Longitude']).agg({
    'Ukupno birača': 'sum',
    'Glasovalo birača': 'sum',
    'Važeći listići': 'sum',
    'Nevažeći listići': 'sum',
    'Naziv BM': lambda x: ' | '.join(str(val) for val in x),
    'Adresa BM': 'first',
    'Grad/općina/država': 'first',
    'Naziv izborne jedinice': 'first'
}).reset_index()

# Find duplicate coordinates
duplicate_coords = df[df.duplicated(subset=['Latitude', 'Longitude'], keep=False)]
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