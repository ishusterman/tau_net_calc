import math
from qgis.core import (
    QgsProject,
    QgsGeometry,
    QgsPointXY,
    QgsFeature,
    QgsSpatialIndex,    
    QgsVectorLayer,    
    QgsWkbTypes,
    QgsDistanceArea,
    QgsCoordinateTransformContext
    )

from qgis.PyQt.QtWidgets import QApplication

class clsCarJSON:
    def __init__(
        self,
        parent,
        idx_direction,
        idx_speed,
        speed_default,
        direction_default = "B",
        MaxPath = 400
    ):
        self.parent = parent
        self.already_display_break = False
        self.idx_direction = idx_direction
        self.idx_speed = idx_speed
        self.MaxPath = MaxPath

        self.speed_default = speed_default
        self.direction_default  = direction_default
        
        
    def make_new_layer_with_projections(self,
                                        layer_roads,
                                        layer_buildings        
                                        ):
                
        self.layer_roads = layer_roads
        self.layer_buildings = layer_buildings

        self.crs = self.layer_buildings.crs()
        self.distance_area = QgsDistanceArea()
        #self.distance_area.setSourceCrs(self.crs, QgsCoordinateTransformContext())
        self.distance_area.setSourceCrs(self.layer_roads.crs(), QgsCoordinateTransformContext())
        self.distance_area.setEllipsoid('WGS84') 
        
        
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

        if self.parent is not None:
            self.parent.setMessage(f'Building the index for the layer of roads...')
            QApplication.processEvents()
        # create a spatial index for the road layer
        self.index = QgsSpatialIndex(self.cloned_layer.getFeatures())
        
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
            self.add_point_to_layer(polygon_geom.centroid().asPoint())

        self.cloned_layer.updateExtents()
        #QgsProject.instance().addMapLayer(self.cloned_layer)
        return self.cloned_layer 
    
    def add_point_to_layer(self, polygon_geom):
        centroid = polygon_geom  # QgsPointXY
        # Ищем ближайшую линию
        nearest_ids = self.index.nearestNeighbor(centroid, 1)

        for fid in nearest_ids:
            line_feat = self.cloned_layer.getFeature(fid)
            attributes = line_feat.attributes()
            line_geom = line_feat.geometry()
            line = line_geom.constGet()

            num_vertices = line.numPoints()
            if num_vertices < 2:
                continue

            # Ищем ближайшую именно к вершинам (узлам) линии
            min_vertex_pt = None
            min_length = float('inf')

            for i in range(num_vertices):
                v = line.pointN(i)
                v_pt = QgsPointXY(v.x(), v.y())

                link_geom = QgsGeometry.fromPolylineXY([centroid, v_pt])
                length = self.distance_area.measureLength(link_geom)

                if not math.isnan(length) and length < min_length:
                    min_length = length
                    min_vertex_pt = v_pt

            # Если ближайшая вершина найдена и её расстояние в пределах нормы
            if min_vertex_pt is not None and min_length <= self.MaxPath:
                link_geom = QgsGeometry.fromPolylineXY([centroid, min_vertex_pt])

                feat_forward = QgsFeature()
                feat_forward.setGeometry(link_geom)
                feat_forward.setAttributes(attributes)
                feat_forward.setAttribute(self.idx_speed, self.speed_default)
                feat_forward.setAttribute(self.idx_direction, self.direction_default)  # прямое направление
                self.provider.addFeature(feat_forward)

            # Достаточно обработать ближайший объект дороги
            break

    
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