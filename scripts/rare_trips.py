import pandas as pd

GTFS_DIR = r"c:/doc/Igor/GIS/GTFS/ISR_2025/"
THRESHOLD_MIN = 10           # порог редкости — реже чем раз в 10 минут

# === LOAD GTFS ===
trips = pd.read_csv(GTFS_DIR + "trips.txt")
stop_times = pd.read_csv(GTFS_DIR + "stop_times.txt")

# === Время отправления первой остановки каждого trip ===
first_stops = (
    stop_times.sort_values(["trip_id", "stop_sequence"])
              .groupby("trip_id")
              .first()
              .reset_index()
)

def time_to_seconds(t):
    h, m, s = map(int, t.split(":"))
    return h*3600 + m*60 + s

first_stops["departure_sec"] = first_stops["departure_time"].apply(time_to_seconds)

# Добавляем route_id
merged = first_stops.merge(trips[["trip_id", "route_id"]], on="trip_id")

# === Анализ по маршрутам ===
results = []

for route_id, group in merged.groupby("route_id"):
    times = sorted(group["departure_sec"].tolist())
    total_trips = len(times)

    if total_trips < 2:
        results.append({
            "route_id": route_id,
            "total_trips": total_trips,
            "rare_intervals": 0,
            "rare_percent": 0.0
        })
        continue

    # интервалы между отправлениями
    intervals = [times[i+1] - times[i] for i in range(total_trips - 1)]

    rare_intervals = sum(1 for x in intervals if x > THRESHOLD_MIN * 60)
    rare_percent = round(rare_intervals / len(intervals) * 100, 2)

    results.append({
        "route_id": route_id,
        "total_trips": total_trips,
        "rare_intervals": rare_intervals,
        "rare_percent": rare_percent
    })

# === Результат ===
df = pd.DataFrame(results)
total_rare = df["rare_intervals"].sum()
print("TOTAL RARE INTERVALS =", total_rare)

