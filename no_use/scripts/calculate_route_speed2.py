import pandas as pd
import numpy as np
import os

def haversine_vectorized(lat1, lon1, lat2, lon2):
    """Calculates distance between consecutive points (vectorized)."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

def analyze_gtfs_to_csv(gtfs_path, output_file=r"c:\doc\Igor\GIS\route_speeds.csv"):
    print("1. Loading data...")
    try:
        trips = pd.read_csv(os.path.join(gtfs_path, "trips.txt"))
        stop_times = pd.read_csv(os.path.join(gtfs_path, "stop_times.txt"))
        shapes = pd.read_csv(os.path.join(gtfs_path, "shapes.txt"))
        routes = pd.read_csv(os.path.join(gtfs_path, "routes.txt"))
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # --- Calculating lengths of all shape_ids ---
    print("2. Calculating path lengths (shapes)...")
    shapes = shapes.sort_values(['shape_id', 'shape_pt_sequence'])
    shapes['lat_prev'] = shapes.groupby('shape_id')['shape_pt_lat'].shift(1)
    shapes['lon_prev'] = shapes.groupby('shape_id')['shape_pt_lon'].shift(1)
    
    mask = shapes['lat_prev'].notnull()
    shapes.loc[mask, 'dist'] = haversine_vectorized(
        shapes.loc[mask, 'lat_prev'], shapes.loc[mask, 'lon_prev'],
        shapes.loc[mask, 'shape_pt_lat'], shapes.loc[mask, 'shape_pt_lon']
    )
    shape_lengths = shapes.groupby('shape_id')['dist'].sum().reset_index()

    # --- Calculating trip durations ---
    print("3. Calculating trip durations...")
    def clean_time(t):
        try:
            h, m, s = map(int, t.split(':'))
            return h * 3600 + m * 60 + s
        except:
            return None

    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
    trip_times = stop_times.groupby('trip_id').agg(
        start_time=('departure_time', 'first'),
        end_time=('arrival_time', 'last')
    ).reset_index()

    # Время в часах для скорости и в минутах для отчета
    trip_times['duration_h'] = (trip_times['end_time'].apply(clean_time) - 
                                trip_times['start_time'].apply(clean_time)) / 3600
    trip_times['duration_min'] = trip_times['duration_h'] * 60

    # --- Data assembly ---
    print("4. Performing final route analysis...")
    df = trips.merge(shape_lengths, on='shape_id', how='left')
    df = df.merge(trip_times, on='trip_id', how='left')
    
    # Расчет скорости
    df['speed'] = df['dist'] / df['duration_h']
    
    # Фильтрация некорректных данных
    df = df[(df['speed'] > 0) & (np.isfinite(df['speed']))]

    # Группировка по route_id: добавляем дистанцию и время
    route_stats = df.groupby('route_id').agg(
        avg_distance_km=('dist', 'mean'),
        avg_duration_min=('duration_min', 'mean'),
        min_speed_kmh=('speed', 'min'),
        max_speed_kmh=('speed', 'max'),
        avg_speed_kmh=('speed', 'mean')
    ).reset_index()
    
    # --- Merging with routes.txt to get descriptions ---
    print("5. Merging with route names and descriptions...")
    cols_to_keep = ['route_id', 'route_short_name', 'route_long_name', 'route_desc']
    existing_cols = [c for c in cols_to_keep if c in routes.columns]
    routes_info = routes[existing_cols]

    final_report = route_stats.merge(routes_info, on='route_id', how='left')
    
    # Округление (2 знака после запятой)
    final_report = final_report.round(2)

    # Упорядочивание колонок для удобства чтения
    # Порядок: ID, Имена, Дистанция, Время, Скорости
    name_cols = [c for c in ['route_short_name', 'route_long_name', 'route_desc'] if c in final_report.columns]
    data_cols = ['avg_distance_km', 'avg_duration_min', 'min_speed_kmh', 'max_speed_kmh', 'avg_speed_kmh']
    
    new_column_order = ['route_id'] + name_cols + data_cols
    final_report = final_report[new_column_order]

    # Save to CSV
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        final_report.to_csv(output_file, index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"Error saving CSV: {e}")
        return
    
    print("-" * 30)
    print(f"Task completed!")
    print(f"Result saved to: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    gtfs_dir = r'c:\doc\Igor\GIS\GTFS\exp_08_2025\ISR_2025'
    analyze_gtfs_to_csv(gtfs_dir)