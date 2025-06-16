"""
149364430,13714,129
149364430,43652,151
149364430,13720,290
149364430,13721,311
149364430,43651,377
149364430,13726,381
149364430,13722,399

"""

import pandas as pd

stop_times_file = r"C:\Users\geosimlab\Documents\Igor\israel-public-transportation_gtfs\2024\PKL2025\GTFS\gtfs_12jan_09h38m27s\stop_times.txt"
trips_file = r"C:\Users\geosimlab\Documents\Igor\israel-public-transportation_gtfs\2024\PKL2025\GTFS\gtfs_12jan_09h38m27s\trips.txt"
specific_stop_id = 13722  

stop_times = pd.read_csv(stop_times_file)
trips = pd.read_csv(trips_file)

filtered_stop_times = stop_times[stop_times["stop_id"] == specific_stop_id]


merged_data = pd.merge(filtered_stop_times, trips, on="trip_id")

direction_counts = merged_data["direction_id"].value_counts().sort_index()


count_direction_0 = direction_counts.get(0, 0) 
count_direction_1 = direction_counts.get(1, 0)


print(f"stop_id = {specific_stop_id}:")
print(f"  direction_id = 0: {count_direction_0}")
print(f"  direction_id = 1: {count_direction_1}")
