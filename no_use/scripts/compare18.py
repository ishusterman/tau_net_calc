import pandas as pd

# Загружаем CSV
df = pd.read_csv(r"c:\doc\Igor\GIS\GTFS\ISR_2025\trips.txt")

# Группируем по shape_id и считаем уникальные route_id
duplicates = (
    df.groupby("shape_id")["route_id"]
      .nunique()
      .reset_index()
      .query("route_id > 1")
)

print("Shape_id, используемые разными route_id:")
print(duplicates)
