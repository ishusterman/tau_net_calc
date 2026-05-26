import pandas as pd

def extract_route_code(s):
    if pd.isna(s):
        return None
    return s.split("-")[0]

# === Загружаем файлы ===
df1 = pd.read_csv(r"c:\doc\Igor\GIS\36_routes_26POI\stat_routes\7\lines_gtfs2025_freq.csv")
df2 = pd.read_csv(r"c:\doc\Igor\GIS\GTFS\ISR_2025\routes.txt")
df3 = pd.read_csv(r"c:\doc\Igor\GIS\36_routes\strategic_matsim_gtfs\routes.txt")

# === Приводим route к числу ===
df1["route"] = df1["route"].astype(int)

# === Подготовка df2 ===
df2["route_id_clean"] = df2["route_id"].astype(int)
df2["route_short_name_clean"] = df2["route_desc"].apply(extract_route_code)

# === Подготовка df3 ===
df3["route_id"] = df3["route_id"].astype(int)

# === 1. merge с df2 (малые маршруты) ===
df = df1.merge(
    df2[["route_id_clean", "route_short_name_clean"]],
    left_on="route",
    right_on="route_id_clean",
    how="left"
)

# === 2. merge с df3 (большие маршруты) ===
df = df.merge(
    df3[["route_id", "route_short_name"]],
    left_on="route",
    right_on="route_id",
    how="left"
)

# === 3. Выбираем правильное имя маршрута ===
# если есть имя из df3 → берём его
# иначе → имя из df2
df["route_short_name_final"] = df["route_short_name"].fillna(df["route_short_name_clean"])

# === 4. Оставляем только нужные колонки ===
df_final = df[["route", "count", "route_short_name_final"]]
df_final = df_final.rename(columns={"route_short_name_final": "route_short_name"})

# === Сохраняем ===
df_final.to_csv(
    r"c:\doc\Igor\GIS\36_routes_26POI\stat_routes\7\lines_gtfs2025_freq_add.csv",
    index=False
)

print("Finish")
