import pandas as pd
import numpy as np

"""
# Загрузка данных из файлов
try:
    # Загружаем первый файл с остановками
    #stops_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\footpath_road_projection_2018.txt')
    stops_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\footpath_road_projection_2025.txt')
    
    # Загружаем второй файл с OSM данными
    #osm_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\312_buildings.csv')
    #osm_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\TLV_26179.csv')
    osm_df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\208287153_building.csv')
    
    # Преобразуем osm_id в числа
    osm_df['osm_id'] = osm_df['osm_id'].astype(str).str.strip('"').astype(int)
    
    # Извлекаем числовую часть из from_stop_id (убираем 'stop' и преобразуем в число)
    stops_df['from_stop_id_clean'] = stops_df['from_stop_id'].astype(str).str.replace('stop', '', regex=False).astype(int)
    
    # Фильтруем первый файл, оставляя только те строки, где from_stop_id_clean есть в osm_id
    filtered_stops = stops_df[stops_df['from_stop_id_clean'].isin(osm_df['osm_id'])]
    
    # Удаляем временную колонку
    filtered_stops = filtered_stops.drop('from_stop_id_clean', axis=1)
    
    # Сохраняем результат в новый файл
    filtered_stops.to_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\footpath__2025_208287153.csv', index=False)
    
    print("Результат сохранен в файл")
   

except FileNotFoundError as e:
    print(f"Ошибка: Файл не найден - {e}")
except Exception as e:
    print(f"Произошла ошибка: {e}")

"""
print("=" * 40)

df = pd.read_csv(r'c:\doc\Igor\GIS\prg\exp_08_2025\footpath__2025_208287153.csv')

# Basic statistics in meters
print(f"Total walking routes: {len(df):,}")
print(f"Residential buildings (origins): {df['from_stop_id'].nunique():,}")
print(f"Transit stops (destinations): {df['to_stop_id'].nunique():,}")

# Distance analysis in meters
print(f"\nWalking distance analysis (meters):")
print(f"Minimum distance: {df['min_transfer_time'].min()} m")
print(f"Maximum distance: {df['min_transfer_time'].max()} m")
print(f"Average distance: {df['min_transfer_time'].mean():.1f} m")
print(f"Median distance: {df['min_transfer_time'].median():.1f} m")

# Distance distribution analysis
distances = df['min_transfer_time']
print(f"\nDistance distribution:")
print(f"Standard deviation: {distances.std():.1f} m")
print(f"25th percentile: {np.percentile(distances, 25):.1f} m")
print(f"75th percentile: {np.percentile(distances, 75):.1f} m")

# Walking distance categories (typical pedestrian thresholds)
print(f"\nWalking distance categories:")
categories = {
    "Very short (<200m)": (0, 200),
    "Short (200-400m)": (200, 400),
    "Medium (400-600m)": (400, 600),
    "Long (600-800m)": (600, 800)
}

for category, (min_dist, max_dist) in categories.items():
    count = len(df[(df['min_transfer_time'] >= min_dist) & (df['min_transfer_time'] < max_dist)])
    percentage = count / len(df) * 100
    print(f"{category}: {count:,} routes ({percentage:.1f}%)")

# Accessibility analysis
print(f"\nAccessibility analysis:")
print(f"Routes within 400m (5 min walk): {len(df[df['min_transfer_time'] <= 400]):,} ({len(df[df['min_transfer_time'] <= 400])/len(df)*100:.1f}%)")
print(f"Routes within 800m (10 min walk): {len(df[df['min_transfer_time'] <= 800]):,} ({len(df[df['min_transfer_time'] <= 800])/len(df)*100:.1f}%)")

# Connectivity per building
buildings_connectivity = df.groupby('from_stop_id').size()
print(f"\nPer building connectivity:")
print(f"Average stops accessible per building: {buildings_connectivity.mean():.1f}")
print(f"Minimum stops accessible: {buildings_connectivity.min()}")
print(f"Maximum stops accessible: {buildings_connectivity.max()}")

# Stops coverage
stops_coverage = df.groupby('to_stop_id').size()
print(f"\nStops coverage analysis:")
print(f"Average buildings per stop: {stops_coverage.mean():.1f}")
print(f"Most accessible stop: {stops_coverage.idxmax()} with {stops_coverage.max()} buildings")
print(f"Least accessible stop: {stops_coverage.idxmin()} with {stops_coverage.min()} buildings")
