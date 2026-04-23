import pandas as pd
from collections import Counter
import time

start_time = time.time()

# Загрузка файлов
file1 = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\roundtrip211621047_2018faster.csv"
file2 = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\all_from_2018.csv"
file3 = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\all_to_2018.csv"
file4 = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\lines.csv"

print("Загрузка файлов...")

# Загружаем только нужные колонки для ускорения
df1 = pd.read_csv(file1, usecols=['Round_Trip_Goal'])
goals = df1['Round_Trip_Goal'].unique()
print(f"Найдено {len(goals)} целей для анализа")

line_stats = Counter()
empty_line2_count = 0

# Функция для извлечения числовой части линии
def extract_line_number(line_id):
    if pd.isna(line_id):
        return None
    line_str = str(line_id)
    # Извлекаем часть до первого подчеркивания
    if '_' in line_str:
        return line_str.split('_')[0]
    return line_str

# Обрабатываем файлы по одному, читая чанками
files_to_process = [(file2, 'all_from'), (file3, 'all_to')]

for file_path, file_name in files_to_process:
    print(f"Обработка {file_name}...")
    
    # Читаем файл частями
    chunk_size = 10000
    for chunk in pd.read_csv(file_path, chunksize=chunk_size, usecols=['Destination_ID', 'Line_ID1', 'Line_ID2']):
        # Фильтруем строки с нужными Destination_ID
        mask = chunk['Destination_ID'].isin(goals)
        filtered_chunk = chunk[mask]
        
        # Извлекаем числовую часть Line_ID1 и собираем статистику
        line_numbers = filtered_chunk['Line_ID1'].apply(extract_line_number).dropna()
        line_stats.update(line_numbers)
        
        # Считаем пустые Line_ID2
        empty_line2_count += len(filtered_chunk[filtered_chunk['Line_ID2'].isna()])

# Сохранение результатов
print("Сохранение результатов...")
result_series = pd.Series(line_stats, name='Count')
result_series.sort_values(ascending=False, inplace=True)
result_series.to_csv(file4, header=True)

end_time = time.time()

print(f"Статистика Line_ID1 сохранена в {file4}")
print(f"Найдено строк с пустым Line_ID2: {empty_line2_count}")
print(f"Всего уникальных номеров линий: {len(line_stats)}")
print(f"Топ-5 самых частых номеров линий:")
for line_id, count in result_series.head().items():
    print(f"  {line_id}: {count}")
print(f"Время выполнения: {end_time - start_time:.2f} секунд")