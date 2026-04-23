import pandas as pd

# Загрузка данных из CSV
file_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\israel-public-transportation_gtfs\\2024\\PKL\\GTFS\\gtfs_04dec_16h31m43s\\stop_times.txt"
#file_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\israel-public-transportation_gtfs\\stop_times.txt"
columns = ["trip_id", "stop_sequence", "arrival_time", "departure_time", "stop_id", "pickup_type", "drop_off_type", "shape_dist_traveled"]
data = pd.read_csv(file_path, names=columns, skiprows=1)

# Преобразование времени в datetime
for col in ["arrival_time", "departure_time"]:
    data[col] = pd.to_datetime(data[col], format="%H:%M:%S", errors='coerce')

# Извлечение часа из времени прибытия
data['hour'] = data['arrival_time'].dt.hour

# Подсчёт количества отправлений для каждого часа
departures_by_hour = data.groupby('hour').size()

# Сохранение результата в CSV
output_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\departures_by_hour.csv"
departures_by_hour.to_csv(output_path, header=["count"])

print("Количество отправлений по часам сохранено в:", output_path)
