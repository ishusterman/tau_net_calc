import networkx as nx
import pickle
import os
import csv
import geopandas as gpd
import pyproj
import math

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsFeature,
    QgsSpatialIndex,
    QgsField,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsDistanceArea,
    QgsCoordinateTransformContext,
    )

from PyQt5.QtWidgets import QApplication

from PyQt5.QtCore import QMetaType

class cls_footpath_on_projection:
    def __init__(
        self,
        parent,
        MaxPath
    ):
        self.parent = parent

        self.already_display_break = False
        self.MaxPath = MaxPath

    def getMax_link_id (self):
        max_id = 0
        for f in self.cloned_layer.getFeatures():

            link_id = f.attribute('link_id')
            if link_id is not None:
                link_id = int(link_id)
            else:
                link_id = 0
            if link_id > max_id:
                max_id = link_id
        
        return int(max_id)

    def make_new_layer_with_projections(self,
                                        layer_roads,
                                        layer_buildings,
                                        layer_buildings_field_id,
                                        path_to_stops):

        self.layer_roads = layer_roads
        self.layer_buildings = layer_buildings

        self.crs = self.layer_buildings.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)

        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(
            self.crs, QgsCoordinateTransformContext())
        self.distance_area.setEllipsoid('WGS84') 

        self.layer_buildings_field_id = layer_buildings_field_id

        self.new_field_id = f'{layer_buildings_field_id}_add'

        if self.parent is not None:
            self.parent.setMessage(f'Making a copy of the layer of roads...')
            QApplication.processEvents()
        # create a new temporary layer based on the type of the source layer
        layer_type = self.layer_roads.wkbType()
        crs = self.layer_roads.crs().authid()
              
        self.cloned_layer = QgsVectorLayer(
            f"{QgsWkbTypes.displayString(layer_type)}?crs={crs}", "Layer with projections", "memory")

        self.provider = self.cloned_layer.dataProvider()

        # add fields from the source layer to the new layer
        self.provider.addAttributes(self.layer_roads.fields())
        self.cloned_layer.updateFields()

        
        count = self.layer_roads.featureCount()
        # transfer all features (geometry and attributes) from the source layer to the new layer
        for i, feature in enumerate(self.layer_roads.getFeatures()):
            if i % 10000 == 0:
                if self.parent is not None:
                    self.parent.setMessage(f'Making a copy of the layer of roads№ {i} of {count}...')
                    QApplication.processEvents()

                if self.verify_break():
                    return 0

            new_feature = QgsFeature()
            new_feature.setGeometry(feature.geometry())  # copy the geometry
            new_feature.setAttributes(
                feature.attributes())  # copy the attributes
            # add the feature to the new layer
            self.provider.addFeature(new_feature)

        # add new fields (if they don't already exist)
        
        if self.new_field_id not in [f.name() for f in self.provider.fields()]:
            self.provider.addAttributes([
                QgsField(self.new_field_id, QMetaType.QString),
               

                #QgsField("distance", QVariant.Double),
                QgsField(name="distance", type=QMetaType.Double),
                QgsField("type", QMetaType.QString, "", 1),

                QgsField(name="from_node", type=QMetaType.Int),
                QgsField(name="to_node", type=QMetaType.Int),
                QgsField(name="length", type=QMetaType.Int),
                QgsField(name="link_id", type=QMetaType.Int),
                
            ])
            self.cloned_layer.updateFields()  # update the fields of the cloned layer
        
        
        #QgsProject.instance().addMapLayer(self.cloned_layer)

        self.osm_id_index = self.provider.fields().indexOf(self.new_field_id)
        self.distance_index = self.provider.fields().indexOf("distance")
        self.type_index = self.provider.fields().indexOf("type")

        self.from_node_index = self.provider.fields().indexOf("from_node")
        self.to_node_index = self.provider.fields().indexOf("to_node")
        self.length_index = self.provider.fields().indexOf("length")
        self.link_id_index = self.provider.fields().indexOf("link_id")

        self.Max_link_id = self.getMax_link_id()

        if self.parent is not None:
            self.parent.setMessage(f'Building the index for the layer of roads...')
            QApplication.processEvents()
        # create a spatial index for the road layer
        self.index = QgsSpatialIndex(self.cloned_layer.getFeatures())

        
        self.stops = self.create_stops_gpd(path_to_stops)
        features = self.stops.itertuples(index=False)
        features_list = list(features)
        count = len(features_list)
        for i, feature in enumerate(features_list):
            if i % 5000 == 0:
                if self.parent is not None:
                    self.parent.setMessage(f'Projecting stops on links №{i} off {count}...')
                    QApplication.processEvents()
                if self.verify_break():
                    return 0
            pFeature = feature.geometry
            osm_id = feature.stop_id
            self.add_point_to_layer(pFeature, osm_id, type="s")

        
        count = self.layer_buildings.featureCount()
        # loop through all the polygons in the buildings layer
        for i, polygon_feat in enumerate(self.layer_buildings.getFeatures()):
            if i % 5000 == 0:
                if self.parent is not None:
                    self.parent.setMessage(f'Projecting buildings on links №{i} of {count}...')
                    QApplication.processEvents()
                if self.verify_break():
                    return 0
            polygon_geom = polygon_feat.geometry()
            osm_id = polygon_feat[self.layer_buildings_field_id]
            self.add_point_to_layer(
                polygon_geom.centroid().asPoint(), osm_id, type="b")
       
        self.cloned_layer.updateExtents()
        #QgsProject.instance().addMapLayer(self.cloned_layer)
        return self.cloned_layer

    def add_point_to_layer(self, polygon_geom, osm_id, type):

        # search for the nearest line using the index
        centroid_geom = QgsGeometry.fromPointXY(polygon_geom)
        # 10 is the number of nearest objects
        nearest_ids = self.index.nearestNeighbor(centroid_geom, 10)

        min_dist = float('inf')
        nearest_point = None
        closest_segment = None

        # check that nearest_ids contains at least one identifier
        for fid in nearest_ids:
            line_feat = self.cloned_layer.getFeature(fid)
            attributes = line_feat.attributes()
            line_geom = line_feat.geometry()

            # searching for the nearest point on the line
            dist, min_dist_point, next_vertex_index, left_or_right = line_geom.closestSegmentWithContext(
                polygon_geom)
            
            # if the distance is smaller than the minimum, we update the values
            if dist < min_dist:
                
                min_dist = dist
                nearest_point = min_dist_point  # nearest point on the line

                # get the indices of the vertices
                start_vertex_index = next_vertex_index - 1  # vertex before the nearest point
                end_vertex_index = next_vertex_index  # vertex after the nearest point

                # get the coordinates of the segment's ends
                start_vertex = line_geom.vertexAt(start_vertex_index)
                end_vertex = line_geom.vertexAt(end_vertex_index)
                
        # add two segments to the cloned layer
        if nearest_point:  

            line_geom = QgsGeometry.fromPolylineXY(
                [centroid_geom.asPoint(), nearest_point])
            
            len = self.distance_area.measureLength(line_geom)
            if not math.isnan(len):

                min_dist_meters = round (len)

                # create the first line from the nearest point to the start of the segment
                feat1 = QgsFeature()
                feat1.setGeometry(QgsGeometry.fromPolylineXY(
                    [nearest_point, QgsPointXY(start_vertex.x(), start_vertex.y())]))
                feat1.setAttributes(attributes)
                # setting the osm_id value
                feat1.setAttribute(self.osm_id_index, osm_id)
                # setting the distance value 
                feat1.setAttribute(self.distance_index, min_dist_meters)
                # setting the type value 
                feat1.setAttribute(self.type_index, type)

                geometry = feat1.geometry()
                length = round (geometry.length())
                feat1.setAttribute(self.length_index, length)

                self.Max_link_id = self.Max_link_id + 1
                feat1.setAttribute(self.link_id_index, self.Max_link_id)

                feat1.setAttribute(self.from_node_index, 999)

                self.provider.addFeature(feat1)

                # create the second line from the nearest point to the end of the segment
                feat2 = QgsFeature()
                feat2.setGeometry(QgsGeometry.fromPolylineXY(
                    [nearest_point, QgsPointXY(end_vertex.x(), end_vertex.y())]))
                feat2.setAttributes(attributes)
                # setting the osm_id value
                feat2.setAttribute(self.osm_id_index, osm_id)
                # setting the distance value 
                feat2.setAttribute(self.distance_index, min_dist_meters)
                # setting the type value
                feat2.setAttribute(self.type_index, type)

                geometry = feat2.geometry()
                length = round (geometry.length())
                feat2.setAttribute(self.length_index, length)

                self.Max_link_id = self.Max_link_id + 1
                feat2.setAttribute(self.link_id_index, self.Max_link_id)

                feat2.setAttribute(self.from_node_index, 999)

                self.provider.addFeature(feat2)

    def build_graph(self, roads, file_path):
        graph = nx.Graph()
        dict_osm_vertex = {}
        dict_vertex_osm = {}
        count = roads.featureCount()

        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(
            roads.crs(), QgsCoordinateTransformContext())
        distance_area.setEllipsoid('WGS84')

        for i, feature in enumerate(roads.getFeatures()):
            if i % 50000 == 0:
                if self.parent is not None:
                    self.parent.setMessage(f'Constructing road network graph №{i} of {count}...')
                    QApplication.processEvents()

                if self.verify_break():
                    return 0

            # get the geometry as a polyline
            line = feature.geometry().asPolyline()
            # calculate the length of the geometry (line)
            length_in_meters = distance_area.measureLength(feature.geometry())

            osm_id = feature[self.new_field_id]

            distance = feature['distance']
            type = feature['type']

            if distance is not None:
                distance = round(distance)

            start_point = (round(line[0].x(), 6), round(line[0].y(), 6))
            end_point = (round(line[-1].x(), 6), round(line[-1].y(), 6))

            if (osm_id is not None) and start_point not in dict_vertex_osm:
                dict_vertex_osm[start_point] = []

            if (osm_id is not None):
                dict_osm_vertex[osm_id] = ((start_point, distance))
                dict_vertex_osm[start_point].append((osm_id, distance, type))

            # if the link is a projection, we add the starting node
            if not (osm_id is None):
                graph.add_node(start_point)

            # if the link is not a projection, we add both nodes.
            if osm_id is None:
                graph.add_node(start_point)
                graph.add_node(end_point)

            # add an edge with the length attribute (weight).
            graph.add_edge(start_point, end_point, weight=length_in_meters)

        dict_path = os.path.join(file_path, 'dict_osm_vertex.pkl')
        with open(dict_path, 'wb') as f:
            pickle.dump(dict_osm_vertex, f)

        dict_path = os.path.join(file_path, 'dict_vertex_osm.pkl')
        with open(dict_path, 'wb') as f:
            pickle.dump(dict_vertex_osm, f)

        return graph

    def save_graph(self, graph, file_path):
        graph_path = os.path.join(file_path, 'graph_projection.pkl')
        graph_data = {
            'nodes': [
                (node, {
                    'pos': graph.nodes[node].get('pos', None),

                }) for node in graph.nodes
            ],
            'edges': [
                (source, target, {
                    'cost': data.get('weight', 0)
                }) for source, target, data in graph.edges(data=True)
            ]
        }

        with open(graph_path, 'wb') as f:
            pickle.dump(graph_data, f)

    def load_graph(self, file_path):
        if self.parent is not None:
            self.parent.setMessage(f'Loading road network graph...')
            QApplication.processEvents()
        # read the saved graph.
        graph_path = os.path.join(file_path, 'graph_projection.pkl')
        with open(graph_path, 'rb') as f:
            graph_data = pickle.load(f)

        # create a NetworkX graph and add nodes with attributes.
        nx_graph = nx.Graph()
        for node_id, node_data in graph_data['nodes']:
            # extract the node attributes: `pos`, `osm_id`, and `distance`.
            pos = node_data.get('pos', (0, 0))  # coordinates of the node.

            # add a node with its attributes.
            nx_graph.add_node(node_id, pos=pos)

        # add edges with weights.
        nx_graph.add_edges_from(
            (source_id, target_id, {'weight': attributes.get('cost', 0)})
            for source_id, target_id, attributes in graph_data['edges']
        )

        return nx_graph

    def load_dict_osm_vertex(self, file_path):
        if self.parent is not None:
            self.parent.setMessage(f'Loading database...')
            QApplication.processEvents()
        dict_path = os.path.join(file_path, 'dict_osm_vertex.pkl')
        with open(dict_path, 'rb') as f:
            osm_vertex = pickle.load(f)
        return osm_vertex

    def load_dict_vertex_osm(self, file_path):
        if self.parent is not None:
            self.parent.setMessage(f'Loading database...')
            QApplication.processEvents()
        dict_path = os.path.join(file_path, 'dict_vertex_osm.pkl')
        with open(dict_path, 'rb') as f:
            vertex_osm = pickle.load(f)
        return vertex_osm

    def construct_dict_transfers_projections(self,
                                             graph,
                                             dict_osm_vertex,
                                             dict_vertex_osm,
                                             layer_buildings,
                                             layer_buildings_field,
                                             path_to_file,
                                             path_to_stops,
                                             ):

        self.layer_buildings = layer_buildings
        path_to_file = os.path.join(
            path_to_file, 'footpath_road_projection.txt')
        with open(path_to_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            # column headers
            writer.writerow(
                ['from_stop_id', 'to_stop_id', 'min_transfer_time'])
            self.stops = self.create_stops_gpd(path_to_stops)
            features = self.stops.itertuples(index=False)
            features_list = list(features)
            count = len(features_list)
            for i, feature in enumerate(features_list):
                
                if i % 100 == 0:
                    if self.parent is not None:
                        self.parent.setMessage(f'Constructing walk routes between stops, stop №{i} of {count}...')
                        QApplication.processEvents()
                    if self.verify_break():
                        return 0

                from_osm_id = feature.stop_id
                dist_list = self.get_nearby_buildings(
                    from_osm_id, graph, dict_osm_vertex, dict_vertex_osm, mode="find_s") 

                # write building_id, building, and dist to the file
                for to_stop_id, dist in dist_list:
                    writer.writerow([from_osm_id, to_stop_id, dist])

            count = layer_buildings.featureCount()
            features = layer_buildings.getFeatures()

            for i, feature in enumerate(features):
            
                if i % 500 == 0:
                    if self.parent is not None:
                        self.parent.setMessage(f'Constructing walk routes between buildings and stops, building №{i} of {count}...')
                        QApplication.processEvents()
                    if self.verify_break():
                        return 0

                building_id = str(feature[layer_buildings_field])

                dist_list = self.get_nearby_buildings(
                    building_id, graph, dict_osm_vertex, dict_vertex_osm, mode="find_s")
                

                # write building_id, building, and dist to the file
                for to_stop_id, dist in dist_list:
                    writer.writerow([building_id, to_stop_id, dist])
                    writer.writerow([to_stop_id, building_id, dist])

    def get_nearby_buildings(self, building_id, graph, dict_osm_vertex, dict_vertex_osm, mode):

        dist = self.MaxPath

        dist_dict = {}
        vertex_id, dist_1 = dict_osm_vertex.get(building_id, ("xxx","xxx"))

        if vertex_id == "xxx":
            return dist_dict

        cutoff = dist - dist_1

        lengths, _ = nx.single_source_dijkstra(graph,
                                               vertex_id,
                                               cutoff=cutoff,
                                               weight='weight'
                                               )
        end_nodes_nearest = list(lengths.keys())

        for node in end_nodes_nearest:  # cicle of all founded node of graph

            list_osm = dict_vertex_osm.get(node)
                
            if list_osm is None:
                continue

            # optimize the mode check before the loop
            if mode == "find_b":
                list_osm = [x for x in list_osm if x[2] == "b"]
            elif mode == "find_s":
                list_osm = [x for x in list_osm if x[2] == "s"]

            if not list_osm:
                continue  # skip if the filtering removed all the elements

            for osm_id, dist_3, _ in list_osm:

                osm_id = osm_id

                if mode == "find_s":
                    if building_id == osm_id:
                        continue

                dist_2 = (lengths[node])
                res_dist = round(dist_1 + dist_2 + dist_3)

                if res_dist > dist:
                    continue

                if osm_id in dist_dict:
                    dist_dict[osm_id] = min(res_dist, dist_dict[osm_id])
                else:
                    dist_dict[osm_id] = res_dist

        # conversion to a list of tuples
        dist_list = [(building, dist) for building, dist in dist_dict.items()]

        return dist_list

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

    def create_stops_gpd(self, path_to_stops):
        wgs84 = pyproj.CRS('EPSG:4326')  # WGS 84
        crs_curr = self.layer_buildings.crs().authid()
        transformer = pyproj.Transformer.from_crs(
            wgs84, crs_curr, always_xy=True)

        points = []

        filename = os.path.join(path_to_stops, 'stops.txt')
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                stop_id = row['stop_id']
                latitude = float(row['stop_lat']) 
                longitude = float(row['stop_lon'])
                x_meter, y_meter = transformer.transform(longitude, latitude)
                qgs_point = QgsPointXY(x_meter, y_meter)
                points.append((stop_id, qgs_point))

        points_copy = gpd.GeoDataFrame(points, columns=['stop_id', 'geometry'])

        return points_copy