import pandas as pd
import os
import shutil
import math
from qgis.PyQt.QtWidgets import QApplication


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
        self.routes_to_add = set(str(r).strip() for r in routes_to_add)
        self.start_date = start_date
        self.end_date = end_date
        self.already_display_break = False

        # Папка для временного скорректированного GTFS 2
        self.adjusted_gtfs2_path = os.path.join((os.path.abspath(self.output_path)),"adjusted_gtfs2")

    def fix_ids(self, df):
        if df is None:
            return df

        id_cols = ['route_id', 'trip_id', 'stop_id', 'service_id', 'agency_id', 'shape_id']

        for col in id_cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.replace(r'\.0$', '', regex=True)
                )

        return df

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
        df = self.fix_ids(df)
        if 'stop_name' in df.columns:
            df['stop_name'] = df['stop_name'].str.strip()

        return df

    def verify_break(self):
        if self.parent is not None:
            if self.parent.break_on:
                self.parent.setMessage("Adding lines to GTFS is interrupted by user")
                if not self.already_display_break:
                    self.parent.textLog.append(
                        '<a><b><font color="red">Adding lines to GTFS is interrupted by user</font> </b></a>'
                    )
                    self.already_display_break = True
                self.parent.progressBar.setValue(0)
                return True
        return False

    # =========================================================================
    # БЛОК ПРЕДВАРИТЕЛЬНОЙ КОРРЕКТИРОВКИ ИДЕНТИФИКАТОРОВ
    # =========================================================================

    def _calculate_offset(self, max_val):
        """
        Вычисляет стартовый номер по правилу: +1 к старшему разряду.
        Примеры:
        max_val = 51064 -> digits = 4, power = 10000 -> (5 + 1) * 10000 = 60000
        max_val = 345   -> digits = 2, power = 100   -> (3 + 1) * 100   = 400
        """
        if max_val <= 0:
            return 1
        digits = int(math.log10(max_val))
        power = 10 ** digits
        leading_digit = max_val // power
        return (leading_digit + 1) * power

    def _get_max_numeric_id(self, path, filenames, col_name):
        """Находит максимальное целое числовое значение идентификатора в указанных файлах."""
        max_val = 0
        for fname in filenames:
            fpath = os.path.join(path, fname)
            if not os.path.exists(fpath):
                continue
            try:
                for chunk in pd.read_csv(
                    fpath, usecols=[col_name], dtype=str,
                    keep_default_na=False, encoding='utf-8-sig', chunksize=200000
                ):
                    s = chunk[col_name].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    # Берем только строки, состоящие строго из цифр
                    digits_only = s[s.str.isdigit()]
                    if not digits_only.empty:
                        cur_max = int(digits_only.astype( 'int64').max())
                        if cur_max > max_val:
                            max_val = cur_max
            except ValueError:
                continue
        return max_val

    def _build_id_mapping(self, unique_ids, start_id):
        """
        Создает словарь {старый_id: новый_id}.
        Нумерация начинается строго со start_id (например, 60000, 60001, 60002...),
        независимо от того, какие числа были во втором GTFS.
        """
        cleaned_ids = [
            str(x).strip() for x in unique_ids
            if str(x).strip() != '' and str(x).strip().lower() != 'nan'
        ]

        numeric_ids = sorted([x for x in cleaned_ids if x.isdigit()], key=lambda x: int(x))
        non_numeric_ids = sorted([x for x in cleaned_ids if not x.isdigit()])
        sorted_ids = numeric_ids + non_numeric_ids

        mapping = {}
        current_id = start_id
        for old_id in sorted_ids:
            mapping[old_id] = str(current_id)
            current_id += 1

        return mapping

    def _prepare_adjusted_gtfs2(self):
        if self.parent is not None:
            self.parent.setMessage("Preparing and re-indexing secondary GTFS...")
            QApplication.processEvents()

        if os.path.exists(self.adjusted_gtfs2_path):
            shutil.rmtree(self.adjusted_gtfs2_path)
        os.makedirs(self.adjusted_gtfs2_path)

        id_configs = {
            'route_id': ['routes.txt'],
            'stop_id': ['stops.txt'],
            'trip_id': ['trips.txt'],
            'service_id': ['calendar.txt', 'calendar_dates.txt', 'trips.txt'],
            'shape_id': ['shapes.txt', 'trips.txt'],
            'agency_id': ['agency.txt', 'routes.txt']
        }

        offsets = {}
        for col, files in id_configs.items():
            max_val = self._get_max_numeric_id(self.gtfs_path1, files, col)
            offsets[col] = self._calculate_offset(max_val)
            if self.parent is not None and hasattr(self.parent, 'textLog'):
                self.parent.textLog.append(
                    f"ID <b>{col}</b>: max in GTFS1 = {max_val} &rarr; new start ID = <b>{offsets[col]}</b>"
                )

        small_files = [
            'routes.txt', 'trips.txt', 'stops.txt',
            'calendar.txt', 'calendar_dates.txt', 'agency.txt', 'shapes.txt'
        ]
        dfs2 = {}
        for fname in small_files:
            if self.verify_break():
                return False
            dfs2[fname] = self._read_file(self.gtfs_path2, fname)

        # Собираем уникальные ID только из нужных таблиц
        unique_vals = {col: set() for col in id_configs}
        for col, files in id_configs.items():
            for fname in files:
                df = dfs2.get(fname)
                if df is not None and col in df.columns:
                    unique_vals[col].update(df[col].unique())


        # Строим словари замен, начиная ровно с вычисленного стартового номера
        mappings = {}
        for col, vals in unique_vals.items():
            mappings[col] = self._build_id_mapping(vals, offsets[col])

        # Обновляем выбранные пользователем route_id на новые значения
        route_map = mappings['route_id']
        self.routes_to_add = set(route_map.get(r, r) for r in self.routes_to_add)

        for fname, df in dfs2.items():
            if self.verify_break():
                return False
            if df is None:
                continue

            for col, mp in mappings.items():
                if col in df.columns:
                    df[col] = df[col].map(lambda x: mp.get(x, x))

            df.to_csv(os.path.join(self.adjusted_gtfs2_path, fname), index=False, encoding='utf-8')

        st_path2 = os.path.join(self.gtfs_path2, 'stop_times.txt')
        if os.path.exists(st_path2):
            out_st2 = os.path.join(self.adjusted_gtfs2_path, 'stop_times.txt')
            first_write = True
            trip_mp = mappings['trip_id']
            stop_mp = mappings['stop_id']

            for chunk in pd.read_csv(
                st_path2, dtype=str, keep_default_na=False,
                encoding='utf-8-sig', chunksize=200000
            ):
                if self.verify_break():
                    return False
                chunk = self.fix_ids(chunk)
                if 'trip_id' in chunk.columns:
                    chunk['trip_id'] = chunk['trip_id'].map(lambda x: trip_mp.get(x, x))
                if 'stop_id' in chunk.columns:
                    chunk['stop_id'] = chunk['stop_id'].map(lambda x: stop_mp.get(x, x))

                chunk.to_csv(out_st2, mode='a', index=False, header=first_write, encoding='utf-8')
                first_write = False

        return True

    # =========================================================================
    # ОСНОВНАЯ ПРОЦЕДУРА СЛИЯНИЯ
    # =========================================================================

    def run(self):
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

        if self.verify_break():
            return 0

        if not self._prepare_adjusted_gtfs2():
            return 0

        working_gtfs2 = self.adjusted_gtfs2_path

        self.files_to_merge = [
            'routes.txt', 'trips.txt', 'stop_times.txt',
            'stops.txt', 'calendar.txt', 'calendar_dates.txt', 'agency.txt', 'shapes.txt'
        ]

        self.parent.setMessage("Loading GTFS files...")
        QApplication.processEvents()

        df_trips2_raw = self._read_file(working_gtfs2, 'trips.txt')
        selected_trips_df = df_trips2_raw[df_trips2_raw['route_id'].isin(self.routes_to_add)]
        trips_to_add = set(selected_trips_df['trip_id'].unique())
        service_ids = selected_trips_df['service_id'].unique()

        df_routes2_raw = self._read_file(working_gtfs2, 'routes.txt')
        used_agency_ids_gtfs2 = set()
        if df_routes2_raw is not None and 'agency_id' in df_routes2_raw.columns:
            sel_routes = df_routes2_raw[df_routes2_raw['route_id'].isin(self.routes_to_add)]
            used_agency_ids_gtfs2 = set(sel_routes['agency_id'].unique())

        used_stop_ids_gtfs2 = set()

        cache1 = {}
        for filename in self.files_to_merge:
            if self.verify_break():
                return 0
            cache1[filename] = self._read_file(self.gtfs_path1, filename)

        self.parent.progressBar.setMaximum(len(self.files_to_merge))

        dedup_cols = {
            'stops.txt': ['stop_id'],
            'routes.txt': ['route_id'],
            'calendar.txt': ['service_id'],
            'agency.txt': ['agency_id'],
            'trips.txt': ['trip_id']
        }

        for i, filename in enumerate(self.files_to_merge):
            if self.verify_break():
                return 0

            self.parent.setMessage(f"Processing '{filename}'...")
            self.parent.progressBar.setValue(i)
            QApplication.processEvents()

            df1 = cache1.get(filename)
            out_path = os.path.join(self.output_path, filename)

            if filename == "stop_times.txt":
                target_columns = df1.columns.tolist() if df1 is not None else None
                first_write = True

                if df1 is not None:
                    df1.to_csv(out_path, mode='w', index=False, header=True, encoding='utf-8')
                    first_write = False

                st_file2 = os.path.join(working_gtfs2, filename)
                if os.path.exists(st_file2):
                    for chunk in pd.read_csv(
                        st_file2, chunksize=200000, dtype=str,
                        keep_default_na=False, encoding='utf-8-sig'
                    ):
                        chunk = self.fix_ids(chunk)
                        chunk = chunk[chunk["trip_id"].isin(trips_to_add)]
                        if chunk.empty:
                            continue

                        used_stop_ids_gtfs2.update(chunk['stop_id'].unique())

                        if target_columns:
                            chunk = chunk.reindex(columns=target_columns)

                        chunk.to_csv(out_path, mode='a', index=False, header=first_write, encoding='utf-8')
                        first_write = False
                        if self.verify_break():
                            return 0
                continue

            if filename == "shapes.txt":
                df2 = self._read_file(working_gtfs2, filename)

                if df2 is None:
                    if df1 is not None:
                        df1.to_csv(out_path, index=False, encoding='utf-8')
                    continue

                df_trips2 = df_trips2_raw[df_trips2_raw['trip_id'].isin(trips_to_add)]
                shape_ids_to_add = set(df_trips2['shape_id'].dropna().unique())

                df2 = df2[df2['shape_id'].isin(shape_ids_to_add)]

                frames = [df for df in (df1, df2) if df is not None]
                if frames:
                    res_df = pd.concat(frames, ignore_index=True)
                    res_df = self.fix_ids(res_df)

                    if 'shape_id' in res_df.columns and 'shape_pt_sequence' in res_df.columns:
                        res_df = res_df.drop_duplicates(
                            subset=['shape_id', 'shape_pt_sequence']
                        )

                    res_df.to_csv(out_path, index=False, encoding='utf-8')
                continue

            df2 = self._read_file(working_gtfs2, filename)
            if df2 is None and filename not in ['calendar.txt', 'calendar_dates.txt']:
                if df1 is not None:
                    df1.to_csv(out_path, index=False, encoding='utf-8')
                continue

            if filename == 'routes.txt':
                df2 = df2[df2['route_id'].isin(self.routes_to_add)]

            elif filename == 'trips.txt':
                df2 = df2[df2['route_id'].isin(self.routes_to_add)]

            elif filename == 'stops.txt':
                df2 = df2[df2['stop_id'].isin(used_stop_ids_gtfs2)]

            elif filename == 'agency.txt':
                if used_agency_ids_gtfs2 and 'agency_id' in df2.columns:
                    df2 = df2[df2['agency_id'].isin(used_agency_ids_gtfs2)]

            elif filename == 'calendar.txt':
                df2 = pd.DataFrame([{
                    'service_id': sid, 'monday': '1', 'tuesday': '1', 'wednesday': '1',
                    'thursday': '1', 'friday': '1', 'saturday': '1', 'sunday': '1',
                    'start_date': self.start_date, 'end_date': self.end_date
                } for sid in service_ids])

            elif filename == 'calendar_dates.txt':
                df2 = None

            frames = [df for df in (df1, df2) if df is not None]
            if frames:
                res_df = pd.concat(frames, ignore_index=True)
                res_df = self.fix_ids(res_df)

                if filename in dedup_cols:
                    cols = [c for c in dedup_cols[filename] if c in res_df.columns]
                    if cols:
                        res_df = res_df.drop_duplicates(subset=cols, keep='first')

                res_df.to_csv(out_path, index=False, encoding='utf-8')

        self.parent.progressBar.setValue(len(self.files_to_merge))
        return 1