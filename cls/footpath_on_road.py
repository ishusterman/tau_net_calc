import os
import csv
import geopandas as gpd
import networkx as nx
import pyproj

from datetime import datetime
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsPointXY
from scipy.spatial import KDTree
from qgis.core import QgsWkbTypes


class footpath_on_road:
    def __init__(self,
                 parent,
                 road_layer,
                 layer_origins,
                 path_to_protocol,
                 layer_origins_field):

        self.path_to_protocol = path_to_protocol
        self.road_layer = road_layer
        self.layer_origins = layer_origins

        self.layer_origins_field = layer_origins_field

        self.parent = parent
        self.count = 0
        self.already_display_break = False

        self.dict_feature_to_node = {}
        self.dict_building_to_node = {}
        self.dict_feature_min_dist_to_finishstop = {}
        self.node_pairs = []
        self.node_pairs_dict = {}
        self.node_pairs_dict_b_b = {}
        self.graph = nx.Graph()

    def create_stops_gpd(self):
        wgs84 = pyproj.CRS('EPSG:4326')  # WGS 84
        web_mercator = pyproj.CRS('EPSG:2039')  # Web Mercator
        transformer = pyproj.Transformer.from_crs(
            wgs84, web_mercator, always_xy=True)

        points = []
        
        filename = os.path.join(self.path_to_protocol, 'stops.txt')
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                stop_id = (row['stop_id'])
                latitude = float(row['stop_lat']) 
                longitude = float(row['stop_lon'])
                x_meter, y_meter = transformer.transform(longitude, latitude)
                qgs_point = QgsPointXY(x_meter, y_meter)
                points.append((stop_id, qgs_point))

        points_copy = gpd.GeoDataFrame(points, columns=['stop_id', 'geometry'])

        return points_copy

    def create_dict_node_to_feature(self):

        comment = 'vertex : {nearby stops, dist}'

        features = list(self.stops.itertuples(index=False))
        points = [(feature.geometry.x(), feature.geometry.y())
                  for feature in features]
        self.kd_tree_stops = KDTree(points)

        nearby_features = {node: [] for node in self.graph.nodes}

        for i, node in enumerate(self.graph_nodes_coords, start=1):
            if i % 10000 == 0:
                self.parent.setMessage(f'Building dictionary, node №{i} of {self.len_graph_nodes_coords}...')
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            distances, indices = self.kd_tree_stops.query(
                node, k=20, distance_upper_bound=400)
            filtered_indices_distances = [(int(index), distance) for index, distance in zip(
                indices, distances) if distance <= 400]
            
            nearest_features = [(features[index][0], distance)
                                for index, distance in filtered_indices_distances]

            nearby_features[node] = nearest_features

        return nearby_features

    def create_dict_feature_to_node(self, mode):

        if mode == 1:  # buildings to stops
            features = self.layer_origins.getFeatures()
            features_list = features
            count = self.layer_origins.featureCount()
            comment = '(building : {nearest vertex, dist})'

        if mode == 2:  # stops to stops
            features = self.stops.itertuples(index=False)
            features_list = list(features)
            count = len(features_list)
            comment = 'stop : {nearest vertex, dist}'
        
        for i, feature in enumerate(features_list):
        
            if i % 10000 == 0:
                self.parent.setMessage(f'Building dictionary {comment}, link №{i} of {count}...')
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            if mode == 1:
                geometry = feature.geometry()

                if geometry.type() == QgsWkbTypes.PointGeometry:
                    points = geometry.asPoint()
                elif geometry.type() == QgsWkbTypes.PolygonGeometry:
                    points = geometry.centroid().asPoint()

                pFeature = points
                source = feature[self.layer_origins_field]

            else:
                pFeature = feature.geometry
                source = feature.stop_id

            idVertex, dist = self.find_nearest_node(pFeature)

            self.dict_feature_to_node[source] = [(idVertex, dist)]

    def find_shortest_paths_b_b(self):

        if self.verify_break():
            return 0

        count = self.layer_origins.featureCount()
        self.parent.progressBar.setMaximum(count)
        self.parent.progressBar.setValue(1)

        for i, feature in enumerate(self.layer_origins.getFeatures()):
            QApplication.processEvents()
            
            if i % 100 == 0:
                self.parent.setMessage(f'Building dictionary, node №{i} of {count}...')
                self.parent.progressBar.setValue(i + 3)
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            self.source = feature[self.layer_origins_field]

            idStart, dist_start = self.dict_building_to_node.get(
                self.source)[0]  
            
            cutoff_value = 400

            lengths, _ = nx.single_source_dijkstra(self.graph,
                                                   idStart,
                                                   cutoff=cutoff_value,
                                                   weight='length'
                                                   )
            end_nodes_nearest = list(lengths.keys())

            for node in end_nodes_nearest:  # cicle of all founded node of graph
                # find many nearest buildings to coords node
                nearest_buiding = self.dict_node_buildings.get(node)
                distance = lengths[node]

                for b, dist_finish in nearest_buiding:  # cicle of all founded buildings nearest to node
                    if b == self.source:
                        continue
                    distance_all = dist_start + distance + dist_finish
                    if (distance_all <= 400):
                        key = (self.source, b)
                        existing_distance = self.node_pairs_dict_b_b.get(key)
                        if existing_distance is None or existing_distance > distance_all:
                            self.node_pairs_dict_b_b[key] = int(distance_all)

    def find_shortest_paths(self, mode):

        if self.verify_break():
            return 0

        if mode == 1:  # buildings to stops
            features = self.layer_origins.getFeatures()
        if mode == 2:  # stops to stops
            features = self.stops.itertuples(index=False)

        features_list = list(features)
        count = len(features_list)

        self.parent.progressBar.setMaximum(count)
        self.parent.progressBar.setValue(1)
        
        for i, feature in enumerate(features_list):
            QApplication.processEvents()
            if i % 1000 == 0:
                self.parent.setMessage(f'Building dictionary, node №{i} of {count}...')
                self.parent.progressBar.setValue(i + 3)
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            if mode == 1:
                self.source = feature[self.layer_origins_field]
            else:
                self.source = feature.stop_id

            idStart, dist_start = self.dict_feature_to_node.get(self.source)[0]

            # dist_val = self.dict_feature_min_dist_to_finishstop.get(self.source, 0)
            cutoff_value = 500 - dist_start  # - dist_val

            lengths, _ = nx.single_source_dijkstra(self.graph,
                                                   idStart,
                                                   cutoff=cutoff_value,
                                                   weight='length'
                                                   )
            end_nodes_nearest = list(lengths.keys())

            for node in end_nodes_nearest:  # cicle of all founded node of graph
                nearest_stops = self.dict_vertex_stops.get(
                    node)  # find one nearest stops to coords node
                distance = lengths[node]

                for b, dist_finish in nearest_stops:

                    if b == self.source:
                        continue
                    distance_all = dist_start + distance + dist_finish

                    if (distance_all <= 400):
                        key = (self.source, b)
                        existing_distance = self.node_pairs_dict.get(key)
                        if existing_distance is None or existing_distance > distance_all:
                            self.node_pairs_dict[key] = int(distance_all)

    def build_graph(self, roads):

        if len(self.graph.edges) > 0:
            return

        i = 0
        count = roads.featureCount()
        for feature in roads.getFeatures():
            i += 1
            if i % 10000 == 0:
                self.parent.setMessage(f'Building dictionary,  link №{i} of {count}...')
                QApplication.processEvents()
                if self.verify_break():
                    return 0
            line = feature.geometry().asPolyline()
            length = feature['length']

            start_point = (line[0].x(), line[0].y())
            end_point = (line[-1].x(), line[-1].y())

            self.graph.add_node(start_point)
            self.graph.add_node(end_point)
            self.graph.add_edge(start_point, end_point, length=length
                                )

        self.build_index_graph()

    def build_index_graph(self):
        self.nodes = list(self.graph.nodes)
        node_positions = [(x, y) for x, y in self.nodes]
        self.kd_tree = KDTree(node_positions)
        # create a list of node coordinates of the graph
        self.graph_nodes_coords = [(node[0], node[1])
                                   for node in self.graph.nodes]
        self.len_graph_nodes_coords = len(self.graph_nodes_coords)

    def find_nearest_node(self, geometry):

        nearest_point_coords = (geometry.x(), geometry.y())
        dist, nearest_node_idx = self.kd_tree.query(nearest_point_coords)
        nearest_node = self.nodes[nearest_node_idx]
        return nearest_node, dist

    def create_head_files(self):

        table_header = "from_stop_id,to_stop_id,min_transfer_time\n"
        self.f = os.path.join(self.path_to_protocol, 'footpath_road.txt')

        with open(self.f, 'w') as self.filetowrite:
            self.filetowrite.write(table_header)

    def create_head_files_b_b(self):

        table_header = "from_stop_id,to_stop_id,min_transfer_time\n"
        self.f_b_b = os.path.join(
            self.path_to_protocol, 'footpath_road_b_b.txt')

        with open(self.f_b_b, 'w') as self.filetowrite:
            self.filetowrite.write(table_header)

    # Creating dict {[buildings] : {building}} on base pre-preparing file with distance
    """
    def create_dict_b_b (self):
    
        self.dict_b_b = {}
        count_dict = 0
        with open(self.path_to_protocol+'footpath_AIR_b_b.txt', 'r') as file:
            reader = csv.reader(file)
            next(reader)

            for row in reader:
                from_osm_id, to_osm_id, dist = row
                
                count_dict = count_dict + 1
                if count_dict > 50000000:
                     break
                if count_dict%1000000 == 0:
                    QApplication.processEvents()
                    if self.verify_break():
                        return 0
                    #self.parent.setMessage(f'Preparing GTFS. Calc footpath on road. Making dictionary based on footpath_air_b_b pair №{count_dict}')
                if from_osm_id not in self.dict_b_b:
                        self.dict_b_b[from_osm_id] = []
                self.dict_b_b[from_osm_id].append((to_osm_id, dist))
    """
    # Creating dict {[buildings] : {stops}} on base pre-preparing file with distance
    """
    def create_dict_b_s (self):
    
        self.dict_b_s = {}
        count_dict = 0
        with open(self.path_to_protocol+'footpath_AIR.txt', 'r') as file:
            reader = csv.reader(file)
            
            next(reader)

            for row in reader:
                from_stop_id, to_stop_id, dist = row
                
                count_dict = count_dict + 1
                if count_dict%1000000 == 0:
                    QApplication.processEvents()
                    if self.verify_break():
                        return 0
                    #self.parent.setMessage(f'Preparing GTFS. Calc footpath on road. Making dictionary based on footpath_air pair №{count_dict}')
                if from_stop_id not in self.dict_b_s:
                        self.dict_b_s[from_stop_id] = []
                self.dict_b_s[from_stop_id].append((to_stop_id, dist))
    """

    def create_dict_building_to_node(self):

        features = self.layer_origins.getFeatures()
        count = self.layer_origins.featureCount()
        comment = 'building : {nearest vertex, dist}'

        for i, feature in enumerate(features):

            if i % 10000 == 0:
                self.parent.setMessage(f'Building dictionary {comment}, node №{i} of {count}...')
                QApplication.processEvents()
                if self.verify_break():
                    return 0

            geometry = feature.geometry()
            if geometry.type() == QgsWkbTypes.PointGeometry:
                points = geometry.asPoint()
            elif geometry.type() == QgsWkbTypes.PolygonGeometry:
                points = geometry.centroid().asPoint()
            pFeature = points
            
            source = feature[self.layer_origins_field]

            idVertex, dist = self.find_nearest_node(pFeature)
            self.dict_building_to_node[source] = [(idVertex, dist)]

    def create_dict_node_to_buildings(self):
        comment = 'vertex : {nearby buildings, dist}'
        features = list(self.layer_origins.getFeatures())
        
        points = []
        for feature in features:
            geometry = feature.geometry()
            if geometry.type() == QgsWkbTypes.PointGeometry:
                point = geometry.asPoint()
            elif geometry.type() == QgsWkbTypes.PolygonGeometry:
                point = geometry.centroid().asPoint()

            points.append((point.x(), point.y()))
        self.kd_tree_buildings = KDTree(points)

        nearby_features = {node: [] for node in self.graph.nodes}

        for i, node in enumerate(self.graph_nodes_coords, start=1):
            if i % 10000 == 0:
                self.parent.setMessage(f' Building dictionary, node №{i} of {self.len_graph_nodes_coords}...')
                QApplication.processEvents()

            distances, indices = self.kd_tree_buildings.query(
                node, k=1000, distance_upper_bound=400)
            filtered_indices_distances = [(int(index), distance) for index, distance in zip(
                indices, distances) if distance <= 400]
            nearest_features = [(features[index][self.layer_origins_field], distance)
                                for index, distance in filtered_indices_distances]
            nearby_features[node] = nearest_features

        return nearby_features

    def run_b_b(self):
        self.create_head_files_b_b()
        self.parent.textLog.append(f'<a>Starting calculating footpath building to building on road</a>')

        QApplication.processEvents()
        self.parent.setMessage(f'Building graph ...')
        self.build_graph(self.road_layer)
        QApplication.processEvents()
        if self.verify_break():
            return 0

        self.create_dict_building_to_node()
        if self.verify_break():
            return 0

        self.dict_node_buildings = self.create_dict_node_to_buildings()
        if self.verify_break():
            return 0

        self.find_shortest_paths_b_b()
        computation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Founded shortest path building to building on time {computation_time}</a>')

        self.node_pairs_b_b = [(source, stop, dist) for (
            source, stop), dist in self.node_pairs_dict_b_b.items()]

        count = 0
        with open(self.f_b_b, 'a') as file:
            if self.node_pairs_b_b:
                for id_source, id_destination, dist in self.node_pairs_b_b:
                    file.write(f'{id_source},{id_destination},{dist}\n')
                    count += 1
                    if count % 100000 == 0:
                        self.parent.setMessage(f'Storing walking paths {count}...')
                        QApplication.processEvents()

        self.parent.setMessage(f'Finished')
        QApplication.processEvents()

    def run(self):
        self.create_head_files()

        self.parent.setMessage('Loadings stops ...')
        QApplication.processEvents()
        self.stops = self.create_stops_gpd().authid()
        self.stops['stop_id'] = self.stops['stop_id'].astype(str)

        QApplication.processEvents()
        self.parent.setMessage(f'Building graph ...')
        self.build_graph(self.road_layer)
        QApplication.processEvents()
        if self.verify_break():
            return 0

        self.create_dict_feature_to_node(mode=1)
        self.create_dict_feature_to_node(mode=2)
        if self.verify_break():
            return 0
        self.dict_vertex_stops = self.create_dict_node_to_feature()
        if self.verify_break():
            return 0

        self.find_shortest_paths(mode=1)
        self.find_shortest_paths(mode=2)

        self.node_pairs = [(source, stop, dist) for (
            source, stop), dist in self.node_pairs_dict.items()]

        with open(self.f, 'a') as file:
            if self.node_pairs:
                for id_source, id_destination, dist in self.node_pairs:
                    file.write(f'{id_source},{id_destination},{dist}\n')
                    file.write(f'{id_destination},{id_source},{dist}\n')

        self.parent.setMessage(f'Finished')
        QApplication.processEvents()

    def verify_break(self):
        if self.parent.break_on:
            self.parent.setMessage("Interrupted (Network walking paths calculations)")
            if not self.already_display_break:
                self.parent.textLog.append(f'<a><b><font color="red">Interrupted (Network walking paths calculations)</font> </b></a>')
                self.already_display_break = True
            self.parent.progressBar.setValue(0)
            return True
        return False
