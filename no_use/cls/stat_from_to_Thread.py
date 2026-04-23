import os
import time
import pandas as pd
import numpy as np
from collections import defaultdict
import gc
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import psutil
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
        self._origin_ids_cache = None
        
        # Определяем количество рабочих процессов (оптимально для CPU-bound операций)
        self.num_workers = max(1, mp.cpu_count() - 1)
                                
    def gather_files_fast(self, path):
        """
        Ультрабыстрый сбор файлов с использованием os.scandir.
        """
        list_files = []
        
        try:
            with os.scandir(path) as entries:
                subdirs = [entry.path for entry in entries if entry.is_dir()]
        except OSError:
            return list_files

        for subdir in subdirs:
            time_extract = extract_time_pattern_from_txt(subdir)
            
            # Быстрый поиск файлов через scandir
            try:
                with os.scandir(subdir) as sub_entries:
                    for entry in sub_entries:
                        if entry.is_file() and entry.name.endswith('_min_duration.csv'):
                            list_files.append((entry.path, time_extract))
            except OSError:
                continue

        if not list_files:
            raise ValueError(f"No CSV files found in the immediate subdirectories of the directory: {path}")
        
        return list_files
    
    def preload_all_data_optimized(self, files):
        """
        Предзагрузка всех данных с максимальной оптимизацией.
        """
        all_data = {}
        
        # Читаем все файлы параллельно
        def read_single_file(args):
            file, time_extract = args
            try:
                # Используем низкоуровневое чтение для максимальной скорости
                df = pd.read_csv(
                    file, 
                    usecols=["Origin_ID", "Destination_ID", "Start_time", "Destination_time", "Duration", "Legs"],
                    dtype={
                        "Origin_ID": "category",
                        "Destination_ID": "category", 
                        "Duration": "float32",
                        "Legs": "int8",
                        "Start_time": "category",
                        "Destination_time": "category"
                    },
                    engine='c',
                    low_memory=False
                )
                return (file, time_extract), df
            except Exception as e:
                print(f"Error reading {file}: {e}")
                return None
        
        # Параллельная загрузка файлов
        with ThreadPoolExecutor(max_workers=min(self.num_workers * 2, len(files))) as executor:
            results = list(executor.map(read_single_file, files))
        
        for result in results:
            if result is not None:
                all_data[result[0]] = result[1]
        
        return all_data
    
    def get_all_origin_ids_fast(self, files_data):
        """
        Ультрабыстрое получение всех уникальных Origin_IDs.
        """
        all_origin_ids = set()
        
        for df in files_data.values():
            # Используем уникальные значения без dropna (быстрее)
            origin_ids = df["Origin_ID"].unique()
            all_origin_ids.update(origin_ids[~pd.isna(origin_ids)])
        
        return all_origin_ids
    
    def build_filtered_dict_ultrafast(self, files_data, origin_id):
        """
        Максимально оптимизированное построение словаря.
        """
        data_dict = defaultdict(list)
        
        for (file, time_extract), df in files_data.items():
            # Быстрая фильтрация через булеву индексацию
            mask = df["Origin_ID"] == origin_id
            if not mask.any():
                continue
                
            filtered_df = df[mask]
            time_value, time_type = time_extract
            
            # Векторизованные операции
            destinations = filtered_df["Destination_ID"].values
            durations = filtered_df["Duration"].values
            legs = filtered_df["Legs"].values
            
            if time_type == "start":
                start_times = np.full(len(filtered_df), time_value, dtype=object)
                end_times = filtered_df["Destination_time"].values
            elif time_type == "end":
                start_times = filtered_df["Start_time"].values
                end_times = np.full(len(filtered_df), time_value, dtype=object)
            else:
                start_times = filtered_df["Start_time"].values
                end_times = filtered_df["Destination_time"].values
            
            # Пакетное добавление данных
            for i in range(len(filtered_df)):
                data_dict[destinations[i]].append((
                    start_times[i], 
                    end_times[i], 
                    durations[i], 
                    legs[i], 
                    origin_id
                ))
        
        return data_dict

    def create_report_list_ultrafast(self, data_dict, file_path, order_from=None):
        """
        Ультрабыстрое создание отчетов через предварительное накопление массивов.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if not data_dict:
            # Создаем пустой файл с заголовком
            with open(file_path, 'w') as f:
                if order_from is None:
                    f.write("Origin_ID,Destination_ID,Start_time,Destination_time,Duration,Legs\n")
                else:
                    f.write("Destination_ID,Origin_ID,Start_time,Destination_time,Duration,Legs\n")
            return True
        
        # Предварительное вычисление размера данных
        total_rows = sum(len(entries) for entries in data_dict.values())
        
        # Создаем предварительно выделенные массивы

        origins = np.empty(total_rows, dtype=object)
        destinations = np.empty(total_rows, dtype=object)
        start_times = np.empty(total_rows, dtype=object)
        end_times = np.empty(total_rows, dtype=object)
        durations = np.empty(total_rows, dtype=np.float32)
        legs = np.empty(total_rows, dtype=np.int8)
        
        """
        if order_from is None:
        else:
            destinations = np.empty(total_rows, dtype=object)
            origins = np.empty(total_rows, dtype=object)
            start_times = np.empty(total_rows, dtype=object)
            end_times = np.empty(total_rows, dtype=object)
            durations = np.empty(total_rows, dtype=np.float32)
            legs = np.empty(total_rows, dtype=np.int8)
        """
        
        # Заполняем массивы
        idx = 0
        for dest_id, entries in data_dict.items():
            for entry in entries:
                if order_from is None:
                    origins[idx] = entry[4]  # origin_id
                    destinations[idx] = dest_id
                else:
                    destinations[idx] = dest_id
                    origins[idx] = entry[4]  # origin_id
                
                start_times[idx] = entry[0]
                end_times[idx] = entry[1]
                durations[idx] = entry[2]
                legs[idx] = entry[3]
                idx += 1
        
        # Создаем DataFrame из массивов
        if order_from is None:
            df = pd.DataFrame({
                'Origin_ID': origins,
                'Destination_ID': destinations,
                'Start_time': start_times,
                'Destination_time': end_times,
                'Duration': durations,
                'Legs': legs
            })
            sort_columns = ["Origin_ID", "Start_time", "Duration"]
        else:
            df = pd.DataFrame({
                'Destination_ID': destinations,
                'Origin_ID': origins,
                'Start_time': start_times,
                'Destination_time': end_times,
                'Duration': durations,
                'Legs': legs
            })
            sort_columns = ["Destination_ID", "Start_time", "Duration"]
        
        # Быстрая сортировка
        df = df.sort_values(sort_columns)
        
        # Сохранение с оптимизацией
        df.to_csv(file_path, index=False)
        return True

    def create_report_bin_ultrafast(self, file_path, report_path, type=None):
        """
        Ультрабыстрое создание bin отчетов с правильным порядком столбцов.
        """
        try:
            # Чтение только нужных колонок
            if type == "from":
                usecols = ['Duration', 'Origin_ID', 'Start_time']
                id_column = 'Origin_ID'
                time_column = 'Start_time'
            else:  # "to"
                usecols = ['Duration', 'Origin_ID', 'Destination_time'] 
                id_column = 'Origin_ID'
                time_column = 'Destination_time'
            
            df = pd.read_csv(file_path, usecols=usecols, dtype={'Duration': 'float32'})
            
            if df.empty:
                return False
            
            # Быстрое создание бинов
            max_duration = df['Duration'].max()
            if pd.isna(max_duration):
                return False
                
            bins_sec = np.arange(0, max_duration + 300 + 1, 300)
            
            # Используем digitize вместо cut для скорости
            indices = np.digitize(df['Duration'], bins_sec) - 1
            indices = np.clip(indices, 0, len(bins_sec) - 2)
            
            # Создаем метки бинов в правильном порядке
            labels_min = [f'{int(i/60)}-{int(i/60)+4}' for i in bins_sec[:-1]]
            df['Duration_bin'] = [labels_min[i] for i in indices]
            
            # Быстрое создание pivot через группировку
            grouped = df.groupby([time_column, id_column, 'Duration_bin']).size().unstack(fill_value=0)
            
            # Восстанавливаем правильный порядок столбцов
            all_bin_columns = labels_min  # Это уже правильный порядок
            existing_columns = [col for col in all_bin_columns if col in grouped.columns]
            missing_columns = [col for col in all_bin_columns if col not in grouped.columns]
            
            # Добавляем отсутствующие колонки с нулевыми значениями
            for col in missing_columns:
                grouped[col] = 0
            
            # Переупорядочиваем колонки в правильном порядке
            grouped = grouped[all_bin_columns]
            
            # Накопительная сумма
            result_df = grouped.cumsum(axis=1).reset_index()
            
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            result_df.to_csv(report_path, index=False)
            return True
            
        except Exception as e:
            print(f"Error creating bin report {report_path}: {e}")
            return False

    def process_single_origin_parallel(self, origin_id):
        """
        Обработка одного origin_id для параллельного выполнения.
        """
        try:
            # Создаем папки для результатов
            list_dir = os.path.join(self.PathToProtocols, "list_reports")
            bin_dir = os.path.join(self.PathToProtocols, "bin_reports")
            os.makedirs(list_dir, exist_ok=True)
            os.makedirs(bin_dir, exist_ok=True)

            # Создаем отфильтрованные словари
            dict_from_filtered = self.build_filtered_dict_ultrafast(self._files_from_data, origin_id)
            dict_to_filtered = self.build_filtered_dict_ultrafast(self._files_to_data, origin_id)
            
            # Создаем файлы list
            origin_file_from = os.path.join(list_dir, f"list_from_{origin_id}.csv")
            origin_file_to = os.path.join(list_dir, f"list_to_{origin_id}.csv")
            
            self.create_report_list_ultrafast(dict_from_filtered, origin_file_from, order_from=None)
            self.create_report_list_ultrafast(dict_to_filtered, origin_file_to, order_from="to")
            
            # Создаем bin отчеты
            origin_bin_from = os.path.join(bin_dir, f"bin_from_{origin_id}.csv")
            origin_bin_to = os.path.join(bin_dir, f"bin_to_{origin_id}.csv")
            
            self.create_report_bin_ultrafast(origin_file_from, origin_bin_from, type="from")
            self.create_report_bin_ultrafast(origin_file_to, origin_bin_to, type="to")
                
            return True
            
        except Exception as e:
            print(f"Error processing origin_id {origin_id}: {e}")
            return False

    def process_files_parallel(self):
        """
        Параллельная обработка всех origin_id.
        """
        if GUI_AVAILABLE:
            self.parent.setMessage('Calculating statistics ...')
            QApplication.processEvents()

        print("Gathering files...")
        start_gather = time.time()
        files_from = self.gather_files_fast(self.folder_name_from)
        files_to = self.gather_files_fast(self.folder_name_to)
        print(f"Files gathered in {time.time() - start_gather:.2f}s")

        print("Preloading data...")
        start_preload = time.time()
        
        # Параллельная загрузка данных
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_from = executor.submit(self.preload_all_data_optimized, files_from)
            future_to = executor.submit(self.preload_all_data_optimized, files_to)
            self._files_from_data = future_from.result()
            self._files_to_data = future_to.result()
        
        print(f"Data preloaded in {time.time() - start_preload:.2f}s")
        
        origin_ids_from = self.get_all_origin_ids_fast(self._files_from_data)
        print(f"Found {len(origin_ids_from)} unique Origin IDs")

        # Параллельная обработка origin_id
        print(f"Starting parallel processing with {self.num_workers} workers...")
        start_processing = time.time()
        
        success_count = 0
        total_count = len(origin_ids_from)
        
        # Используем ProcessPoolExecutor для CPU-bound задач
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Создаем частичную функцию для передачи в процессы
            from functools import partial
            process_func = partial(process_origin_wrapper, 
                                 PathToProtocols=self.PathToProtocols,
                                 files_from_data=self._files_from_data,
                                 files_to_data=self._files_to_data)
            
            results = executor.map(process_func, origin_ids_from, chunksize=max(1, total_count // (self.num_workers * 4)))
            
            for i, result in enumerate(results):
                if result:
                    success_count += 1
                #if (i + 1) % 100 == 0:
                print(f"Processed {i+1}/{total_count} origin IDs")
                if GUI_AVAILABLE:
                    self.parent.setMessage(f'Processing origin {i+1}/{total_count} ...')
                    QApplication.processEvents()

        processing_time = time.time() - start_processing
        print(f"Parallel processing completed in {processing_time:.2f}s")
        print(f"Processing rate: {total_count/processing_time:.2f} origin_id/s")

        # Очистка памяти
        self._files_from_data = None
        self._files_to_data = None
        gc.collect()

        print(f"Successfully processed {success_count}/{total_count} origin IDs")
        
        if GUI_AVAILABLE:
            self.parent.setMessage('Finished')
            QApplication.processEvents()

        return success_count == total_count

    def process_files(self):
        """
        Основной метод обработки (использует параллельную версию).
        """
        return self.process_files_parallel()


# Глобальные функции для параллельной обработки
def process_origin_wrapper(origin_id, PathToProtocols, files_from_data, files_to_data):
    """
    Обертка для параллельной обработки одного origin_id.
    """
    try:
        # Создаем временный процессор для этого origin_id
        temp_processor = StatFromTo(None, None, None, PathToProtocols, "")
        temp_processor._files_from_data = files_from_data
        temp_processor._files_to_data = files_to_data
        
        return temp_processor.process_single_origin_parallel(origin_id)
    except Exception as e:
        print(f"Error in parallel processing for {origin_id}: {e}")
        return False


if __name__ == "__main__":
    folder_name_from = r'f:\Igor\output\exp_08_2025\1510\2025-110b\251015_164449_PFXA_from'
    folder_name_to = r'f:\Igor\output\exp_08_2025\1510\2025-110b\251015_164449_PFXA_to'
    output_path = r'f:\Igor\output\exp_08_2025\7\1510\2025-110b'

    parent = None
    alias = ""

    start_time = time.time()
    
    processor = StatFromTo(parent, folder_name_from, folder_name_to, output_path, alias)
    success = processor.process_files()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Processing {'completed successfully' if success else 'failed'}")
    print(f"Total execution time: {execution_time:.2f} seconds ({execution_time/60:.2f} minutes)")

