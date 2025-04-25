from GTFSGeneraror import GTFSGenerator
from qgis.core import QgsApplication


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
            'MaxTimeTravel': "30",
            'MaxWaitTime': "10",
            'MaxWaitTimeTransfer': "10",
            'TimeInterval': "1",
            'Layer': "RCity_Buildings",
            'Layer_field': "building_id",
            'LayerDest': "RCity_Buildings",
            'LayerDest_field': "building_id",
            'LayerViz': "",
            'LayerViz_field': "",
            'Field_ch': "",
            'RunOnAir': "True"
        }
    },
    'folder_name': r'c:\temp\5',
    'alias': 'output'
    }

params = config(config_dict)
sources = [1010]
    
mode_raptor = 1
time_start = "07:59:59"
protocol_type = 2 
timetable_mode = True

gen = GTFSGenerator(
        path_nodes=r'c:\doc\QGIS_prj\RCity\RCity_Nodes.geojson',
        path_links=r'c:\doc\QGIS_prj\RCity\RCity_Links.geojson',
        path_buildings=r'c:\doc\QGIS_prj\RCity\RCity_buildings_digital.geojson',
        path_to_GTFS = r'c:\temp\5\GTFS',
        path_to_PKL = r'c:\temp\5\PKL',
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
                      sources = sources)
    
gen.create_layer_routes()

qgs.exitQgis()
print("Finish")