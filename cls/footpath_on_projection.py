import networkx as nx
import os
import csv
import geopandas as gpd
import pyproj
import math
import json

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsFeature,
    QgsSpatialIndex,
    QgsField,
    QgsVectorLayer,
    QgsDistanceArea,
    QgsCoordinateTransformContext,
    QgsProject,    
    QgsWkbTypes,    
    NULL
    )

from qgis.PyQt.QtWidgets import QApplication

from qgis.PyQt.QtCore import QMetaType, QVariant

from tau_net_calc.cls.common import get_existing_path

class cls_footpath_on_projection:
    def __init__(
        self,
        parent,
        MaxPath = 400
    ):
        self.parent = parent

        self.already_display_break = False
        self.MaxPath = MaxPath

        self.link_counter = 1

    def make_new_layer_with_projections(self,
                                        layer_roads,
                                        layer_buildings,
                                        layer_buildings_field_id,
                                        path_to_stops,
                                        file_name_gpkg,
                                        prefix = "" ):
                
        self.layer_roads = layer_roads
        self.layer_buildings = layer_buildings

        self.crs = self.layer_buildings.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)

        # ##################################
        # слой линков от объектов до проекций
        crs_link = QgsProject.instance().crs()
        self.layer_links = QgsVectorLayer(f"LineString?crs={crs_link.authid()}", f'{prefix}_projection_on_road', "memory")

        self.links_provider = self.layer_links.dataProvider()
        
        int_type = getattr(QMetaType, "Int", QVariant.Int)
        double_type = getattr(QMetaType, "Double", QVariant.Double)
        string_type = getattr(QMetaType, "QString", QVariant.String)

        self.links_provider.addAttributes([
                QgsField("id", int_type),
                QgsField("obj_aid", string_type),
                QgsField("obj_type", string_type),
                QgsField("link_aid", string_type),
            ])


        
        self.layer_links.updateFields()
        self.id_index = self.layer_links.fields().indexOf("id")
        self.obj_aid_index = self.layer_links.fields().indexOf("obj_aid")
        self.obj_type_index = self.layer_links.fields().indexOf("obj_type")
        self.link_aid_index = self.layer_links.fields().indexOf("link_aid")
        ###########################

        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(self.crs, QgsCoordinateTransformContext())
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
            f"{QgsWkbTypes.displayString(layer_type)}?crs={crs}", "roads_with_projections", "memory")

        self.provider = self.cloned_layer.dataProvider()

        # add fields from the source layer to the new layer
        self.provider.addAttributes(self.layer_roads.fields())
        self.cloned_layer.updateFields()

        
        count = self.layer_roads.featureCount()
        # transfer all features (geometry and attributes) from the source layer to the new layer
        for i, feature in enumerate(self.layer_roads.getFeatures()):
            if i % 10000 == 0:
                if self.parent is not None:
                    self.parent.setMessage(f'Making a copy of the layer of roads {i} of {count}...')
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
                QgsField(self.new_field_id, string_type),
                QgsField("distance", double_type),
                QgsField("type", string_type),
            ])

            self.cloned_layer.updateFields()  # update the fields of the cloned layer
  
        self.osm_id_index = self.provider.fields().indexOf(self.new_field_id)
        self.distance_index = self.provider.fields().indexOf("distance")
        self.type_index = self.provider.fields().indexOf("type")

        if self.parent is not None:
            self.parent.setMessage(f'Building the index for the layer of roads...')
            QApplication.processEvents()
        # create a spatial index for the road layer
        self.index = QgsSpatialIndex(self.cloned_layer.getFeatures())

        if path_to_stops:
            self.stops = self.create_stops_gpd(path_to_stops)
            features = self.stops.itertuples(index=False)
            features_list = list(features)
            count = len(features_list)
            for i, feature in enumerate(features_list):
                if i % 5000 == 0:
                    if self.parent is not None:
                        self.parent.setMessage(f'Projecting stops on links {i} of {count}...')
                        QApplication.processEvents()
                    if self.verify_break():
                        return 0
                pFeature = feature.geometry
                osm_id = feature.stop_id
                self.add_point_to_layer(pFeature, osm_id, type="s")

        
        count = self.layer_buildings.featureCount()
        # loop through all the polygons in the buildings layer
        for i, polygon_feat in enumerate(self.layer_buildings.getFeatures()):
            if i % 1000 == 0:
                if self.parent is not None:
                    self.parent.setMessage(f'Projecting buildings on links {i} of {count}...')
                    QApplication.processEvents()
                if self.verify_break():
                    return 0
            polygon_geom = polygon_feat.geometry()
            osm_id = polygon_feat[self.layer_buildings_field_id]
            self.add_point_to_layer(polygon_geom.centroid().asPoint(), osm_id, type="b")

        self.cloned_layer.updateExtents()

        # --- Сохраняем слой в GPKG ---
        if file_name_gpkg:
            """
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.layerName = "links_to_roads"
            options.fileEncoding = "UTF-8"
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

            err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(
                self.layer_links,
                file_name_gpkg ,   # путь к твоему GPKG
                QgsProject.instance().transformContext(),
                options
            )

            # --- Подключаем слой из GPKG ---
            uri = f"{file_name_gpkg }|layername=links_to_roads"
            layer = QgsVectorLayer(uri, "links_to_roads", "ogr")
            """
            #QgsProject.instance().addMapLayer(self.layer_links)

        
        
        return self.cloned_layer, self.layer_links

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

                line_feat_nearest = line_feat
                
                min_dist = dist
                nearest_point = min_dist_point  # nearest point on the line

                # get the indices of the vertices
                start_vertex_index = next_vertex_index - 1  # vertex before the nearest point
                end_vertex_index = next_vertex_index  # vertex after the nearest point

                # get the coordinates of the segment's ends
                start_vertex = line_geom.vertexAt(start_vertex_index)
                end_vertex = line_geom.vertexAt(end_vertex_index)
                best_attr = attributes
                
        # add two segments to the cloned layer
        if nearest_point: 
            line_geom = QgsGeometry.fromPolylineXY([centroid_geom.asPoint(), nearest_point])            
            len = self.distance_area.measureLength(line_geom)
            if not math.isnan(min_dist) and len <= self.MaxPath:

                str_osm_id = self.normalize_id(osm_id)
                min_dist_meters = round (len)
                # === создаём линию от объекта до точки проекции ===
                if type == "b":
                    feat_link = QgsFeature(self.layer_links.fields())                
                    feat_link.setGeometry(QgsGeometry.fromPolylineXY([centroid_geom.asPoint(), nearest_point]))
                    feat_link.setAttribute(self.id_index, self.link_counter)
                    feat_link.setAttribute(self.obj_aid_index, str_osm_id)
                    feat_link.setAttribute(self.obj_type_index, type)                
                    link_aid = line_feat_nearest["aid"]
                    feat_link.setAttribute(self.link_aid_index, link_aid)

                    self.link_counter += 1
                    self.links_provider.addFeature(feat_link)
                # =====================

                # create the first line from the nearest point to the start of the segment
                feat1 = QgsFeature()
                feat1.setGeometry(QgsGeometry.fromPolylineXY(
                    [nearest_point, QgsPointXY(start_vertex.x(), start_vertex.y())]))
                feat1.setAttributes(best_attr)
                # setting the osm_id value
                feat1.setAttribute(self.osm_id_index, str_osm_id)
                # setting the distance value 
                feat1.setAttribute(self.distance_index, min_dist_meters)
                # setting the type value 
                feat1.setAttribute(self.type_index, type)

                self.provider.addFeature(feat1)
                # create the second line from the nearest point to the end of the segment
                feat2 = QgsFeature()
                feat2.setGeometry(QgsGeometry.fromPolylineXY(
                    [nearest_point, QgsPointXY(end_vertex.x(), end_vertex.y())]))
                feat2.setAttributes(best_attr)
                # setting the osm_id value
                feat2.setAttribute(self.osm_id_index, str_osm_id)
                # setting the distance value 
                feat2.setAttribute(self.distance_index, min_dist_meters)
                # setting the type value
                feat2.setAttribute(self.type_index, type)

                self.provider.addFeature(feat2)

    def build_graph(self, roads, file_path = ""):
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
                    self.parent.setMessage(f'Constructing road network graph link {i} of {count}...')
                    QApplication.processEvents()

                if self.verify_break():
                    return 0

            geom = feature.geometry()
            poly = geom.asPolyline()
            if not poly or len(poly) < 2:
                continue
            
            coords = [(p.x(), p.y()) for p in poly]

            osm_id = self.normalize_id(feature[self.new_field_id])
            distance = feature['distance']
            type = feature['type']

            if distance is not None:
                distance = round(distance)

            start_point = coords[0]
            end_point = coords[-1]
            
            if (osm_id is not None) and start_point not in dict_vertex_osm:
                dict_vertex_osm[start_point] = []

            if (osm_id is not None):
                dict_osm_vertex[osm_id] = ((start_point, distance))
                dict_vertex_osm[start_point].append((osm_id, distance, type))

            # === разбиваем полилинию на сегменты ===
            for j in range(len(coords) - 1):
                u = coords[j]
                v = coords[j + 1]

                seg_len = QgsGeometry.fromPolylineXY([
                    QgsPointXY(*u), QgsPointXY(*v)
                ]).length()

                graph.add_node(u)
                graph.add_node(v)

                # добавляем ребро с геометрией сегмента
                graph.add_edge(
                    u, v,
                    weight=seg_len,
                    geometry=[u, v]
                )
        if file_path:
            prefix = os.path.basename(file_path)           

            ROUND = 3

            json_osm_vertex = {
                osm_id: [[round(vertex_xy[0], ROUND), round(vertex_xy[1], ROUND)], dist]
                for osm_id, (vertex_xy, dist) in dict_osm_vertex.items()
            }

            json_vertex_osm = {
                f"{round(x, ROUND)},{round(y, ROUND)}": [
                    [osm_id, dist, t] for (osm_id, dist, t) in lst
                ]
                for (x, y), lst in dict_vertex_osm.items()
            }
            
            with open(os.path.join(file_path, f"{prefix}_dict_osm_vertex.json"), "w", encoding="utf-8") as f:
                json.dump(json_osm_vertex, f, ensure_ascii=False)

            with open(os.path.join(file_path, f"{prefix}_dict_vertex_osm.json"), "w", encoding="utf-8") as f:
                json.dump(json_vertex_osm, f, ensure_ascii=False)

        
        QApplication.processEvents()

        return graph, dict_osm_vertex, dict_vertex_osm

    def save_graph(self, graph, file_path):
        prefix = os.path.basename(file_path)
        graph_path = os.path.join(file_path, f"{prefix}_graph_projection.json")

        ROUND = 3

        graph_data = {
            "nodes": [
                [[round(node[0], ROUND), round(node[1], ROUND)], data]
                for node, data in graph.nodes(data=True)
            ],
            "edges": [
                [
                    [round(u[0], ROUND), round(u[1], ROUND)],
                    [round(v[0], ROUND), round(v[1], ROUND)],
                    {"cost": round(data.get("weight", 0), ROUND)}
                ]
                for u, v, data in graph.edges(data=True)
            ]
        }

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False)

    def load_graph(self, file_path):
        graph_path = get_existing_path(file_path, "graph_projection.json")

        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)

        nx_graph = nx.Graph()

        # узлы
        for node_xy, node_data in graph_data["nodes"]:
            nx_graph.add_node(tuple(node_xy), **node_data)

        # рёбра
        for u_xy, v_xy, attributes in graph_data["edges"]:
            nx_graph.add_edge(
                tuple(u_xy),
                tuple(v_xy),
                weight=attributes.get("cost", 0)
            )

        return nx_graph
    
    def load_dict_osm_vertex(self, file_path):
        if self.parent:
            self.parent.setMessage("Loading database...")
            QApplication.processEvents()

        dict_path = get_existing_path(file_path, "dict_osm_vertex.json")

        with open(dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # восстановление tuple
        return {
            osm_id: ((xy[0], xy[1]), dist)
            for osm_id, (xy, dist) in data.items()
        }


    def load_dict_vertex_osm(self, file_path):
        if self.parent:
            self.parent.setMessage("Loading database...")
            QApplication.processEvents()

        dict_path = get_existing_path(file_path, "dict_vertex_osm.json")

        with open(dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # ключи были "x,y" → превращаем обратно в tuple
        result = {}
        for key, lst in data.items():
            x, y = key.split(",")
            vertex_xy = (float(x), float(y))
            result[vertex_xy] = [(osm_id, dist, t) for osm_id, dist, t in lst]

        return result

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
        path_to_file = os.path.join(path_to_file, 'footpath_road_projection.txt')
        
        rows = []
        rows.append(['from_stop_id', 'to_stop_id', 'min_transfer_time'])

        # Обработка остановок
        self.stops = self.create_stops_gpd(path_to_stops)
        features_list = list(self.stops.itertuples(index=False))
        count = len(features_list)
     
        for i, feature in enumerate(features_list):

            if i % 200 == 0:
                if self.parent is not None:
                    self.parent.setMessage(
                        f'Constructing walk routes, stop {i} of {count}...')
                    QApplication.processEvents()
                if self.verify_break():
                    return 0

            from_osm_id = self.normalize_id(feature.stop_id)
            
            dist_stops, dist_buildings = self.get_nearby(from_osm_id, graph, dict_osm_vertex, dict_vertex_osm)

            # Остановки
            for to_stop_id, dist in dist_stops.items():
                rows.append([from_osm_id, to_stop_id, dist])

            # Здания
            for building_id, dist in dist_buildings.items():
                rows.append([from_osm_id, building_id, dist])
                rows.append([building_id, from_osm_id, dist])

        with open(path_to_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
    
    def get_nearby(self, osm_id, graph, dict_osm_vertex, dict_vertex_osm, mode=None):
        max_dist = self.MaxPath

        search_id = self.normalize_id(osm_id)
        data = dict_osm_vertex.get(search_id)
        if data is None:
            return {} if mode else ({}, {})

        vertex_id, dist_1 = data
        cutoff = max_dist - dist_1
        if cutoff <= 0:
            return {} if mode else ({}, {})

        lengths = nx.single_source_dijkstra_path_length(
            graph,
            vertex_id,
            cutoff=cutoff,
            weight='weight'
        )

        stops = {}
        buildings = {}

        for node, dist_2 in lengths.items():
            lst = dict_vertex_osm.get(node)
            if not lst:
                continue

            for osm2, dist_3, t in lst:
                total = round(dist_1 + dist_2 + dist_3)
                if total > max_dist:
                    continue

                if t == "s":
                    if osm2 != osm_id:
                        prev = stops.get(osm2)
                        if prev is None or total < prev:
                            stops[osm2] = total

                elif t == "b":
                    prev = buildings.get(osm2)
                    if prev is None or total < prev:
                        buildings[osm2] = total

        # Возврат в зависимости от режима
        if mode == "s":
            return stops
        if mode == "b":
            return buildings

        return stops, buildings

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
    
    def normalize_id(self, val):
        if val is None or val == NULL:
            return None
        try:
            return str(int(float(val)))
        except (ValueError, TypeError):
            return str(val).strip()