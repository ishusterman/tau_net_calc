import pandas as pd
import os
import shutil
from PyQt5.QtWidgets import QApplication

class GTFSExcludeRoutes:
    def __init__(self, parent, gtfs_path, output_path=None,
                 excluded_data_path=None, exclude_ids_list=None):
        """
        Arguments:
            gtfs_path (str): Path to original GTFS.
            exclude_file_path (str): Path to CSV/TXT with route_id to exclude.
            output_path (str): Path for cleaned GTFS.
            excluded_data_path (str): Path for GTFS containing only excluded records.
            exclude_ids_list (list[str]): Direct list of route_id to exclude.
        """
        self.parent = parent
        self.gtfs_path = gtfs_path
        self.output_path = output_path
        self.excluded_data_path = excluded_data_path
        self.exclude_ids_list = exclude_ids_list
        self.exclude_ids = []
        self.already_display_break = False

    
    def _load_exclude_ids(self):
    
        if self.exclude_ids_list is not None:
            self.exclude_ids = [str(x) for x in self.exclude_ids_list]
            return
        self.exclude_ids = []

    def _prepare_dirs(self):
        for path in [self.output_path, self.excluded_data_path]:
            if path is None:
                continue
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)

    def verify_break(self):
        if self.parent is not None:
            if self.parent.break_on:
                self.parent.setMessage("Deleting lines from GTFS is interrupted by user")
                if not self.already_display_break:
                    self.parent.textLog.append(f'<a><b><font color="red">Deleting lines from GTFS is interrupted by user</font> </b></a>')
                    self.already_display_break = True
                self.parent.progressBar.setValue(0)
                return True
        return False
    
    def run(self):
        self._load_exclude_ids()
        self._prepare_dirs()

        try:
            # --- ROUTES ---
            if self.verify_break():
                return 0
            routes_df = pd.read_csv(os.path.join(self.gtfs_path, 'routes.txt'),
                                    dtype={'route_id': str})

            mask_excluded = routes_df['route_id'].isin(self.exclude_ids)

            filtered_routes = routes_df[~mask_excluded]
            removed_routes = routes_df[mask_excluded]

            filtered_routes.to_csv(os.path.join(self.output_path, 'routes.txt'), index=False)
            removed_routes.to_csv(os.path.join(self.excluded_data_path, 'routes.txt'), index=False)

            # --- TRIPS ---
            if self.verify_break():
                return 0
            self.parent.progressBar.setValue(1)
            self.parent.setMessage("Deleting lines from GTFS ('trips.txt') ...")
            QApplication.processEvents()
            trips_df = pd.read_csv(os.path.join(self.gtfs_path, 'trips.txt'),
                                   dtype={'route_id': str, 'trip_id': str, 'service_id': str})

            mask_trips_excluded = trips_df['route_id'].isin(self.exclude_ids)

            filtered_trips = trips_df[~mask_trips_excluded]
            removed_trips = trips_df[mask_trips_excluded]

            filtered_trips.to_csv(os.path.join(self.output_path, 'trips.txt'), index=False)
            removed_trips.to_csv(os.path.join(self.excluded_data_path, 'trips.txt'), index=False)
            
            # --- STOP TIMES ---
            if self.verify_break():
                return 0
            self.parent.progressBar.setValue(2)
            self.parent.setMessage("Deleting lines from GTFS ('stop_times.txt') ...")
            QApplication.processEvents()

            st_path = os.path.join(self.gtfs_path, 'stop_times.txt')
            st_iter = pd.read_csv(st_path, dtype={'trip_id': str, 'stop_id': str}, chunksize=200000)

            keep_trip_ids = set(filtered_trips['trip_id'])

            out_f_path = os.path.join(self.output_path, 'stop_times.txt')
            out_e_path = os.path.join(self.excluded_data_path, 'stop_times.txt')

            first = True

            with open(out_f_path, 'w', newline='') as out_f, \
                open(out_e_path, 'w', newline='') as out_e:

                for chunk in st_iter:
                    if self.verify_break():
                        return 0  # файлы всё равно закроются автоматически

                    mask = chunk['trip_id'].isin(keep_trip_ids)

                    f_chunk = chunk[mask]
                    e_chunk = chunk[~mask]

                    f_chunk.to_csv(out_f, index=False, header=first)
                    e_chunk.to_csv(out_e, index=False, header=first)

                    first = False
                    QApplication.processEvents()

    

            # --- STOPS ---
            if self.verify_break():
                return 0
            self.parent.progressBar.setValue(3)
            self.parent.setMessage("Deleting lines from GTFS ('stops.txt') ...")
            QApplication.processEvents()
            stops_df = pd.read_csv(os.path.join(self.gtfs_path, 'stops.txt'),
                                   dtype={'stop_id': str})

            f_stop_ids = pd.read_csv(os.path.join(self.output_path, 'stop_times.txt'),
                                     usecols=['stop_id'], dtype={'stop_id': str})['stop_id'].unique()

            e_stop_ids = pd.read_csv(os.path.join(self.excluded_data_path, 'stop_times.txt'),
                                     usecols=['stop_id'], dtype={'stop_id': str})['stop_id'].unique()

            stops_df[stops_df['stop_id'].isin(f_stop_ids)].to_csv(
                os.path.join(self.output_path, 'stops.txt'), index=False)

            stops_df[stops_df['stop_id'].isin(e_stop_ids)].to_csv(
                os.path.join(self.excluded_data_path, 'stops.txt'), index=False)
            
            
            # --- CALENDAR ---
            if self.verify_break():
                return 0
            self.parent.progressBar.setValue(4)
            self.parent.setMessage("Deleting lines from GTFS ('calendar.txt') ...")
            QApplication.processEvents()
            active_f_services = filtered_trips['service_id'].unique()
            active_e_services = removed_trips['service_id'].unique()

            for file in ['calendar.txt', 'calendar_dates.txt']:
                p = os.path.join(self.gtfs_path, file)
                if os.path.exists(p):
                    c_df = pd.read_csv(p, dtype={'service_id': str})
                    c_df[c_df['service_id'].isin(active_f_services)].to_csv(
                        os.path.join(self.output_path, file), index=False)
                    c_df[c_df['service_id'].isin(active_e_services)].to_csv(
                        os.path.join(self.excluded_data_path, file), index=False)
            QApplication.processEvents()  
            self.parent.progressBar.setValue(5)      

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

