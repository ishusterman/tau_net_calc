import os
import datetime as dt
import zipfile
import numpy as np
import shutil
import transitfeed
import geopandas as gpd
import pandas as pd
from types import SimpleNamespace

from pyproj import Transformer
from PKL import PKL
from GTFS import GTFS
from query_file import myload_all_dict, runRaptorWithProtocol
from common import time_to_seconds

from qgis.core import QgsApplication, QgsVectorLayer, QgsProject
from shapely.geometry import LineString

class config:
        def __init__(self, config_dict):
            self.config = config_dict['config']
            self.folder_name = config_dict['folder_name']
            self.alias = config_dict['alias']


class generator:
    def __init__(self,
                 path_nodes,
                 path_links,
                 path_buildings,
                 
                 path_to_GTFS,
                 path_to_PKL,
                 params,
                 route_definitions=None,
                 max_walking_distance = 150,
                 layer_building_field = "building_id"):

        

        self.path_to_GTFS = path_to_GTFS
        os.makedirs(self.path_to_GTFS, exist_ok=True)
        self.path_to_PKL = path_to_PKL
        os.makedirs(self.path_to_PKL, exist_ok=True)
        self.params = params

        self.path_nodes = path_nodes
        self.path_links = path_links
        self.path_buildings = path_buildings
        
        self.route_definitions = route_definitions or []
        self.max_walking_distance = max_walking_distance
        self.layer_building_field = layer_building_field

        self.transformer = Transformer.from_crs('EPSG:2039', 'EPSG:4326', always_xy=True)

        self.r_nodes = gpd.read_file(self.path_nodes)
        self.r_links = gpd.read_file(self.path_links)
        self.r_buildings = gpd.read_file(self.path_buildings)
        
        self.layer_buildings = QgsVectorLayer(self.path_buildings, "RCity_Buildings", "ogr")
        QgsProject.instance().addMapLayer(self.layer_buildings)

        self.layer_roads = QgsVectorLayer(self.path_links, "RCity_Roads", "ogr")
        QgsProject.instance().addMapLayer(self.layer_roads)

        self.n_coords = {
            n: (x, y) for (n, x, y) in self.r_nodes[['node_id', 'x', 'y']].to_records(index=False)
        }
        self.l_length = {
            (i, j): d for (_, i, j, d) in self.r_links[['link_id', 'from_node', 'to_node', 'length']].to_records(index=False)
        }
        self.l_length.update({
            (j, i): d for (_, i, j, d) in self.r_links[['link_id', 'from_node', 'to_node', 'length']].to_records(index=False)
        })

    def create_layer_routes(self):
        # Читаем узлы
        nodes_gdf = self.r_nodes
        nodes_gdf['node_id'] = nodes_gdf['node_id'].astype(int)

        # Создаём пустые GeoDataFrame
        all_routes = gpd.GeoDataFrame(columns=['name', 'FCLASS', 'ONEWAY', 'maxspeed', 'geometry'], crs=nodes_gdf.crs)
        all_stops = gpd.GeoDataFrame(columns=['node_id', 'route_name', 'stop_sequence', 'geometry'], crs=nodes_gdf.crs)

        for route_info in self.route_definitions:
            name = route_info['name']
            route_ids = route_info['route']
            stops_ids = route_info['stops']

            # --- Маршрут как линия ---
            route_points = nodes_gdf[nodes_gdf['node_id'].isin(route_ids)]
            route_points_sorted = route_points.set_index('node_id').loc[route_ids]
            route_line = LineString(route_points_sorted.geometry.tolist())

            
            route_gdf = gpd.GeoDataFrame({
                'name': [name],
                'FCLASS': [None],      
                'ONEWAY': ['B'],       
                'maxspeed': [None],    
                'geometry': [route_line]
                }, crs=nodes_gdf.crs)

            all_routes = pd.concat([all_routes, route_gdf], ignore_index=True)

            # --- Остановки как точки ---
            stops_gdf = nodes_gdf[nodes_gdf['node_id'].isin(stops_ids)].copy()
            stops_gdf['route_name'] = name

            # Добавляем stop_sequence в порядке следования
            stop_sequence_df = pd.DataFrame({
                'node_id': stops_ids,
                'stop_sequence': range(1, len(stops_ids)+1)
            })

            # Объединяем с геометрией
            stops_gdf = stops_gdf.merge(stop_sequence_df, on='node_id')
            stops_gdf = stops_gdf[['node_id', 'route_name', 'stop_sequence', 'geometry']]

            all_stops = pd.concat([all_stops, stops_gdf], ignore_index=True)

        # --- Сохраняем итоговые файлы ---
        routes_filename = os.path.join(self.params.folder_name, 'routes.geojson')
        stops_filename = os.path.join(self.params.folder_name, 'stops.geojson')

        all_routes.to_file(routes_filename, driver='GeoJSON')
        all_stops.to_file(stops_filename, driver='GeoJSON')




    def dict_to_namespace(self, d):
        if isinstance(d, dict):
            return SimpleNamespace(**{k: self.dict_to_namespace(v) for k, v in d.items()})
        return d            

    def timestr2sec(self, time_string):
        try:
            pt = dt.datetime.strptime(time_string, '%H:%M:%S')
            return pt.second + pt.minute * 60 + pt.hour * 3600
        except ValueError:
            parts = time_string.split(':')
            if len(parts) != 3:
                return np.NaN
            hh, mm, ss = map(int, parts)
            return ss + mm * 60 + hh * 3600

    def sec2timestring(self, seconds):
        h = seconds // 3600
        seconds %= 3600
        m = seconds // 60
        s = seconds % 60
        return '{:02}:{:02}:{:02}'.format(int(h), int(m), int(s))

    def generate(self):
        schedule = transitfeed.Schedule()
        agency = schedule.AddAgency(
            "My Little Pony Express",
            "https://www.mylittlepony.co.il",
            "Israel/Tel Aviv"
        )
        schedule.SetDefaultAgency(agency)

        service_period = schedule.GetDefaultServicePeriod()
        service_period.SetWeekdayService(True)
        service_period.SetDateHasService(dt.datetime.now().strftime("%Y%m%d"))

        gtfs_stops = {}
        START_INDEX = 1
        stop_id_idx = START_INDEX

        for idx, r in enumerate(self.route_definitions):
            r_name = r['name']
            r_departures = []

            if r['departures'] is None:
                t_start = self.timestr2sec(r['start_time'])
                t_end = self.timestr2sec(r['end_time'])
                r_hdw = self.timestr2sec(r['headway'])
                r_departures = range(t_start, t_end + 1, r_hdw)
            else:
                r_departures = [self.timestr2sec(t) for t in r['departures']]
            
            r_profile = {r['stops'][0]: 0.0}
            dist = 0.0
            for k, n in enumerate(r['route'][1:]):
                dist += self.l_length[r['route'][k], n]
                if n in r['stops']:
                    r_profile[n] = dist / r['speed']

            """
            for s in r['stops']:
                lng, lat = self.transformer.transform(*self.n_coords[s])
                gtfs_stop = schedule.AddStop(lng=lng, lat=lat, name=str(s), stop_id=str(s))
                gtfs_stops[s] = gtfs_stop
                stop_id_idx += 1
            """    

            for s in r['stops']:
                if s not in gtfs_stops:
                    lng, lat = self.transformer.transform(*self.n_coords[s])
                    gtfs_stop = schedule.AddStop(lng=lng, lat=lat, name=str(s), stop_id=str(s))
                    gtfs_stops[s] = gtfs_stop    

            route = schedule.AddRoute(short_name=r_name, long_name='', route_id=START_INDEX + idx, route_type=0)
            for dep_start in r_departures:
                
                route_trip = route.AddTrip(schedule, headsign=r_name + '_' + self.sec2timestring(dep_start))
                for stop_id in r['stops']:
                    tt = r_profile[stop_id]
                    stop_time_s = self.sec2timestring(dep_start + tt)
                    route_trip.AddStopTime(gtfs_stops[stop_id], stop_time=stop_time_s)

        self.gtfs_schedule_path = os.path.join(self.path_to_GTFS, "GTFS.zip")
        schedule.WriteGoogleTransitFeed(self.gtfs_schedule_path)
        with zipfile.ZipFile(self.gtfs_schedule_path, 'r') as zip_ref:
            zip_ref.extractall(self.path_to_GTFS)
        if os.path.exists(self.gtfs_schedule_path):
            os.remove(self.gtfs_schedule_path)

        self.postprocess_gtfs()

    def postprocess_gtfs(self):
        
        calc_GTFS = GTFS(
            parent = None,
            path_to_file = self.path_to_GTFS,
            path_to_GTFS = self.path_to_GTFS,
            pkl_path = self.path_to_PKL,
            layer_origins = self.layer_buildings,
            layer_road = self.layer_roads,
            layer_origins_field = self.layer_building_field,
            MaxPathRoad = str(self.max_walking_distance),
            MaxPathAir= str(self.max_walking_distance)
        )
        calc_GTFS.create_footpath_AIR()
        filename = os.path.join(self.params.folder_name, 'layer_with_projection.geojson')
        calc_GTFS.create_footpath_on_graph(need_save_layer_with_projection = True, 
                                           filename = filename)
        
        calc_PKL = PKL(
            None,
            path_to_pkl = self.path_to_PKL,
            path_to_GTFS = self.path_to_GTFS,
            layer_buildings = self.layer_buildings,
            building_id_field = self.layer_building_field
        )
        calc_PKL.create_files()

    def create_output (self, var, mode, time, protocol_type, timetable_mode, sources,
                       ):

        dictionary  = myload_all_dict(
                        self = None,
                        PathToNetwork = self.path_to_PKL,
                        mode = mode,
                        RunOnAir = (var.config['Settings']['RunOnAir'] == "True"),
                        )
        
        D_TIME = time_to_seconds(time)
        runRaptorWithProtocol(self = var,
                                  sources = sources,
                                  raptor_mode = mode,
                                  protocol_type = protocol_type,
                                  timetable_mode = timetable_mode,
                                  D_TIME = D_TIME,
                                  selected_only1 = False,
                                  selected_only2 = False,
                                  dictionary = dictionary,
                                  shift_mode = True,
                                  layer_dest_obj = self.layer_buildings,
                                  layer_origin_obj = self.layer_buildings,
                                  path_to_pkl = self.path_to_PKL
                                  )
    
    def compare_files(self, script_dir, params, test_name, add_name=""):
        expected_result = os.path.join(script_dir, f'{params.alias}{add_name}_min_duration_expected.csv')
        result = os.path.join(params.folder_name, f"{params.alias}{add_name}_min_duration.csv")

        # Читаем файлы как данные без заголовков
        df1 = pd.read_csv(result, header=0)  # header=0 означает, что первая строка - это заголовок
        df2 = pd.read_csv(expected_result, header=0)
        
        # Берем только данные (игнорируем заголовки для сравнения)
        df1_data = df1.values
        df2_data = df2.values
        
        # Сортируем данные по всем столбцам
        df1_sorted = pd.DataFrame(df1_data).sort_values(by=list(range(len(df1_data[0])))).reset_index(drop=True)
        df2_sorted = pd.DataFrame(df2_data).sort_values(by=list(range(len(df2_data[0])))).reset_index(drop=True)
        
        try:
            pd.testing.assert_frame_equal(df1_sorted, df2_sorted, check_dtype=False, check_names=False)
            print(f"✅ {test_name} - OK")
        except AssertionError as e:
            print(f"❌ {test_name} - error")
            print(e)