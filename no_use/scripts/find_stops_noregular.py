import pandas as pd

# Загрузка данных из CSV
file_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\israel-public-transportation_gtfs\\2024\\PKL\\GTFS\\gtfs_04dec_16h31m43s\\stop_times.txt"
columns = ["trip_id", "stop_sequence", "arrival_time", "departure_time", "stop_id", "pickup_type", "drop_off_type", "shape_dist_traveled"]
data = pd.read_csv(file_path, names=columns, skiprows=1)

# Преобразование времени в datetime
for col in ["arrival_time", "departure_time"]:
    data[col] = pd.to_datetime(data[col], format="%H:%M:%S", errors='coerce')

# Определение временных интервалов и меток
bins = [5, 10, 16, 21]  # Утро, день, вечер
time_labels = ["morning", "daytime", "evening"]  # Метки для 3 интервалов

# Преобразование arrival_time в интервалы
data['time_interval'] = pd.cut(data['arrival_time'].dt.hour, bins=bins, labels=time_labels, right=False)

# Группировка по stop_id и временным интервалам
stop_activity = data.groupby(['stop_id', 'time_interval']).size().unstack(fill_value=0)

# Фильтрация stop_id с высокой активностью в одном из временных интервалов
stop_activity['peak_increase'] = (
    (stop_activity['morning'] > 1.3 * stop_activity['daytime']) | 
    (stop_activity['evening'] > 1.3 * stop_activity['daytime'])
) & (stop_activity['daytime'] > 5)  # Условие на дневную активность

# Отбор остановок, соответствующих условиям
frequent_peak_stops = stop_activity[stop_activity['peak_increase']]

# Сохранение результата в CSV
output_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\frequent_peak_stops.csv"
frequent_peak_stops.to_csv(output_path)

print("Анализ завершён. Результаты сохранены в:", output_path)
