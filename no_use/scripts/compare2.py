import pandas as pd
from datetime import datetime

def merge_csv_by_origin_destination(file1, file2, check_field="Duration"):
    """
    Объединяет CSV файлы по Origin_ID и Destination_ID
    
    Parameters:
    file1, file2: пути к CSV файлам
    check_field: поле для сравнения ("Duration" или "Destination_time")
    """
    
    # Загружаем полные данные из файлов как строки чтобы сохранить оригинальный формат
    df1_full = pd.read_csv(file1, dtype=str, keep_default_na=False)
    df2_full = pd.read_csv(file2, dtype=str, keep_default_na=False)
    
    # Для слияния используем только нужные колонки
    df1_for_merge = df1_full[["Origin_ID", "Destination_ID", check_field]].copy()
    df2_for_merge = df2_full[["Origin_ID", "Destination_ID", check_field]].copy()
    
    # Преобразуем в соответствующий тип данных для сравнения
    if check_field == "Duration":
        df1_for_merge[check_field] = pd.to_numeric(df1_for_merge[check_field])
        df2_for_merge[check_field] = pd.to_numeric(df2_for_merge[check_field])
    elif check_field == "Destination_time":
        # Преобразуем время в формат для сравнения
        df1_for_merge[check_field] = pd.to_datetime(df1_for_merge[check_field])
        df2_for_merge[check_field] = pd.to_datetime(df2_for_merge[check_field])
    
    df1_for_merge.rename(columns={check_field: "schedule"}, inplace=True)
    df2_for_merge.rename(columns={check_field: "fix"}, inplace=True)
    
    # Основное слияние
    merged_df = pd.merge(df1_for_merge, df2_for_merge, on=["Origin_ID", "Destination_ID"], how="inner")
    
    return merged_df, df1_full, df2_full

def print_greater_duration_examples(merged_df, df1_full, df2_full, check_field="Duration", num_examples=5):
    """Выводит примеры, где значение в file_fix больше чем в file_schedule"""
    
    # Находим строки, где fix > schedule
    greater_duration_mask = merged_df["fix"] > merged_df["schedule"]
    greater_duration_df = merged_df[greater_duration_mask].copy()
    
    if len(greater_duration_df) == 0:
        print(f"\nNo cases where fix {check_field} is greater than schedule {check_field}")
        return
    
    print(f"\nEXAMPLES WHERE FIX {check_field.upper()} > SCHEDULE {check_field.upper()} (first {min(num_examples, len(greater_duration_df))} examples):")
    print("="*80)
    
    # Ограничиваем количество примеров
    examples_df = greater_duration_df.head(num_examples).copy()
    
    # Получаем полные данные для этих примеров из обоих файлов
    for idx, row in examples_df.iterrows():
        origin_id = row["Origin_ID"]
        destination_id = row["Destination_ID"]
        fix_value = row["fix"]
        schedule_value = row["schedule"]
        
        # Находим полные строки из оригинальных данных
        schedule_row = df1_full[
            (df1_full["Origin_ID"] == origin_id) & 
            (df1_full["Destination_ID"] == destination_id)
        ].iloc[0]
        
        fix_row = df2_full[
            (df2_full["Origin_ID"] == origin_id) & 
            (df2_full["Destination_ID"] == destination_id)
        ].iloc[0]
        
        print(f"\nExample {idx + 1}:")
        print(f"Origin_ID: {origin_id}, Destination_ID: {destination_id}")
        print(f"Schedule {check_field}: {schedule_value}, Fix {check_field}: {fix_value}")
        
        # Вычисляем разницу в зависимости от типа поля
        if check_field == "Duration":
            difference = fix_value - schedule_value
            print(f"Difference: {difference}")
        elif check_field == "Destination_time":
            difference = fix_value - schedule_value
            print(f"Difference: {difference}")
        
        print("\nFull row from file_fix:")
        print("-" * 40)
        fix_csv = ','.join([str(fix_row[col]) for col in fix_row.index])
        print(fix_csv)
        print("-" * 80)

def compare_csv_files(file_schedule, file_fix, check_field="Duration"):
    """
    Основная функция сравнения CSV файлов
    
    Parameters:
    file_schedule: путь к файлу schedule
    file_fix: путь к файлу fix  
    check_field: поле для сравнения ("Duration" или "Destination_time")
    """
    
    merged_df, df1_full, df2_full = merge_csv_by_origin_destination(file_schedule, file_fix, check_field)
    
    # Статистика сравнений
    count_less = (merged_df["fix"] < merged_df["schedule"]).sum()
    count_equal = (merged_df["fix"] == merged_df["schedule"]).sum()
    count_greater = (merged_df["fix"] > merged_df["schedule"]).sum()
    
    print(f"Comparison by {check_field} in merged pairs:")
    print(f"fix < schedule: {count_less}")
    print(f"fix = schedule: {count_equal}") 
    print(f"fix > schedule: {count_greater}")
    
    # Проверяем, что сумма совпадает с общим количеством пар
    total_check = count_less + count_equal + count_greater
    print(f"Total (verification): {total_check}")
    
    # Выводим примеры, где fix значение больше чем schedule значение
    print_greater_duration_examples(merged_df, df1_full, df2_full, check_field, num_examples=5)
    
    return merged_df

# Использование функции
file_schedule = r"c:\doc\Igor\GIS\temp\1811-211621047\211621047_schedule\211621047_schedule_min_endtime.csv"
file_fix = r"c:\doc\Igor\GIS\temp\1811-211621047\211621047_schedule_fix-5\211621047_schedule_fix-5_min_endtime.csv"

# Сравнение по Duration (по умолчанию)
print("=== COMPARISON BY DURATION ===")
merged_df_duration = compare_csv_files(file_schedule, file_fix, check_field="Duration")

print("\n" + "="*100 + "\n")

# Сравнение по Destination_time
print("=== COMPARISON BY DESTINATION_TIME ===")
merged_df_time = compare_csv_files(file_schedule, file_fix, check_field="Destination_time")