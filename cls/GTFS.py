import pandas as pd
import csv
import pyproj
import re
import geopandas as gpd
import os
from collections import defaultdict
from scipy.spatial import cKDTree
from shapely.geometry import Point
from pyproj import Geod

from qgis.core import QgsVectorFileWriter, QgsProject
from PyQt5.QtWidgets import QApplication


from footpath_on_projection import cls_footpath_on_projection
from converter_layer import MultiLineStringToLineStringConverter
from common import convert_meters_to_degrees, getDateTime, time_to_seconds, seconds_to_time


class GTFS ():

    def __init__(self,
                 parent,
                 path_to_file,
                 path_to_GTFS,
                 pkl_path,
                 layer_origins,
                 layer_road,
                 layer_origins_field="",
                 MaxPathRoad = "400",
                 MaxPathAir = "400"
                 ):
        self.pkl_path = pkl_path
        self.__path_to_file = path_to_file
        self.__path_to_GTFS = path_to_GTFS
        self.MaxPathRoad = int(MaxPathRoad)
        self.MaxPathAir = int(MaxPathAir)
        self.parent = parent
        self.layer_origins = layer_origins
        self.layer_road = layer_road
        self.layer_origins_field = layer_origins_field
        self.already_display_break = False

        postfix = getDateTime()
        self.filelog_name = f'{self.__path_to_file}//log_processing_GTFS_{postfix}.txt'
        self.log_processing = []
        self.line_break = '-----------------------------'
    

    def change_time(self, time1_str):
        # time conversion, with the ability to handle invalid values
        time1 = pd.to_datetime(time1_str, errors='coerce')
        if not pd.isnull(time1):  # check if the value is empty
            next_day_midnight = pd.to_datetime(
                '00:00:00') + pd.Timedelta(days=1)
            time_diff = next_day_midnight - \
                pd.Timestamp.combine(pd.Timestamp.today(), time1.time())
            result = ((pd.Timestamp('00:00:00') + time_diff).time())
            return result
        else:
            return pd.NaT  # return `NaT` for empty time values.

    # modify time 24:00:00 - xx.yy.zz in stop_times.txt
    # change stop_sequency, change sorting

    def modify_time_and_sequence(self):

        stops_df = pd.read_csv(f'{self.__path_to_file}//stop_times.txt')

        print("# Filtering stoptimes")
        trips_df = pd.read_csv(
            f'{self.__path_to_file}//trips.txt', encoding='utf-8')
        unique_trip_ids = trips_df['trip_id'].unique()

        filtered_stops_df = stops_df[stops_df['trip_id'].isin(
            unique_trip_ids)].sort_values(by='arrival_time')
        filtered_stops_df[['hour', 'minute', 'second']
                          ] = filtered_stops_df['arrival_time'].str.split(':', expand=True)
        filtered_stops_df['hour'] = filtered_stops_df['hour'].astype(int)
        filtered_stops_df = filtered_stops_df[filtered_stops_df['hour'] <= 23]

        filtered_stops_df['arrival_time'] = filtered_stops_df['hour'].astype(
            str) + ':' + filtered_stops_df['minute'].astype(str) + ':' + filtered_stops_df['second'].astype(str)
        filtered_stops_df.drop(
            columns=['hour', 'minute', 'second'], inplace=True)

        df = filtered_stops_df

        print("# change pd.to_datetime")
        df['arrival_time'] = pd.to_datetime(df['arrival_time'])
        df['departure_time'] = pd.to_datetime(df['departure_time'])

        # get midnight (00:00:00) of the next day
        next_day_midnight = pd.to_datetime('00:00:00') + pd.Timedelta(days=1)

        print("modify the arrival and departure times")
        # modify the arrival and departure times
        df['arrival_time'] = next_day_midnight - \
            (df['arrival_time'] - df['arrival_time'].dt.normalize())
        df['departure_time'] = next_day_midnight - \
            (df['departure_time'] - df['departure_time'].dt.normalize())
        df['arrival_time'] = df['arrival_time'].dt.time
        df['departure_time'] = df['departure_time'].dt.time

        print("change the order of `stop_sequence`")
        # change the order of `stop_sequence`
        df['stop_sequence'] = df.groupby('trip_id')['stop_sequence'].transform(
            lambda x: x.max() - x + x.min())

        print("sorting the values within each `trip_id` by `stop_sequence`")
        # sorting the values within each `trip_id` by `stop_sequence`
        df = df.groupby('trip_id').apply(lambda x: x.sort_values(
            by='stop_sequence')).reset_index(drop=True)

        print("save the changes back to the file")
        # save the changes back to the file
        df.to_csv(f'{self.__path_to_file}//stop_times_mod.txt', index=False)

    # modify time 24:00:00 - xx.yy.zz in filename (csv protokol)
    # in all columns

    def modify_time_in_file(self, filename):
        df = pd.read_csv(filename)
        directory = os.path.dirname(filename)
        modified_file_path = os.path.join(directory, 'modified_your_file.csv')

        # converting all time columns to the time format
        time_columns = ['Start_time',
                        'Bus1_start_time',
                        'Bus1_finish_time',
                        'Bus2_start_time',
                        'Bus2_finish_time',
                        'Bus3_start_time',
                        'Bus3_finish_time',
                        'Destination_time']
        for col in time_columns:
            # `errors='coerce'` allows handling incorrect time values by converting them to `NaT`
            df[col] = pd.to_datetime(df[col], errors='coerce')

        # applying the `change_time` function to each time column
        for col in time_columns:
            df[col] = df[col].apply(self.change_time)

        # saving the changes to the file
        df.to_csv(modified_file_path, index=False)
        

    # function for comparing `stop_id` and `stop_sequence` arrays.

    def compare_trip(self, trip1, trip2):
        return trip1['stop_id'] == trip2['stop_id'] and trip1['stop_sequence'] == trip2['stop_sequence']

    #####################
    # Dividing routes into subgroups if different trips are used at different stops
    #####################
    def create_my_routes(self):

        stop_times_file = self.stop_times_df.reset_index()

        routes_file = self.routes_df.reset_index()
        routes_file = routes_file.set_index('route_id')

        trips_file1 = self.trips_df.reset_index()
        trips_file2 = self.trips_df.reset_index()
        trips_file2 = trips_file2.set_index('trip_id')

        # merging
        df = pd.merge(stop_times_file, trips_file1, on='trip_id')
        df.set_index(['stop_id', 'stop_sequence'], inplace=True)

        # dictionary for storing trip types and their arrays of `stop_id` and `stop_sequence`
        trip_types = defaultdict(list)
        result = []
        result_routes = []

        # grouping data by `route_id`
        grouped_routes = df.groupby('route_id')

        self.log_processing.append(f'Separated route')
        # iteration through groups

        for i, (route_id, route_group) in enumerate(grouped_routes):
            if i % 50 == 0:
                self.parent.setMessage(f'Separating route {i} of {len(grouped_routes)}...')
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            # grouping data by `trip_id`
            grouped_trips = route_group.groupby(['trip_id'])

            num_route = 0
            trip_types = defaultdict(list)
            # iteration through trips
            for trip_id, trip_group in grouped_trips:

                trip_id = trip_id[0]
                
                target_trip = trips_file2.loc[trip_id]  # access through index

                current_trip = {'stop_id': trip_group.index.get_level_values('stop_id').tolist(),
                                'stop_sequence': trip_group.index.get_level_values('stop_sequence').tolist()}
                trip_found = False

                # check the current trip for a match with existing trip types
                for trip_type, trip_type_data in trip_types.items():
                    for existing_trip in trip_type_data:

                        if self.compare_trip(current_trip, existing_trip):
                            
                            result.append((trip_type,
                                           target_trip['service_id'],
                                           target_trip.name,
                                           target_trip.get(
                                               'trip_headsign', None),
                                           target_trip.get(
                                               'direction_id', None),
                                           target_trip.get('shape_id', None)
                                           ))

                            trip_found = True
                            break

                    if trip_found:
                        break

                # if the trip does not have an existing type, create a new type
                if not trip_found:
                    num_route += 1
                    trip_types[f'{route_id}_{num_route}'].append(current_trip)

                    new_route_id = f'{route_id}_{num_route}'

                    result.append((new_route_id,
                                   target_trip['service_id'],
                                   target_trip.name,
                                   target_trip.get('trip_headsign', None),
                                   target_trip.get('direction_id', None),
                                   target_trip.get('shape_id', None)
                                   ))
                    target_routes = routes_file.loc[route_id]
                    result_routes.append((new_route_id,
                                          target_routes.get('agency_id', None),
                                          target_routes.get(
                                              'route_short_name', None),
                                          target_routes.get(
                                              'route_long_name', None),
                                          target_routes.get(
                                              'route_desc', None),
                                          target_routes['route_type'],
                                          target_routes.get('route_color', None)))

                    self.log_processing.append(
                        f'Route {route_id} -> {new_route_id}')

        self.log_processing.append(self.line_break)
        trips_result_df = pd.DataFrame(result)
        routes_result_df = pd.DataFrame(result_routes)

        self.trips_df = trips_result_df

        self.trips_df.columns = ['route_id',
                                 'service_id',
                                 'trip_id',
                                 'trip_headsign',
                                 'direction_id',
                                 'shape_id']
        self.routes_df = routes_result_df
        self.routes_df.columns = ['route_id',
                                  'agency_id',
                                  'route_short_name',
                                  'route_long_name',
                                  'route_desc',
                                  'route_type',
                                  'route_color']

        return 1

    # Group data by `trip_id` and check that `stop_sequence` has no gaps
    # and start at 1
    
    def check_stop_sequence(self, stop_times):

        count = stop_times.groupby('trip_id').ngroups
        for i, (trip_id, group) in enumerate(stop_times.groupby('trip_id')):
            if i % 100 == 0:
                if self.verify_break():
                    return 0
                self.parent.setMessage(f'Filtering data (group {i} from {count})...')
                QApplication.processEvents()

            max_sequence = group['stop_sequence'].max()
            min_sequence = group['stop_sequence'].min()
            unique_count = group['stop_sequence'].nunique()

            if max_sequence - min_sequence + 1 != unique_count or min_sequence != 1:
                # fix the numbering of `stop_sequence`
                corrected_sequence = list(range(1, len(group) + 1))
                stop_times.loc[group.index,
                               'stop_sequence'] = corrected_sequence

        return 1
        

    def load_GTFS(self):

        self.parent.setMessage(f'Loading data ...')

        QApplication.processEvents()
        if self.verify_break():
            return 0
        self.routes_df = pd.read_csv(
            f'{self.__path_to_GTFS}//routes.txt', sep=',')
        self.trips_df = pd.read_csv(
            f'{self.__path_to_GTFS}//trips.txt', sep=',')
        QApplication.processEvents()
        if self.verify_break():
            return 0
        self.stop_times_df = pd.read_csv(
            f'{self.__path_to_GTFS}//stop_times.txt', sep=',', dtype={'stop_id': str})
        
        QApplication.processEvents()
        if self.verify_break():
            return 0
        self.stop_df = pd.read_csv(
            f'{self.__path_to_GTFS}//stops.txt', sep=',', dtype={'stop_id': str})

        path_to_calendar = f'{self.__path_to_GTFS}//calendar.txt'
        calendar_exist = os.path.exists(path_to_calendar)
        if calendar_exist:
            self.calendar_df = pd.read_csv(
                f'{self.__path_to_GTFS}//calendar.txt', sep=',')

            ######################################################
            # Selecting Tuesday trips
            ######################################################

            self.parent.setMessage(f'Selecting Tuesday trips ...')
            self.log_processing.append('Selecting Tuesday trips ...')
            QApplication.processEvents()

            all_service_ids = set(self.calendar_df["service_id"])
            included_service_ids = set(
                self.calendar_df[self.calendar_df["tuesday"] == 1]["service_id"])
            excluded_service_ids = all_service_ids - included_service_ids
            excluded_service_ids_list = list(excluded_service_ids)
            self.log_processing.append(
                f'Services excluded {excluded_service_ids_list} ')

            calendar_dates_path = f'{self.__path_to_GTFS}//calendar_dates.txt'
            if os.path.isfile(calendar_dates_path):
                df_calendar_dates = pd.read_csv(calendar_dates_path)
                df_calendar_dates["date"] = pd.to_datetime(
                    df_calendar_dates["date"], format="%Y%m%d")
                df_calendar_dates["weekday"] = df_calendar_dates["date"].dt.weekday
                # filter only records where `date` is Tuesday (`weekday == 1`)
                tuesday_dates = df_calendar_dates[df_calendar_dates["weekday"] == 1]
                first_tuesday_dates = tuesday_dates.sort_values(
                    "date").drop_duplicates(subset=["service_id"], keep="first")
                for _, row in first_tuesday_dates.iterrows():
                    service_id = row["service_id"]
                    exception_type = row["exception_type"]
                    if exception_type == 1:
                        included_service_ids.add(service_id)
                        self.log_processing.append(
                            f'Service {service_id} added')
                    elif exception_type == 2:
                        included_service_ids.discard(service_id)
                        self.log_processing.append(
                            f'Service {service_id} excluded')
            self.trips_df = self.trips_df[self.trips_df["service_id"].isin(
                included_service_ids)]
            ######################################################
            self.log_processing.append(self.line_break)

            # filtering on trip_id
            self.parent.setMessage(f'Filtering data ...')
            self.stop_times_df = self.stop_times_df[self.stop_times_df['trip_id'].isin(self.trips_df['trip_id'])]

            # Преобразуем время в формат HH:MM:SS
            self.parent.setMessage(f'Correcting date ...')
            self.stop_times_df["arrival_time"] = self.stop_times_df["arrival_time"].apply(
            lambda x: f"{int(x.split(':')[0]):02}:{x.split(':')[1]}:{x.split(':')[2]}"
            )
            self.stop_times_df["departure_time"] = self.stop_times_df["arrival_time"]

    def interpolate_times(self):
        
        # group by `trip_id` and interpolate missing times
        num_groups = self.stop_times_df.groupby('trip_id').ngroups    
        for i, (trip_id, group) in enumerate(self.stop_times_df.groupby('trip_id')):
            if i % 100 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()
                self.parent.setMessage(f'Interpolating trips’ arrival times {i} from {num_groups}...')

            group = group.sort_values('stop_sequence')
            if group['arrival_time'].isna().any() or group['departure_time'].isna().any():
                group['arrival_seconds'] = group['arrival_time'].apply(time_to_seconds)
                # interpolation only if there are missing values
                group['arrival_seconds'] = group['arrival_seconds'].interpolate(
                    method='linear', limit_direction='both')
                # convert back to time
                group['arrival_time'] = group['arrival_seconds'].apply(
                    seconds_to_time)
                group['departure_time'] = group['arrival_time']

                # update the main DataFrame
                self.stop_times_df.loc[group.index, [
                    'arrival_time', 'departure_time']] = group[['arrival_time', 'departure_time']]

    def correcting_files(self):

        self.parent.progressBar.setMaximum(15)
        self.parent.progressBar.setValue(0)

        self.parent.break_on = False
        
        self.load_GTFS()

        self.parent.progressBar.setValue(1)
        if self.verify_break():
            return 0
        QApplication.processEvents()
       
        ##############################
        # interpolate  arrivel_times if skipped value
        ##############################
        if self.stop_times_df['arrival_time'].isna().any():
            self.interpolate_times()
        if self.verify_break():
            return 0
        QApplication.processEvents()
        
        ######################
        # check exist file frequencies.txt
        ######################
        
        path_to_frequencies = f'{self.__path_to_GTFS}//frequencies.txt'
        if os.path.isfile(path_to_frequencies):
            self.frequencies_df = pd.read_csv(path_to_frequencies)
            
            if len(self.frequencies_df) > 0:
                self.stop_times_df, self.trips_df = self.expand_frequencies(self.stop_times_df, 
                                                    self.frequencies_df, 
                                                    self.trips_df)  
        if self.verify_break():
            return 0
        QApplication.processEvents()
        
        ######################    
        self.create_my_routes()
        self.parent.progressBar.setValue(2)
        if self.verify_break():
            return 0
        QApplication.processEvents()

        ######################    
        self.correct_repeated_stops_in_trips()
        self.parent.progressBar.setValue(3)
        if self.verify_break():
            return 0
        QApplication.processEvents()
                    
        ##############################
        #  Exclude trips where  'arrival_time' is not monotonic_increasing:
        ##############################
        excluded_trips = []
        trips_group = self.stop_times_df.groupby("trip_id")
        self.stop_times_df.reset_index()
        
        self.parent.setMessage(f'Filtering data ...')
        self.parent.progressBar.setValue(4)
        trips_with_correct_timestamps = []
        
        self.stop_times_df['arrival_time_seconds'] = self.stop_times_df['arrival_time'].apply(time_to_seconds)

        for i, (id, trip) in enumerate(trips_group):
            if i % 100 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()

            if not trip['arrival_time_seconds'].is_monotonic_increasing:
                excluded_trips.append(id)
                continue

            trips_with_correct_timestamps.append(id)
        

        self.stop_times_df = self.stop_times_df[self.stop_times_df['trip_id'].isin(
            trips_with_correct_timestamps)]
        if excluded_trips:
            self.log_processing.append(
                f'Excluded trips (arrival_time no increasing): {excluded_trips}')
            self.log_processing.append(self.line_break)

        self.stop_times_df = self.stop_times_df.drop(
            columns=['arrival_time_seconds'])
        self.stop_times_df.reset_index()

        
        ##############################
        #  Correcting trips where 'stop_sequence' is monotonic increasing:
        ##############################
        self.parent.setMessage(f"Correcting sequence of stops...")
        self.parent.progressBar.setValue(5)

        for i, (id, trip) in enumerate(trips_group):
            if i % 100 == 0:
                QApplication.processEvents()
                if self.verify_break():
                    return 0
               
            if not trip['stop_sequence'].is_monotonic_increasing:

                trip_rows = self.stop_times_df[self.stop_times_df['trip_id'] == id]
                if len(trip_rows) == 0:
                    continue  

                self.stop_times_df.loc[self.stop_times_df['trip_id'] == id, 'stop_sequence'] = range(1, len(trip) + 1)
                self.log_processing.append(f"Renumbered stop_sequence for trip {id} due to incorrect order.")

        if self.verify_break():
            return 0
        QApplication.processEvents()
        ###################################
        # Another bug in GTFS – missing `stop_sequence` number
        # Checking the stop sequence and correcting incorrect `trip_id`
        ###################################

        self.parent.setMessage(f'Filtering data ... ')
        self.parent.progressBar.setValue(6)
        self.check_stop_sequence(self.stop_times_df)
        if self.verify_break():
            return 0
        QApplication.processEvents()
        ####################################
        
        self.parent.setMessage(f'Saving ...')
        self.parent.progressBar.setValue(7)
        self.stop_times_df = self.stop_times_df.reset_index()
        if self.verify_break():
            return 0
        QApplication.processEvents()
        self.save_GTFS()

        self.parent.progressBar.setValue(8)
        with open(self.filelog_name, "w", encoding="utf-8") as file:
            for line in self.log_processing:
                file.write(line + "\n")
        #################################        
        
        self.parent.setMessage(f'Building aerial paths between buildings and stops...')
        QApplication.processEvents()
        self.create_footpath_AIR()
        self.parent.progressBar.setValue(9)
        if self.verify_break():
            return 0
        
        ##########################################
        # Calc footpath on graph with projections
        ##########################################
        self.create_footpath_on_graph()
        return 1

    def create_footpath_on_graph(self, need_save_layer_with_projection = False, filename = ""):
        if self.parent is not None:
            self.parent.setMessage('Converting multilines into lines...')
        self.converter = MultiLineStringToLineStringConverter(
            self.parent, self.layer_road)
        self.layer_road = self.converter.execute()

        if self.verify_break():
            return 0
        
        if self.parent is not None:
            self.parent.progressBar.setValue(10)
            QApplication.processEvents()

        path_to_stops = self.__path_to_file

        footpath_on_projection = cls_footpath_on_projection(self.parent, self.MaxPathRoad)
        new_layer = footpath_on_projection.make_new_layer_with_projections(self.layer_road,
                                                                           self.layer_origins,
                                                                           self.layer_origins_field,
                                                                           path_to_stops
                                                                           )
        
        if need_save_layer_with_projection:

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GeoJSON"
            options.fileEncoding = "UTF-8"

            QgsVectorFileWriter.writeAsVectorFormatV3(
                new_layer, 
                filename, 
                QgsProject.instance().transformContext(), 
                options)

        if self.verify_break():
            return 0
        if self.parent is not None:
            self.parent.progressBar.setValue(11)
            QApplication.processEvents()
        graph = footpath_on_projection.build_graph(new_layer, self.pkl_path)
        if self.verify_break():
            return 0
        if self.parent is not None:
            self.parent.progressBar.setValue(12)
            QApplication.processEvents()
        footpath_on_projection.save_graph(graph, self.pkl_path)
        if self.verify_break():
            return 0

        graph_projection = footpath_on_projection.load_graph(self.pkl_path)
        if self.parent is not None:
            self.parent.progressBar.setValue(13)
            QApplication.processEvents()
        dict_osm_vertex = footpath_on_projection.load_dict_osm_vertex(
            self.pkl_path)
        dict_vertex_osm = footpath_on_projection.load_dict_vertex_osm(
            self.pkl_path)
        if self.parent is not None:
            self.parent.progressBar.setValue(14)
            QApplication.processEvents()

        footpath_on_projection.construct_dict_transfers_projections(graph_projection,
                                                                    dict_osm_vertex,
                                                                    dict_vertex_osm,
                                                                    self.layer_origins,
                                                                    self.layer_origins_field,
                                                                    self.__path_to_file,
                                                                    path_to_stops
                                                                    )
        if self.parent is not None:
            self.parent.progressBar.setValue(15)
            QApplication.processEvents()

        self.converter.remove_temp_layer()


    def found_repeated_in_trips_stops(self):
        stop_times_file = pd.read_csv(
            f'{self.__path_to_GTFS}/stop_times.txt', sep=',')
        trips_group = stop_times_file.groupby("trip_id")

        for trip_id, trip in trips_group:

            stop_ids = {}  # create an empty set to track unique `stop_id` in a trip

            # check each stop in the trip
            for index, stop in trip.iterrows():
                stop_id = stop["stop_id"]
                if stop_id in stop_ids:
                    stop_ids[stop_id] += 1
                    
                else:
                    stop_ids[stop_id] = 1

    def correct_repeated_stops_in_trips(self):

        self.stop_times_df.reset_index
        self.parent.setMessage(f'Merging data ...')

        self.merged_df = pd.merge(self.routes_df, self.trips_df, on="route_id")
        self.merged_df = pd.merge(
            self.merged_df, self.stop_times_df, on="trip_id")
        
        QApplication.processEvents()
        if self.verify_break():
            return 0

        self.stop_times_df = self.stop_times_df.set_index(
            ['trip_id', 'stop_sequence'])

        self.parent.setMessage(f'Correcting duplicated stops...')

        QApplication.processEvents()

        self.parent.setMessage(f'Grouping ...')
        QApplication.processEvents()

        grouped = self.merged_df.groupby('route_id')

        self.max_stop_id = "stop0000"

        all_routes = len(grouped)

        new_stops = []
        for count, (route_id, group) in enumerate(grouped):
            if count % 100 == 0:

                self.parent.setMessage(f'Cleaning duplicate stops, route {count} of {all_routes}')
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            first_trip_id = group['trip_id'].iloc[0]
                        
            trip = self.stop_times_df.xs(first_trip_id, level='trip_id')
            trip = trip.reset_index()
            stop_ids = []

            for index, row in trip.iterrows():
                stop_id = row['stop_id']
                stop_sequence = row['stop_sequence']

                if stop_id in stop_ids:
                    new_stop_id = self.create_new_stop(stop_id)
                    new_stops.append((route_id, stop_sequence, new_stop_id))
                else:
                    stop_ids.append(stop_id)

        if True:
            new_stops_df = pd.DataFrame(
                new_stops, columns=['route_id', 'stop_sequence', 'new_stop_id'])

            # Merge with stop_times_df to identify rows to update
            stops_to_update = self.merged_df.merge(
                new_stops_df, on=['route_id', 'stop_sequence'], how='inner')
            update_index = stops_to_update.set_index(
                ['trip_id', 'stop_sequence'])

            self.parent.setMessage(f'Cleaning duplicated stops...')
            QApplication.processEvents()
            if self.verify_break():
                return 0

            
            #self.stop_times_df = self.stop_times_df.reset_index()
            #self.stop_times_df.set_index(['trip_id', 'stop_sequence'], inplace=True)
            update_df = update_index[['new_stop_id']]
            common_indices = self.stop_times_df.index.intersection(update_df.index)
            self.stop_times_df.loc[common_indices, 'stop_id'] = update_df.loc[common_indices, 'new_stop_id'].values
            
            self.stop_times_df.reset_index(inplace=True)            
            
        if new_stops:

            logs = [
                f"Trip_id={index[0]}, Stop_sequence={index[1]}, changed stop_id to {row['new_stop_id']}"
                for index, row in update_index.iterrows()
            ]
            self.log_processing.append('Corrected repeated stops...')
            self.log_processing.extend(logs)
            self.log_processing.append(self.line_break)


    def save_GTFS(self):
        
        self.parent.setMessage('Saving stops ...')
        QApplication.processEvents()
        if self.verify_break():
            return 0
        self.stop_df.to_csv(f'{self.__path_to_file}//stops.txt', index=False)
        self.parent.setMessage('Saving time schedule ...')
        QApplication.processEvents()
        if self.verify_break():
            return 0
       
        self.stop_times_df.reset_index(inplace=True)
        
        selected_columns = ['trip_id', 'arrival_time',
                            'departure_time', 'stop_id', 'stop_sequence', ]
        
        ##################
        # For testing algo!!!!!!!!
        ##################
        #self.filter_trips(nth=3)
        ##################
        ##################
        ##################

        self.stop_times_df[selected_columns].to_csv(
            f'{self.__path_to_file}//stop_times.txt', index=False)

        unique_trip_ids = self.stop_times_df['trip_id'].unique()

        self.parent.setMessage('Saving trips ...')
        QApplication.processEvents()
        if self.verify_break():
            return 0

        self.trips_df.columns = ['route_id',
                                 'service_id',
                                 'trip_id',
                                 'trip_headsign',
                                 'direction_id',
                                 'shape_id']
        self.trips_df = self.trips_df[self.trips_df['trip_id'].isin(
            unique_trip_ids)]
        self.trips_df.to_csv(f'{self.__path_to_file}//trips.txt', header=['route_id',
                                                                          'service_id',
                                                                          'trip_id',
                                                                          'trip_headsign',
                                                                          'direction_id',
                                                                          'shape_id'], index=False)

        self.parent.setMessage('Saving routes ...')
        QApplication.processEvents()
        if self.verify_break():
            return 0

        self.routes_df.columns = ['route_id',
                                  'agency_id',
                                  'route_short_name',
                                  'route_long_name',
                                  'route_desc',
                                  'route_type',
                                  'route_color']
        unique_routes_ids = self.trips_df['route_id'].unique()
        self.routes_df = self.routes_df[self.routes_df['route_id'].isin(
            unique_routes_ids)]
        self.routes_df.to_csv(f'{self.__path_to_file}//routes.txt', header=['route_id',
                                                                            'agency_id',
                                                                            'route_short_name',
                                                                            'route_long_name',
                                                                            'route_desc',
                                                                            'route_type',
                                                                            'route_color'],
                              index=False)
        if self.verify_break():
            return 0

        return 1

    def get_new_stop_id(self):
        match = re.search(r'(\D+)(\d+)', self.max_stop_id)
        prefix, number = match.groups()
        # increase the numeric part and format it with leading zeros
        next_number = str(int(number) + 1).zfill(len(number))
        new_stop_id = f"{prefix}{next_number}"
        self.max_stop_id = new_stop_id
        return new_stop_id

    def create_new_stop(self, stop_id):

        new_stop_id = self.get_new_stop_id()
        new_stop = self.stop_df[self.stop_df['stop_id'] == stop_id].copy()
        new_stop['stop_id'] = new_stop_id
        self.stop_df = pd.concat([self.stop_df, new_stop], ignore_index=True)
        return new_stop_id

    def create_stops_gpd(self):
        wgs84 = pyproj.CRS('EPSG:4326')  # WGS 84
        crs_curr = self.layer_origins.crs().authid()
        transformer = pyproj.Transformer.from_crs(
            wgs84, crs_curr, always_xy=True)

        points = []

        filename = os.path.join(self.__path_to_file, 'stops.txt')
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                stop_id = row['stop_id']
                latitude = float(row['stop_lat'])  
                longitude = float(row['stop_lon']) 
                x_meter, y_meter = transformer.transform(longitude, latitude)
                points.append((stop_id, Point(x_meter, y_meter)))

        points_copy = gpd.GeoDataFrame(
            points, columns=['stop_id', 'geometry'], crs=crs_curr)
        return points_copy

    def calculate_geodesic_distance(self, geom1, geom2):
        geod = Geod(ellps="WGS84")
        lon1, lat1 = (geom1.x, geom1.y)
        lon2, lat2 = (geom2.x, geom2.y)
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        return distance

    def create_footpath_AIR(self):

        stops = self.create_stops_gpd()
        buildings = self.layer_origins

        dist = self.MaxPathAir
        dist_m = self.MaxPathAir
        self.crs = buildings.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)

        centroids_buildings = []
        for i, feature in enumerate(buildings.getFeatures()):
            if i % 1000 == 0:
                QApplication.processEvents()
                if self.verify_break():
                    return 0
            geom = feature.geometry()

            centroid = geom.centroid().asPoint()
            centroids_buildings.append((feature[self.layer_origins_field], Point(centroid)))

        centroids_coords = [(centroid[1].x, centroid[1].y)
                            for centroid in centroids_buildings]
        centroids_tree_buildings = cKDTree(centroids_coords)

        close_pairs = []
        current_combination = 0

        # find building - stop pairs
        for i, geom in enumerate(stops.geometry):
            stop_id1 = stops.iloc[i]['stop_id']

            if self.crs_grad:
                dist = convert_meters_to_degrees(dist_m, geom.y)
            nearest_centroids_buildings = centroids_tree_buildings.query_ball_point(
                (geom.x, geom.y), dist)

            for j in nearest_centroids_buildings:
                current_combination = current_combination + 1
                if current_combination % 5000 == 0:
                    self.parent.setMessage(f'Processing building-stop pair {current_combination}')
                    QApplication.processEvents()
                    if self.verify_break():
                        return 0

                if self.crs_grad:
                    distance = self.calculate_geodesic_distance(
                        geom, centroids_buildings[j][1])
                else:
                    distance = geom.distance(centroids_buildings[j][1])

                if distance <= dist_m:
                    close_pairs.append(
                        (centroids_buildings[j][0], stop_id1, round(distance)))

        stops_coords = [(geom.x, geom.y) for geom in stops.geometry]
        stops_tree = cKDTree(stops_coords)
        # find stop pairs
        for i, geom in enumerate(stops.geometry):
            stop_id1 = stops.iloc[i]['stop_id']

            if self.crs_grad:
                dist = convert_meters_to_degrees(dist_m, geom.y)
            nearest_stops = stops_tree.query_ball_point((geom.x, geom.y), dist)

            for j in nearest_stops:
                if i == j:
                    continue
                current_combination += 1
                if current_combination % 1000 == 0:
                    self.parent.setMessage(f'Processing stop-stop pair {current_combination}')
                    QApplication.processEvents()
                    if self.verify_break():
                        return 0

                if self.crs_grad:
                    distance = self.calculate_geodesic_distance(
                        geom, stops.iloc[j]['geometry'])
                else:
                    distance = geom.distance(stops.iloc[j]['geometry'])

                if distance <= dist_m and stops.iloc[j]['stop_id'] != stop_id1:
                    close_pairs.append(
                        (stops.iloc[j]['stop_id'], stop_id1, round(distance)))

        filename = os.path.join(self.__path_to_file,'footpath_AIR.txt')
        with open(filename, 'w') as file:
            file.write(f'from_stop_id,to_stop_id,min_transfer_time\n')
            for pair in close_pairs:
                id_from_points_layer = pair[0]
                stop_id1 = pair[1]
                distance = pair[2]
                file.write(f'{id_from_points_layer},{stop_id1},{distance}\n')
                file.write(f'{stop_id1},{id_from_points_layer},{distance}\n')

    def verify_break(self):
        if self.parent is not None:
            if self.parent.break_on:
                self.parent.setMessage("Database construction is interrupted by user")
                if not self.already_display_break:
                    self.parent.textLog.append(f'<a><b><font color="red">Database construction is interrupted by user</font> </b></a>')
                    self.already_display_break = True
                self.parent.progressBar.setValue(0)
                return True
        return False
    
    def expand_frequencies(self, stop_times_df, frequencies_df, trips_df):
        # Preprocess frequencies_df for start and end times in seconds
        frequencies_df["start_time_sec"] = frequencies_df["start_time"].map(time_to_seconds)
        frequencies_df["end_time_sec"] = frequencies_df["end_time"].map(time_to_seconds)

        # Result lists for expanded rows and new trips
        expanded_rows = []
        new_trips = []

        total_frequencies = len(frequencies_df)

        
        trip_id_str = (trips_df["trip_id"].dtype == "object")

        if trip_id_str:
            max_trip_id = f"trip_ac_1"
        else:
           max_trip_id = trips_df["trip_id"].max() + 1
        
        for i, freq_row in frequencies_df.iterrows():
            if i % 1 == 0:
                self.parent.setMessage(f'Processing line schedule ({i} from {total_frequencies})')
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            #if i == 1000:
            #    break

            trip_id = freq_row["trip_id"]
            trip_data = trips_df[trips_df["trip_id"] == trip_id]
            if trip_data.empty:
                continue

            start_time = freq_row["start_time_sec"]
            end_time = freq_row["end_time_sec"]
            headway_secs = freq_row["headway_secs"]

            # Filter stop_times for the current trip_id
            trip_stops = stop_times_df[stop_times_df["trip_id"] == trip_id].copy()
            if trip_stops.empty:
                continue
            trip_stops["departure_time_sec"] = trip_stops["departure_time"].map(time_to_seconds)

            current_time = start_time
            while current_time < end_time:
                offset = current_time - trip_stops["departure_time_sec"].iloc[0]
                new_trip = trip_stops.copy()
                new_trip["departure_time_sec"] += offset
                new_trip["departure_time"] = new_trip["departure_time_sec"].map(seconds_to_time)
                new_trip["arrival_time"] = new_trip["departure_time"]
                new_trip_id = max_trip_id    
                new_trip["trip_id"] = new_trip_id
                expanded_rows.append(new_trip)

                new_trip_data = {
                   "trip_id": new_trip_id,
                    "route_id": trip_data.get("route_id", pd.Series([None])).iloc[0],
                    "service_id": trip_data.get("service_id", pd.Series([None])).iloc[0],
                    "direction_id": trip_data.get("direction_id", pd.Series([None])).iloc[0],
                    "shape_id": trip_data.get("shape_id", pd.Series([None])).iloc[0]
                }

                new_trips.append(new_trip_data)

                current_time += headway_secs

                # Assign new trip_id
                if trip_id_str:
                    max_trip_id = f"trip_ac_{int(max_trip_id.split('_')[-1]) + 1}"
                else:
                    max_trip_id += 1

        # Batch combine expanded rows into a DataFrame
        if expanded_rows:
            expanded_df = pd.concat(expanded_rows, ignore_index=True)
            expanded_df.drop(columns=["departure_time_sec"], inplace=True)

            # Combine and save data
            stop_times_df = pd.concat([stop_times_df, expanded_df], ignore_index=True)
            df_new_trips = pd.DataFrame(new_trips)
            #df_new_trips.to_csv(r"C:\\Users\\geosimlab\\Documents\\Igor\\gtfs_others\\petersburg\\new_trips.csv", index=False)

            trips_df = pd.concat([trips_df, df_new_trips], ignore_index=True)

        return stop_times_df, trips_df

