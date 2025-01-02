import pandas as pd

# Загрузка данных из CSV
file_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\israel-public-transportation_gtfs\\2024\\PKL\\GTFS\\gtfs_04dec_16h31m43s\\stop_times.txt"
columns = ["trip_id", "stop_sequence", "arrival_time", "departure_time", "stop_id", "pickup_type", "drop_off_type", "shape_dist_traveled"]
data = pd.read_csv(file_path, names=columns, skiprows=1)

# Преобразование времени в datetime
for col in ["arrival_time", "departure_time"]:
    data[col] = pd.to_datetime(data[col], format="%H:%M:%S", errors='coerce')

# Добавление временного интервала
conditions = [
    (data['arrival_time'].dt.hour >= 6) & (data['arrival_time'].dt.hour < 10),
    (data['arrival_time'].dt.hour >= 10) & (data['arrival_time'].dt.hour < 16),
    (data['arrival_time'].dt.hour >= 16) & (data['arrival_time'].dt.hour < 22)
]
time_labels = ["morning", "daytime", "evening"]
data['time_interval'] = pd.cut(data['arrival_time'].dt.hour, bins=[5, 10, 16, 22], labels=time_labels, right=False)

# Группировка по stop_id и временным интервалам
stop_activity = data.groupby(['stop_id', 'time_interval']).size().unstack(fill_value=0)

# Фильтрация stop_id с высокой дневной активностью
stop_activity['day_vs_others'] = (stop_activity['daytime'] > 1.3 * stop_activity['morning']) & (stop_activity['daytime'] > 1.3 * stop_activity['evening'])
frequent_stops = stop_activity[stop_activity['day_vs_others']]

frequent_stops.to_csv(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\frequent_stops.csv")
print("Ok")
