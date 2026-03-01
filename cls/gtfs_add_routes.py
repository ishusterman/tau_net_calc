import pandas as pd
import os
import shutil
from PyQt5.QtWidgets import QApplication



class GTFSAddRoutes:
    def __init__(self, parent, gtfs_path1, gtfs_path2, output_path,
                 routes_to_add, start_date, end_date):
        """
        gtfs_path1: основной GTFS
        gtfs_path2: GTFS, из которого добавляем маршруты
        output_path: куда сохранять результат
        routes_to_add: список route_id, которые нужно добавить
        start_date, end_date: строки 'YYYYMMDD'
        """
        self.parent = parent
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

        self.already_display_break = False

    def _read_file(self, path, filename):
        file_path = os.path.join(path, filename)
        if not os.path.exists(file_path):
            return None
        dtypes = {
            'route_id': str,
        }
        return pd.read_csv(file_path, dtype=dtypes)

    def verify_break(self):
        if self.parent is not None:
            if self.parent.break_on:
                self.parent.setMessage("Adding lines to GTFS is interrupted by user")
                if not self.already_display_break:
                    self.parent.textLog.append(f'<a><b><font color="red">Adding lines to GTFS is interrupted by user</font> </b></a>')
                    self.already_display_break = True
                self.parent.progressBar.setValue(0)
                return True
        return False
        
    def run(self):

        # --- 0. Подготовка ---
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

        if self.verify_break():
                return 0
        self.parent.setMessage("Loading GTFS files...")
        QApplication.processEvents()

        # --- 1. Читаем routes и trips из GTFS2 ---
        df_routes2 = self._read_file(self.gtfs_path2, 'routes.txt')
        if self.verify_break():
                return 0
        df_trips2 = self._read_file(self.gtfs_path2, 'trips.txt')
        if self.verify_break():
                return 0

        df_routes2 = df_routes2[df_routes2['route_id'].isin(self.routes_to_add)]
        if self.verify_break():
                return 0

        trips_to_add = set(
            df_trips2[df_trips2['route_id'].isin(self.routes_to_add)]['trip_id'].unique()
        )
        if self.verify_break():
                return 0
        
        service_ids = df_trips2[df_trips2['route_id'].isin(self.routes_to_add)]['service_id'].unique()
        if self.verify_break():
                return 0

        QApplication.processEvents()

        # --- 2. Кэшируем df1 (основной GTFS) ---
        cache1 = {}
        for filename in self.files_to_merge:
            if self.verify_break():
                return 0
            cache1[filename] = self._read_file(self.gtfs_path1, filename)

        # --- 3. Обработка файлов ---
        for i, filename in enumerate(self.files_to_merge):
            if self.verify_break():
                return 0

            self.parent.setMessage(f"Adding lines to GTFS ('{filename}')...")
            self.parent.progressBar.setValue(i)
            QApplication.processEvents()

            df1 = cache1[filename]
            df2 = None

            # --- 3.1 Быстрая обработка маленьких файлов ---
            if filename in ("routes.txt", "trips.txt", "stops.txt", "calendar.txt", "calendar_dates.txt"):

                df2 = self._read_file(self.gtfs_path2, filename)

                if filename == 'routes.txt':
                    df2 = df2[df2['route_id'].isin(self.routes_to_add)]

                elif filename == 'trips.txt':
                    df2 = df2[df2['route_id'].isin(self.routes_to_add)]

                elif filename == 'calendar.txt':
                    df2 = pd.DataFrame([
                        {
                            'service_id': sid,
                            'monday': 1,
                            'tuesday': 1,
                            'wednesday': 1,
                            'thursday': 1,
                            'friday': 1,
                            'saturday': 1,
                            'sunday': 1,
                            'start_date': self.start_date,
                            'end_date': self.end_date
                        }
                        for sid in service_ids
                    ])

                elif filename == 'calendar_dates.txt':
                    df2 = None  # игнорируем

                # Сохраняем
                frames = [df for df in (df1, df2) if df is not None]
                if frames:
                    pd.concat(frames, ignore_index=True).to_csv(
                        os.path.join(self.output_path, filename), index=False
                    )

                continue

            # --- 3.2 Ускоренная обработка stop_times.txt (chunking) ---
            if filename == "stop_times.txt":

                out_path = os.path.join(self.output_path, filename)
                first_write = True

                # Читаем GTFS2 чанками
                for chunk in pd.read_csv(
                    os.path.join(self.gtfs_path2, filename),
                    chunksize=200000,
                    dtype=str
                ):
                    # фильтруем только нужные trip_id
                    chunk = chunk[chunk["trip_id"].isin(trips_to_add)]

                    if chunk.empty:
                        continue

                    # сохраняем порциями
                    chunk.to_csv(out_path, mode='w' if first_write else 'a',
                                index=False, header=first_write)
                    first_write = False

                    if self.verify_break():
                        return 0
                    QApplication.processEvents()

                # Теперь добавляем df1 (основной GTFS)
                if self.verify_break():
                        return 0
                
                if df1 is not None:
                    df1.to_csv(out_path, mode='a', index=False, header=first_write)

                continue

        return 1



