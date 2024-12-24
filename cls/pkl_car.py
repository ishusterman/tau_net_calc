import pickle
import os
import shutil
import math
from datetime import datetime
from scipy.spatial import KDTree

from PyQt5.QtWidgets import QApplication
from qgis.core import (QgsVectorLayer,
                       QgsFeature,
                       QgsWkbTypes,
                       QgsPointXY,
                       )

from PyQt5.QtCore import QVariant


from qgis.analysis import (
    QgsGraphBuilder,
    QgsVectorLayerDirector,
    QgsNetworkSpeedStrategy,
    QgsNetworkDistanceStrategy
)
from converter_layer import MultiLineStringToLineStringConverter
from common import getDateTime


class pkl_car ():

    def __init__(self, parent=""):
        self.parent = parent
        self.already_display_break = False

    def create_files(self):

        self.crs = self.parent.layer_road.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        QApplication.processEvents()

        self.parent.progressBar.setMaximum(8)
        self.parent.progressBar.setValue(0)
        

        self.parent.setMessage('Converting multilines into lines ...')
        self.converter = MultiLineStringToLineStringConverter(
            self.parent, self.parent.layer_road)
        self.layer_roads = self.converter.execute()

        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(1)
        QApplication.processEvents()

        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')
        source_path_road = os.path.join(
            config_path, "car_speed_by_link_type.csv")
        dest_path_road = os.path.join(
            self.parent.path_to_protocol, "car_speed_by_link_type.csv")

        shutil.copy(source_path_road, dest_path_road)

        source_path_factor_speed = os.path.join(config_path, "cdi_index.csv")
        dest_path_factor_speed = os.path.join(
            self.parent.path_to_protocol, "cdi_index.csv")
        shutil.copy(source_path_factor_speed, dest_path_factor_speed)

        if self.verify_break():
            return 0

        self.parent.progressBar.setValue(2)

        if self.parent.idx_field_direction != -1:

            valid_values = {"T", "F", "B"}

            field = self.layer_roads.fields().at(self.parent.idx_field_direction)
            for count, feature in enumerate(self.layer_roads.getFeatures()):

                if count % 50000 == 0:
                    if self.verify_break():
                        return 0
                    self.parent.setMessage(f'Checking layer of roads ...')
                    QApplication.processEvents()

                field_value = feature.attribute(
                    self.parent.idx_field_direction)
                if not (field_value in valid_values):
                    self.parent.textLog.append(
                        f'<a><b><font color="red"> WARNING: The field with direction value "{field.name()}" must use values ​​(T,F,B). The direction of movement field will not be included in the calculations</font> </b></a>')
                    self.idx_field_direction = -1
                    break

        field = self.layer_roads.fields().at(self.parent.idx_field_speed)
        field_type = field.type()

        if not (field_type in [QVariant.Int, QVariant.Double, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong]):
            self.parent.textLog.append(
                f'<a><b><font color="red"> WARNING: The field with speed value "{field.name()}" must be a digilal type. The speed of movement field will not be included in the calculations</font> </b></a>')
            self.parent.idx_field_speed = -1

        self.parent.progressBar.setValue(3)

        self.create_graph(mode=1)
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(4)
        self.create_graph(mode=2)
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(5)

        self.count_item = self.parent.layer_buildings.featureCount()
        self.buildings = self.create_list_buidings()

        self.create_spatial_index_graph()
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(6)
        self.create_dict_building_vertex()
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(7)
        self.create_dict_vertex_buildings()
        if self.verify_break():
            return 0

        self.converter.remove_temp_layer()
        self.parent.progressBar.setValue(8)
        QApplication.processEvents()

        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(
            f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.parent.textLog.toPlainText()
        postfix = getDateTime()
        filelog_name = f'{self.parent.path_to_protocol}//log_pkl_car_{postfix}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)

        self.parent.textLog.append(
            f'<a href="file:///{self.parent.path_to_protocol}" target="_blank" >pkl in folder</a>')
        self.parent.setMessage('Finished.')

    def create_spatial_index_graph(self):

        vertex_coords = []
        c = 0
        for i in range(self.graph.vertexCount()):
            c += 1

            if c % 1000 == 0:
                if self.verify_break():
                    return 0
                self.parent.setMessage('Building spatial index...')
                QApplication.processEvents()

            vertex_point = self.graph.vertex(i).point()
            vertex_coords.append([vertex_point.x(), vertex_point.y()])

        self.graph_vertex_index = KDTree(vertex_coords)

    def create_graph(self, mode):

        self.mode = mode
        self.layer_roads_mod = self.change_road_layer()
        if self.verify_break():
            return 0
        director = QgsVectorLayerDirector(self.layer_roads_mod,
                                          self.parent.idx_field_direction,
                                          '', '', '',
                                          QgsVectorLayerDirector.DirectionBoth
                                          )

        defaultValue = int(self.parent.speed)

        toMetricFactor = 1 / 3.6  # for speed km/h

        if self.parent.strategy_id == 1:
            strategy = QgsNetworkSpeedStrategy(self.parent.idx_field_speed,
                                               defaultValue,
                                               toMetricFactor
                                               )
        else:
            strategy = QgsNetworkDistanceStrategy()
        if self.verify_break():
            return 0
        director.addStrategy(strategy)
        if self.verify_break():
            return 0
        builder = QgsGraphBuilder(self.crs)
        QApplication.processEvents()
        comment = ""
        if self.mode == 2:
            comment = "backward "
        self.parent.setMessage(f'Constructing {comment}graph  ...')

        QApplication.processEvents()
        if self.verify_break():
            return 0
        director.makeGraph(builder, [])
        if self.verify_break():
            return 0
        self.graph = builder.graph()

        self.parent.setMessage(f'Saving {comment}graph...')
        QApplication.processEvents()
        file_path = os.path.join(self.parent.path_to_protocol, 'graph.pkl')
        if self.mode == 2:
            file_path = os.path.join(
                self.parent.path_to_protocol, 'graph_rev.pkl')
        self.save_graph(self.graph, file_path)

        return self.graph

    def save_graph(self, graph, file_path):

        graph_data = {
            'nodes': [(graph.vertex(i).point().x(), graph.vertex(i).point().y()) for i in range(graph.vertexCount())],
            'edges': []
        }

        c = 0
        for edge_id in range(graph.edgeCount()):
            c += 1
            if c % 10000 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()
            edge = graph.edge(edge_id)
            source_id = edge.fromVertex()
            target_id = edge.toVertex()
            cost = edge.cost(0)  # index 0 for the first value
            strategies = edge.strategies()
            graph_data['edges'].append(
                (source_id, target_id, cost, strategies))

        with open(file_path, 'wb') as f:
            pickle.dump(graph_data, f)

    def load_graph(self, mode, pathtopkl, crs):

        QApplication.processEvents()

        if mode == 1:
            graph_path = os.path.join(pathtopkl, 'graph.pkl')
        else:
            graph_path = os.path.join(pathtopkl, 'graph_rev.pkl')

        with open(graph_path, 'rb') as f:
            graph_data = pickle.load(f)

        builder = QgsGraphBuilder(crs)

        vertices = {}

        vertex_id = 0
        for point in graph_data['nodes']:
            qgs_point_xy = QgsPointXY(point[0], point[1])  
            # add a vertex with an identifier and a point
            builder.addVertex(vertex_id, qgs_point_xy)
            # save the correspondence between the vertex ID and the point
            vertices[vertex_id] = point
            vertex_id += 1  # increment the identifier for the next vertex

        for source_id, target_id, cost, strategies in graph_data['edges']:
            # get the coordinates of the vertices
            source_point = vertices[source_id]
            target_point = vertices[target_id]

            # convert coordinates to QgsPointXY
            source_qgs_point_xy = QgsPointXY(source_point[0], source_point[1])
            target_qgs_point_xy = QgsPointXY(target_point[0], target_point[1])

            # add an edge
            builder.addEdge(source_id, source_qgs_point_xy,
                            target_id, target_qgs_point_xy, [cost] + strategies)

        return builder.graph()

    def change_road_layer(self):
        comment = ""
        if self.mode == 2:
            comment = "backward "
        self.parent.setMessage(f'Modifying {comment}roads ...')
        QApplication.processEvents()
        features = self.layer_roads.getFeatures()
        new_features = []

        for count, feature in enumerate(features):

            if count % 50000 == 0:
                if self.verify_break():
                    return 0
                self.parent.setMessage(
                    f'Modifying {comment}roads (link №{count}) ... ')
                QApplication.processEvents()
            new_feature = QgsFeature(feature)

            if self.parent.idx_field_direction != -1:
                current_value = new_feature.attribute(
                    self.parent.idx_field_direction)

                new_value = 2

                if self.mode == 1:  # raptor
                    if current_value == "T":
                        new_value = 1
                    elif current_value == "F":
                        new_value = 0

                if self.mode == 2:  # backward raptor
                    if current_value == "T":
                        new_value = 0
                    elif current_value == "F":
                        new_value = 1

                new_feature.setAttribute(
                    self.parent.idx_field_direction, new_value)

            fclass_value = new_feature[self.parent.layer_road_type_road]
            speed_value = new_feature[self.parent.speed_fieldname]
            if speed_value == 0 or speed_value == "0":
                new_value = self.parent.type_road_speed_default.get(
                    fclass_value, int(self.parent.speed))
                new_feature.setAttribute(
                    self.parent.idx_field_speed, int(new_value))

            new_features.append(new_feature)

        # Create a new QgsVectorLayer from the modified features
        layer_fields = self.layer_roads.fields()
        layer_crs = self.crs  
        road_layer_mod = QgsVectorLayer(
            f'LineString?crs={layer_crs.authid()}', 'modified_road_layer', 'memory')
        road_layer_mod_data_provider = road_layer_mod.dataProvider()

        road_layer_mod_data_provider.addAttributes(layer_fields)
        road_layer_mod.updateFields()

        road_layer_mod.deleteFeatures([])

        (success, result) = road_layer_mod_data_provider.addFeatures(new_features)

        road_layer_mod.updateExtents()

        return road_layer_mod

    def load_files(self, pathtopkl):

        QApplication.processEvents()
        # load dict_building_vertex
        dict_building_vertex_path = os.path.join(
            pathtopkl, 'dict_building_vertex.pkl')
        with open(dict_building_vertex_path, 'rb') as f:
            dict_building_vertex = pickle.load(f)

        QApplication.processEvents()
        # load dict_vertex_buildings
        dict_vertex_buildings_path = os.path.join(
            pathtopkl, 'dict_vertex_buildings.pkl')
        with open(dict_vertex_buildings_path, 'rb') as f:
            dict_vertex_buildings = pickle.load(f)
        QApplication.processEvents()

        return dict_building_vertex, dict_vertex_buildings

    def converting_roads(self):
        self.converter = MultiLineStringToLineStringConverter(
            self.parent, self.parent.layer_road)
        layer_road = self.converter.execute()

        return layer_road

    def verify_break(self):
        if self.parent.break_on:
            self.parent.setMessage("Interrupted (Building CAR dictionary)")
            if not self.already_display_break:
                self.parent.textLog.append(
                    f'<a><b><font color="red">Interrupted (Building CAR dictionary)</font> </b></a>')
                self.already_display_break = True
            self.parent.progressBar.setValue(0)
            return True
        return False

    def convert_distance_to_meters(self, distance_in_degrees, latitude):
        # length of one degree of longitude at a given latitude in meters
        meters_per_degree_longitude = 111320 * math.cos(math.radians(latitude))
        # convert distance from degrees to meters
        return distance_in_degrees * meters_per_degree_longitude

    def create_dict_vertex_buildings(self):

        dict_vertex_nearest_buildings = {}

        for c, (id, point) in enumerate(self.buildings):

            if c % 1000 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()
                self.parent.setMessage(
                    f'Constructing dictionary №{c} of {self.count_item}...')
            building_id = id
            # create a circle with a radius of 250 meters around the building
            point_coords = [point.x(), point.y()]
            latitude = point.y()
            buffer_radius = 250
            distances, indices = self.graph_vertex_index.query(point_coords,
                                                               k=1000,
                                                               distance_upper_bound=buffer_radius)

            for index, distance in zip(indices, distances):
                if self.crs_grad:
                    distance = self.convert_distance_to_meters(
                        distance, latitude)
                if distance <= buffer_radius:  # check that the distance does not exceed the radius
                    nearest_vertex_id = index
                    if nearest_vertex_id in dict_vertex_nearest_buildings:
                        dict_vertex_nearest_buildings[nearest_vertex_id].append(
                            (building_id, round(distance)))
                    else:
                        # initialize the element as a list
                        dict_vertex_nearest_buildings[nearest_vertex_id] = [
                            (building_id, round(distance))]

        file_path = os.path.join(
            self.parent.path_to_protocol, 'dict_vertex_buildings.pkl')
        with open(file_path, 'wb') as f:
            pickle.dump(dict_vertex_nearest_buildings, f)

    def create_list_buidings(self):

        # get points from the building layer
        points = []

        for c, feature in enumerate(self.parent.layer_buildings.getFeatures()):

            if c % 50000 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()
                self.parent.setMessage(
                    f'Reading buildings item №{c} of {self.count_item}...')

            geom = feature.geometry()

            if geom.type() == QgsWkbTypes.PointGeometry:
                point = geom.asPoint()
            elif geom.type() == QgsWkbTypes.PolygonGeometry:
                point = geom.centroid().asPoint()
            points.append((
                          feature[self.parent.layer_buildings_field],
                          QgsPointXY(point.x(), point.y())
                          ))
        return points

    def create_dict_building_vertex(self):

        point_to_vertex_dict = {}
        for c, (id, point) in enumerate(self.buildings):

            if c % 50000 == 0:
                if self.verify_break():
                    return 0
                self.parent.setMessage(
                    f'Constructing dictionary №{c} of {self.count_item}...')
                QApplication.processEvents()

            point_coords = [point.x(), point.y()]
            latitude = point.y()
            distance, nearest_vertex_index = self.graph_vertex_index.query(
                point_coords, k=1)
            if self.crs_grad:
                distance = self.convert_distance_to_meters(distance, latitude)
            point_to_vertex_dict[int(id)] = (
                (nearest_vertex_index, round(distance)))

        file_path = os.path.join(
            self.parent.path_to_protocol, 'dict_building_vertex.pkl')
        with open(file_path, 'wb') as f:
            pickle.dump(point_to_vertex_dict, f)

        return point_to_vertex_dict
