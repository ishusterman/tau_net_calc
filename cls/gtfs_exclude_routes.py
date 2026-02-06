import pandas as pd
import os
import shutil

class GTFSExcludeRoutes:
    def __init__(self, gtfs_path, exclude_file_path, output_path, excluded_data_path=None):
        """
        Arguments:
            gtfs_path (str): Path to original GTFS.
            exclude_file_path (str): Path to CSV/TXT with route_id to exclude.
            output_path (str): Path for cleaned GTFS.
            excluded_data_path (str): Path for GTFS containing only excluded records.
        """
        self.gtfs_path = gtfs_path
        self.exclude_file_path = exclude_file_path
        self.output_path = output_path
        self.excluded_data_path = excluded_data_path
        self.exclude_ids = []

    def _load_exclude_ids(self):
        df = pd.read_csv(self.exclude_file_path)
        self.exclude_ids = df['route_id'].astype(str).unique().tolist()

    def _prepare_dirs(self):
        for path in [self.output_path, self.excluded_data_path]:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)

    def run(self):
        self._load_exclude_ids()
        self._prepare_dirs()
        
        try:
            # --- STEP 1: ROUTES ---
            routes_df = pd.read_csv(os.path.join(self.gtfs_path, 'routes.txt'), dtype={'route_id': str})
            
            mask_excluded = routes_df['route_id'].isin(self.exclude_ids)
            
            filtered_routes = routes_df[~mask_excluded]
            removed_routes = routes_df[mask_excluded]
            
            filtered_routes.to_csv(os.path.join(self.output_path, 'routes.txt'), index=False)
            removed_routes.to_csv(os.path.join(self.excluded_data_path, 'routes.txt'), index=False)

            # --- STEP 2: TRIPS ---
            trips_df = pd.read_csv(os.path.join(self.gtfs_path, 'trips.txt'), dtype={'route_id': str, 'trip_id': str, 'service_id': str})
            
            mask_trips_excluded = trips_df['route_id'].isin(self.exclude_ids)
            
            filtered_trips = trips_df[~mask_trips_excluded]
            removed_trips = trips_df[mask_trips_excluded]
            
            filtered_trips.to_csv(os.path.join(self.output_path, 'trips.txt'), index=False)
            removed_trips.to_csv(os.path.join(self.excluded_data_path, 'trips.txt'), index=False)

            # --- STEP 3: STOP TIMES ---
            # Читаем чанками, если файл большой
            st_path = os.path.join(self.gtfs_path, 'stop_times.txt')
            st_iter = pd.read_csv(st_path, dtype={'trip_id': str, 'stop_id': str}, chunksize=200000)
            
            keep_trip_ids = set(filtered_trips['trip_id'])
            
            first_f, first_e = True, True
            for chunk in st_iter:
                f_chunk = chunk[chunk['trip_id'].isin(keep_trip_ids)]
                e_chunk = chunk[~chunk['trip_id'].isin(keep_trip_ids)]
                
                f_chunk.to_csv(os.path.join(self.output_path, 'stop_times.txt'), mode='a', index=False, header=first_f)
                e_chunk.to_csv(os.path.join(self.excluded_data_path, 'stop_times.txt'), mode='a', index=False, header=first_e)
                first_f, first_e = False, False

            # --- STEP 4: STOPS ---
            stops_df = pd.read_csv(os.path.join(self.gtfs_path, 'stops.txt'), dtype={'stop_id': str})
            
            # Собираем ID остановок для обеих групп
            f_stop_ids = pd.read_csv(os.path.join(self.output_path, 'stop_times.txt'), usecols=['stop_id'], dtype={'stop_id': str})['stop_id'].unique()
            e_stop_ids = pd.read_csv(os.path.join(self.excluded_data_path, 'stop_times.txt'), usecols=['stop_id'], dtype={'stop_id': str})['stop_id'].unique()
            
            stops_df[stops_df['stop_id'].isin(f_stop_ids)].to_csv(os.path.join(self.output_path, 'stops.txt'), index=False)
            stops_df[stops_df['stop_id'].isin(e_stop_ids)].to_csv(os.path.join(self.excluded_data_path, 'stops.txt'), index=False)

            # --- STEP 5 & 6: CALENDAR ---
            active_f_services = filtered_trips['service_id'].unique()
            active_e_services = removed_trips['service_id'].unique()

            for file in ['calendar.txt', 'calendar_dates.txt']:
                p = os.path.join(self.gtfs_path, file)
                if os.path.exists(p):
                    c_df = pd.read_csv(p, dtype={'service_id': str})
                    c_df[c_df['service_id'].isin(active_f_services)].to_csv(os.path.join(self.output_path, file), index=False)
                    c_df[c_df['service_id'].isin(active_e_services)].to_csv(os.path.join(self.excluded_data_path, file), index=False)

            print(f"Filtering complete.")
            print(f"Clean GTFS: {self.output_path}")
            print(f"Excluded GTFS: {self.excluded_data_path}")

        except Exception as e:
            print(f"Error: {e}")
            return 0
        return 1
    
if __name__ == "__main__":
    src = r"c:\doc\Igor\GIS\temp\ISR_2025"
    excl = r"c:\doc\Igor\GIS\temp\routes.txt"
    out = r"c:\doc\Igor\GIS\temp\excluded"
    out2 = r"c:\doc\Igor\GIS\temp\_deleted_lines"
    cleaner = GTFSExcludeRoutes(
        gtfs_path = src, 
        exclude_file_path = excl,
        output_path = out,
        excluded_data_path = out2
    )
    run_ok = cleaner.run()

