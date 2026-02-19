import pandas as pd
import os
import pickle
from io import StringIO
from collections import defaultdict

try:
    from PyQt5.QtWidgets import QApplication
    IN_QGIS = True
except ImportError:
    IN_QGIS = False

from common import time_to_seconds

class PKL ():

    def __init__(self, 
                 parent, 
                 path_to_pkl='', 
                 path_to_GTFS='', 
                 layer_buildings='', 
                 building_id_field = "osm_id"):
        
        if path_to_GTFS == '':
            self.__path_gtfs = path_to_pkl
        else:
            self.__path_gtfs = path_to_GTFS

        self.__path_pkl = path_to_pkl
        self.prefix = os.path.basename(self.__path_pkl)

        
        self.parent = parent
        self.layer_buildings = layer_buildings

        self.__transfers_start_file1 = pd.read_csv(
            f'{self.__path_gtfs}/footpath_air.txt', sep=',', dtype={'from_stop_id': str, 'to_stop_id': str})
        self.__transfers_start_file2 = pd.read_csv(
            f'{self.__path_gtfs}/footpath_road_projection.txt', sep=',', dtype={'from_stop_id': str, 'to_stop_id': str})

        os.makedirs(self.__path_pkl, exist_ok=True)

        self.already_display_break = False
        self.building_id_field = building_id_field

        self.IN_QGIS = True
        if self.parent == None:
            self.IN_QGIS = False


    def build_list_stops(self):
        list_stops = pd.read_csv(
            f'{self.__path_gtfs}/stops.txt', sep=',', dtype={'stop_id': str})
        stop_ids = list_stops['stop_id']
        f = os.path.join(self.__path_pkl, f"{self.prefix}_stop_ids.pkl")
        stop_ids.to_pickle(f)

    def create_files(self):
        if self.IN_QGIS:
            self.parent.progressBar.setMaximum(12)
            self.parent.progressBar.setValue(0)

        self.load_gtfs()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(1)
        if self.verify_break():
            return 0

        self.build_list_stops()

        self.__stop_pkl = self.build_stops_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(2)
        if self.verify_break():
            return 0

        self.build_stopstimes_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(3)
        if self.verify_break():
            return 0

        self.build_stop_idx_in_route()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(4)
        if self.verify_break():
            return 0
        
        self.build_footpath_dict(
            self.__transfers_start_file1, "transfers_dict_air.pkl")
        if self.IN_QGIS:
            self.parent.progressBar.setValue(5)
        if self.verify_break():
            return 0

        self.build_footpath_dict(
            self.__transfers_start_file2, "transfers_dict_projection.pkl")
        if self.IN_QGIS:
            self.parent.progressBar.setValue(5)
        if self.verify_break():
            return 0
        
        self.build__route_by_stop()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(7)
        if self.verify_break():
            return 0

        self.build_routes_by_stop_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(8)
        if self.verify_break():
            return 0

        self.build_reversed_stops_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(9)
        if self.verify_break():
            return 0

        self.build_reversed_stoptimes_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(10)
        if self.verify_break():
            return 0

        self.build_reverse_stoptimes_file_txt()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(11)
        if self.verify_break():
            return 0

        self.build_rev_stop_idx_in_route()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(12)
        if self.verify_break():
            return 0
        
        return 1

    def load_gtfs(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Loading GTFS ...')
        if self.IN_QGIS:    
            QApplication.processEvents()
        if self.verify_break():
            return 0

        self.__trips_file = pd.read_csv(
            f'{self.__path_gtfs}/trips.txt', sep=',', dtype={'trip_id': str})
        
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0
        
        self.__stop_times_file = pd.read_csv(
            f'{self.__path_gtfs}/stop_times.txt', sep=',', dtype={'stop_id': str, 'trip_id': str})
        
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

        self.__stop_times_file = pd.merge(
            self.__stop_times_file, self.__trips_file, on='trip_id')
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

        self.__routes_file = pd.read_csv(
            f'{self.__path_gtfs}/routes.txt', sep=',')
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

    def build_route_desc__route_id_dict(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building route desciption for {route_id} ...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        route_dict = {}

        for _, row in self.__routes_file.iterrows():
            route_desc = row['route_desc']
            key = route_desc.split('-')[0]
            route_id = row['route_id']

            if key not in route_dict:
                route_dict[key] = []
            route_dict[key].append(route_id)

        f = os.path.join(self.__path_pkl, f"{self.prefix}_route_desc__route_id.pkl")

        with open(f, "wb") as pickle_file:
            pickle.dump(route_dict, pickle_file)

        return 1

    def build_stops_dict(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for from-accessibility ...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        stop_times = self.__stop_times_file

        route_groups = stop_times.drop_duplicates(subset=['route_id', 'stop_sequence'])[
            ['stop_id', 'route_id', 'stop_sequence']].groupby('route_id')
        stops_dict = {id: routes.sort_values(by='stop_sequence')[
            'stop_id'].to_list() for id, routes in route_groups}
        
        f = os.path.join(self.__path_pkl, f"{self.prefix}_stops_dict_pkl.pkl")

       
        with open(f, "wb") as pickle_file:
            pickle.dump(stops_dict, pickle_file)
       

        return stops_dict

    def build_stopstimes_dict(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for from-accessibility ...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        merged_data = self.__stop_times_file.merge(
            self.__trips_file, on='trip_id')
        grouped_data = merged_data.groupby('route_id_y')
        result_dict = {}

        len_data = len(grouped_data)
        for cycle, (route_id, group) in enumerate(grouped_data):

            if cycle % 500 == 0:

                if self.IN_QGIS:
                    self.parent.setMessage(f'Building database for route {cycle} of {len_data}...')
                    QApplication.processEvents()
                if self.verify_break():
                    return 0

            trip_dict = {}
            for trip_id, trip_data in group.groupby('trip_id'):
                trip_data = trip_data.sort_values(
                    'arrival_time', ascending=True)
                trip_dict[trip_id] = list(
                    zip(trip_data['stop_id'], trip_data['arrival_time']))

            sorted_trips = sorted(
                trip_dict.items(), key=lambda x: x[1][0][1], reverse=False)

            result_dict[route_id] = {trip_id: [(stop_id, time_to_seconds(
                arrival_time)) for stop_id, arrival_time in trip_data] for trip_id, trip_data in sorted_trips}

        f = os.path.join(self.__path_pkl, f"{self.prefix}_stoptimes_dict_pkl.pkl")
        
        with open(f, "wb") as pickle_file:
            pickle.dump(result_dict, pickle_file)
        return 1
    
    # Function to merge dictionary values
    def merge_dicts(self, dict1, dict2):
        result = defaultdict(list)
        for d in (dict1, dict2):
            for key, value in d.items():
                result[key].extend(value)
        return dict(result)
        
    def build_footpath_dict(self, obj_txt, file_name):
        """Build footpath dictionary with optimized performance."""
        if self.IN_QGIS:
            self.parent.setMessage(f'Building transfers {file_name}...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        # Grouping and processing
        grouped = obj_txt.groupby("from_stop_id")
        footpath_dict = {
            from_stop: list(zip(details["to_stop_id"], details["min_transfer_time"]))
            for from_stop, details in grouped
        }

        # Path to save the pickle file
        pickle_path = os.path.join(self.__path_pkl, f"{self.prefix}_{file_name}")

        # Write or append to the pickle file
        
        with open(pickle_path, "wb") as pickle_file:
            pickle.dump(footpath_dict, pickle_file)
        
        return 1

    def build_stop_idx_in_route(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building index ...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        stoptimes_txt = pd.read_csv(
            f'{self.__path_gtfs}/stop_times.txt', sep=',', dtype={'stop_id': str, 'trip_id': str})

        stop_times_file = pd.merge(
            stoptimes_txt, self.__trips_file, on='trip_id')

        pandas_group = stop_times_file.groupby(["route_id", "stop_id"])
        idx_by_route_stop = {
            route_stop_pair: details.stop_sequence.iloc[0] for route_stop_pair, details in pandas_group}

        f = os.path.join(self.__path_pkl, f"{self.prefix}_idx_by_route_stop.pkl")
        
        with open(f, "wb") as pickle_file:
            pickle.dump(idx_by_route_stop, pickle_file)
        

        return 1

    def build_routes_by_stop_dict(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building index ...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        f = os.path.join(self.__path_pkl, f"{self.prefix}_stops_dict_pkl.pkl")
        
        with open(f, 'rb') as file:
            stops_dict = pickle.load(file)

        routes_stops_index = {}

        for route, stops in stops_dict.items():
            for stop_index, stop in enumerate(stops):
                routes_stops_index[(route, stop)] = stop_index
        routesindx_by_stop_dict = routes_stops_index

        f = os.path.join(self.__path_pkl, f"{self.prefix}_routesindx_by_stop.pkl")
     
        with open(f, "wb") as pickle_file:
            pickle.dump(routesindx_by_stop_dict, pickle_file)
     

        return 1

    def build_reversed_stops_dict(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        for key in self.__stop_pkl.keys():
            self.__stop_pkl[key] = self.__reverse(self.__stop_pkl[key])

        f = os.path.join(self.__path_pkl, f"{self.prefix}_stops_dict_reversed_pkl.pkl")

    
        with open(f, "wb") as pickle_file:
            pickle.dump(self.__stop_pkl, pickle_file)
    

    def __reverse(self, lst):
        new_lst = lst[::-1]
        return new_lst

    def build_reversed_stoptimes_dict(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        merged_data = self.__stop_times_file.merge(
            self.__trips_file, on='trip_id')
        grouped_data = merged_data.groupby('route_id_y')
        result_dict = {}

        len_data = len(grouped_data)
        for cycle, (route_id, group) in enumerate(grouped_data):

            if cycle % 500 == 0:
                if self.IN_QGIS:    
                    self.parent.setMessage(f'Building database, route {cycle} of {len_data}...')
                    QApplication.processEvents()
                if self.verify_break():
                    return 0

            trip_dict = {}
            for trip_id, trip_data in group.groupby('trip_id'):
                trip_data = trip_data.sort_values(
                    'arrival_time', ascending=False)
                trip_dict[trip_id] = list(
                    zip(trip_data['stop_id'], trip_data['arrival_time']))

            sorted_trips = sorted(
                trip_dict.items(), key=lambda x: x[1][0][1], reverse=True)
            result_dict[route_id] = {trip_id: [(stop_id, time_to_seconds(
                arrival_time)) for stop_id, arrival_time in trip_data] for trip_id, trip_data in sorted_trips}

        f = os.path.join(self.__path_pkl, f"{self.prefix}_stoptimes_dict_reversed_pkl.pkl")
        
        with open(f, "wb") as pickle_file:
            pickle.dump(result_dict, pickle_file)
        

    # Function to swap stop numbers with the opposite ones within each trip

    """
    def reverse_stop_sequence(self, group, *args, **kwargs):

        num_stops = len(group)
        reversed_stop_sequence = range(num_stops, 0, -1)
        group = group.assign(stop_sequence=reversed_stop_sequence)
        return group

    
    def build_reverse_stoptimes_file_txt(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        with open(self.__path_gtfs + "/stop_times.txt", "r") as f:
            allrows = f.readlines()
        
        # convert a list of strings to a delimited string and create a DataFrame
        data_str = '\n'.join(allrows)
        df = pd.read_csv(StringIO(data_str))

        #df_result = df.groupby('trip_id', group_keys=False).apply(self.reverse_stop_sequence)
        
        df_result = df.drop(columns='trip_id').groupby(df['trip_id'], group_keys=False).apply(
        lambda group: self.reverse_stop_sequence(group).assign(trip_id=group.name))

        # using StringIO again to write a DataFrame to a String
        output_str = StringIO()
        df_result.to_csv(output_str, index=False, lineterminator='\n')

        # get a row of data
        output_data = output_str.getvalue()
        f = self.__path_gtfs + "/rev_stop_times.txt"

        with open(f, "w") as output_file:
            output_file.write(output_data)

        return 1
    """

    def build_reverse_stoptimes_file_txt(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0
        
        with open(self.__path_gtfs + "/stop_times.txt", "r") as f:
            df = pd.read_csv(f, dtype={'trip_id': str, 'stop_id': str})
            
        group_max = df.groupby('trip_id')['stop_sequence'].transform('max')
        df['stop_sequence'] = group_max - df['stop_sequence'] + 1
        
        path_rev = self.__path_gtfs + "/rev_stop_times.txt"
        df.to_csv(path_rev, index=False, lineterminator='\n')

        return 1    

    def build_rev_stop_idx_in_route(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        reverse_stoptimes_txt = pd.read_csv(
            f'{self.__path_gtfs}/rev_stop_times.txt', sep=',', dtype={'stop_id': str, 'trip_id': str})
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0
        rev_stop_times_file = pd.merge(
            reverse_stoptimes_txt, self.__trips_file, on='trip_id')
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

        pandas_group = rev_stop_times_file.groupby(["route_id", "stop_id"])
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0
        idx_by_route_stop = {
            route_stop_pair: details.stop_sequence.iloc[0] for route_stop_pair, details in pandas_group}
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

        
        f = os.path.join(self.__path_pkl, f"{self.prefix}_rev_idx_by_route_stop.pkl")
        
        with open(f, "wb") as pickle_file:
            pickle.dump(idx_by_route_stop, pickle_file)
        

        return 1

    def build__route_by_stop(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        stops_by_route = self.__stop_times_file.drop_duplicates(
            subset=['route_id', 'stop_id'])[['stop_id', 'route_id']].groupby('stop_id')
        route_by_stop_dict = {id: list(routes.route_id)
                              for id, routes in stops_by_route}
        # add buildings
        for feature in self.layer_buildings.getFeatures():
            osm_id = feature[self.building_id_field]
            route_by_stop_dict[osm_id] = []
        f = os.path.join(self.__path_pkl, f"{self.prefix}_routes_by_stop.pkl")
        with open(f, "wb") as pickle_file:
                pickle.dump(route_by_stop_dict, pickle_file)
        return 1

    def verify_break(self):
        if self.IN_QGIS:  
            if self.parent.break_on:
                self.parent.setMessage("Building database is interrupted by user")
                if not self.already_display_break:
                    self.parent.textLog.append(f'<a><b><font color="red">Building database is interrupted by user</font> </b></a>')
                    self.already_display_break = True
                self.parent.progressBar.setValue(0)
                return True
        return False
