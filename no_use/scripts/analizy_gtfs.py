import pandas as pd

def filter_and_extract(file1, file2, str1, str2):
    # Read the first file
    df1 = pd.read_csv(file1)

    # Convert route_id to string (if it's numeric)
    df1['route_id'] = df1['route_id'].astype(str).str.strip()

    # Filter by route_id
    filtered_df1 = df1[df1['route_id'] == str1]

    # Get the list of trip_id values
    trip_ids = set(filtered_df1['trip_id'].astype(str).str.strip())

    #print("Found trip_id:", trip_ids)

    # Read the second file
    df2 = pd.read_csv(file2)

    # Convert trip_id and stop_id to string
    df2['trip_id'] = df2['trip_id'].astype(str).str.strip()
    df2['stop_id'] = df2['stop_id'].astype(str).str.strip()

    # Check for matching trip_id
    common_trip_ids = trip_ids.intersection(set(df2['trip_id']))
    print("Matching trip_id:", common_trip_ids)

    if not common_trip_ids:
        print("No matching trip_id found in stop_times.txt")
        return

    # Keep only rows with found trip_id
    df2_filtered = df2[df2['trip_id'].isin(trip_ids)]
    print("Number of records after filtering by trip_id:", len(df2_filtered))

    # Filter by stop_id
    df2_filtered = df2_filtered[df2_filtered['stop_id'] == str2]

    if df2_filtered.empty:
        print(f"No records found for stop_id={str2}")
        return

    # Convert arrival_time to datetime
    df2_filtered['arrival_time'] = pd.to_datetime(df2_filtered['arrival_time'], errors='coerce', format='%H:%M:%S')

    # Drop rows with NaT (if time format is incorrect)
    df2_filtered = df2_filtered.dropna(subset=['arrival_time'])

    if df2_filtered.empty:
        print("All arrival_time values are invalid")
        return

    # Sort by time
    df2_filtered = df2_filtered.sort_values(by='arrival_time')

    # Calculate time difference
    df2_filtered['time_diff'] = df2_filtered['arrival_time'].diff()

    # Print results
    for index, row in df2_filtered.iterrows():
        print(f"time: {row['arrival_time'].time()},+: {row['time_diff']}")

# Usage
file1 = r"c:\doc\Игорь\GIS\PKL\PKL2025-2\GTFS\gtfs_09feb_08h42m16s\trips.txt"
file2 = r"c:\doc\Игорь\GIS\PKL\PKL2025-2\GTFS\gtfs_09feb_08h42m16s\stop_times.txt"
#str1 = "26983"
#str1 = "2692"
#str2 = "13471"

str1 = "39171_1"
str2 = "13503"

filter_and_extract(file1, file2, str1, str2)
