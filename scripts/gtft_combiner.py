import pandas as pd
import os
import shutil

class GTFSCombiner:
    def __init__(self, gtfs_path1, gtfs_path2, output_path):
        """
        Инициализирует класс для слияния двух наборов GTFS.

        Аргументы:
        gtfs_path1 (str): Путь к первой папке GTFS.
        gtfs_path2 (str): Путь ко второй папке GTFS.
        output_path (str): Путь для сохранения объединённых файлов.
        """
        self.gtfs_path1 = gtfs_path1
        self.gtfs_path2 = gtfs_path2
        self.output_path = output_path
        self.files_to_merge = ['routes.txt', 'trips.txt', 'stop_times.txt', 'stops.txt', 'calendar.txt']

    def _read_file(self, path, filename):
        """Считывает файл CSV и возвращает DataFrame."""
        file_path = os.path.join(path, filename)
        if not os.path.exists(file_path):
            print(f"Warning: File {filename} not found in {path}. Skipping.")
            return None
        return pd.read_csv(file_path)

    def combine_gtfs(self):
        """
        Основной метод, который выполняет слияние и сохранение файлов.
        """
        print(f"Starting to combine GTFS data from {self.gtfs_path1} and {self.gtfs_path2} without prefixes.")
        
        # Создание выходной папки
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

        for filename in self.files_to_merge:
            try:
                # Чтение данных из первого набора
                df1 = self._read_file(self.gtfs_path1, filename)
                
                # Чтение данных из второго набора
                df2 = self._read_file(self.gtfs_path2, filename)
                
                if df1 is None and df2 is None:
                    continue
                
                # Объединение DataFrame
                combined_df = pd.concat([df1, df2], ignore_index=True)
                
                # Сохранение объединенного файла
                combined_df.to_csv(os.path.join(self.output_path, filename), index=False)
                print(f"{filename} merged successfully.")

            except FileNotFoundError as e:
                print(f"Error: A required file ({filename}) was not found in one of the directories. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while processing {filename}: {e}")
       

        print(f"Combined GTFS files saved to: {self.output_path}")

if __name__ == "__main__":
    gtfs_path1 = r"c:/doc/Igor/GIS/GTFS/exp_08_2025/ISR_2025/"
    gtfs_path2 = r"c:/doc/Igor/GIS/GTFS/exp_08_2025/Green_Purple/"
    output_path = r"c:/doc/Igor/GIS/GTFS/exp_08_2025/ISR_2025_add_Green_Purple/"
    
    gtfs_filter = GTFSCombiner(gtfs_path1, gtfs_path2, output_path)
    gtfs_filter.combine_gtfs()