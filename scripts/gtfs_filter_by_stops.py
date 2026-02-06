import pandas as pd
import os

# Paths
stops_file = r'c:\doc\Igor\GIS\test_012026\stops_2025_TAMA.csv'
gtfs_path = r'c:\doc\Igor\GIS\test_012026\gtfs'
output_file = r'c:\doc\Igor\GIS\test_012026\routes_TAMA.txt'

def filter_routes_by_stops(stops_csv, gtfs_dir):
    # 1. Load target stop_ids from your CSV
    stops_df = pd.read_csv(stops_csv)
    target_stop_ids = set(stops_df['stop_id'].astype(str))
    
    print(f"Target stops loaded: {len(target_stop_ids)}")

    # 2. Read stop_times.txt to find trip_ids passing through these stops
    stop_times_path = os.path.join(gtfs_dir, 'stop_times.txt')
    # Using chunks to handle potentially large stop_times file
    stop_times_iter = pd.read_csv(stop_times_path, usecols=['trip_id', 'stop_id'], 
                                  dtype={'trip_id': str, 'stop_id': str}, chunksize=100000)
    
    relevant_trip_ids = set()
    for chunk in stop_times_iter:
        filtered_chunk = chunk[chunk['stop_id'].isin(target_stop_ids)]
        relevant_trip_ids.update(filtered_chunk['trip_id'].unique())
    
    print(f"Relevant trips found: {len(relevant_trip_ids)}")

    # 3. Read trips.txt to map those trip_ids to route_ids
    trips_path = os.path.join(gtfs_dir, 'trips.txt')
    trips_df = pd.read_csv(trips_path, usecols=['trip_id', 'route_id'], 
                           dtype={'trip_id': str, 'route_id': str})
    
    relevant_route_ids = set(trips_df[trips_df['trip_id'].isin(relevant_trip_ids)]['route_id'].unique())
    
    print(f"Relevant routes identified: {len(relevant_route_ids)}")

    # 4. Filter routes.txt and save the output
    routes_path = os.path.join(gtfs_dir, 'routes.txt')
    routes_df = pd.read_csv(routes_path, dtype={'route_id': str})
    
    filtered_routes = routes_df[routes_df['route_id'].isin(relevant_route_ids)]
    
    filtered_routes.to_csv(output_file, index=False)
    print(f"Success! Filtered routes saved to: {output_file}")

if __name__ == "__main__":
    filter_routes_by_stops(stops_file, gtfs_path)