import os
import datetime as dt
import zipfile
import numpy as np
import shutil
import transitfeed
import geopandas as gpd

from pyproj import Transformer
from PKL import PKL
from GTFS import GTFS
from query_file import myload_all_dict, runRaptorWithProtocol
from common import time_to_seconds

from qgis.core import QgsApplication, QgsVectorLayer, QgsProject
from types import SimpleNamespace




class GTFSGenerator:
    def __init__(self,
                 path_nodes,
                 path_links,
                 path_buildings,
                 
                 path_to_GTFS = r'c:\temp\1\GTFS',
                 path_to_PKL = r'c:\temp\1\PKL',
                 route_definitions=None,
                 max_walking_distance = 150,
                 layer_building_field = "building_id"):

        

        self.path_to_GTFS = path_to_GTFS
        os.makedirs(self.path_to_GTFS, exist_ok=True)
        self.path_to_PKL = path_to_PKL
        os.makedirs(self.path_to_PKL, exist_ok=True)

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
        
        self.layer_buildings = QgsVectorLayer(self.path_buildings, "RCity_Nodes", "ogr")
        QgsProject.instance().addMapLayer(self.layer_buildings)

        self.n_coords = {
            n: (x, y) for (n, x, y) in self.r_nodes[['node_id', 'x', 'y']].to_records(index=False)
        }
        self.l_length = {
            (i, j): d for (_, i, j, d) in self.r_links[['link_id', 'from_node', 'to_node', 'length']].to_records(index=False)
        }
        self.l_length.update({
            (j, i): d for (_, i, j, d) in self.r_links[['link_id', 'from_node', 'to_node', 'length']].to_records(index=False)
        })

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
                r_departures = range(t_start, t_end, r_hdw)
            else:
                r_departures = [self.timestr2sec(t) for t in r['departures']]

            r_profile = {r['stops'][0]: 0.0}
            dist = 0.0
            for k, n in enumerate(r['route'][1:]):
                dist += self.l_length[r['route'][k], n]
                if n in r['stops']:
                    r_profile[n] = dist / r['speed']

            for s in r['stops']:
                lng, lat = self.transformer.transform(*self.n_coords[s])
                gtfs_stop = schedule.AddStop(lng=lng, lat=lat, name=str(s), stop_id=str(s))
                gtfs_stops[s] = gtfs_stop
                stop_id_idx += 1

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
            pkl_path = "",
            layer_origins = self.layer_buildings,
            layer_road = "",
            layer_origins_field = self.layer_building_field,
            MaxPathRoad = str(self.max_walking_distance),
            MaxPathAir= str(self.max_walking_distance)
        )
        calc_GTFS.create_footpath_AIR()
        src = os.path.join(self.path_to_GTFS, 'footpath_AIR.txt')
        dst = os.path.join(self.path_to_GTFS, 'footpath_road_projection.txt')
        shutil.copy(src, dst)

        calc_PKL = PKL(
            None,
            path_to_pkl = self.path_to_PKL,
            path_to_GTFS = self.path_to_GTFS,
            layer_buildings = self.layer_buildings,
            mode_append = False,
            building_id_field = self.layer_building_field
        )
        calc_PKL.create_files()

    def create_output (self, var, mode, time, protocol_type, timetable_mode, sources):

        dictionary, dictionary2 = myload_all_dict(
                        self = None,
                        PathToNetwork = self.path_to_PKL,
                        mode = mode,
                        RunOnAir = True,

                        layer_origin = self.layer_buildings,
                        layer_dest = self.layer_buildings,
                        MaxWalkDist1 = 150,
                        layer_dest_field = self.layer_building_field,
                        Speed = 1
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
                                  dictionary2 = dictionary2,
                                  shift_mode = True
                                  )
        

       

if __name__ == "__main__":

    QgsApplication.setPrefixPath("C:/Program Files/QGIS 3.40.2", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    class config:
        def __init__(self, config_dict):
            self.config = config_dict['config']
            self.folder_name = config_dict['folder_name']
            self.alias = config_dict['alias']


    ROUTES = [
    {
        'name': 'R1',
        'route': [41, 109, 93, 77, 17, 65, 5, 59, 0, 58, 3, 63, 13, 73, 89, 105, 33],
        'stops': [41, 93, 17, 5, 0, 3, 13, 89, 33],
        'departures': None,
        'start_time': '08:00:00',
        'end_time': '08:30:00',
        'headway': '00:05:00',
        'speed': 5.0
    }
    ]

    

    config_dict = {
    'config': {
        'Settings': {
            'Min_transfer': "0",
            'Max_transfer': "2",
            'MaxExtraTime': "0",
            'Speed': "3.6",
            'MaxWalkDist1': "150",
            'MaxWalkDist2': "150",
            'MaxWalkDist3': "150",
            'MaxTimeTravel': "20",
            'MaxWaitTime': "10",
            'MaxWaitTimeTransfer': "10",
            'TimeInterval': "1",
            'Layer': "RCity_Nodes",
            'Layer_field': "building_id",
            'LayerDest': "RCity_Nodes",
            'LayerDest_field': "building_id",
            'LayerViz': "",
            'LayerViz_field': "",
            'Field_ch': "",
            'RunOnAir': "True"
        }
    },
    'folder_name': r'c:\temp\1',
    'alias': 'output'
    }

    params = config(config_dict)
    sources = ['B1', 'B2']
    
    mode_raptor = 1
    time_start = "8:00:00"
    protocol_type = 2 
    timetable_mode = False

    gen = GTFSGenerator(
        path_nodes=r'c:\doc\QGIS_prj\RCity\RCity_Nodes.geojson',
        path_links=r'c:\doc\QGIS_prj\RCity\RCity_Links.geojson',
        path_buildings=r'c:\doc\QGIS_prj\RCity\RCity_Buildings.geojson',
        path_to_GTFS = r'c:\temp\1\GTFS',
        path_to_PKL = r'c:\temp\1\PKL',
        route_definitions = ROUTES,
        max_walking_distance = 150,
        layer_building_field = "building_id"
    )

    gen.generate()
    
    gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources)

    qgs.exitQgis()
    print("Finish")
