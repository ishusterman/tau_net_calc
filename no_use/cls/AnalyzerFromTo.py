import os
import csv
from collections import defaultdict


class TripAnalyzer:
    def __init__(self, path_from, path_to, duration_max, result_path):
        """
        path_from — директория с файлами Output_from
        path_to — директория с файлами Output_to
        duration_max — максимальное суммарное время в пути (в секундах)
        result_path — путь к выходному CSV-файлу
        """
        self.path_from = path_from
        self.path_to = path_to
        self.duration_max = duration_max
        self.result_path = result_path

        self.files_from = []
        self.files_to = []
        self.dict_from = defaultdict(set)
        self.dict_to = defaultdict(set)
        self.result = defaultdict(int)

    import os

    def gather_files(self, path):
        """Собирает все CSV-файлы, оканчивающиеся на 'min_duration.csv', рекурсивно по всем вложенным папкам"""
        # Рекурсивно ищем файлы в path
        list_files = []
        for root_dir_entry in os.scandir(path):
            if root_dir_entry.is_dir():
                root_dir = root_dir_entry.path

                # В каждом таком каталоге ищем вложенные каталоги
                for nested_dir_entry in os.scandir(root_dir):
                    if nested_dir_entry.is_dir():
                        nested_dir = nested_dir_entry.path

                        # В каждом вложенном каталоге ищем нужные CSV-файлы
                        for file in os.listdir(nested_dir):
                            if file.endswith("min_duration.csv"):
                                full_path = os.path.join(nested_dir, file)
                                list_files.append(full_path)            
           
        return list_files
        

    def load_output_from(self):
        """
        Загружает данные из Output_from:
        dict_from[(origin_id, dest_id)] = {(destination_time, duration), ...}
        """
        for num, file_path in enumerate(self.files_from):
            if num%100 == 0: 
                print (f'Loading output from num {num}')
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        origin = int(row["Origin_ID"])
                        dest = int(row["Destination_ID"])
                        time = row["Destination_time"]
                        duration = int(row["Duration"])
                        self.dict_from[(origin, dest)].add((time, duration))
                    except (ValueError, KeyError):
                        continue

    def load_output_to(self):
        """
        Загружает данные из Output_to:
        dict_to[(dest_id, origin_id)] = {(start_time, duration), ...}
        """
        for num, file_path in enumerate(self.files_to):
            if num%100 == 0: 
                print (f'Loading output to num {num}')
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dest = int(row["Destination_ID"])
                        origin = int(row["Origin_ID"])
                        time = row["Start_time"]
                        duration = int(row["Duration"])
                        self.dict_to[(dest, origin)].add((time, duration))
                    except (ValueError, KeyError):
                        continue

    def time_to_seconds(self, t):
        """Преобразует HH:MM:SS в секунды"""
        try:
            h, m, s = map(int, t.split(":"))
            return h * 3600 + m * 60 + s
        except:
            return None

    def compute_result(self):
        """
        Вычисляет количество достижимых зданий по условиям задачи:
        Result[start_id] = count
        """
        for (start_id, end_id), from_variants in self.dict_from.items():
            to_variants = self.dict_to.get((end_id, start_id), set())
            if not to_variants:
                continue

            for time_end_str, dur_from in from_variants:
                time_end = self.time_to_seconds(time_end_str)
                if time_end is None:
                    continue

                for time_start_str, dur_to in to_variants:
                    time_start = self.time_to_seconds(time_start_str)
                    if time_start is None:
                        continue

                    total_duration = dur_from + dur_to

                    if time_end < time_start and total_duration <= self.duration_max:
                        self.result[start_id] += 1
                        break  # нашли подходящую пару — проверяем след. end_id
                else:
                    continue
                break

    def save_result_to_file(self):
        """Сохраняет результат в CSV-файл"""
        with open(self.result_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Origin_ID", "Value"])
            for origin_id, count in self.result.items():
                writer.writerow([origin_id, count])

    def run(self):
        """Запускает весь анализ"""
        self.files_from =  self.gather_files(self.path_from)[:300]
        print(f'files_from {len(self.files_from)}')
        self.files_to =  self.gather_files(self.path_to)[:300]
        print(f'files_to {len(self.files_to)}')
        self.load_output_from()
        self.load_output_to()
        self.compute_result()
        self.save_result_to_file()
        return self.result


if __name__ == "__main__":
    analyzer = TripAnalyzer( 
        path_from = r'c:/doc/output/exp042025/from_aerial',
        path_to = r'c:/doc/output/exp042025/to_aerial',
        duration_max = 3600,  # 30 минут
        result_path = r'c:/temp/result.csv'
    )
    result = analyzer.run()
    
    for origin_id, count in result.items():
        print(f"{origin_id} — {count}")
