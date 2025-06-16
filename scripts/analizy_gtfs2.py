import pandas as pd

def find_routes_by_stop(file1, file2, stop_id):
    # Read stop_times.txt
    df2 = pd.read_csv(file2)
    
    # Convert stop_id and trip_id to string
    df2['stop_id'] = df2['stop_id'].astype(str).str.strip()
    df2['trip_id'] = df2['trip_id'].astype(str).str.strip()
    
    # Filter trips passing through the given stop_id
    trips_passing_stop = set(df2[df2['stop_id'] == stop_id]['trip_id'])
    
    print(f"Found {len(trips_passing_stop)} trip_id passing through stop_id {stop_id}")
    
    if not trips_passing_stop:
        print("No trips found for the given stop_id.")
        return
    
    # Read trips.txt
    df1 = pd.read_csv(file1)
    
    # Convert route_id and trip_id to string
    df1['trip_id'] = df1['trip_id'].astype(str).str.strip()
    df1['route_id'] = df1['route_id'].astype(str).str.strip()
    
    # Find matching routes
    routes_used = set(df1[df1['trip_id'].isin(trips_passing_stop)]['route_id'])
    
    print(f"Found {len(routes_used)} unique route_id for trips passing through stop_id {stop_id}")
    print("Routes:", routes_used)

# Usage
file1 = r"c:\doc\Игорь\GIS\PKL\PKL2025-2\GTFS\gtfs_09feb_08h42m16s\trips.txt"
file2 = r"c:\doc\Игорь\GIS\PKL\PKL2025-2\GTFS\gtfs_09feb_08h42m16s\stop_times.txt"
#stop_id = "13471"
stop_id = "13503"

find_routes_by_stop(file1, file2, stop_id)
