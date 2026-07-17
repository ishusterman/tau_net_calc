import pandas as pd
from collections import Counter

# Пути к файлам
file_round = r'c:\doc\Igor\GIS\prg\211621047-112025\exp2\roundtrip211621047_2018faster.csv'
file_routes_list = [
    r'c:\doc\Igor\GIS\prg\211621047-112025\exp2\all_to_2018.csv',
    r'c:\doc\Igor\GIS\prg\211621047-112025\exp2\all_from_2018.csv'
]
output_csv = r'c:\doc\Igor\GIS\prg\211621047-112025\exp2\line_frequencies_sum.csv'

# 1️⃣ Чтение Round_Trip_Goal
df_round = pd.read_csv(file_round, dtype={'Round_Trip_Goal': str})
goals = df_round['Round_Trip_Goal'].unique()

# 2️⃣ Инициализация счетчиков для каждого столбца
counters = {
    'Line_ID1': Counter(),
    'Line_ID2': Counter(),
    'Line_ID3': Counter()
}

# 3️⃣ Проходим по каждому файлу маршрутов
for file_routes in file_routes_list:
    df_routes = pd.read_csv(file_routes, dtype={
        'Origin_ID': str,
        'Destination_ID': str,
        'Line_ID1': str,
        'Line_ID2': str,
        'Line_ID3': str
    }, low_memory=False)

    # Безопасная конвертация Duration
    df_routes['Duration'] = pd.to_numeric(df_routes['Duration'], errors='coerce')

    # Фильтруем по Round_Trip_Goal
    filtered = df_routes[df_routes['Destination_ID'].isin(goals)]

    # Подсчет частот по каждому столбцу
    for col in ['Line_ID1', 'Line_ID2', 'Line_ID3']:
        series = filtered[col].dropna()
        series = series[series != '']
        series = series.str.split('_').str[0]
        counters[col].update(series)

# 4️⃣ Подготовка результата
rows = []
for col, counter in counters.items():
    for line, count in counter.most_common():
        rows.append({'Line_Column': col, 'Line': line, 'Count': count})

df_result = pd.DataFrame(rows)
df_result.to_csv(output_csv, index=False, encoding='utf-8')

print(f"Готово! Просуммированные частоты сохранены в: {output_csv}")
