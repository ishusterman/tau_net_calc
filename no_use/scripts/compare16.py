import pandas as pd

def time_to_seconds(time_str):
    """Convert HH:MM:SS to seconds"""
    if pd.isna(time_str):
        return None
    try:
        # Обрабатываем разные форматы времени
        time_str = str(time_str).strip()
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h*3600 + m*60 + s
        else:
            return None
    except:
        return None

def filter_times_by_14h(time_str):
    """Check if time is before or after 14:00"""
    total_seconds = time_to_seconds(time_str)
    if total_seconds is None:
        return None
    if total_seconds < 14*3600:  # до 14:00
        return "before_14"
    else:  # после 14:00
        return "after_14"

def count_all_line_occurrences_by_time(filename, search_lines, time_column='Start_time'):
    """
    Подсчитывает общее количество вхождений всех значений из search_lines
    с разделением на до 14:00 и после 14:00
    """
    # Читаем файл с указанием кодировки и обработкой смешанных типов
    df = pd.read_csv(filename, low_memory=False)
    
    results = {
        'before_14': 0,
        'after_14': 0,
        'invalid_time': 0,
        'total': 0
    }
    
    for index, row in df.iterrows():
        for field in ['Line_ID1', 'Line_ID2', 'Line_ID3']:
            value = row[field]
            
            if pd.isna(value) or value == '':
                continue
            
            value_str = str(value).strip()
            
            # Проверяем, содержит ли значение любой из искомых строк
            for search_line in search_lines:
                if search_line in value_str:
                    # Определяем временную категорию
                    time_value = row.get(time_column)
                    if not pd.isna(time_value):
                        time_str = str(time_value).strip()
                        time_category = filter_times_by_14h(time_str)
                        if time_category == "before_14":
                            results['before_14'] += 1
                            
                        elif time_category == "after_14":
                            results['after_14'] += 1
                            
                        else:
                            results['invalid_time'] += 1
                            
                    else:
                        results['invalid_time'] += 1
                        
                    
                    results['total'] += 1
                    break  # переходим к следующему полю
    
    return results

# Использование:
search_lines = ['13429_1']
filename = r'c:\doc\Igor\GIS\prg\211621047-112025\exp2\all_from+to_2025.csv'

results = count_all_line_occurrences_by_time(filename, search_lines, time_column='Start_time')
print(f"До 14:00: {results['before_14']}")
print(f"После 14:00: {results['after_14']}")
print(f"Некорректное время: {results['invalid_time']}")
print(f"Всего вхождений: {results['total']}")
