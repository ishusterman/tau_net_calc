import pandas as pd
from math import radians, sin, cos, sqrt, atan2
import numpy as np
import os

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def calculate_avg_speed(gtfs_path, route_id):
    """Вычисляет среднюю скорость маршрута (первая поездка)."""
    try:
        trips = pd.read_csv(os.path.join(gtfs_path, "trips.txt"))
        stop_times = pd.read_csv(os.path.join(gtfs_path, "stop_times.txt"))
        shapes = pd.read_csv(os.path.join(gtfs_path, "shapes.txt"))
    except FileNotFoundError as e:
        return route_id, f"Ошибка загрузки файлов: {e}"

    route_trips = trips[trips['route_id'] == route_id]
    if route_trips.empty:
        return route_id, "Маршрут не найден"

    trip = route_trips.iloc[0]
    shape_points = shapes[shapes['shape_id'] == trip['shape_id']].sort_values('shape_pt_sequence')
    if len(shape_points) < 2:
        return route_id, "Недостаточно shape-точек"

    # Расстояние
    dist = sum(haversine(shape_points.iloc[i-1]['shape_pt_lat'], shape_points.iloc[i-1]['shape_pt_lon'],
                         shape_points.iloc[i]['shape_pt_lat'], shape_points.iloc[i]['shape_pt_lon'])
               for i in range(1, len(shape_points)))

    # Время
    trip_stops = stop_times[stop_times['trip_id'] == trip['trip_id']].sort_values('stop_sequence')
    if len(trip_stops) < 2:
        return route_id, "Недостаточно остановок"
    try:
        t1 = pd.to_timedelta(trip_stops.iloc[0]['departure_time'])
        t2 = pd.to_timedelta(trip_stops.iloc[-1]['arrival_time'])
        hours = (t2 - t1).total_seconds() / 3600
        if hours <= 0:
            return route_id, "Некорректное время"
        return route_id, round(dist / hours, 2)
    except Exception:
        return route_id, "Ошибка времени"

def analyze_routes(gtfs_path, route_ids):
    print(f"\n{'Route ID':<12} {'Avg Speed (km/h)':<18} {'Status'}")
    print("=" * 50)
    for rid in route_ids:
        rid, result = calculate_avg_speed(gtfs_path, rid)
        if isinstance(result, (int, float)):
            print(f"{rid:<12} {result:<18} OK")
        else:
            print(f"{rid:<12} {'-':<18} {result}")

if __name__ == "__main__":
    gtfs_path = r'c:\doc\Igor\GIS\GTFS\exp_08_2025\ISR_2025_cut'
    route_ids = [34445, 34446, 34447, 34448, 34449, 34450]  # Добавьте нужные ID маршрутов
    #gtfs_path = r"c:\doc\Igor\GIS\GTFS\exp_08_2025\ISR_2018"
    #route_ids = [13429, 13428, 2332]
    analyze_routes(gtfs_path, route_ids)