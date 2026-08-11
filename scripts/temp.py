import csv
from datetime import datetime

input_file = "c:\doc\Igor\GIS\output\log_routes.log"
output_file = "c:\doc\Igor\GIS\output\log_routes_new.log"

rows = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # пример строки:
        # < 600 34448_1_585438096_090225, 19 arrival=09:06:15 t1=09:09:23

        parts = line.split()
        id_part = parts[2].rstrip(",")
        idx = parts[3]
        arrival = parts[4].split("=")[1]
        t1 = parts[5].split("=")[1]

        t_arr = datetime.strptime(arrival, "%H:%M:%S")
        t_t1 = datetime.strptime(t1, "%H:%M:%S")
        delta = int((t_t1 - t_arr).total_seconds())

        rows.append([id_part, idx, arrival, t1, delta])

# запись CSV
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "idx", "arrival", "t1", "delta_seconds"])
    writer.writerows(rows)

print("Готово:", output_file)
