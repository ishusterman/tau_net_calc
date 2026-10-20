import pandas as pd
import os
from collections import defaultdict
import shutil
import json

try:
    from qgis.PyQt.QtWidgets import QApplication
    IN_QGIS = True
except ImportError:
    IN_QGIS = False

from tau_net_calc.cls.common import time_to_seconds

class PKL ():

    def __init__(self, 
                 parent, 
                 path_to_pkl='', 
                 path_to_GTFS='', 
                 layer_buildings='', 
                 building_id_field = "osm_id",
                 to_delete_gtfs = True):
        
        if path_to_GTFS == '':
            self.__path_gtfs = path_to_pkl
        else:
            self.__path_gtfs = path_to_GTFS

        self.__path_pkl = path_to_pkl
        self.prefix = os.path.basename(self.__path_pkl)
        self.parent = parent
        self.layer_buildings = layer_buildings

        self.to_delete_gtfs = to_delete_gtfs
        
        self.__transfers_start_file2 = pd.read_csv(f'{self.__path_gtfs}/footpath_road_projection.txt', sep=',', dtype={'from_stop_id': str, 'to_stop_id': str})

        os.makedirs(self.__path_pkl, exist_ok=True)

        self.already_display_break = False
        self.building_id_field = building_id_field

        self.IN_QGIS = True
        if self.parent is None:
            self.IN_QGIS = False

    def build_list_stops(self):
        list_stops = pd.read_csv( f'{self.__path_gtfs}/stops.txt', sep=',', dtype={'stop_id': str})        
        stop_ids = list_stops['stop_id'].tolist()
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stop_ids.json")        
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(stop_ids, f, ensure_ascii=False)
        return stop_ids
    
    def create_files(self):
        if self.IN_QGIS:
            self.parent.progressBar.setMaximum(11)
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
       
        self.build_footpath_dict(self.__transfers_start_file2, "transfers.json")
        if self.IN_QGIS:
            self.parent.progressBar.setValue(5)
        if self.verify_break():
            return 0
        
        self.build__route_by_stop()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(7)
        if self.verify_break():
            return 0

        self.build_reversed_stops_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(8)
        if self.verify_break():
            return 0

        self.build_reversed_stoptimes_dict()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(9)
        if self.verify_break():
            return 0

        self.build_reverse_stoptimes_file_txt()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(10)
        if self.verify_break():
            return 0

        self.build_rev_stop_idx_in_route()
        if self.IN_QGIS:
            self.parent.progressBar.setValue(11)
        if self.verify_break():
            return 0
        
        if self.to_delete_gtfs:
            if os.path.exists(self.__path_gtfs):
                shutil.rmtree(self.__path_gtfs)
        
        return 1

    def load_gtfs(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Loading GTFS ...')
        if self.IN_QGIS:    
            QApplication.processEvents()
        if self.verify_break():
            return 0

        self.__trips_file = pd.read_csv(f'{self.__path_gtfs}/trips.txt', sep=',', dtype={'trip_id': str})
        
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0
        
        self.__stop_times_file = pd.read_csv(f'{self.__path_gtfs}/stop_times.txt', sep=',', dtype={'stop_id': str, 'trip_id': str})
        
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

        self.__stop_times_file = pd.merge(self.__stop_times_file, self.__trips_file, on='trip_id')
        if self.IN_QGIS:
            QApplication.processEvents()
        if self.verify_break():
            return 0

    def build_stops_dict(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for from-accessibility ...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        stop_times = self.__stop_times_file

        route_groups = stop_times.drop_duplicates(subset=['route_id', 'stop_sequence'])[['stop_id', 'route_id', 'stop_sequence']].groupby('route_id')
        stops_dict = {id: routes.sort_values(by='stop_sequence')['stop_id'].to_list() for id, routes in route_groups}
        
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stops.json")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(stops_dict, f, ensure_ascii=False)       

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
                #trip_dict[trip_id] = list(zip(trip_data['stop_id'], trip_data['arrival_time']))
                trip_dict[trip_id] = [
                                        [stop_id, arrival_time]
                                        for stop_id, arrival_time in zip(trip_data['stop_id'], trip_data['arrival_time'])
                                    ]


            sorted_trips = sorted(
                trip_dict.items(), key=lambda x: x[1][0][1], reverse=False)

            result_dict[route_id] = {trip_id: [[stop_id, time_to_seconds(arrival_time)] for stop_id, arrival_time in trip_data] for trip_id, trip_data in sorted_trips}

        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stoptimes.json")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False) 
        
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
            from_stop: [[to, t] for to, t in zip(details["to_stop_id"], details["min_transfer_time"])]
            for from_stop, details in grouped
        }
        
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_{file_name}")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(footpath_dict, f, ensure_ascii=False)   

        
        return 1

    def build_stop_idx_in_route(self):

        if self.IN_QGIS:
            self.parent.setMessage('Building stop index by route...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        stoptimes_txt = pd.read_csv(
            f'{self.__path_gtfs}/stop_times.txt', sep=',', dtype={'stop_id': str, 'trip_id': str})

        stop_times_file = pd.merge(stoptimes_txt, self.__trips_file, on='trip_id')

        stop_times = stop_times_file

        # Группируем по route_id
        route_groups = stop_times.groupby('route_id')

        # Вложенный словарь:
        # { route_id: { stop_id: stop_sequence } }
        idx_by_route_stop = {}

        for route_id, group in route_groups:

            # сортируем по stop_sequence
            group_sorted = group.sort_values('stop_sequence')

            # создаём вложенный словарь
            idx_by_route_stop[route_id] = {
                stop_id: int(seq)
                for stop_id, seq in zip(
                    group_sorted['stop_id'],
                    group_sorted['stop_sequence']
                )
            }
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stop_idx_in_route.json")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(idx_by_route_stop, f, ensure_ascii=False)

        return idx_by_route_stop

    def build_reversed_stops_dict(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        for key in self.__stop_pkl.keys():
            self.__stop_pkl[key] = self.__reverse(self.__stop_pkl[key])

        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stops_rev.json")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(self.__stop_pkl, f, ensure_ascii=False)
    

    def __reverse(self, lst):
        new_lst = lst[::-1]
        return new_lst

    def build_reversed_stoptimes_dict(self):
        if self.IN_QGIS:
            self.parent.setMessage('Building database for to-accessibility...')
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

                # сортировка в обратном порядке
                trip_data = trip_data.sort_values('arrival_time', ascending=False)

                # создаём список списков, НЕ tuple
                trip_dict[trip_id] = [
                    [stop_id, time_to_seconds(arrival_time)]
                    for stop_id, arrival_time in zip(
                        trip_data['stop_id'], trip_data['arrival_time']
                    )
                ]

            # сортировка по времени первой остановки
            sorted_trips = sorted(
                trip_dict.items(),
                key=lambda x: x[1][0][1],
                reverse=True
            )

            # сохраняем только list, без tuple
            result_dict[route_id] = {
                trip_id: trip_data
                for trip_id, trip_data in sorted_trips
            }

        # сохраняем JSON
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stoptimes_rev.json")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False)

        return 1
       
    
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
            self.parent.setMessage('Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        # читаем reverse stop_times
        reverse_stoptimes_txt = pd.read_csv(
            f'{self.__path_gtfs}/rev_stop_times.txt',
            sep=',',
            dtype={'stop_id': str, 'trip_id': str}
        )

        if self.verify_break():
            return 0

        # объединяем с trips.txt
        rev_stop_times_file = pd.merge(
            reverse_stoptimes_txt,
            self.__trips_file,
            on='trip_id'
        )

        if self.verify_break():
            return 0

        # группируем по route_id
        route_groups = rev_stop_times_file.groupby('route_id')

        # вложенный словарь: route_id → stop_id → stop_sequence
        idx_by_route_stop = {}

        for route_id, group in route_groups:

            # сортируем по stop_sequence (уже обратный порядок)
            group_sorted = group.sort_values('stop_sequence')

            # создаём вложенный словарь
            idx_by_route_stop[route_id] = {
                stop_id: int(seq)
                for stop_id, seq in zip(
                    group_sorted['stop_id'],
                    group_sorted['stop_sequence']
                )
            }

        # сохраняем JSON
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_stop_idx_in_route_rev.json")

        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(idx_by_route_stop, f, ensure_ascii=False)

        return 1

    def build__route_by_stop(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        stops_by_route = self.__stop_times_file.drop_duplicates(subset=['route_id', 'stop_id'])[['stop_id', 'route_id']].groupby('stop_id')
        route_by_stop_dict = {id: list(routes.route_id)
                              for id, routes in stops_by_route}
        # add buildings
        for feature in self.layer_buildings.getFeatures():
            osm_id = feature[self.building_id_field]
            route_by_stop_dict[osm_id] = []
        f_json = os.path.join(self.__path_pkl, f"{self.prefix}_routes_by_stop.json")
        
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump(route_by_stop_dict, f, ensure_ascii=False)               
        return 1

    def verify_break(self):
        if self.IN_QGIS:  
            if self.parent.break_on:
                self.parent.setMessage("Building database is interrupted by user")
                if not self.already_display_break:
                    self.parent.textLog.append(f'<a><b><font color="red">Building database is interrupted by user</font> </b></a>')
                    self.already_display_break = True
                    if self.to_delete_gtfs:
                        if os.path.exists(self.__path_gtfs):
                            shutil.rmtree(self.__path_gtfs)
                self.parent.progressBar.setValue(0)
                return True
        return False
