import pandas as pd

# Список файлов
files = [
    r"C:\\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo Bek\\to_8_00_30min_PT_PBX\\to_8_00_30min_PT_PBX.csv",
    r"C:\\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo Bek\\from_07_55_45min_PT_PFX_PT_PFX\\from_07_55_45min_PT_PFX_PT_PFX.csv",
    r"C:\\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo Bek\\from_12_45_45min_PT_PFX\\from_12_45_45min_PT_PFX.csv",
    r"C:\\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo Bek\\from_13_35_45min_PT_PFX_PT_PFX\\from_13_35_45min_PT_PFX_PT_PFX.csv",
]

# Чтение первого файла и сохранение его Destination_ID
df_first = pd.read_csv(files[0])
if "Destination_ID" not in df_first.columns or "Duration" not in df_first.columns:
    raise ValueError(f"Первый файл {files[0]} не содержит необходимых столбцов.")

# Получение списка Destination_ID из первого файла
valid_ids = df_first["Destination_ID"].unique()

# Переименовываем колонку Duration в заголовок для итогового DataFrame
df_first = df_first[["Destination_ID", "Duration"]].rename(columns={"Duration": "to_8_00_30min"})

# Итоговый DataFrame
result = df_first.copy()

# Обработка остальных файлов
file_headers = [
    "from_07_55_45min",
    "from_12_45_45min",
    "from_13_35_45min",
]

for file, header in zip(files[1:], file_headers):
    df = pd.read_csv(file)
    
    # Проверка наличия необходимых колонок
    if "Destination_ID" in df.columns and "Duration" in df.columns:
        # Выбор нужных данных и фильтрация по valid_ids
        df = df[["Destination_ID", "Duration"]]
        df = df[df["Destination_ID"].isin(valid_ids)].copy()
        
        # Переименование колонки Duration
        df = df.rename(columns={"Duration": header})
        
        # Объединяем данные по Destination_ID
        result = pd.merge(result, df, on="Destination_ID", how="left")
    else:
        print(f"Файл {file} не содержит необходимые столбцы.")

# Сохранение результата в файл
result.to_csv(r"C:\\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo Bek\\result.csv", index=False)

print("Обработка завершена")
