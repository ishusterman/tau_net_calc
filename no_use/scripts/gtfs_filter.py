import pandas as pd
import os
import shutil

class GTFSFilter:
    def __init__(self, gtfs_path, route_ids, output_path):
        """
        Initializes the class for filtering GTFS data.

        Arguments:
        gtfs_path (str): The path to the original GTFS folder.
        route_ids (list): A list of route identifiers (route_id) for filtering.
        output_path (str): The path to save the filtered GTFS files.
        """
        self.gtfs_path = gtfs_path
        self.route_ids = route_ids
        self.output_path = output_path

    def _read_and_filter_routes(self):
        """Reads routes.txt and filters it by route_id."""
        routes_df = pd.read_csv(os.path.join(self.gtfs_path, 'routes.txt'))
        return routes_df[routes_df['route_id'].isin(self.route_ids)]

    def _read_and_filter_trips(self, filtered_routes):
        """Reads trips.txt and filters it based on route_id from filtered_routes."""
        trips_df = pd.read_csv(os.path.join(self.gtfs_path, 'trips.txt'))
        return trips_df[trips_df['route_id'].isin(filtered_routes['route_id'])]

    def _read_and_filter_stop_times(self, filtered_trips):
        """Reads stop_times.txt and filters it based on trip_id from filtered_trips."""
        stop_times_df = pd.read_csv(os.path.join(self.gtfs_path, 'stop_times.txt'))
        return stop_times_df[stop_times_df['trip_id'].isin(filtered_trips['trip_id'])]

    def _read_and_filter_stops(self, filtered_stop_times):
        """
        Reads stops.txt and filters it, keeping only the stops
        that are in the filtered stop_times.
        """
        stops_df = pd.read_csv(os.path.join(self.gtfs_path, 'stops.txt'))
        required_stop_ids = filtered_stop_times['stop_id'].unique()
        return stops_df[stops_df['stop_id'].isin(required_stop_ids)]

    def _read_and_filter_calendar(self, filtered_trips):
        """
        Reads calendar.txt, filters it based on the service_id from the filtered trips,
        and sets the start_date year to 2020.
        """
        calendar_df = pd.read_csv(os.path.join(self.gtfs_path, 'calendar.txt'))
        
        # 1. Фильтрация по service_id
        required_service_ids = filtered_trips['service_id'].unique()
        filtered_calendar_df = calendar_df[calendar_df['service_id'].isin(required_service_ids)].copy()
        
        # 2. Преобразование start_date в формат даты
        filtered_calendar_df['start_date'] = pd.to_datetime(
            filtered_calendar_df['start_date'],
            format='%Y%m%d'
        )
        
        # 3. Изменение года на 2017
        filtered_calendar_df['start_date'] = filtered_calendar_df['start_date'].apply(
            lambda x: x.replace(year=2017)
        )
        
        # 4. Преобразование start_date обратно в числовой формат YYYYMMDD
        filtered_calendar_df['start_date'] = filtered_calendar_df['start_date'].dt.strftime('%Y%m%d').astype(int)

        return filtered_calendar_df

    def create_filtered_gtfs(self):
        """
        Main method that performs all the filtering and saving.
        """
        print(f"Starting GTFS data filtering for routes: {self.route_ids}")

        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

        try:
            # Step 1: Filter routes.txt
            filtered_routes = self._read_and_filter_routes()
            filtered_routes.to_csv(os.path.join(self.output_path, 'routes.txt'), index=False)
            print("routes.txt filtered successfully.")

            # Step 2: Filter trips.txt
            filtered_trips = self._read_and_filter_trips(filtered_routes)
            filtered_trips.to_csv(os.path.join(self.output_path, 'trips.txt'), index=False)
            print("trips.txt filtered successfully.")

            # Step 3: Filter stop_times.txt
            filtered_stop_times = self._read_and_filter_stop_times(filtered_trips)
            filtered_stop_times.to_csv(os.path.join(self.output_path, 'stop_times.txt'), index=False)
            print("stop_times.txt filtered successfully.")
            
            # Step 4: Filter stops.txt
            filtered_stops = self._read_and_filter_stops(filtered_stop_times)
            filtered_stops.to_csv(os.path.join(self.output_path, 'stops.txt'), index=False)
            print("stops.txt filtered successfully.")

            # Step 5: Filter calendar.txt
            filtered_calendar = self._read_and_filter_calendar(filtered_trips)
            filtered_calendar.to_csv(os.path.join(self.output_path, 'calendar.txt'), index=False)
            print("calendar.txt filtered successfully.")


        except FileNotFoundError as e:
            print(f"Error: GTFS file not found. Please ensure all required files are in the directory {self.gtfs_path}. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    source_gtfs_folder = r"c:/doc/Igor/GIS/GTFS/exp_08_2025/Yellow_Green_Purple"
    output_path = r"c:/doc/Igor/GIS/GTFS/exp_08_2025/Green_Purple/"
    routes_to_keep = [100000,100001,100002,100003,100004,100005,100006,100007,100008,100009,]

    gtfs_filter = GTFSFilter(gtfs_path=source_gtfs_folder, route_ids=routes_to_keep, output_path = output_path)
    gtfs_filter.create_filtered_gtfs()