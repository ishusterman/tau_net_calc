import csv

def find_buildings_with_higher_total(file1_path, file2_path):
    """
    Находит Origin_ID во втором файле, у которых bldg_total на 200+ больше,
    чем в первом файле.
    """
    # 1. Читаем первый файл и сохраняем данные в словарь
    file1_data = {}
    with open(file1_path, 'r') as file1:
        reader = csv.DictReader(file1)
        for row in reader:
            origin_id = row['Origin_ID']
            bldg_total = int(row['bldg_total'])
            file1_data[origin_id] = bldg_total

    # 2. Читаем второй файл и сравниваем данные
    result_ids = []
    with open(file2_path, 'r') as file2:
        reader = csv.DictReader(file2)
        for row in reader:
            origin_id = row['Origin_ID']
            bldg_total_file2 = int(row['bldg_total'])

            # 3. Сравниваем значения
            if origin_id in file1_data:
                bldg_total_file1 = file1_data[origin_id]
                if bldg_total_file2 > bldg_total_file1 + 200:
                    result_ids.append(origin_id)

    return result_ids

# Пример использования
file2_path = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\reg_1408\250814_160250_PFXR_add_Green_Purple\250814_160250_PFXR_add_Green_Purple_bldg_min_duration.csv'
file1_path = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\reg_1408\250814_171151_PFXR_add_3lines\250814_171151_PFXR_add_3lines_bldg_min_duration.csv'

# Предположим, что у вас есть два файла file1.csv и file2.csv с данными
# Содержимое file1.csv
# Origin_ID,5m,10m,15m,20m,25m,30m,bldg_total
# 167164260,14,50,615,2715,7628,14834,14834
# 336916983,148,507,2263,5537,9468,16644,16644

# Содержимое file2.csv
# Origin_ID,5m,10m,15m,20m,25m,30m,bldg_total
# 167164260,14,50,615,2715,7628,15050,15050 # bldg_total > 14834 + 200
# 336916983,148,507,2263,5537,9468,16644,16644 # bldg_total == 16644

higher_total_ids = find_buildings_with_higher_total(file1_path, file2_path)
print(f"Origin_ID, у которых bldg_total во втором файле превышает значение из первого на 200+: {higher_total_ids}")