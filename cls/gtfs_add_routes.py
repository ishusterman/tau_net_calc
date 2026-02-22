import pandas as pd
import os
import shutil
from PyQt5.QtWidgets import QApplication


class GTFSAddRoutes:
    def __init__(self, gtfs_path1, gtfs_path2, output_path,
                 routes_to_add, start_date, end_date):
        """
        gtfs_path1: основной GTFS
        gtfs_path2: GTFS, из которого добавляем маршруты
        output_path: куда сохранять результат
        routes_to_add: список route_id, которые нужно добавить
        start_date, end_date: строки 'YYYYMMDD'
        """
        self.gtfs_path1 = gtfs_path1
        self.gtfs_path2 = gtfs_path2
        self.output_path = output_path
        self.routes_to_add = set(routes_to_add)
        self.start_date = start_date
        self.end_date = end_date

        self.files_to_merge = [
            'routes.txt', 'trips.txt', 'stop_times.txt',
            'stops.txt', 'calendar.txt', 'calendar_dates.txt'
        ]

    def _read_file(self, path, filename):
        file_path = os.path.join(path, filename)
        if not os.path.exists(file_path):
            return None
        return pd.read_csv(file_path)

    def run(self):

        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

        # Загружаем routes и trips из GTFS2
        df_routes2 = self._read_file(self.gtfs_path2, 'routes.txt')
        df_trips2 = self._read_file(self.gtfs_path2, 'trips.txt')

        # Фильтруем маршруты
        df_routes2 = df_routes2[df_routes2['route_id'].isin(self.routes_to_add)]

        # trip_id, которые нужно добавить
        trips_to_add = df_trips2[df_trips2['route_id'].isin(self.routes_to_add)]['trip_id'].unique()

        # service_id для добавляемых маршрутов
        service_ids = df_trips2[df_trips2['route_id'].isin(self.routes_to_add)]['service_id'].unique()

        for filename in self.files_to_merge:
            try:
                df1 = self._read_file(self.gtfs_path1, filename)
                QApplication.processEvents()
                df2 = self._read_file(self.gtfs_path2, filename)
                QApplication.processEvents()

                if df1 is None and df2 is None:
                    continue

                # Обработка по типу файла
                if filename == 'routes.txt':
                    df2 = df2[df2['route_id'].isin(self.routes_to_add)]

                elif filename == 'trips.txt':
                    df2 = df2[df2['route_id'].isin(self.routes_to_add)]

                elif filename == 'stop_times.txt':
                    df2 = df2[df2['trip_id'].isin(trips_to_add)]

                elif filename == 'stops.txt':
                    # stops.txt оставляем как есть — GTFS2 может содержать только нужные stops
                    pass

                elif filename == 'calendar.txt':
                    # создаём новые строки календаря для service_id
                    df2 = pd.DataFrame({
                        'service_id': service_ids,
                        'monday': 1,
                        'tuesday': 1,
                        'wednesday': 1,
                        'thursday': 1,
                        'friday': 1,
                        'saturday': 1,
                        'sunday': 1,
                        'start_date': self.start_date,
                        'end_date': self.end_date
                    })

                elif filename == 'calendar_dates.txt':
                    # полностью игнорируем calendar_dates для добавляемых маршрутов
                    df2 = None

                combined_df = pd.concat([df1, df2], ignore_index=True)

                combined_df.to_csv(os.path.join(self.output_path, filename), index=False)
                QApplication.processEvents()

            except Exception as e:
                print(f"Error processing {filename}: {e}")
                return 0

        return 1
