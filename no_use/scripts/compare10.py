import pandas as pd

def filter_rows(file1, file2, output_file):
    # Читаем файлы
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    
    # Создаем словарь с максимальными значениями из второго файла
    max_duration_file2 = df2.groupby('Round_Trip_Goal')['Duration_AVG'].max().to_dict()
    
    # Фильтруем строки из первого файла
    filtered_rows = []
    for _, row in df1.iterrows():
        goal = row['Round_Trip_Goal']
        duration_file1 = row['Duration_AVG']
        
        # Если цели нет во втором файле ИЛИ значение в первом меньше
        if goal not in max_duration_file2 or duration_file1 < max_duration_file2[goal]:
            filtered_rows.append(row)
    
    # Сохраняем результат
    result_df = pd.DataFrame(filtered_rows)
    result_df.to_csv(output_file, index=False)

# Запуск
file1 = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\2018-40min\result_round_trip.csv"
file2 = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\2025-40min\result_round_trip.csv"
output_file = r"c:\doc\Igor\GIS\prg\211621047-112025\exp2\filtered_results.csv"

filter_rows(file1, file2, output_file)
print(f"Результат сохранен в: {output_file}")