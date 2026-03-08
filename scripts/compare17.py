import pandas as pd

df = pd.read_csv(
    r"c:\doc\Igor\GIS\test_012026\pkl_exp27_test\GTFS\footpath_road_projection.txt",
    dtype=str  # читаем всё как строки, чтобы не падало
)

# оставляем только строки, где from_stop_id состоит ТОЛЬКО из цифр
df_clean = df[df["from_stop_id"].str.match(r"^\d+$", na=False)]

# преобразуем в число
df_clean["from_stop_id"] = df_clean["from_stop_id"].astype(int)

# считаем уникальные > 100000
count_unique = df_clean[df_clean["from_stop_id"] > 100000]["from_stop_id"].nunique()

print("Количество уникальных from_stop_id > 100000:", count_unique)
