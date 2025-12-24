import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from tau_net_calc.cls.generator import generator, config
from qgis.core import QgsApplication


QgsApplication.setPrefixPath("C:/Program Files/QGIS 3.40.2", True)
qgs = QgsApplication([], False)
qgs.initQgis()

path_to_result = r'c:\temp\test_generator'
os.makedirs(path_to_result, exist_ok=True)
ROUTES = [
    {
        'name': 'H1',
        'route': [41, 109, 93, 77, 17, 65, 5, 59, 0, 57, 1],
        'stops': [41, 93, 17, 5, 0, 1],
        'departures': None,
        'start_time': '08:00:00',
        'end_time': '08:15:00',
        'headway': '00:03:00',
        'speed': 5.0
    },

    {
        'name': 'V1',
        'route': [7, 60, 0, 58, 3, 63, 13, 73, 89, 105, 33],
        'stops': [7, 0, 3, 13, 89, 33],
        'departures': None,
        'start_time': '08:00:00',
        'end_time': '08:15:00',
        'headway': '00:03:00',
        'speed': 5.0
    },

    {
        'name': 'W1',
        'route': [7, 60, 0, 58,3, 63, 13, 73, 89, 105,33],
        'stops': [7, 0, 3, 13, 89, 33],
        'departures': None,
        'start_time': '08:00:00',
        'end_time': '08:18:00',
        'headway': '00:06:00',
        'speed': 6.0
    }
    ]

    

config_dict = {
    'config': {
        'Settings': {
            'Min_transfer': "0",
            'Max_transfer': "2",
            'MaxExtraTime': "10",
            'Speed': "3.6",
            'MaxWalkDist1': "150",
            'MaxWalkDist2': "150",
            'MaxWalkDist3': "150",
            'MaxTimeTravel': "10",
            'MaxWaitTime': "10",
            'MaxWaitTimeTransfer': "10",
            'TimeInterval': "5",
            'Layer': "RCity_Buildings",
            'Layer_field': "building_id",
            'LayerDest': "RCity_Buildings",
            'LayerDest_field': "building_id",
            'LayerViz': "",
            'LayerViz_field': "",
            'Field_ch': "",
            'RunOnAir': "False"
        }
    },
    'folder_name': path_to_result,
    'alias': 'output1'
     }

params = config(config_dict)
sources = [10000010]
    
mode_raptor = 1
time_start = "07:59:59"
protocol_type = 2 
timetable_mode = True

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rcity_path = os.path.join(base_dir, "rcity")
print(rcity_path)


gen = generator(
        path_nodes=os.path.join(rcity_path, "RCity_Nodes.geojson"),
        path_links=os.path.join(rcity_path, "RCity_Links.geojson"),
        path_buildings=os.path.join(rcity_path, "RCity_buildings_digital.geojson"),
        path_to_GTFS = os.path.join(path_to_result, 'GTFS'), 
        path_to_PKL = os.path.join(path_to_result, 'PKL'),
        route_definitions = ROUTES,
        max_walking_distance = 150,
        layer_building_field = "building_id",
        params = params
    )

gen.generate()
    
gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources
                          )
    
gen.create_layer_routes()

script_dir = os.path.dirname(os.path.abspath(__file__))
gen.compare_files (script_dir, params, "Test1 (schedule-based)")


timetable_mode = False
params.alias = "output2"
gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources)    

gen.compare_files (script_dir, params, "Test2 (fixed-time)")

sources = [10000008]
params.alias = "output3"
gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources)    
gen.compare_files (script_dir, params, "Test3 (fixed-time, origin too far from any stop)")


protocol_type = 1
sources = [10000010]
params.config['Settings']['TimeInterval'] = 5
params.config['Settings']['Field_ch'] = "building_id"
params.alias = "output4"
gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources)    
gen.compare_files (script_dir, params, "Test4 (fixed-time, Region maps, aggregate)", add_name = "_building_id")

protocol_type = 2
mode_raptor = 2
sources = [10000011]
params.alias = "output5"
time_start = "08:06:00"
gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources)    
gen.compare_files (script_dir, params, "Test5 (fixed-time, TO)")


sources = [10000010]
mode_raptor = 1
time_start = "07:59:59"
protocol_type = 2 
params.config['Settings']['MaxWaitTimeTransfer'] = "0"
params.alias = "output6"
gen.create_output(params, 
                      mode = mode_raptor, 
                      time = time_start, 
                      protocol_type = protocol_type, 
                      timetable_mode = timetable_mode, 
                      sources = sources)    
gen.compare_files (script_dir, params, "Test6 (fixed-time, Wait Time Transfer = 0)")


qgs.exitQgis()
print("Finish")