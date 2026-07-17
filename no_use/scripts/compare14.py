import pandas as pd
import os

def time_to_seconds(time_str):
    """Convert HH:MM:SS to seconds"""
    h, m, s = map(int, time_str.split(':'))
    return h*3600 + m*60 + s

def filter_times(time_str):
    """Check if time is in 07:00-09:00 or 16:00-18:00 ranges"""
    total_seconds = time_to_seconds(time_str)
    if 7*3600 <= total_seconds <= 9*3600:
        return "morning"
    elif 16*3600 <= total_seconds <= 18*3600:
        return "evening"
    else:
        return "other"

def mean_interval(times):
    """Compute mean interval in minutes for a list of HH:MM:SS times"""
    if len(times) < 2:
        return None
    seconds_list = [time_to_seconds(t) for t in times]
    intervals = [seconds_list[i+1] - seconds_list[i] for i in range(len(seconds_list)-1)]
    return sum(intervals)/len(intervals)/60  # in minutes

def get_route_start_times(gtfs_path, route_ids):
    trips = pd.read_csv(os.path.join(gtfs_path, "trips.txt"))
    stop_times = pd.read_csv(os.path.join(gtfs_path, "stop_times.txt"))

    results = {}

    for route_id in route_ids:
        # Преобразуем route_id в строку для обработки
        route_id_str = str(route_id)
        
        # Пробуем разные варианты поиска
        search_variants = [
            route_id_str,  # как строка
            route_id_str.replace('_1', ''),  # без суффикса
            int(route_id_str.replace('_1', '')) if route_id_str.replace('_1', '').isdigit() else route_id_str,  # как число
            route_id  # оригинальное значение
        ]
        
        route_trips = None
        used_variant = None
        
        for variant in search_variants:
            print(f"Trying to find route with variant: {variant} (type: {type(variant)})")
            route_trips = trips[trips['route_id'] == variant]
            if not route_trips.empty:
                used_variant = variant
                print(f"Found route using variant: {variant}")
                break
        
        if route_trips is None or route_trips.empty:
            print(f"Route {route_id} not found in any variant")
            results[route_id] = {
                "start_times_all_day": [],
                "start_times_morning": [],
                "start_times_evening": [],
                "start_times_other": [],
                "count_all_day": 0,
                "count_morning": 0,
                "count_evening": 0,
                "count_other": 0,
                "mean_interval_all_day": None,
                "mean_interval_morning": None,
                "mean_interval_evening": None,
                "mean_interval_other": None
            }
            continue

        print(f"Found {len(route_trips)} trips for route {used_variant}")

        first_stops = stop_times[stop_times['trip_id'].isin(route_trips['trip_id'])]
        if first_stops.empty:
            print(f"No stop times found for trips of route {used_variant}")
            results[route_id] = {
                "start_times_all_day": [],
                "start_times_morning": [],
                "start_times_evening": [],
                "start_times_other": [],
                "count_all_day": 0,
                "count_morning": 0,
                "count_evening": 0,
                "count_other": 0,
                "mean_interval_all_day": None,
                "mean_interval_morning": None,
                "mean_interval_evening": None,
                "mean_interval_other": None
            }
            continue

        first_stops = first_stops.sort_values(['trip_id', 'stop_sequence']).groupby('trip_id').first()
        start_times_all_day = sorted(first_stops['departure_time'].tolist())
        
        print(f"Route {route_id}: Found {len(start_times_all_day)} total start times")
        
        # Separate times into categories
        morning_times = sorted([t for t in start_times_all_day if filter_times(t) == "morning"])
        evening_times = sorted([t for t in start_times_all_day if filter_times(t) == "evening"])
        other_times = sorted([t for t in start_times_all_day if filter_times(t) == "other"])

        results[route_id] = {
            "start_times_all_day": start_times_all_day,
            "start_times_morning": morning_times,
            "start_times_evening": evening_times,
            "start_times_other": other_times,
            "count_all_day": len(start_times_all_day),
            "count_morning": len(morning_times),
            "count_evening": len(evening_times),
            "count_other": len(other_times),
            "mean_interval_all_day": mean_interval(start_times_all_day),
            "mean_interval_morning": mean_interval(morning_times),
            "mean_interval_evening": mean_interval(evening_times),
            "mean_interval_other": mean_interval(other_times)
        }

    return results

# Example usage
gtfs_folder = r"c:\doc\Igor\GIS\GTFS\exp_08_2025\ISR_2018"

gtfs_folder = r"c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2018_800m\GTFS\gtfs_250820_125553"

# Пробуем разные варианты
routes_list = [39167, 39168]  # как числа

routes_list = [22189]  # как числа

route_info = get_route_start_times(gtfs_folder, routes_list)
for route, info in route_info.items():
    print(f"\nRoute {route}:")
    print(f"  Total starts (all day): {info['count_all_day']}")
    print(f"  Morning starts (07:00-09:00): {info['count_morning']}")
    print(f"  Evening starts (16:00-18:00): {info['count_evening']}")
    print(f"  Other time starts: {info['count_other']}")
    print(f"  Mean interval all day: {info['mean_interval_all_day']} minutes")
    print(f"  Mean interval morning: {info['mean_interval_morning']} minutes")
    print(f"  Mean interval evening: {info['mean_interval_evening']} minutes")
    print(f"  Mean interval other: {info['mean_interval_other']} minutes")
    
    # ВЫВОДИМ ВСЕ ВРЕМЕНА СТАРТОВ В ТЕЧЕНИЕ СУТОК
    if info['count_all_day'] > 0:
        print(f"  ALL START TIMES THROUGHOUT THE DAY:")
        for i, time in enumerate(info['start_times_all_day'], 1):
            print(f"    {i:2d}. {time}")
    
    # Также выводим отдельно времена вне пиковых диапазонов
    if info['count_other'] > 0:
        print(f"  NON-PEAK START TIMES:")
        for i, time in enumerate(info['start_times_other'], 1):
            print(f"    {i:2d}. {time}")
    
    print("-" * 80)