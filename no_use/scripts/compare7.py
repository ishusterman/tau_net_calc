import pandas as pd

# Read files
df_2018 = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\208287153\2018\result_round_trip.csv')
df_2025 = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\208287153\2025\result_round_trip.csv')

# Find goals that exist only in one file
goals_only_2018 = set(df_2018['Round_Trip_Goal']) - set(df_2025['Round_Trip_Goal'])
goals_only_2025 = set(df_2025['Round_Trip_Goal']) - set(df_2018['Round_Trip_Goal'])

# Merge data by Round_Trip_Goal
merged = pd.merge(df_2018, df_2025, on='Round_Trip_Goal', 
                  suffixes=('_2018', '_2025'))

# Compare Duration_AVG
merged['Duration_Increase'] = merged['Duration_AVG_2025'] > merged['Duration_AVG_2018']
merged['Duration_Decrease'] = merged['Duration_AVG_2025'] < merged['Duration_AVG_2018']
merged['Duration_Same'] = merged['Duration_AVG_2025'] == merged['Duration_AVG_2018']

# Count results
total = len(merged)
increase_count = merged['Duration_Increase'].sum()
decrease_count = merged['Duration_Decrease'].sum()
same_count = merged['Duration_Same'].sum()

print("COMPARISON RESULTS:")
print(f"Total comparable goals: {total}")
print(f"Duration_AVG increased: {increase_count} ({increase_count/total*100:.1f}%)")
print(f"Duration_AVG decreased: {decrease_count} ({decrease_count/total*100:.1f}%)")
print(f"Duration_AVG no change: {same_count} ({same_count/total*100:.1f}%)")

# Additional statistics
merged['Duration_Diff'] = merged['Duration_AVG_2025'] - merged['Duration_AVG_2018']
print(f"\nAverage Duration_AVG change: {merged['Duration_Diff'].mean():.1f}")
print(f"Median Duration_AVG change: {merged['Duration_Diff'].median():.1f}")
print(f"Max increase: {merged['Duration_Diff'].max():.1f}")
print(f"Max decrease: {merged['Duration_Diff'].min():.1f}")

# Summary statistics
print(f"\nSUMMARY STATISTICS:")
print(f"Total goals in 2018 file: {len(df_2018)}")
print(f"Total goals in 2025 file: {len(df_2025)}")
print(f"Common goals: {total}")
print(f"Goals only in 2018: {len(goals_only_2018)}")
print(f"Goals only in 2025: {len(goals_only_2025)}")

# Analyze boarding opportunities for 2018 and 2025
print(f"\n" + "="*60)
print("BOARDING OPPORTUNITIES ANALYSIS")
print("="*60)

