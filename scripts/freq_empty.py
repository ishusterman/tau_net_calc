import csv
from collections import defaultdict

def percent_trips_missing_times(path_to_stop_times):
    trips_missing = set()
    all_trips = set()
    trips_with_all_times = set()

    # Отслеживаем пропуски и количество остановок
    trip_has_missing = defaultdict(bool)
    trip_stop_count = defaultdict(int)

    with open(path_to_stop_times, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row["trip_id"]
            all_trips.add(trip_id)

            arrival = row["arrival_time"].strip()
            departure = row["departure_time"].strip()

            # Считаем количество остановок
            trip_stop_count[trip_id] += 1

            # Проверяем пропуски
            if arrival == "" or departure == "":
                trip_has_missing[trip_id] = True

    # Формируем итоговые множества
    for trip_id in all_trips:
        if trip_has_missing[trip_id]:
            trips_missing.add(trip_id)
        else:
            # Добавляем только поездки с >2 остановками
            if trip_stop_count[trip_id] > 2:
                trips_with_all_times.add(trip_id)

    if not all_trips:
        percent_missing = 0.0
    else:
        percent_missing = len(trips_missing) / len(all_trips) * 100

    return percent_missing, trips_with_all_times


# пример вызова
percent, full_trips = percent_trips_missing_times(
    r"c:\doc\Igor\GIS\GTFS\exp\hong kong\stop_times.txt"
)

print("Процент поездок с пропущенными временами:", percent)
print("Поездки, где все времена есть и более двух остановок:")
for t in full_trips:
    print(t)
