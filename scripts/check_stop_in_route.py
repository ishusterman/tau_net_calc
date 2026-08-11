import pandas as pd

# === УКАЖИ ПУТИ К ФАЙЛАМ GTFS ===
TRIPS = r"c:\doc\Igor\GIS\GTFS\ISR_2025\trips.txt"
STOP_TIMES = r"c:\doc\Igor\GIS\GTFS\ISR_2025\stop_times.txt"
STOPS = r"c:\doc\Igor\GIS\GTFS\ISR_2025\stops.txt"

# === ВВОД ДАННЫХ ===
route_id = 13815        # маршрут
stop_id = 13154        # остановка

# === ЗАГРУЗКА GTFS ===
trips = pd.read_csv(TRIPS)
stop_times = pd.read_csv(STOP_TIMES)
stops = pd.read_csv(STOPS)

# === НАХОДИМ ВСЕ TRIP'ы МАРШРУТА ===
route_trips = trips[trips["route_id"] == route_id]
print (route_trips)

# === ФИЛЬТРУЕМ STOP_TIMES ПО НУЖНЫМ TRIP И ОСТАНОВКЕ ===
filtered = stop_times[
    (stop_times["trip_id"].isin(route_trips["trip_id"])) &
    (stop_times["stop_id"] == stop_id)
]

# === СОРТИРУЕМ ПО ВРЕМЕНИ ===
filtered = filtered.sort_values("arrival_time")

# === ВЫВОД РЕЗУЛЬТАТОВ ===
for _, row in filtered.iterrows():
    print(f"- Trip {row['trip_id']} - {row['arrival_time']}")

print ('Finish')