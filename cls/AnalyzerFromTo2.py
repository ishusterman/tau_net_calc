import os
import csv
import pickle
from collections import defaultdict


class TripAnalyzer:
    def __init__(self, path_from, path_to, duration_max, result_path):
        self.path_from = path_from
        self.path_to = path_to
        self.duration_max = duration_max
        self.result_path = result_path

        # Пути к кэш-файлам
        self.cache_from = result_path.replace('.csv', '_from.pkl')
        self.cache_to = result_path.replace('.csv', '_to.pkl')

    def save_dict_to_pickle(self, data, path):
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    def load_dict_from_pickle(self, path):
        with open(path, 'rb') as f:
            return pickle.load(f)

    def gather_common_max_durations_all(self, path_to_files):
        dict_result = defaultdict(int)

        for num, root_entry in enumerate(os.scandir(path_to_files)):
            print(f'num = {num}')
            if not root_entry.is_dir():
                continue

            root_path = root_entry.path
            nested_dirs = [entry.path for entry in os.scandir(root_path) if entry.is_dir()]
            if not nested_dirs:
                continue

            origin_id = None
            dest_sets = []
            dest_max_duration = defaultdict(int)

            for nested in nested_dirs:
                local_dest_durations = {}
                for file in os.listdir(nested):
                    if file.endswith("min_duration.csv"):
                        file_path = os.path.join(nested, file)
                        
                        with open(file_path, newline='', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                dest = int(row["Destination_ID"])
                                duration = int(row["Duration"])
                                if origin_id is None:
                                    origin_id = int(row["Origin_ID"])
                                if dest not in local_dest_durations or duration > local_dest_durations[dest]:
                                    local_dest_durations[dest] = duration

                dest_sets.append(set(local_dest_durations.keys()))
                for dest, duration in local_dest_durations.items():
                    if duration > dest_max_duration[dest]:
                        dest_max_duration[dest] = duration

            if not origin_id:
                continue

            common_dests = set.intersection(*dest_sets) if dest_sets else set()
            for dest in common_dests:
                dict_result[(origin_id, dest)] = dest_max_duration[dest]

        return dict_result

    def merge_and_sum_dicts(self, dict1, dict2):
        merged = {}
        for key in dict1:
            if key in dict2:
                total = dict1[key] + dict2[key]
                if total <= self.duration_max:
                    merged[key] = total
        return merged

    def group_durations_by_time_bins(self, result):
        bin_counts = defaultdict(lambda: defaultdict(int))
        max_bin_code = self.duration_max // 600
        for (origin_id, dest_id), duration in result.items():
            bin_code = duration // 600
            bin_counts[origin_id][bin_code] += 1

        for origin_id in bin_counts:
            for bin_code in range(max_bin_code + 1):
                if bin_code not in bin_counts[origin_id]:
                    bin_counts[origin_id][bin_code] = 0

        return bin_counts

    def save_bins_to_file(self, bin_counts, path):
        with open(path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Origin_ID", "Time_Bin", "Count"])
            for origin_id, bins in bin_counts.items():
                for bin_code, count in sorted(bins.items()):
                    writer.writerow([origin_id, bin_code, count])

    def run(self):
        # Чтение или генерация result_from
        if os.path.exists(self.cache_from):
            print("Loading result_from from cache...")
            result_from = self.load_dict_from_pickle(self.cache_from)
        else:
            print("Generating result_from...")
            result_from = self.gather_common_max_durations_all(self.path_from)
            self.save_dict_to_pickle(result_from, self.cache_from)

        # Чтение или генерация result_to
        if os.path.exists(self.cache_to):
            print("Loading result_to from cache...")
            result_to = self.load_dict_from_pickle(self.cache_to)
        else:
            print("Generating result_to...")
            result_to = self.gather_common_max_durations_all(self.path_to)
            self.save_dict_to_pickle(result_to, self.cache_to)

        result = self.merge_and_sum_dicts(result_from, result_to)
        bin_counts = self.group_durations_by_time_bins(result)
        self.save_bins_to_file(bin_counts, self.result_path)
        return bin_counts


if __name__ == "__main__":
    analyzer = TripAnalyzer(
        path_from=r'c:/doc/output/test_from',
        path_to=r'c:/doc/output/test_to',
        duration_max=5400,  # 60 минут
        result_path=r'c:/temp/result.csv'
    )
    result = analyzer.run()