try:
    # Define file paths for both years
    transfers_2018_path = r'c:\doc\Igor\GIS\prg\exp_08_2025\footpath__2018_208287153.csv'
    transfers_2025_path = r'c:\doc\Igor\GIS\prg\exp_08_2025\footpath__2025_208287153.csv'
    stop_times_2018_path = r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2018_800m\GTFS\gtfs_250820_125553\stop_times.txt'
    stop_times_2025_path = r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2025_800m\GTFS\gtfs_250817_085821\stop_times.txt'
    
    # Read transfers files
    df_transfers_2018 = pd.read_csv(transfers_2018_path)
    df_transfers_2025 = pd.read_csv(transfers_2025_path)
    
    # Get all to_stop_id values for both years
    to_stop_ids_2018 = df_transfers_2018['to_stop_id'].unique()
    to_stop_ids_2025 = df_transfers_2025['to_stop_id'].unique()
    
    print(f"Transfers analysis:")
    print(f"2018: {len(to_stop_ids_2018)} unique to_stop_id values")
    print(f"2025: {len(to_stop_ids_2025)} unique to_stop_id values")
    
    # Function to count boarding opportunities per stop
    def count_boarding_opportunities(stop_times_file, to_stop_ids, year):
        # Read stop_times file
        df_stop_times = pd.read_csv(stop_times_file, low_memory=False)
        
        # Convert stop_id to string for consistent comparison
        df_stop_times['stop_id'] = df_stop_times['stop_id'].astype(str)
        to_stop_ids_str = [str(stop_id) for stop_id in to_stop_ids]
        
        # Filter only stops that are in our transfers list
        df_filtered_stops = df_stop_times[df_stop_times['stop_id'].isin(to_stop_ids_str)]
        
        # Count total boarding opportunities (all stop events)
        total_boardings = len(df_filtered_stops)
        
        # Count unique stops with routes
        stops_with_routes = df_filtered_stops['stop_id'].nunique()
        
        # Count unique trips (trip_id) through these stops
        unique_trips = df_filtered_stops['trip_id'].nunique()
        
        # Calculate average boardings per stop
        avg_boardings_per_stop = total_boardings / stops_with_routes if stops_with_routes > 0 else 0
        
        print(f"\n{year} BOARDING ANALYSIS:")
        print(f"  Stops with routes: {stops_with_routes}")
        print(f"  Total boarding opportunities: {total_boardings}")
        print(f"  Unique trips: {unique_trips}")
        print(f"  Average boardings per stop: {avg_boardings_per_stop:.1f}")
        
        return {
            'stops_with_routes': stops_with_routes,
            'total_boardings': total_boardings,
            'unique_trips': unique_trips,
            'avg_boardings_per_stop': avg_boardings_per_stop
        }
    
    # Analyze boarding opportunities for both years
    boarding_2018 = count_boarding_opportunities(stop_times_2018_path, to_stop_ids_2018, "2018")
    boarding_2025 = count_boarding_opportunities(stop_times_2025_path, to_stop_ids_2025, "2025")
    
    # Calculate changes
    stops_change = boarding_2025['stops_with_routes'] - boarding_2018['stops_with_routes']
    boardings_change = boarding_2025['total_boardings'] - boarding_2018['total_boardings']
    trips_change = boarding_2025['unique_trips'] - boarding_2018['unique_trips']
    
    stops_change_pct = (stops_change / boarding_2018['stops_with_routes']) * 100 if boarding_2018['stops_with_routes'] > 0 else 0
    boardings_change_pct = (boardings_change / boarding_2018['total_boardings']) * 100 if boarding_2018['total_boardings'] > 0 else 0
    trips_change_pct = (trips_change / boarding_2018['unique_trips']) * 100 if boarding_2018['unique_trips'] > 0 else 0
    
    print(f"\n" + "="*50)
    print("BOARDING OPPORTUNITIES COMPARISON")
    print("="*50)
    print(f"Stops with routes: {boarding_2018['stops_with_routes']} → {boarding_2025['stops_with_routes']} ({stops_change:+.0f}, {stops_change_pct:+.1f}%)")
    print(f"Total boarding opportunities: {boarding_2018['total_boardings']} → {boarding_2025['total_boardings']} ({boardings_change:+.0f}, {boardings_change_pct:+.1f}%)")
    print(f"Unique trips: {boarding_2018['unique_trips']} → {boarding_2025['unique_trips']} ({trips_change:+.0f}, {trips_change_pct:+.1f}%)")
    print(f"Average boardings per stop: {boarding_2018['avg_boardings_per_stop']:.1f} → {boarding_2025['avg_boardings_per_stop']:.1f}")
    
    # CORRECTED ANALYSIS WITH PROPER TERMINOLOGY
    print(f"\n" + "="*60)
    print("CORRECTED BOARDING OPPORTUNITIES ANALYSIS")
    print("="*60)

    def correct_boarding_analysis(stop_times_file, to_stop_ids, year):
        df_stop_times = pd.read_csv(stop_times_file, low_memory=False)
        df_stop_times['stop_id'] = df_stop_times['stop_id'].astype(str)
        to_stop_ids_str = [str(stop_id) for stop_id in to_stop_ids]
        
        df_filtered_stops = df_stop_times[df_stop_times['stop_id'].isin(to_stop_ids_str)]
        
        # Правильные метрики
        total_boardings = len(df_filtered_stops)  # Все остановки транспорта
        unique_trips = df_filtered_stops['trip_id'].nunique()  # Уникальные рейсы
        unique_stops = df_filtered_stops['stop_id'].nunique()  # Уникальные остановки
        
        # Средние значения
        avg_boardings_per_trip = total_boardings / unique_trips if unique_trips > 0 else 0
        avg_boardings_per_stop = total_boardings / unique_stops if unique_stops > 0 else 0
        avg_trips_per_stop = unique_trips / unique_stops if unique_stops > 0 else 0
        
        print(f"\n{year} CORRECTED ANALYSIS:")
        print(f"  Total boarding opportunities: {total_boardings}")  # Всего возможностей посадки
        print(f"  Unique trips (trip_id): {unique_trips}")  # Уникальных рейсов
        print(f"  Unique stops with service: {unique_stops}")  # Остановок с обслуживанием
        print(f"  Average boardings per trip: {avg_boardings_per_trip:.1f}")  # Среднее остановок на рейс
        print(f"  Average boardings per stop: {avg_boardings_per_stop:.1f}")  # Среднее остановок на остановку
        print(f"  Average trips per stop: {avg_trips_per_stop:.1f}")  # Среднее рейсов на остановку
        
        return {
            'total_boardings': total_boardings,
            'unique_trips': unique_trips,
            'unique_stops': unique_stops,
            'avg_boardings_per_trip': avg_boardings_per_trip,
            'avg_boardings_per_stop': avg_boardings_per_stop,
            'avg_trips_per_stop': avg_trips_per_stop
        }

    # Провести корректный анализ
    corrected_2018 = correct_boarding_analysis(stop_times_2018_path, to_stop_ids_2018, "2018")
    corrected_2025 = correct_boarding_analysis(stop_times_2025_path, to_stop_ids_2025, "2025")

    # Сравнение
    print(f"\n" + "="*50)
    print("CORRECTED COMPARISON")
    print("="*50)
    print(f"Total boarding opportunities: {corrected_2018['total_boardings']} → {corrected_2025['total_boardings']}")
    print(f"Unique trips: {corrected_2018['unique_trips']} → {corrected_2025['unique_trips']}")
    print(f"Stops with service: {corrected_2018['unique_stops']} → {corrected_2025['unique_stops']}")
    print(f"Avg boardings per trip: {corrected_2018['avg_boardings_per_trip']:.1f} → {corrected_2025['avg_boardings_per_trip']:.1f}")
    print(f"Avg trips per stop: {corrected_2018['avg_trips_per_stop']:.1f} → {corrected_2025['avg_trips_per_stop']:.1f}")
    
    # Explanation of the difference
    print(f"\n" + "="*60)
    print("EXPLANATION OF THE DIFFERENCE")
    print("="*60)
    ratio_2018 = corrected_2018['total_boardings'] / corrected_2018['unique_trips']
    ratio_2025 = corrected_2025['total_boardings'] / corrected_2025['unique_trips']
    
    print(f"2018: {corrected_2018['total_boardings']:,} boardings / {corrected_2018['unique_trips']:,} trips = {ratio_2018:.1f} boardings per trip")
    print(f"2025: {corrected_2025['total_boardings']:,} boardings / {corrected_2025['unique_trips']:,} trips = {ratio_2025:.1f} boardings per trip")
    print(f"\nThis means:")
    print(f"- Each trip makes on average {ratio_2018:.1f} stops at our transfer stops (2018)")
    print(f"- Each trip makes on average {ratio_2025:.1f} stops at our transfer stops (2025)")
    print(f"- Higher ratio = more transfer stops served by each trip")
        
except FileNotFoundError as e:
    print(f"File not found: {e}")
except Exception as e:
    print(f"Error analyzing boarding opportunities: {e}")