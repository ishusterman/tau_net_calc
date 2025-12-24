import os
import csv
import pickle
import sys
import statistics
from collections import defaultdict
import numpy as np
try:
    from PyQt5.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

GUI_AVAILABLE = False


class TripAnalyzer:
    def __init__(self, parent, path_from, path_to, duration_max):
        self.parent = parent
        self.path_from = path_from
        self.path_to = path_to
        self.duration_max = duration_max
        

    def save_dict_to_pickle(self, data, path):
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    def load_dict_from_pickle(self, path):
        with open(path, 'rb') as f:
            return pickle.load(f)

    def gather_common_avg_durations_all(self, path_to_files):
        
        dict_result = {}
        common_dest_counts = defaultdict(int)
        dest_all_durations = defaultdict(list)
        dest_all_legs = defaultdict(list)
        dest_walk_times = defaultdict(list)
        origin_id = None
        file_count = 0
        
        if self.mode == "duration":
            name = "min_duration.csv"
        elif self.mode == "endtime":
            name = "min_endtime.csv"
        else:
            return {} # Возвращаем пустой результат, если режим не задан

        is_from_path = path_to_files == self.path_from

        for root_entry in os.scandir(path_to_files):
            if not root_entry.is_dir():
                continue

            root_path = root_entry.path
            for file_entry in os.scandir(root_path):
                file_name = file_entry.name

                if file_name.endswith(name):
                    file_path = file_entry.path
                    file_count += 1
                    local_dests = set()

                    row_count = 0

                    with open(file_path, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:

                            row_count += 1
                            if row_count%1000000 == 0:
                                print(f'\r file_count{file_count} row_count: {row_count}')
                                
                            origin_id = int(row["Origin_ID"])
                            dest = int(row["Destination_ID"])
                            duration = int(row["Duration"])
                            legs = int(row["Legs"])
                                                        
                            if is_from_path:
                                walk_time_key = "DestWalk_time"
                            else:
                                walk_time_key = "Walk_time1"
                            
                            walk_time_str = row.get(walk_time_key, "")
                            walk_time = int(walk_time_str) if walk_time_str else 0

                            # Используем локальное множество для отслеживания пар (origin_id, dest)
                            # в текущем файле, чтобы избежать дублирования.
                            dest_pair = (origin_id, dest)
                            if dest_pair not in local_dests:
                                local_dests.add(dest_pair)

                            dest_all_durations[dest_pair].append(duration)
                            dest_all_legs[dest_pair].append(legs)
                            dest_walk_times[dest_pair].append(walk_time)
                    
                    for dest_pair in local_dests:
                        common_dest_counts[dest_pair] += 1

        if file_count == 0:
            return dict_result

        # Вычисляем общие направления, которые есть во всех файлах.
        common_dests = {
            dest_pair for dest_pair, count in common_dest_counts.items()
            if count == file_count
        }

        # Далее, обрабатываем только те пары, которые есть во всех файлах.
        for dest_pair in common_dests:
            durations = dest_all_durations[dest_pair]
            legs = dest_all_legs[dest_pair]
            walk_times = dest_walk_times[dest_pair]

            
            dict_result[dest_pair] = {
                'durations': durations,
                'legs': legs,
                'walk_times': walk_times
            }

        return dict_result
    

    def merge_and_sum_dicts(self, dict1, dict2):
        """
        Объединяет данные из двух словарей, суммируя средние значения,
        и вычисляя объединенные стандартные отклонения, медианы и IQR
        на основе всех возможных комбинаций длительностей from и to.
        """
        merged = {}
        total_items = len(dict1)
        i = 0 

        for key in dict1:
            i += 1

            if i%5000 == 0:

                print (f"Merged {i} from {total_items}")

            if key in dict2:
                durations1 = dict1[key]['durations']
                durations2 = dict2[key]['durations']
                walk_times1 = dict1[key]['walk_times']
                walk_times2 = dict2[key]['walk_times']
                                
                avg1_dur = statistics.mean(dict1[key]['durations'])
                avg2_dur = statistics.mean(dict2[key]['durations'])

                if avg1_dur > 2/3 * self.duration_max or avg2_dur > 2/3 * self.duration_max:
                    continue
                                                
                if avg1_dur <= 2 * avg2_dur and avg2_dur <= 2 * avg1_dur:
                    
                    # Создаем список всех возможных комбинаций сумм длительностей
                    total_durations_list = [d1 + d2 for d1 in durations1 for d2 in durations2 if d1 + d2 <= self.duration_max]

                    # Расчет медианы и IQR по этому новому списку
                    if total_durations_list:
                        duration_median =  np.median(total_durations_list)
                        duration_iqr = np.percentile(total_durations_list, 75) - np.percentile(total_durations_list, 25)
                        duration_mean = statistics.mean(total_durations_list)
                    else:
                        continue

                    # Объединенное стандартное отклонение (путем сложения дисперсий)

                    if len(dict1[key]['durations']) > 1:
                        std1_dur = statistics.stdev(dict1[key]['durations'])
                        std1_legs = statistics.stdev(dict1[key]['legs'])
                    else:
                        std1_dur = 0.0
                        std1_legs = 0.0

                    if len(dict2[key]['durations']) > 1:
                        std2_dur = statistics.stdev(dict2[key]['durations'])
                        std2_legs = statistics.stdev(dict2[key]['legs'])
                    else:
                        std2_dur = 0.0
                        std2_legs = 0.0
                    std_dur = (std1_dur**2 + std2_dur**2)**0.5 
                    std_legs = (std1_legs**2 + std2_legs**2)**0.5

                    avg1_legs = statistics.mean(dict1[key]['legs'])
                    avg2_legs = statistics.mean(dict2[key]['legs'])
                    legs = avg1_legs + avg2_legs
                    

                    merged[key] = {
                            
                            'duration_mean': duration_mean,
                            'std_dur': std_dur,
                            'duration_median': duration_median,
                            'duration_iqr': duration_iqr,
                            'legs': legs,
                            'std_legs': std_legs,
                            'walk_times_from': walk_times1,
                            'walk_times_to': walk_times2
                        }
        return merged

    def save_round_trip_to_file(self, merged_dict, path):
        # Создаем папку если не существует
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Группируем данные по start_id
        grouped_data = {}
        for key, data in merged_dict.items():
            start_id, goal_id = key
            if start_id not in grouped_data:
                grouped_data[start_id] = []
            grouped_data[start_id].append((key, data))
        
        # Сохраняем каждый start_id в отдельный файл
        for start_id, data_list in grouped_data.items():
            # Формируем имя файла с start_id
            base_name = os.path.splitext(os.path.basename(path))[0]
            dir_name = os.path.dirname(path)
            start_file_path = os.path.join(dir_name, f"{base_name}_{start_id}.csv")
            
            with open(start_file_path, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(['Round_Trip_Start', 'Round_Trip_Goal', 'Duration_AVG', 'Duration_STD', 'Duration_Median', 'Duration_IQR', 'Legs', 'Legs_STD', 'DestWalk_time', 'Walk_time1'])
                
                for key, data in data_list:
                    start_id, goal_id = key
                    writer.writerow([
                        start_id,
                        goal_id,
                        f"{data['duration_mean']:.0f}",
                        f"{data['std_dur']:.0f}",
                        f"{data['duration_median']:.0f}",
                        f"{data['duration_iqr']:.0f}",
                        f"{data['legs']:.2f}",
                        f"{data['std_legs']:.2f}",
                        ";".join(f"{t:03d}" for t in data['walk_times_to']),
                        ";".join(f"{t:03d}" for t in data['walk_times_from'])
                    ])

        
        # Также сохраняем общий файл со всеми данными (опционально)
        with open(path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['Round_Trip_Start', 'Round_Trip_Goal', 'Duration_AVG', 'Duration_STD', 'Duration_Median', 'Duration_IQR', 'Legs', 'Legs_STD', 'DestWalk_time', 'Walk_time1'])
            for key, data in merged_dict.items():
                start_id, goal_id = key
                writer.writerow([
                    start_id,
                    goal_id,
                    f"{data['duration_mean']:.0f}",
                    f"{data['std_dur']:.0f}",
                    f"{data['duration_median']:.0f}",
                    f"{data['duration_iqr']:.0f}",
                    f"{data['legs']:.2f}",
                    f"{data['std_legs']:.2f}",
                    ";".join(f"{t:03d}" for t in data['walk_times_to']),
                    ";".join(f"{t:03d}" for t in data['walk_times_from'])
                ])            
                        
        return True
    
    def group_durations_by_time_bins(self, result):
        bin_counts = defaultdict(lambda: defaultdict(int))
        max_bin_code = self.duration_max // 600
        for (origin_id, dest_id), data in result.items():
            duration = data['duration_mean']
            bin_code = int(duration // 600)
            
            # Перенаправляем поездки длительностью 60 минут в бин 5
            if bin_code == 6:
                bin_code = 5
                
            bin_counts[origin_id][bin_code] += 1

        return bin_counts
    
    def save_bins_to_file(self, bin_counts, path):
        
        all_bin_codes = sorted(list(set(bin_code for bins in bin_counts.values() for bin_code in bins.keys())))
        
        with open(path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ["Origin_ID"] + all_bin_codes
            writer.writerow(header)
        
            for origin_id, bins in bin_counts.items():
                row = [origin_id]
                cumulative_count = 0
                for bin_code in all_bin_codes:
                    cumulative_count += bins.get(bin_code, 0)
                    row.append(cumulative_count)
                writer.writerow(row)

    def run(self, result_path1, result_path2, mode):

        self.result_path1 = result_path1
        self.result_path2 = result_path2
        self.mode = mode

        self.cache_from = result_path1.replace('.csv', '_from.pkl')
        self.cache_to = result_path1.replace('.csv', '_to.pkl')

        
        if os.path.exists(self.cache_from):
            print("Loading result_from from cache...")
            result_from = self.load_dict_from_pickle(self.cache_from)
        else:
            print("Generating result_from...")
            if GUI_AVAILABLE:
                self.parent.setMessage('Generating result_from...')
                QApplication.processEvents()
            result_from = self.gather_common_avg_durations_all(self.path_from)
            self.save_dict_to_pickle(result_from, self.cache_from)
        
        if os.path.exists(self.cache_to):
            print("Loading result_to from cache...")
            result_to = self.load_dict_from_pickle(self.cache_to)
        else:
            print("Generating result_to...")
            if GUI_AVAILABLE:
                self.parent.setMessage('Generating result_to...')
                QApplication.processEvents()
            result_to = self.gather_common_avg_durations_all(self.path_to)
            self.save_dict_to_pickle(result_to, self.cache_to)

        print("Merging result from and to...")
        if GUI_AVAILABLE:
                self.parent.setMessage('Merging result from and to...')
                QApplication.processEvents()
        result = self.merge_and_sum_dicts(result_from, result_to)
        
        print("Saving result ...")
        if GUI_AVAILABLE:
                self.parent.setMessage('Saving result ...')
                QApplication.processEvents()
        self.save_round_trip_to_file(result, self.result_path2)
        bin_counts = self.group_durations_by_time_bins(result)
        self.save_bins_to_file(bin_counts, self.result_path1)

        print("Finish")
        if GUI_AVAILABLE:
                self.parent.setMessage('Finish')
                QApplication.processEvents()
        
        return 0 #bin_counts

if __name__ == "__main__":
    #folder_name_from = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\7hexagons-2025\251006_083748_PFXA_from'
    #folder_name_to = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\7hexagons-2025\251006_083748_PFXA_to'
    #output_path1 = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\7hexagons-2025\result_bin.csv'
    #output_path2 = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\7hexagons-2025\result_round_trip.csv'

    folder_name_from = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\1410\2018-312b\251014_084533_PFXA_from'
    folder_name_to = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\1410\2018-312b\251014_084533_PFXA_to'
    output_path1 = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\1410\2018-312b\result_bin.csv'
    output_path2 = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\1410\2018-312b\result_round_trip.csv'

    analyzer = TripAnalyzer(
        None,
        path_from = folder_name_from,
        path_to = folder_name_to,
        duration_max = 60*60,
        )

    result = analyzer.run(output_path1, output_path2, mode = "duration")

    print("ok")