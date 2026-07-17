import csv
from collections import Counter

input_file = r"c:\doc\Igor\GIS\36_routes_26POI\stat_routes\lines_gtfs2025.txt"
output_file = r"c:\doc\Igor\GIS\36_routes_26POI\stat_routes\lines_gtfs2025_freq.csv"

with open(input_file, "r", encoding="utf-8") as f:
    routes = [line.strip() for line in f if line.strip()]

freq = Counter(routes)

# сортировка по убыванию count
sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)

with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["route", "count"])
    for route, count in sorted_freq:
        writer.writerow([route, count])

print("Finish")
