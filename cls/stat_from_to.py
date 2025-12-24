import os
import pandas as pd
import numpy as np
from collections import defaultdict
import gc
try:
    from PyQt5.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
GUI_AVAILABLE = False

from common import extract_time_pattern_from_txt


class StatFromTo:
    
    def __init__(self, 
                 parent, 
                 folder_name_from, 
                 folder_name_to, 
                 PathToProtocols, 
                 alias                 
                 ):
        
        self.parent = parent
        self.folder_name_from = folder_name_from
        self.folder_name_to = folder_name_to
        self.PathToProtocols = PathToProtocols
        self.alias = alias
        
        self.file_from = os.path.join(PathToProtocols, f"list_from.csv")
        self.file_to = os.path.join(PathToProtocols, f"list_to.csv")
        self.report_from = os.path.join(PathToProtocols, f"bin_from.csv")
        self.report_to = os.path.join(PathToProtocols, f"bin_to.csv")

        os.makedirs(self.PathToProtocols, exist_ok=True)
        
        # Кэши для данных
        self._files_from_data = None
        self._files_to_data = None
                                
    def gather_files(self, path):
        """
        Оптимизированный сбор файлов с использованием glob.
        """
        list_files = []
        
        try:
            subdirs = [os.path.join(path, d) for d in os.listdir(path) 
                      if os.path.isdir(os.path.join(path, d))]
        except OSError:
            return list_files

        for subdir in subdirs:
            time_extract = extract_time_pattern_from_txt(subdir)
            
            # Используем glob для быстрого поиска файлов
            import glob
            pattern = os.path.join(subdir, "*_min_duration.csv")
            matching_files = glob.glob(pattern)
            
            for file in matching_files:
                list_files.append((file, time_extract))

        if not list_files:
            raise ValueError(f"No CSV files found in the immediate subdirectories of the directory: {path}")
        
        return list_files
    
    def preload_all_data(self, files):
        """
        Предзагрузка всех данных в память с оптимизированными типами.
        """
        all_data = {}
        print("Preloading data...")
        
        for i, (file, time_extract) in enumerate(files):
            
            print(f"  Loading file {i+1}/{len(files)}")
                
            # Читаем только нужные колонки с оптимизированными типами
            df = pd.read_csv(
                file, 
                usecols=["Origin_ID", "Destination_ID", "Start_time", "Destination_time", "Duration", "Legs"],
                dtype={
                    "Origin_ID": "category",
                    "Destination_ID": "category", 
                    "Duration": "float32",
                    "Legs": "int8"
                },
                engine='c'  # Используем быстрый C парсер
            )
            all_data[(file, time_extract)] = df
        
        return all_data
    
    def get_all_origin_ids_optimized(self, files_data):
        """
        Быстрое получение всех уникальных Origin_IDs.
        """
        all_origin_ids = set()
        
        for df in files_data.values():
            origin_ids = set(df["Origin_ID"].dropna().unique())
            all_origin_ids.update(origin_ids)
        
        return all_origin_ids
    
    def build_filtered_dict_fast(self, files_data, origin_id, common_ids):
        """
        Оптимизированное построение словаря с использованием векторизованных операций.
        """
        data_dict = defaultdict(list)
        
        for (file, time_extract), df in files_data.items():
            # Быстрая фильтрация через pandas
            mask = df["Origin_ID"] == origin_id
            if common_ids:
                mask &= df["Destination_ID"].isin(common_ids)
            
            filtered_df = df[mask].copy()
            
            if filtered_df.empty:
                continue
                
            time_value, time_type = time_extract
            
            # Векторизованные операции вместо итераций по строкам
            if time_type == "start":
                start_times = [time_value] * len(filtered_df)
                end_times = filtered_df["Destination_time"].values
            elif time_type == "end":
                start_times = filtered_df["Start_time"].values
                end_times = [time_value] * len(filtered_df)
            else:
                start_times = filtered_df["Start_time"].values
                end_times = filtered_df["Destination_time"].values
            
            # Быстрое добавление в словарь через zip
            destinations = filtered_df["Destination_ID"].values
            durations = filtered_df["Duration"].values
            legs = filtered_df["Legs"].values
            origins = filtered_df["Origin_ID"].values
            
            for dest, st, et, dur, leg, orig in zip(destinations, start_times, end_times, durations, legs, origins):
                data_dict[dest].append((st, et, dur, leg, orig))
        
        # Сортируем маршруты для каждого destination_id
        for key in data_dict:
            data_dict[key].sort(key=lambda x: (x[0], x[2]))
        
        return data_dict

    def create_report_list_fast(self, data_dict, file_path, order_from=None):
        """
        Оптимизированное создание отчетов через сбор в DataFrame.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Собираем все данные в списки для быстрого создания DataFrame
        all_data = []
        
        for dest_id, entries in data_dict.items():
            for entry in entries:
                if order_from is None:
                    all_data.append([entry[4], dest_id, entry[0], entry[1], entry[2], entry[3]])
                else:
                    all_data.append([dest_id, entry[4], entry[0], entry[1], entry[2], entry[3]])
        
        if not all_data:
            print(f"Warning: No data to write for {file_path}")
            # Создаем пустой файл с заголовком
            with open(file_path, 'w') as f:
                if order_from is None:
                    f.write("Origin_ID,Destination_ID,Start_time,Destination_time,Duration,Legs\n")
                else:
                    f.write("Destination_ID,Origin_ID,Start_time,Destination_time,Duration,Legs\n")
            return True
            
        # Создаем DataFrame и сортируем
        if order_from is None:
            columns = ["Origin_ID", "Destination_ID", "Start_time", "Destination_time", "Duration", "Legs"]
            sort_columns = ["Origin_ID", "Start_time", "Duration"]
        else:
            columns = ["Destination_ID", "Origin_ID", "Start_time", "Destination_time", "Duration", "Legs"]
            sort_columns = ["Destination_ID", "Start_time", "Duration"]
            
        df = pd.DataFrame(all_data, columns=columns)
        
        # Оптимизированная сортировка
        df = df.sort_values(sort_columns)
        
        # Быстрое сохранение без индекса
        df.to_csv(file_path, index=False)
        return True

    def create_report_bin_fast(self, file_path, report_path, type=None):
        """
        Оптимизированное создание bin отчетов.
        """
        # Чтение с оптимизированными типами
        df = pd.read_csv(
            file_path, 
            dtype={
                'Duration': 'float32',
                'Origin_ID': 'category',
                'Destination_ID': 'category'
            }
        )
        
        if type == "from":
            id_column = 'Origin_ID'
            time_column = 'Start_time'
        elif type == "to":
            id_column = 'Origin_ID'
            time_column = 'Destination_time'
        
        # Оптимизированные бины
        max_duration = df['Duration'].max()
        if pd.isna(max_duration):
            print(f"Warning: No valid duration data in {file_path}")
            return False
            
        bins_sec = np.arange(0, max_duration + 300 + 1, 300)
        labels_min = [f'{int(i/60)}-{int(i/60)+4}' for i in bins_sec[:-1]]

        df['Duration_bin'] = pd.cut(
            df['Duration'], 
            bins=bins_sec, 
            right=False, 
            labels=labels_min, 
            include_lowest=True
        )

        # Используем crosstab для большей скорости вместо pivot_table
        pivot_df = pd.crosstab(
            index=[df[time_column], df[id_column]],
            columns=df['Duration_bin'],
            values=df['Duration'],
            aggfunc='count',
            dropna=False
        ).fillna(0)

        # Накопительная сумма
        result_df = pivot_df.cumsum(axis=1).reset_index()

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        result_df.to_csv(report_path, index=False)
        return True

    def process_single_origin_optimized(self, origin_id, files_from_data, files_to_data):
        """
        Оптимизированная обработка одного origin_id.
        """
        try:
            # Создаем папки для результатов
            list_dir = os.path.join(self.PathToProtocols, "list_reports")
            bin_dir = os.path.join(self.PathToProtocols, "bin_reports")
            os.makedirs(list_dir, exist_ok=True)
            os.makedirs(bin_dir, exist_ok=True)

            # Создаем отфильтрованные словари для list отчетов
            dict_from_filtered = self.build_filtered_dict_fast(files_from_data, origin_id, None)
            dict_to_filtered = self.build_filtered_dict_fast(files_to_data, origin_id, None)
            
            # Создаем файлы list для этого origin_id
            origin_file_from = os.path.join(list_dir, f"list_from_{origin_id}.csv")
            origin_file_to = os.path.join(list_dir, f"list_to_{origin_id}.csv")
            
            self.create_report_list_fast(dict_from_filtered, origin_file_from, order_from=None)
            self.create_report_list_fast(dict_to_filtered, origin_file_to, order_from="to")
            
            # Создаем НЕфильтрованные данные для bin отчетов
            dict_from_all = self.build_filtered_dict_fast(files_from_data, origin_id, None)
            dict_to_all = self.build_filtered_dict_fast(files_to_data, origin_id, None)
            
            # Создаем временные файлы с НЕфильтрованными данными для bin отчетов
            temp_file_from = os.path.join(self.PathToProtocols, f"temp_from_{origin_id}.csv")
            temp_file_to = os.path.join(self.PathToProtocols, f"temp_to_{origin_id}.csv")
            
            self.create_report_list_fast(dict_from_all, temp_file_from, order_from=None)
            self.create_report_list_fast(dict_to_all, temp_file_to, order_from="to")
            
            # Создаем bin отчеты из временных файлов
            origin_bin_from = os.path.join(bin_dir, f"bin_from_{origin_id}.csv")
            origin_bin_to = os.path.join(bin_dir, f"bin_to_{origin_id}.csv")
            
            self.create_report_bin_fast(temp_file_from, origin_bin_from, type="from")
            self.create_report_bin_fast(temp_file_to, origin_bin_to, type="to")
            
            # Удаляем временные файлы
            if os.path.exists(temp_file_from):
                os.remove(temp_file_from)
            if os.path.exists(temp_file_to):
                os.remove(temp_file_to)
                
            return True
            
        except Exception as e:
            print(f"Error processing origin_id {origin_id}: {e}")
            return False

    def process_files(self):
        """
        Оптимизированный основной метод обработки.
        """
        if GUI_AVAILABLE:
            self.parent.setMessage('Calculating statistics ...')
            QApplication.processEvents()

        print("Gathering files...")
        files_from = self.gather_files(self.folder_name_from)
        files_to = self.gather_files(self.folder_name_to)

        print("Preloading data...")
        # Предзагружаем все данные один раз
        self._files_from_data = self.preload_all_data(files_from)
        self._files_to_data = self.preload_all_data(files_to)

        print("Finding all origin IDs...")
        origin_ids_from = self.get_all_origin_ids_optimized(self._files_from_data)
        origin_ids_to = self.get_all_origin_ids_optimized(self._files_to_data)
        all_origin_ids = origin_ids_from | origin_ids_to
        
        print(f"Found {len(all_origin_ids)} unique Origin IDs")

        # Обрабатываем каждый origin_id с прогресс-баром
        success_count = 0
        total_count = len(all_origin_ids)
        
        for i, origin_id in enumerate(all_origin_ids):
            if GUI_AVAILABLE:
                self.parent.setMessage(f'Processing origin {i+1}/{total_count} ...')
                QApplication.processEvents()
                
            
            print(f"Processed {i+1}/{total_count} origin IDs")
            # Периодическая сборка мусора для управления памятью
            gc.collect()

            success = self.process_single_origin_optimized(
                origin_id, 
                self._files_from_data, 
                self._files_to_data
            )
            
            if success:
                success_count += 1

        # Очистка памяти
        self._files_from_data = None
        self._files_to_data = None
        gc.collect()

        print(f"Successfully processed {success_count}/{total_count} origin IDs")
        
        if GUI_AVAILABLE:
            self.parent.setMessage('Finished')
            QApplication.processEvents()

        return success_count == total_count


if __name__ == "__main__":
    folder_name_from = r'f:\Igor\output\exp_08_2025\1510\2025-110b\251015_164449_PFXA_from'
    folder_name_to = r'f:\Igor\output\exp_08_2025\1510\2025-110b\251015_164449_PFXA_to'
    output_path = r'f:\Igor\output\exp_08_2025\1510\2025-110b'

    parent = None
    alias = ""
    
    processor = StatFromTo(parent, folder_name_from, folder_name_to, output_path, alias)
    processor.process_files()
    print("Optimized processing completed")