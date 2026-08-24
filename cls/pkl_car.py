import json
import os
import shutil
import math
from datetime import datetime
from scipy.spatial import KDTree

from qgis.PyQt.QtWidgets import QApplication
from qgis.core import (QgsVectorLayer,
                       QgsFeature,
                       QgsWkbTypes,
                       QgsPointXY                       
                       )

from qgis.analysis import (
    QgsGraphBuilder,
    QgsVectorLayerDirector,
    QgsNetworkSpeedStrategy,
    QgsNetworkDistanceStrategy
)

from converter_layer import MultiLineStringToLineStringConverter
from footpath_on_projection import cls_footpath_on_projection
from common import (getDateTime, 
                    convert_distance_to_meters, 
                    get_existing_path,
                    transform_log_to_csv_text,
                    FIELD_ID)


class pkl_car ():

    def __init__(self, parent=""):
        self.parent = parent
        self.already_display_break = False
        ########### experiment !!!!!!
        #if parent != "":
        #    self.parent.idx_field_speed = 26
        

    def create_files(self):

        self.crs = self.parent.layer_road.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)


        #############################################
        

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        QApplication.processEvents()

        self.parent.progressBar.setMaximum(10)
        self.parent.progressBar.setValue(0)
        
        if self.verify_break():
            return 0
        
        ###
        # experiment
        
        self.parent.setMessage('Converting multilines into lines ...')
        self.converter = MultiLineStringToLineStringConverter( self.parent, self.parent.layer_road)
        self.layer_roads = self.converter.execute()
        #self.layer_roads = self.parent.layer_road
        ###
        # experiment

        if self.verify_break():
            return 0

        removed = self.remove_features_with_value(self.layer_roads, self.parent.idx_field_direction, "N")
        #print(f"Removed {removed} features with value 'N'")

        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(1)
        QApplication.processEvents()

        prefix = os.path.basename(self.parent.path_to_protocol)

        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')
        source_path_road = os.path.join(config_path, "car_speed_by_link_type.csv")
        dest_path_road = os.path.join(self.parent.path_to_protocol, f"{prefix}_car_speed_by_link_type.csv")

        shutil.copy(source_path_road, dest_path_road)

        source_path_factor_speed = os.path.join(config_path, "cdi_index.csv")
        dest_path_factor_speed = os.path.join(
            self.parent.path_to_protocol, f"{prefix}_cdi_index.csv")
        shutil.copy(source_path_factor_speed, dest_path_factor_speed)

        if self.verify_break():
            return 0

        self.parent.progressBar.setValue(2)

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
        self.converter.remove_temp_layer()        
        QApplication.processEvents()


        #############################
        # 2. Строим словарь координата → ID вершины QGIS-графа
        coord_to_vertex_id = self.build_coord_to_vertex_id(self.graph)

        # 3. Создаём слой с проекциями
        footpath_on_projection_car = cls_footpath_on_projection(self.parent, MaxPath=400)
        new_layer, _ = footpath_on_projection_car.make_new_layer_with_projections(
            layer_roads=self.layer_roads,
            layer_buildings=self.parent.layer_buildings,
            layer_buildings_field_id=FIELD_ID,
            path_to_stops="",
            file_name_gpkg=""
        )

        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(6)

        graph_origin = footpath_on_projection_car.build_graph_original(self.layer_roads)
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(7)
        graph, dict_osm_vertex, dict_vertex_osm = footpath_on_projection_car.build_graph(new_layer)
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(8)

        # 6. Расчёт расстояний
        
        footpath_on_projection_car.construct_dict_near_buildings_stream_json(
            graph_origin,
            graph,
            dict_vertex_osm,
            coord_to_vertex_id,
            self.get_full_filename("dict_vertex_buildings.json")
        )

        #self.save_pkl (dict_vertex_buildings,"dict_vertex_buildings.json")
        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(9)

        dict_building_vertex = footpath_on_projection_car.construct_dict_nearest_origin_vertex_for_buildings(
            graph_origin,
            graph,
            dict_osm_vertex,
            coord_to_vertex_id            
        )
        
        self.save_pkl (dict_building_vertex, "dict_building_vertex.json")

        if self.verify_break():
            return 0
        self.parent.progressBar.setValue(10)

        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

        text = transform_log_to_csv_text(self.parent.textLog.toPlainText())
        postfix = getDateTime()
        filelog_name = f'{self.parent.path_to_protocol}//log_json_car_{postfix}.csv'
        with open(filelog_name, "w") as file:
            file.write(text)

        self.parent.textLog.append(f'<a href="file:///{self.parent.path_to_protocol}" target="_blank" >database in folder</a>')
        self.parent.setMessage('Finished.')

    def remove_features_with_value(self, layer, field_index, target_value) -> int:
        """
        Removes features from the given layer where the value at field_index equals target_value.

        :param layer: QgsVectorLayer from which to remove features
        :param field_index: Index of the field to check
        :param target_value: Value to compare (e.g., 'N')
        :return: Number of removed features
        """
        if not layer.isEditable():
            layer.startEditing()

        field_name = layer.fields().field(field_index).name()
        
        ids_to_delete = [
            f.id()
            for f in layer.getFeatures()
            if str(f[field_name]) == target_value
        ]

        layer.deleteFeatures(ids_to_delete)
        layer.commitChanges()

        return len(ids_to_delete)
    

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

        """
        if self.parent.default_direction == "B":
            direction = QgsVectorLayerDirector.DirectionBoth
        if self.mode == 1:
            if self.parent.default_direction == "T":
                direction = QgsVectorLayerDirector.DirectionForward
            if self.parent.default_direction == "F":
                direction = QgsVectorLayerDirector.DirectionBackward
        else:
            if self.parent.default_direction == "T":
                direction = QgsVectorLayerDirector.DirectionBackward
            if self.parent.default_direction == "F":
                direction = QgsVectorLayerDirector.DirectionForward
        """

        direction = QgsVectorLayerDirector.Direction.DirectionBoth

        
        director = QgsVectorLayerDirector(self.layer_roads_mod,
                                          self.parent.idx_field_direction,
                                          "T", "F", "B", direction
                                          )

        defaultValue = int(self.parent.speed)

        toMetricFactor = 1 / 3.6  # for speed km/h

        #if self.parent.strategy_id == 1:
        strategy1 = QgsNetworkSpeedStrategy(self.parent.idx_field_speed,
                                               defaultValue,
                                               toMetricFactor
                                               )
        #else:
        #strategy2 = QgsNetworkDistanceStrategy()
        if self.verify_break():
            return 0
        director.addStrategy(strategy1)
        #director.addStrategy(strategy2)
        if self.verify_break():
            return 0
        builder = QgsGraphBuilder(self.crs)
        QApplication.processEvents()
        comment = ""
        if self.mode == 2:
            comment = "backward "
        self.parent.setMessage(f'Constructing {comment}network graph  ...')

        QApplication.processEvents()
        if self.verify_break():
            return 0
        director.makeGraph(builder, [])
        if self.verify_break():
            return 0
        self.graph = builder.graph()

        self.parent.setMessage(f'Saving {comment}network graph...')
        QApplication.processEvents()
        self.prefix = os.path.basename(self.parent.path_to_protocol)
        file_path = os.path.join(self.parent.path_to_protocol, f'{self.prefix}_graph.json')
        
        if self.mode == 2:
            file_path = os.path.join(self.parent.path_to_protocol, f'{self.prefix}_graph_rev.json')
        self.save_graph(self.graph, file_path)

        return self.graph






    def save_graph(self, graph, file_path):
        ROUND = 3

        graph_data = {
            "nodes": [
                [round(graph.vertex(i).point().x(),ROUND),
                round(graph.vertex(i).point().y(),ROUND), ]
                for i in range(graph.vertexCount())
            ],
            "edges": []
        }

        for edge_id in range(graph.edgeCount()):
            edge = graph.edge(edge_id)
            source_id = edge.fromVertex()
            target_id = edge.toVertex()

            strategies = edge.strategies()
            costs = [round(edge.cost(i), ROUND) for i in range(len(strategies))]

            graph_data["edges"].append([source_id, target_id, costs])

        json_path = file_path
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False)

    def load_graph(self, mode, pathtopkl, crs):

        if mode == 1:
            graph_path = get_existing_path(pathtopkl, "graph.json")
        else:
            graph_path = get_existing_path(pathtopkl, "graph_rev.json")

        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)

        builder = QgsGraphBuilder(crs)

        # add vertices
        for vid, (x, y) in enumerate(graph_data["nodes"]):
            builder.addVertex(vid, QgsPointXY(x, y))

        # add edges
        for source_id, target_id, costs in graph_data["edges"]:
            x1, y1 = graph_data["nodes"][source_id]
            x2, y2 = graph_data["nodes"][target_id]

            builder.addEdge(
                source_id, QgsPointXY(x1, y1),
                target_id, QgsPointXY(x2, y2),
                costs
            )

        return builder.graph()

        """
        # --- Сохраняем координаты вершин ---
        with open(nodes_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["id", "x", "y"])
            for vid, (x, y) in enumerate(graph_data['nodes']):
                writer.writerow([vid, x, y])

        print(f"Файл с вершинами сохранён: {nodes_file}")

        # --- Сохраняем рёбра с WKT ---
        with open(edges_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "edge_id", "source_id", "target_id",
                "x1", "y1", "x2", "y2",
                "cost", "wkt"
            ])

            for eid, (source_id, target_id, costs) in enumerate(graph_data['edges']):
                x1, y1 = graph_data['nodes'][source_id]
                x2, y2 = graph_data['nodes'][target_id]

                cost = costs[0] if isinstance(costs, (list, tuple)) else costs

                wkt = f"LINESTRING({x1} {y1}, {x2} {y2})"

                writer.writerow([eid, source_id, target_id, x1, y1, x2, y2, cost, wkt])

        print(f"Файл с рёбрами сохранён: {edges_file}")
        """
 
    def change_road_layer(self):
        comment = ""
        if self.mode == 2:
            comment = "backward "
        self.parent.setMessage(f'Modifying {comment}road links ...')
        QApplication.processEvents()
        features = self.layer_roads.getFeatures()
        new_features = []

        for count, feature in enumerate(features):

            if count % 50000 == 0:
                if self.verify_break():
                    return 0
                self.parent.setMessage(f'Modifying {comment}road links (link {count}) ... ')
                QApplication.processEvents()
            new_feature = QgsFeature(feature)

            if self.parent.idx_field_direction != -1:
                current_value = new_feature.attribute(
                    self.parent.idx_field_direction)

                current_value = new_feature.attribute(self.parent.idx_field_direction)

                if self.mode == 1:
                    new_value = current_value

                elif self.mode == 2:
                    if current_value == "T":
                        new_value = "F"
                    elif current_value == "F":
                        new_value = "T"
                    else:
                        new_value = "B"
                
                new_feature.setAttribute(self.parent.idx_field_direction, new_value)

            
            if self.parent.layer_road_type_road != '':
                fclass_value = new_feature[self.parent.layer_road_type_road]
                speed_value = new_feature[self.parent.speed_fieldname]
                if not speed_value or speed_value == 0 or speed_value == "0":
                    new_value = self.parent.type_road_speed_default.get(fclass_value, int(self.parent.speed))
                    new_feature.setAttribute(self.parent.idx_field_speed, int(new_value))
            
            if self.parent.layer_road_type_road == '':
                speed_value = new_feature[self.parent.speed_fieldname]
                speed = int(self.parent.speed)
                if not speed_value or speed_value == 0 or speed_value == "0":
                    new_feature.setAttribute(self.parent.idx_field_speed, speed)


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

        # dict_building_vertex
        path1 = get_existing_path(pathtopkl, "dict_building_vertex.json")
        with open(path1, "r", encoding="utf-8") as f:
            raw1 = json.load(f)

        dict_building_vertex = {
            int(k): tuple(v)
            for k, v in raw1.items()
        }

        # dict_vertex_buildings
        path2 = get_existing_path(pathtopkl, "dict_vertex_buildings.json")
        with open(path2, "r", encoding="utf-8") as f:
            raw2 = json.load(f)

        dict_vertex_buildings = {
            int(k): [(b, d) for b, d in v]
            for k, v in raw2.items()
        }

        return dict_building_vertex, dict_vertex_buildings



    def converting_roads(self):
        self.converter = MultiLineStringToLineStringConverter(self.parent, self.parent.layer_road)
        layer_road = self.converter.execute()

        return layer_road

    def verify_break(self):
        if self.parent.break_on:
            self.parent.setMessage("Building car routing database is interrupted by user")
            if not self.already_display_break:
                self.parent.textLog.append(f'<a><b><font color="red">Building car routing database is interrupted by user</font> </b></a>')
                self.already_display_break = True
            self.parent.progressBar.setValue(0)
            return True
        return False
    
    def get_full_filename (self, filename):
        self.prefix = os.path.basename(self.parent.path_to_protocol)
        path = os.path.join(self.parent.path_to_protocol, f"{self.prefix}_{filename}")

        return path
        

    def save_pkl(self, data, filename):
        self.prefix = os.path.basename(self.parent.path_to_protocol)
        path = os.path.join(self.parent.path_to_protocol, f"{self.prefix}_{filename}")

        # convert tuple → list
        def convert(obj):
            if isinstance(obj, tuple):
                return list(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        data_json = convert(data)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data_json, f, ensure_ascii=False)


    def create_list_buidings(self):

        # get points from the building layer
        points = []
        
        for c, feature in enumerate(self.parent.layer_buildings.getFeatures()):

            if c % 50000 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()
                self.parent.setMessage(f'Retrieving building features item {c} of {self.count_item}...')

            geom = feature.geometry()

            if geom.type() == QgsWkbTypes.GeometryType.PointGeometry:
                point = geom.asPoint()
            elif geom.type() == QgsWkbTypes.GeometryType.PolygonGeometry:
                point = geom.centroid().asPoint()

            points.append((
                          feature[self.parent.layer_buildings_field],
                          QgsPointXY(point.x(), point.y())
                          ))
        return points

    def build_coord_to_vertex_id(self, graph):
            coord_to_id = {}

            for vid in range(graph.vertexCount()):
                p = graph.vertex(vid).point()                
                key = (p.x(), p.y())
                coord_to_id[key] = vid

            return coord_to_id
