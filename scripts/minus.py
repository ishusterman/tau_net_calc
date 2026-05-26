# читаем первый файл
with open(r"c:\doc\Igor\GIS\36_routes_26POI\excluded_routes.csv", "r", encoding="utf-8") as f:
    first = {line.strip() for line in f if line.strip() and line.strip() != "route_id"}

# читаем второй файл
with open(r"c:\doc\Igor\GIS\36_routes_26POI\restore_v2_more2mln.csv", "r", encoding="utf-8") as f:
    second = {line.strip() for line in f if line.strip() and line.strip() != "route_id"}

# разность множеств
result = sorted(first - second)

# вывод через запятую
print(",".join(result))
