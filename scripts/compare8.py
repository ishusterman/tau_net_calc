import pandas as pd

"""
df = pd.read_csv(r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2018_800m\GTFS\footpath_road_projection.txt')
from_stop_id = '316947726'
filtered_df = df[df['from_stop_id'] == from_stop_id]
filtered_df.to_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\2zone\footpath_2018_316947726.csv', index=False)
"""

#footpath_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\2zone\footpath_2018_211621047.csv')
#footpath_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\2zone\footpath_2018_316947726.csv')
#trips_df = pd.read_csv(r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2018_800m\GTFS\gtfs_250820_125553\stop_times.txt')
#trips_info_df = pd.read_csv(r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2018_800m\GTFS\gtfs_250820_125553\trips.txt')
#shapes_df = pd.read_csv(r'c:\doc\Igor\GIS\GTFS\exp_08_2025\ISR_2018\shapes.txt')


#footpath_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\2zone\footpath_2025_211621047.csv')
footpath_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\2zone\footpath_2025_316947726.csv')
trips_df = pd.read_csv(r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2025_800m\GTFS\gtfs_250817_085821\stop_times.txt')
trips_info_df = pd.read_csv(r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2025_800m\GTFS\gtfs_250817_085821\trips.txt')
shapes_df = pd.read_csv(r'c:\doc\Igor\GIS\GTFS\exp_08_2025\ISR_2025\shapes.txt')

# Загружаем файл с информацией о маршрутах

footpath_stop_ids = footpath_df['to_stop_id'].astype(str).tolist()
trips_df['stop_id'] = trips_df['stop_id'].astype(str)
used_stops = trips_df[trips_df['stop_id'].isin(footpath_stop_ids)]

print(f"Total stops in footpath: {len(footpath_stop_ids)}")
print(f"Stops used in trips file: {len(used_stops)}")
print(f"Unique stops: {used_stops['stop_id'].nunique()}")

if len(used_stops) > 0:
    # Фильтруем по времени отдельно для 7:00-7:30 и 16:00-16:30
    morning_filtered = used_stops[used_stops['arrival_time'].between('07:00:00', '07:30:00')]
    evening_filtered = used_stops[used_stops['arrival_time'].between('16:00:00', '16:30:00')]
    
    # Получаем уникальные trip_id для каждого интервала
    morning_trip_ids = morning_filtered['trip_id'].unique()
    evening_trip_ids = evening_filtered['trip_id'].unique()
    
    # Находим соответствующие route_id и shape_id для trip_id
    morning_routes_info = trips_info_df[trips_info_df['trip_id'].isin(morning_trip_ids)]
    evening_routes_info = trips_info_df[trips_info_df['trip_id'].isin(evening_trip_ids)]
    
    morning_routes = morning_routes_info['route_id'].unique()
    evening_routes = evening_routes_info['route_id'].unique()
    
    morning_shapes = morning_routes_info['shape_id'].unique()
    evening_shapes = evening_routes_info['shape_id'].unique()
    
    # Статистика для утреннего интервала 7:00-7:30
    print(f"Morning interval 7:00-7:30:")
    print(f"  Unique trip_id: {len(morning_trip_ids)}")
    print(f"  Unique route_id: {len(morning_routes)}")
    print(f"  Unique shape_id: {len(morning_shapes)}")
    print(f"  Total stop occurrences: {len(morning_filtered)}")
    
    # Формируем фильтр shape_id для QGIS (утро)
    morning_shape_filter = " OR ".join([f'"shape_id" = {shape}' for shape in morning_shapes])
    print(f"  QGIS shape filter for morning:")
    print(f"    {morning_shape_filter}")
    
    # Статистика для вечернего интервала 16:00-16:30
    print(f"Evening interval 16:00-16:30:")
    print(f"  Unique trip_id: {len(evening_trip_ids)}")
    print(f"  Unique route_id: {len(evening_routes)}")
    print(f"  Unique shape_id: {len(evening_shapes)}")
    print(f"  Total stop occurrences: {len(evening_filtered)}")
    
    # Формируем фильтр shape_id для QGIS (вечер)
    evening_shape_filter = " OR ".join([f'"shape_id" = {shape}' for shape in evening_shapes])
    print(f"  QGIS shape filter for evening:")
    print(f"    {evening_shape_filter}")
    
    # Общая статистика по обоим интервалам
    total_filtered = len(morning_filtered) + len(evening_filtered)
    
    # Объединяем trip_id из обоих интервалов
    all_trip_ids = set(morning_trip_ids).union(set(evening_trip_ids))
    all_routes_info = trips_info_df[trips_info_df['trip_id'].isin(all_trip_ids)]
    all_routes = all_routes_info['route_id'].unique()
    all_shapes = all_routes_info['shape_id'].unique()
    
    print(f"Total statistics (7:00-7:30 + 16:00-16:30):")
    print(f"  Unique trip_id: {len(all_trip_ids)}")
    print(f"  Unique route_id: {len(all_routes)}")
    print(f"  Unique shape_id: {len(all_shapes)}")
    print(f"  Total stop occurrences: {total_filtered}")
    
    # Формируем общий фильтр shape_id для QGIS
    total_shape_filter = " OR ".join([f'"shape_id" = {shape}' for shape in all_shapes])
    print(f"  QGIS shape filter for total:")
    print(f"    {total_shape_filter}")

# ДИАГНОСТИКА: Проверяем наличие shape_id в shapes.txt
try:
    
    
    # Проверяем, какие shape_id из нашего списка существуют в shapes.txt
    existing_shapes = shapes_df[shapes_df['shape_id'].isin(all_shapes)]
    missing_shapes = set(all_shapes) - set(existing_shapes['shape_id'].unique())
    
    print(f"\nDIAGNOSTICS:")
    print(f"  Total shape_id in our analysis: {len(all_shapes)}")
    print(f"  Shape_id found in shapes.txt: {existing_shapes['shape_id'].nunique()}")
    print(f"  Missing shape_id in shapes.txt: {len(missing_shapes)}")
    
    if len(missing_shapes) > 0:
        print(f"  Missing shape_id values: {sorted(missing_shapes)}")
        
except FileNotFoundError:
    print(f"\nWARNING: shapes.txt file not found at expected location")
    print(f"  Cannot verify which shape_id exist in the dataset")

# Дополнительная диагностика: проверяем типы данных
print(f"\nDATA TYPE CHECK:")
print(f"  Shape_id data type in trips_info: {trips_info_df['shape_id'].dtype}")
print(f"  Sample shape_id values: {list(all_shapes)[:5]}")