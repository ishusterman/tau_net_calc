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
                 mode_append=False, 
                 building_id_field = "osm_id"):
        
        if path_to_GTFS == '':
            self.__path_gtfs = path_to_pkl
        else:
            self.__path_gtfs = path_to_GTFS

        self.__path_pkl = path_to_pkl

        self.prefix = os.path.basename(self.__path_pkl)

        
        self.parent = parent
        self.layer_buildings = layer_buildings

        self.mode_append = mode_append

        self.__transfers_start_file1 = pd.read_csv(
            f'{self.__path_gtfs}/footpath_air.txt', sep=',', dtype={'from_stop_id': str, 'to_stop_id': str})
        self.__transfers_start_file2 = pd.read_csv(
            f'{self.__path_gtfs}/footpath_road_projection.txt', sep=',', dtype={'from_stop_id': str, 'to_stop_id': str})

        if not os.path.exists(self.__path_pkl):
            os.makedirs(self.__path_pkl)

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

        if not (self.mode_append):
            with open(f, "wb") as pickle_file:
                pickle.dump(stops_dict, pickle_file)
        else:
            with open(f, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)
            existing_data.update(stops_dict)
            with open(f, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

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
        if not (self.mode_append):
            with open(f, "wb") as pickle_file:
                pickle.dump(result_dict, pickle_file)
        else:
            with open(f, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)
            existing_data.update(result_dict)
            with open(f, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

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
        if not self.mode_append:
            with open(pickle_path, "wb") as pickle_file:
                pickle.dump(footpath_dict, pickle_file)
        else:
            with open(pickle_path, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)

            # Merging dictionaries
            for key, value in footpath_dict.items():
                existing_data.setdefault(key, []).extend(value)

            with open(pickle_path, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

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
        if not (self.mode_append):
            with open(f, "wb") as pickle_file:
                pickle.dump(idx_by_route_stop, pickle_file)
        else:
            with open(f, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)
            existing_data.update(idx_by_route_stop)
            with open(f, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

        return 1
    
    def build_rev_stop_idx_in_route(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building reversed index from file...')
            QApplication.processEvents()
        
        if self.verify_break():
            return 0

        # 1. Читаем файл. Так как route_id уже внутри, нам не нужен merge с trips!
        # Это экономит массу времени и памяти.
        f_input = os.path.join(self.__path_gtfs, "rev_stop_times.txt")
        
        # Читаем только нужные колонки, чтобы не забивать память
        df = pd.read_csv(
            f_input, 
            sep=',', 
            usecols=['route_id', 'stop_id', 'stop_sequence'],
            dtype={'stop_id': str, 'route_id': str, 'stop_sequence': int}
        )

        # 2. Формируем индекс. 
        # Нам нужно для каждой пары (маршрут, остановка) знать её порядковый номер.
        # drop_duplicates гарантирует, что мы не получим гигантский словарь, если данных много.
        temp_df = df.drop_duplicates(subset=['route_id', 'stop_id'])
        
        # Создаем словарь: {(route_id, stop_id): stop_sequence}
        idx_by_route_stop = dict(zip(
            zip(temp_df['route_id'], temp_df['stop_id']), 
            temp_df['stop_sequence']
        ))

        # 3. Сохранение в PKL
        f_output = os.path.join(self.__path_pkl, f"{self.prefix}_rev_idx_by_route_stop.pkl")
        
        if not self.mode_append:
            with open(f_output, "wb") as pickle_file:
                pickle.dump(idx_by_route_stop, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # Если режим добавления, сначала читаем старое
            if os.path.exists(f_output):
                with open(f_output, 'rb') as pickle_file:
                    existing_data = pickle.load(pickle_file)
                existing_data.update(idx_by_route_stop)
                with open(f_output, 'wb') as pickle_file:
                    pickle.dump(existing_data, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with open(f_output, "wb") as pickle_file:
                    pickle.dump(idx_by_route_stop, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)

        if self.IN_QGIS:
            QApplication.processEvents()
            
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
        if not (self.mode_append):
            with open(f, "wb") as pickle_file:
                pickle.dump(routesindx_by_stop_dict, pickle_file)
        else:
            with open(f, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)
            existing_data.update(routesindx_by_stop_dict)
            with open(f, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

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

        if not (self.mode_append):
            with open(f, "wb") as pickle_file:
                pickle.dump(self.__stop_pkl, pickle_file)
        else:
            with open(f, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)
            existing_data.update(self.__stop_pkl)
            with open(f, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

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
        if not (self.mode_append):
            with open(f, "wb") as pickle_file:
                pickle.dump(result_dict, pickle_file)
        else:
            with open(f, 'rb') as pickle_file:
                existing_data = pickle.load(pickle_file)
            existing_data.update(result_dict)
            with open(f, 'wb') as pickle_file:
                pickle.dump(existing_data, pickle_file)

    def build_reverse_stoptimes_file_txt(self):

        if self.IN_QGIS:
            self.parent.setMessage(f'Building database for to-accessibility...')
            QApplication.processEvents()
        if self.verify_break():
            return 0
        
        df = self.__stop_times_file.copy()
        
        # Умный разворот: считаем максимальную последовательность в каждом трипе
        # и вычитаем текущую. Это векторная операция.
        max_seq = df.groupby('trip_id')['stop_sequence'].transform('max')
        df['stop_sequence'] = max_seq - df['stop_sequence'] + 1
        
        df.to_csv(os.path.join(self.__path_gtfs, "rev_stop_times.txt"), index=False)
    
    def build__route_by_stop(self):
        if self.IN_QGIS:
            self.parent.setMessage(f'Building route by stop database...')
            QApplication.processEvents()
        if self.verify_break():
            return 0

        # 1. Сначала обрабатываем остановки из GTFS
        # Используем drop_duplicates для оптимизации
        stops_by_route = self.__stop_times_file.drop_duplicates(
            subset=['route_id', 'stop_id'])[['stop_id', 'route_id']].groupby('stop_id')
        
        route_by_stop_dict = {str(stop_id): list(routes.route_id)
                            for stop_id, routes in stops_by_route}
        
        # 2. Добавляем здания (Исправленная часть)
        if self.layer_buildings:
            # Получаем индекс поля по имени
            idx = self.layer_buildings.fields().indexOf(self.building_id_field)
            if idx != -1:
                # uniqueValues — самый быстрый способ получить все ID без дубликатов
                # Если вам нужны абсолютно все (даже дубликаты), используйте генератор ниже
                building_ids = self.layer_buildings.uniqueValues(idx)
                
                # Добавляем их в словарь с пустым списком маршрутов
                for b_id in building_ids:
                    if b_id is not None:
                        route_by_stop_dict[str(b_id)] = []
        
        # 3. Сохранение в PKL
        f = os.path.join(self.__path_pkl, f"{self.prefix}_routes_by_stop.pkl")
        
        with open(f, "wb") as pickle_file:
                pickle.dump(route_by_stop_dict, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)
        
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
