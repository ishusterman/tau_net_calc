import os
from datetime import datetime

import math

from qgis.PyQt.QtCore import QObject, pyqtSignal

from PyQt5.QtCore import QMetaType

from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsTask,
    QgsProject,
    QgsFeature,
    QgsField,
    QgsSpatialIndex,
    QgsRectangle,
    QgsPointXY,
    QgsGeometry    
    )

from qgis import processing

from common import convert_meters_to_degrees, get_unique_path

class TaskSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    set_message = pyqtSignal(str)
    save_log = pyqtSignal(bool)
    add_layers = pyqtSignal(list) 
    change_button_status = pyqtSignal(bool) 

class cls_clean_visualization(QgsTask):
    def __init__(self, 
                 begin_computation_time, 
                 layer, 
                 folder_name, 
                 layer_field,
                 runVoronoi,
                 spacing,
                 task_name="Voronoi and Hexagons task"):
        super().__init__(task_name)
        self.signals = TaskSignals()
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.layer_field = layer_field
        self.runVoronoi = runVoronoi
        self.exception = None
        self.break_on = False
        self.spacing = spacing
        self.dist_buffer = 50
        
    def run(self):
        try: 
     
        
            self.list_layer = []
            input_layer = self.layer
            
            if input_layer.providerType() == "memory":
                input_layer = self.layer
                self.file_name = input_layer.name()
                self.name = self.file_name
                self.ext = ".shp" 
            else:
                self.input_layer_path = input_layer.source()
                input_layer = QgsVectorLayer(self.input_layer_path, "Layer Name", "ogr")
                self.file_name = os.path.basename(self.input_layer_path)
                self.name, self.ext = os.path.splitext(self.file_name)
            #############################################
            self.signals.set_message.emit('Constructing buildings’ centroids ...')
            centroids_layer = self.make_centroids(self.layer)
            
            
            if self.break_on:
                return 0
            self.signals.progress.emit(1)
            units = input_layer.crs().mapUnits()
            crs_grad = (units == 6)
            first_feature = next(input_layer.getFeatures())
            first_point = first_feature.geometry().centroid().asPoint()
            
            if crs_grad:
                self.dist_buffer = convert_meters_to_degrees(
                    self.dist_buffer, first_point.y())

            #############################################
            if self.runVoronoi:
                self.Voronoi(centroids_layer)
            #############################################
            if self.break_on:
                    return 0
            
            for i, spacing in enumerate(self.spacing):

                spacing_info = round (spacing/math.sqrt(3))
                self.signals.set_message.emit(f'Constructing hexagons {spacing_info}m ...')
                spacing_current_x = spacing
                spacing_current_y = spacing
                
                if crs_grad:
                    spacing_current_x = convert_meters_to_degrees(
                    spacing_current_x, first_point.x())

                    spacing_current_y = convert_meters_to_degrees(
                    spacing_current_y, first_point.y())

                buffer_x = spacing_current_x / 2
                buffer_y = spacing_current_y / 2
                
                extent = input_layer.extent()
                extent = QgsRectangle(extent.xMinimum() - buffer_x,
                        extent.yMinimum() - buffer_y,
                        extent.xMaximum() + buffer_x,
                        extent.yMaximum() + buffer_y)
                width = extent.width()
                height = extent.height()
                if width < spacing_current_x or height < spacing_current_y:
                    continue
                
                hexagones_result = processing.run("native:creategrid", 
                        {'TYPE':4,
                            'EXTENT':extent,
                            'HSPACING':spacing_current_x,
                            'VSPACING':spacing_current_y,
                            'HOVERLAY':0,
                            'VOVERLAY':0,
                            'CRS':input_layer.crs(),
                            'OUTPUT':'TEMPORARY_OUTPUT'}
                            )
                hexagones_layer = hexagones_result['OUTPUT']
                                    
                if self.break_on:
                    return 0
                self.signals.progress.emit(6 + i*4)
                #############################################
                self.signals.set_message.emit(f'Filtering hexagons {spacing_info}m...')
                self.filter_hexagons_by_intersection(hexagones_layer, self.layer)
            
                if self.break_on:
                    return 0
                self.signals.progress.emit(7 + i*4)
                
                #############################################
                self.signals.set_message.emit(f'Matching between buildings and hexagons {spacing_info}m...')
                self.add_nearest_osm_id(hexagones_layer, centroids_layer)
            

                if self.break_on:
                    return 0
                self.signals.progress.emit(8 + i*4)
                
                #############################################
                self.signals.set_message.emit(f'Dissolving adjacent hexagons with the same ID {spacing_info}m on osm_id...')
                dissolve_result = processing.run("native:dissolve", 
                            {
                            'INPUT': hexagones_layer,
                            'FIELD': [self.layer_field],
                            'OUTPUT': 'memory:'
                            })
                dissolved_layer = dissolve_result['OUTPUT']
                if self.break_on:
                    return 0
                self.signals.progress.emit(9 + i*4)
                            
                #########################
                # Saving result
                #########################
            
                self.signals.set_message.emit('Saving ...')
                file_dir = self.folder_name
                self.ext = ".shp"
                self.output_file_name = f"{self.name}_hex_{spacing_info}m{self.ext}"
                output_path = os.path.join(file_dir, self.output_file_name)
                unique_output_path = get_unique_path(output_path)
            
                self.layer_name = os.path.splitext(os.path.basename(unique_output_path))[0]

                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "ESRI Shapefile"
                options.fileEncoding = "UTF-8"

                QgsVectorFileWriter.writeAsVectorFormatV3(
                    dissolved_layer, 
                    unique_output_path, 
                    QgsProject.instance().transformContext(), 
                    options)
                            
                self.list_layer.append((unique_output_path, self.layer_name))
                
                if self.break_on:
                    return 0
                
                self.signals.progress.emit(10 + i*4)
                ###################################
            
            self.signals.progress.emit(25)

            self.write_finish_info()
            self.signals.change_button_status.emit(True)

        except Exception as e:
            print(f"Error h: {e}") 
        
        return True
    
    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.signals.log.emit(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.signals.log.emit(f'<a>Processing time: {duration_without_microseconds}</a>')
        self.signals.save_log.emit(True)
        for _, name_layer in self.list_layer:    
            self.signals.log.emit(f'"{name_layer}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
        self.signals.set_message.emit(f'Finished')
        self.signals.add_layers.emit(self.list_layer)

    def cancel(self):
        try:
            self.signals.progress.emit(0)
            self.signals.set_message.emit(f'')
            self.break_on = True
            super().cancel()
        except:
            return

    def filter_hexagons_by_intersection(self, hexagones_layer, input_layer):
        """
        Retain only features in hexagones_layer that intersect with any feature in input_layer.

        :param hexagones_layer: QgsVectorLayer, the layer containing hexagons.
        :param input_layer: QgsVectorLayer, the input layer to check intersections against.
        :raises ValueError: If either of the layers is invalid.
        """
        
        # Start editing the hexagones_layer
        if not hexagones_layer.isEditable():
            hexagones_layer.startEditing()

        # Create a spatial index for input_layer
        input_index = QgsSpatialIndex(input_layer.getFeatures())
        count = hexagones_layer.featureCount()

        # Iterate through hexagones_layer and check for intersection
        for i, hex_feature in enumerate(hexagones_layer.getFeatures()):
            if i%10000 == 0:
                if self.break_on:
                    return 0
                self.signals.set_message.emit(f'Filtering hexagons {i} from {count}...')
            hex_geom = hex_feature.geometry()

            # Get potential intersecting features using the spatial index
            candidate_ids = input_index.intersects(hex_geom.boundingBox())

            # Check if the hexagon intersects with any candidate geometry
            intersects = False
            for candidate_id in candidate_ids:
                candidate_feature = input_layer.getFeature(candidate_id)
                if hex_geom.intersects(candidate_feature.geometry()):
                    intersects = True
                    break

            # Delete the hexagon if it does not intersect
            if not intersects:
                hexagones_layer.deleteFeature(hex_feature.id())

        # Commit the changes to the hexagones_layer
        hexagones_layer.commitChanges()

    def add_nearest_osm_id(self, hexagones_layer, centroids_layer):

        hexagones_layer.startEditing()

        if self.layer_field not in [field.name() for field in hexagones_layer.fields()]:
            hexagones_layer.dataProvider().addAttributes([QgsField(self.layer_field, QMetaType.Type.QString)])
            hexagones_layer.updateFields()

        field_index = hexagones_layer.fields().lookupField(self.layer_field)    
    
        input_index = QgsSpatialIndex(centroids_layer.getFeatures())
        input_features = {feat.id(): feat for feat in centroids_layer.getFeatures()}
        hex_centroids = {feat.id(): feat.geometry().centroid() for feat in hexagones_layer.getFeatures()}
        count = len(hex_centroids)

        updates = {}
        for i, (feat_id, hex_centroid) in enumerate(hex_centroids.items()):
            if i % 1000 == 0:
                if self.break_on:
                    return 0
                self.signals.set_message.emit(f'Matching between buildings and hexagons {i} from {count}...')
        
            nearest_id = input_index.nearestNeighbor(hex_centroid.asPoint(), 1)
            if nearest_id:
                nearest_feature = input_features[nearest_id[0]]
                nearest_osm_id = nearest_feature[self.layer_field]
                updates[feat_id] = {field_index: nearest_osm_id}    
        
        hexagones_layer.dataProvider().changeAttributeValues(updates)
        
        hexagones_layer.commitChanges()
    
    def make_centroids(self, input_layer):
        result = processing.run(
            "native:centroids",
            {
                'INPUT': input_layer,
                'ALL_PARTS': False,
                'OUTPUT': 'memory:'
            }
        )
    
        new_layer = result['OUTPUT']
        return new_layer            
    
    #############################################
    # Voronoi
    #########################
    def Voronoi (self, centroids_layer):
      
        extent = centroids_layer.extent()
        buffer = extent.width() * 0.2  

        expanded_extent = QgsRectangle(
            extent.xMinimum() - buffer,
            extent.yMinimum() - buffer,
            extent.xMaximum() + buffer,
            extent.yMaximum() + buffer
            )

        # Создаём фиктивные точки
        extra_points = [
            QgsFeature(),
            QgsFeature(),
            QgsFeature(),
            QgsFeature()
            ]

        extra_coords = [
                QgsPointXY(expanded_extent.xMinimum(), expanded_extent.yMinimum()),
                QgsPointXY(expanded_extent.xMaximum(), expanded_extent.yMinimum()),
                QgsPointXY(expanded_extent.xMaximum(), expanded_extent.yMaximum()),
                QgsPointXY(expanded_extent.xMinimum(), expanded_extent.yMaximum()),
                ]

        for feat, pt in zip(extra_points, extra_coords):
            feat.setGeometry(QgsGeometry.fromPointXY(pt))
            feat.setAttributes([None] * centroids_layer.fields().count())  # Пустые атрибуты

        # Копируем оригинальные точки + добавляем фиктивные
        mem_layer = QgsVectorLayer("Point?crs=" + centroids_layer.crs().authid(), "temp_points", "memory")
        mem_layer.dataProvider().addAttributes(centroids_layer.fields())
        mem_layer.updateFields()

        # Добавляем оригинальные + рамочные
        features = list(centroids_layer.getFeatures()) + extra_points
        mem_layer.dataProvider().addFeatures(features)

        try: 
        
            self.signals.set_message.emit('Constructing Voronoi polygons...')
                        
            voronoi_result = processing.run("native:voronoipolygons",
                                        {'INPUT': mem_layer,
                                         'BUFFER': 0,
                                         'TOLERANCE': 0,
                                         'COPY_ATTRIBUTES': True,
                                         'OUTPUT': 'TEMPORARY_OUTPUT'}
                                        )
            voronoi_layer = voronoi_result['OUTPUT']

            QgsProject.instance().addMapLayer(voronoi_layer, False)

            if self.break_on:
                return 0
            self.signals.progress.emit(2)
            #########################
            # Index for voronoi_layer
            #########################
            
            self.signals.set_message.emit('Constructing index ...')
            processing.run("native:createspatialindex",
                       {'INPUT': voronoi_layer})
        
            #########################
            # Buffer
            #########################
            
            self.signals.set_message.emit('Constructing buffers ...')
            buffer_result = processing.run("native:buffer",
                                       {'INPUT': self.input_layer_path,
                                        'DISTANCE': self.dist_buffer,
                                        'SEGMENTS': 5,
                                        'END_CAP_STYLE': 0,
                                        'JOIN_STYLE': 0,
                                        'MITER_LIMIT': 2,
                                        'DISSOLVE': True,
                                        'SEPARATE_DISJOINT': True,
                                        'OUTPUT': 'TEMPORARY_OUTPUT'})
            buffer_layer = buffer_result['OUTPUT']
            if self.break_on:
                return 0
            self.signals.progress.emit(3)
            #######################
            # Clip - voronoi_layer and buffer_layer
            ########################
            self.signals.set_message.emit('Clipping ...')
            
            clip_layer = self.make_clip(buffer_layer, voronoi_layer)
        
            if self.break_on:
                return 0
            self.signals.progress.emit(4)
            #########################
            # Saving result
            #########################
            self.signals.set_message.emit('Saving ...')
            file_dir = self.folder_name
            ext = ".shp"
            output_file_name = f"{self.name}_vor{ext}"

            output_path = os.path.join(file_dir, output_file_name)
            unique_output_path = get_unique_path(output_path)
            
            voronoi_layer_name = os.path.splitext(
                os.path.basename(unique_output_path))[0]

            
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "UTF-8"

            QgsVectorFileWriter.writeAsVectorFormatV3(
                clip_layer, 
                unique_output_path, 
                QgsProject.instance().transformContext(), 
                options)

            

            self.list_layer.append((unique_output_path, voronoi_layer_name))

            if self.break_on:
                return 0
            QgsProject.instance().removeMapLayer(voronoi_layer.id())
            self.signals.progress.emit(5)
        
        except Exception as e:
            print (f"error voronoi: {e}")

    ###################################
    
    def make_clip(self, buffer_layer, voronoi_layer):
        result_layer = QgsVectorLayer(
        "Polygon?crs=" + voronoi_layer.crs().authid(), "Clipped Voronoi", "memory")
        result_provider = result_layer.dataProvider()
        result_provider.addAttributes(voronoi_layer.fields())
        result_layer.updateFields()

        count_buffers = buffer_layer.featureCount()
        batch_size = 20  
        buffer_features = []
    
        for i, buffer_feature in enumerate(buffer_layer.getFeatures()):
            if i % 10 == 0:
                if self.break_on:
                    return 0
                self.signals.set_message.emit(f'Clipping buffers {i + 1} to from {count_buffers} ...')

            buffer_features.append(buffer_feature)

            
            if len(buffer_features) == batch_size or i == count_buffers - 1:
                single_buffer_layer = QgsVectorLayer(
                "Polygon?crs=" + buffer_layer.crs().authid(), "Batch Buffers", "memory")
                buffer_provider = single_buffer_layer.dataProvider()
                buffer_provider.addAttributes(buffer_layer.fields())
                single_buffer_layer.updateFields()
                buffer_provider.addFeatures(buffer_features)

                try:
                    clip_result = processing.run("native:clip",
                                             {
                                                 'INPUT': voronoi_layer.id(),
                                                 'OVERLAY': single_buffer_layer,
                                                 'OUTPUT': 'TEMPORARY_OUTPUT'
                                             })
                    clipped_layer = clip_result['OUTPUT']
                    result_provider.addFeatures(clipped_layer.getFeatures())

                except Exception as e:
                    print(f"Error clipped : {e}")

                finally:
                    del single_buffer_layer
                    del clipped_layer
                    buffer_features = []  # Очищаем список перед следующей партией

        result_layer.updateExtents()
        return result_layer
