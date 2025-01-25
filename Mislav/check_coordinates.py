import pandas as pd
import glob
import numpy as np

def find_outliers_in_file(file_path):
    df = pd.read_excel(file_path)
    
    # Skip if no coordinates
    if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        return []
    
    # Remove rows with NaN coordinates
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # Calculate mean and standard deviation for each coordinate
    lat_mean = df['Latitude'].mean()
    lat_std = df['Latitude'].std()
    lon_mean = df['Longitude'].mean()
    lon_std = df['Longitude'].std()
    
    # Define threshold (2 standard deviations from mean)
    threshold = 2
    
    outliers = []
    for _, row in df.iterrows():
        lat_z_score = abs((row['Latitude'] - lat_mean) / lat_std)
        lon_z_score = abs((row['Longitude'] - lon_mean) / lon_std)
        
        if lat_z_score > threshold and lon_z_score > threshold:
            outliers.append({
                'Source File': file_path,
                'Location': row['Naziv BM'],
                'Address': row['Adresa BM'],
                'City': row['Grad/općina/država'],
                'Latitude': row['Latitude'],
                'Longitude': row['Longitude'],
                'Lat Z-Score': f"{lat_z_score:.2f}",
                'Lon Z-Score': f"{lon_z_score:.2f}",
                'File Mean Location': f"({lat_mean:.4f}, {lon_mean:.4f})"
            })
    
    return outliers

def check_all_files():
    geocoded_files = glob.glob('02_*_geocoded.xlsx')
    all_outliers = []
    
    for file in geocoded_files:
        print(f"\nChecking {file}...")
        outliers = find_outliers_in_file(file)
        all_outliers.extend(outliers)
    
    if all_outliers:
        output_file = 'coordinate_outliers_AND.xlsx'
        pd.DataFrame(all_outliers).to_excel(output_file, index=False)
        print(f"\nFound {len(all_outliers)} potential outliers.")
        print(f"Details saved to {output_file}")
    else:
        print("\nNo outliers found.")

if __name__ == "__main__":
    check_all_files() 