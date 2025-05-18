from scipy.spatial import KDTree
from qgis.core import QgsWkbTypes
from PyQt5.QtWidgets import QApplication
from pyproj import Geod

from common import convert_meters_to_degrees


class cls_footpath_on_air_b_b:
    def __init__(self, 
                 layer_origins, 
                 layer_dest, 
                 walk_dist=300, 
                 layer_origins_field_id="osm_id", 
                 speed = 1):
        
        self.layer_origins = layer_origins
        self.layer_dest = layer_dest
        self.layer_origins_field_id = layer_origins_field_id

        self.features_origins = list(self.layer_origins.getFeatures())
        self.features_dest = list(self.layer_dest.getFeatures())
        self.walk_dist = walk_dist
        self.speed = speed

        self.crs = self.layer_origins.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)

        points = []
        count = 0
        for feature in self.features_dest:
            count += 1
            if count % 50000 == 0:
                QApplication.processEvents()
            geom = feature.geometry()
            if geom.type() == QgsWkbTypes.PointGeometry:
                pt = geom.asPoint()
            elif geom.type() == QgsWkbTypes.PolygonGeometry:
                pt = geom.centroid().asPoint()
            else:
                multi_polygon = geom.asMultiPolygon()
                pt = multi_polygon[0]

            points.append((pt.x(), pt.y()))

        self.kd_tree_buildings = KDTree(points)

    def calculate_geodesic_distance(self, geom1, geom2):
        geod = Geod(ellps="WGS84")
        lon1, lat1 = (geom1.x(), geom1.y())
        lon2, lat2 = (geom2.x(), geom2.y())
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        return distance

    def get_nearby_buildings(self, id):

        target_feature = None
        nearest_features = []
        
        try:
            for feature in self.features_origins:
                if str(feature.attribute(self.layer_origins_field_id)) == str(id):
                    target_feature = feature
                    break
        except KeyError:
            return nearest_features


        geom = target_feature.geometry()
        if geom.type() == QgsWkbTypes.PointGeometry:
            target_feature_pt = geom.asPoint()
        elif geom.type() == QgsWkbTypes.PolygonGeometry:
            target_feature_pt = geom.centroid().asPoint()
        else:
            multi_polygon = geom.asMultiPolygon()
            target_feature_pt = multi_polygon[0]

        target_point = (target_feature_pt.x(), target_feature_pt.y())

        nearest_features = []

        dist = self.walk_dist
        if self.crs_grad:
            dist = convert_meters_to_degrees(
                self.walk_dist, target_feature_pt.y())

        indices = self.kd_tree_buildings.query_ball_point(target_point, r=dist)

        for index in indices:
            feature = self.features_dest[index]
            feature_geom = feature.geometry().centroid().asPoint()

            if self.crs_grad:
                distance = self.calculate_geodesic_distance(
                    target_feature_pt, feature_geom)
            else:
                distance = target_feature_pt.distance(feature_geom)
            
            if str(feature.attribute(self.layer_origins_field_id)) != str(id):
                nearest_features.append(
                ((feature.attribute(self.layer_origins_field_id)), round(distance/self.speed)))

        return nearest_features
