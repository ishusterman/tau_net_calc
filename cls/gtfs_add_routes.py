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
        string_cols = ['route_id', 'trip_id', 'stop_id', 'service_id']
            
        header = pd.read_csv(file_path, nrows=0).columns
        dtype_dict = {col: str for col in string_cols if col in header}
        
        return pd.read_csv(file_path, dtype=dtype_dict)
    

    def _read_file(self, path, filename):
        file_path = os.path.join(path, filename)
        if not os.path.exists(file_path):
            return None
        df = pd.read_csv(
                file_path, 
                dtype=str, 
                keep_default_na=False, 
                encoding='utf-8-sig',
                sep=','
            )
        for col in ['route_id', 'trip_id', 'stop_id', 'service_id', 'stop_code','stop_name']:
                if col in df.columns:
                    df[col] = df[col].str.strip()
                    
        return df

  
    

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
        
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

        if self.verify_break(): return 0
        
        
        self.files_to_merge = [
            'routes.txt', 'trips.txt', 'stop_times.txt', 
            'stops.txt', 'calendar.txt', 'calendar_dates.txt'
        ]

        self.parent.setMessage("Loading GTFS files...")
        QApplication.processEvents()

        df_trips2_raw = self._read_file(self.gtfs_path2, 'trips.txt')
        selected_trips_df = df_trips2_raw[df_trips2_raw['route_id'].isin(self.routes_to_add)]
        trips_to_add = set(selected_trips_df['trip_id'].unique())
        service_ids = selected_trips_df['service_id'].unique()


        used_stop_ids_gtfs2 = set()

        cache1 = {}
        for filename in self.files_to_merge:
            if self.verify_break(): return 0
            cache1[filename] = self._read_file(self.gtfs_path1, filename)

        for i, filename in enumerate(self.files_to_merge):
            if self.verify_break(): return 0

            self.parent.setMessage(f"Processing '{filename}'...")
            self.parent.progressBar.setValue(int((i / len(self.files_to_merge)) * 100))
            QApplication.processEvents()

            df1 = cache1.get(filename)
            out_path = os.path.join(self.output_path, filename)

            if filename == "stop_times.txt":
                target_columns = df1.columns.tolist() if df1 is not None else None
                first_write = True
                
                if df1 is not None:
                    df1.to_csv(out_path, mode='w', index=False, header=True, encoding='utf-8')
                    first_write = False


                for chunk in pd.read_csv(os.path.join(self.gtfs_path2, filename), chunksize=200000, dtype=str):
                    chunk = chunk[chunk["trip_id"].isin(trips_to_add)]
                    if chunk.empty: continue

                    used_stop_ids_gtfs2.update(chunk['stop_id'].unique())
                    
                    if target_columns:
                        chunk = chunk.reindex(columns=target_columns)
                    
                    chunk.to_csv(out_path, mode='a', index=False, header=first_write, encoding='utf-8')
                    first_write = False
                    if self.verify_break(): return 0
                continue

            df2 = self._read_file(self.gtfs_path2, filename)
            if df2 is None and filename not in ['calendar.txt', 'calendar_dates.txt']:
                # Если файла нет во втором GTFS, просто сохраняем первый
                if df1 is not None:
                    df1.to_csv(out_path, index=False, encoding='utf-8')
                continue

            if filename == 'routes.txt':
                df2 = df2[df2['route_id'].isin(self.routes_to_add)]

            elif filename == 'trips.txt':
                df2 = df2[df2['route_id'].isin(self.routes_to_add)]

            elif filename == 'stops.txt':
                df2 = df2[df2['stop_id'].isin(used_stop_ids_gtfs2)]

            elif filename == 'calendar.txt':
                df2 = pd.DataFrame([{
                    'service_id': sid, 'monday': 1, 'tuesday': 1, 'wednesday': 1,
                    'thursday': 1, 'friday': 1, 'saturday': 1, 'sunday': 1,
                    'start_date': self.start_date, 'end_date': self.end_date
                } for sid in service_ids])

            elif filename == 'calendar_dates.txt':
                df2 = None # Очищаем, так как создали общий календарь выше

            frames = [df for df in (df1, df2) if df is not None]
            if frames:
                res_df = pd.concat(frames, ignore_index=True)

                if filename in ['stops.txt', 'routes.txt', 'calendar.txt']:
                    id_col = filename.replace('.txt', '_id')
                    if id_col in res_df.columns:
                        res_df = res_df.drop_duplicates(subset=[id_col])
                
                res_df.to_csv(out_path, index=False, encoding='utf-8')

        self.parent.progressBar.setValue(100)
        return 1



