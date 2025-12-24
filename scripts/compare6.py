import csv

def find_destinations_with_longer_duration(file1_path, file2_path):
    """
    Находит Destination_ID во втором файле, у которых Duration стал больше,
    чем в первом файле.
    """
    # 1. Читаем первый файл и сохраняем данные в словарь.
    # Ключ: Origin_ID + Destination_ID (для уникальности), значение: Duration
    file1_data = {}
    with open(file1_path, 'r', newline='', encoding='utf-8') as file1:
        reader = csv.DictReader(file1)
        for row in reader:
            # Создаем уникальный ключ из Origin_ID и Destination_ID
            key = (row['Origin_ID'], row['Destination_ID'])
            # Преобразуем Duration в число
            try:
                duration = int(row['Duration'])
                file1_data[key] = duration
            except (ValueError, KeyError):
                # Пропускаем строки с некорректными данными
                continue

    # 2. Читаем второй файл и сравниваем данные.
    longer_duration_destinations = []
    with open(file2_path, 'r', newline='', encoding='utf-8') as file2:
        reader = csv.DictReader(file2)
        for row in reader:
            key = (row['Origin_ID'], row['Destination_ID'])
            
            try:
                duration_file2 = int(row['Duration'])
                
                # 3. Сравниваем значения.
                if key in file1_data:
                    duration_file1 = file1_data[key]
                    if duration_file2 > duration_file1:
                        longer_duration_destinations.append(row['Destination_ID'])
            except (ValueError, KeyError):
                # Пропускаем строки с некорректными данными
                continue
    
    # Возвращаем только уникальные Destination_ID
    return sorted(list(set(longer_duration_destinations)))

# Пример использования
file1 = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\304777527-2\250814_152439_PFXA_add_Green_Purple\250814_152439_PFXA_add_Green_Purple_min_duration.csv'
file2 = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\304777527-2\250814_152343_PFXA_add_3lines\250814_152343_PFXA_add_3lines_min_duration.csv'

# Предположим, что файл 'файл1.csv' содержит:
# Origin_ID,Start_time,...,Destination_ID,...,Duration
# 304777527,08:00:00,...,304777527,...,0
# 304777527,08:00:00,...,350662183,...,98

# И файл 'файл2.csv' содержит:
# Origin_ID,Start_time,...,Destination_ID,...,Duration
# 304777527,08:00:00,...,304777527,...,100  (Duration стал больше: 100 > 0)
# 304777527,08:00:00,...,350662183,...,150  (Duration стал больше: 150 > 98)

longer_destinations = find_destinations_with_longer_duration(file1, file2)
print(f"Destination_ID, у которых Duration стал больше: {longer_destinations}")
