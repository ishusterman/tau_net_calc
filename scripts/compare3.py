import csv

def load_csv_rows(file):
    """Загружает строки CSV в множество для проверки их наличия."""
    rows = set()
    with open(file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            rows.add(tuple(row))  # Преобразуем в кортеж для хеширования
    return rows

def compare_csv_files(file1, file2):
    data1 = load_csv_rows(file1)
    data2 = load_csv_rows(file2)
    
    missing_rows = data1 - data2  # Найти строки, которые есть в первом файле, но нет во втором
    extra_rows = data2 - data1  # Найти строки, которые есть во втором файле, но нет в первом
    
    if missing_rows:
        print("Rows found in", file1, "but not in", file2, ":")
        for row in missing_rows:
            print(row)
    
    if extra_rows:
        print("Rows found in", file2, "but not in", file1, ":")
        for row in extra_rows:
            print(row)
    
    if not missing_rows and not extra_rows:
        print("All rows from", file1, "are present in", file2, "and vice versa.")
    
    print("ok")

if __name__ == "__main__":
    file1 = r'c:\temp\1\18\2_stat_to.csv'
    file2 = r'c:\temp\1\18\1_stat_to.csv'
    compare_csv_files(file1, file2)
