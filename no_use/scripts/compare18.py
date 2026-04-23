import csv

def filter_transfers(input_file, output_file, target_stop_id):
    """
    Фильтрует CSV-файл, оставляя только строки, 
    где from_stop_id совпадает с заданным значением.
    """
    # Преобразуем в строку на случай, если передано число
    target_stop_id = str(target_stop_id)
    
    with open(input_file, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        # Сохраняем названия колонок для записи в новый файл
        fieldnames = reader.fieldnames
        
        with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                if row['from_stop_id'] == target_stop_id:
                    writer.writerow(row)

# Пример использования:
path1 = r'c:\doc\Igor\GIS\36_routes\PKL_ISR2025+36routes\GTFS\footpath_road_projection.txt'
path2 = r'c:\doc\Igor\GIS\36_routes\PKL_ISR2025+36routes\GTFS\footpath_road_projection_gesher.txt'
aid = 1049165
filter_transfers(path1, path2, aid)