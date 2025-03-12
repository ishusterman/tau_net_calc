import os
from datetime import datetime
from random import choice
from matplotlib.colors import CSS4_COLORS
import math

from PyQt5.QtCore import QVariant

from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsTask,
    QgsProject,
    QgsFeature,
    QgsField,
    QgsSpatialIndex,
    QgsFillSymbol,
    QgsRectangle,
    edit)

from qgis.core import QgsProcessing

from qgis import processing

from common import getDateTime, convert_meters_to_degrees

class cls_clean_visualization(QgsTask):
    def __init__(self, parent, begin_computation_time, layer, folder_name, task_name="Voronoi and Hexagons task"):
        super().__init__(task_name)
        self.parent = parent
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.exception = None
        self.break_on = False
        self.parent.progressBar.setMaximum(25)
        self.spacing = [50*math.sqrt(3), 100*math.sqrt(3), 200*math.sqrt(3), 400*math.sqrt(3)]
        if self.parent.add_hex != "" and int (self.parent.add_hex) not in (50,100,200,400):
            self.spacing.append(int(self.parent.add_hex) * math.sqrt(3))

        #self.spacing = [800]
        self.layer_result_list = []
        self.dist_buffer = 50
        self.voronoi_layer_name = ""
        
    def run(self):
       try: 
        uri = self.layer.dataProvider().dataSourceUri()
        self.input_layer_path = uri.split("|")[0] if "|" in uri else uri
        self.file_name = os.path.basename(self.input_layer_path)
        self.name, self.ext = os.path.splitext(self.file_name)
        input_layer = QgsVectorLayer(self.input_layer_path, "Layer Name", "ogr")
        #############################################
        self.parent.setMessage('Constructing buildings’ centroids ...')
        centroid_layer_id, centroids_layer = self.make_centroids(self.layer)
        self.centroids_layer_id = centroid_layer_id
        
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(1)


        units = input_layer.crs().mapUnits()
        crs_grad = (units == 6)
        first_feature = next(input_layer.getFeatures())
        first_point = first_feature.geometry().centroid().asPoint()
        
        self.dist_buffer = 50
        if crs_grad:
            self.dist_buffer = convert_meters_to_degrees(
                self.dist_buffer, first_point.y())

        #############################################
        self.Voronoi()
        #############################################
        if self.break_on:
                return 0
        
        for i, spacing in enumerate(self.spacing):

            spacing_info = round (spacing/math.sqrt(3))
            self.parent.setMessage(f'Constructing hexagons {spacing_info}m ...')
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
            self.parent.progressBar.setValue(6 + i*4)
            #############################################
            self.parent.setMessage(f'Filtering hexagons {spacing_info}m...')
            self.filter_hexagons_by_intersection(hexagones_layer, self.layer)
        
            if self.break_on:
                return 0
            self.parent.progressBar.setValue(7 + i*4)
            #############################################
            self.parent.setMessage(f'Matching between buildings and hexagons {spacing_info}m...')
            self.add_nearest_osm_id(hexagones_layer, centroids_layer)
        

            if self.break_on:
                return 0
            self.parent.progressBar.setValue(8 + i*4)

            #############################################
            self.parent.setMessage(f'Dissolving adjacent hexagons with the same ID {spacing_info}m on osm_id...')
            dissolve_result = processing.run("native:dissolve", 
                        {
                        'INPUT': hexagones_layer,
                        'FIELD': ['osm_id'],
                        'OUTPUT': 'memory:'
                        })
            dissolved_layer = dissolve_result['OUTPUT']
            if self.break_on:
                return 0
            self.parent.progressBar.setValue(9 + i*4)
               
            #########################
            # Saving result
            #########################
        
            self.parent.setMessage('Saving ...')
            file_dir = self.folder_name
            self.output_file_name = f"{self.name}_hexagons_{spacing_info}m{self.ext}"
            output_path = os.path.join(file_dir, self.output_file_name)
            self.unique_output_path = self.get_unique_path(output_path)
        
            self.layer_name = os.path.splitext(os.path.basename(self.unique_output_path))[0]
            self.layer_result_list.append(self.layer_name)

            QgsVectorFileWriter.writeAsVectorFormat(
                dissolved_layer,
                self.unique_output_path,
                "UTF-8",
                dissolved_layer.crs(),
                "ESRI Shapefile"
            )
        
            saved_layer = QgsVectorLayer(self.unique_output_path, self.layer_name, "ogr")
            if saved_layer.isValid():
                QgsProject.instance().addMapLayer(saved_layer)
                self.style_polygon_layer(saved_layer)
            if self.break_on:
                return 0
            
            self.parent.progressBar.setValue(10 + i*4)
            ###################################

        QgsProject.instance().removeMapLayer(self.centroids_layer_id) 
        self.parent.progressBar.setValue(25)

        ###
        #self.voronoi_layer_name = "test"    
        ###

        self.write_finish_info()
        self.parent.btnBreakOn.setEnabled(False)
        self.parent.close_button.setEnabled(True)

       except Exception as e:
            print(f"Error h: {e}") 
        
       return True
    
    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.parent.textLog.toPlainText()
        postfix = getDateTime()

        filelog_name = f'{self.folder_name}//log_visualization_database_{postfix}.txt'
        
        with open(filelog_name, "w") as file:
            file.write(text)

        if self.voronoi_layer_name != "":
            self.parent.textLog.append(f'"{self.voronoi_layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
                
        for item in self.layer_result_list:
            self.parent.textLog.append(f'"{item}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')

        self.parent.setMessage(f'Finished')

    def cancel(self):
        try:
            self.parent.progressBar.setValue(0)
            self.parent.setMessage(f'')
            self.break_on = True
            super().cancel()
        except:
            return

    def get_unique_path(self, base_path):
        """
        Generates a unique path by appending an index if the file already exists.
        :param base_path: The initial path for saving the file
        :return: A unique path with an appended index
        """
        if not os.path.exists(base_path):
            return base_path

        base, ext = os.path.splitext(base_path)
        index = 1
        while os.path.exists(f"{base}_{index}{ext}"):
            index += 1
        return f"{base}_{index}{ext}"
   

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
                self.parent.setMessage(f'Filtering hexagons {i} from {count}...')
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

        if "osm_id" not in [field.name() for field in hexagones_layer.fields()]:
            hexagones_layer.dataProvider().addAttributes([QgsField("osm_id", QVariant.String)])
            hexagones_layer.updateFields()

        field_index = hexagones_layer.fields().lookupField("osm_id")    
    
        input_index = QgsSpatialIndex(centroids_layer.getFeatures())
        input_features = {feat.id(): feat for feat in centroids_layer.getFeatures()}
        hex_centroids = {feat.id(): feat.geometry().centroid() for feat in hexagones_layer.getFeatures()}
        count = len(hex_centroids)

        updates = {}
        for i, (feat_id, hex_centroid) in enumerate(hex_centroids.items()):
            if i % 1000 == 0:
                if self.break_on:
                    return 0
                self.parent.setMessage(f'Matching between buildings and hexagons {i} from {count}...')
        
            nearest_id = input_index.nearestNeighbor(hex_centroid.asPoint(), 1)
            if nearest_id:
                nearest_feature = input_features[nearest_id[0]]
                nearest_osm_id = nearest_feature["osm_id"]
                updates[feat_id] = {field_index: nearest_osm_id}    
        
        hexagones_layer.dataProvider().changeAttributeValues(updates)
        
        hexagones_layer.commitChanges()

    def make_centroids(self, input_layer):

        centroid_layer = QgsVectorLayer(
            "Point?crs=" + input_layer.crs().authid(), "Centroids", "memory")
        provider = centroid_layer.dataProvider()
        provider.addAttributes(input_layer.fields())
        centroid_layer.updateFields()

        with edit(centroid_layer):
            for i, feature in enumerate(input_layer.getFeatures()):
                if i % 100 == 0:
                    if self.break_on:
                        return 0
                centroid = feature.geometry().centroid()
                if centroid.isEmpty():
                    continue
                centroid_feature = QgsFeature()
                centroid_feature.setGeometry(centroid)
                centroid_feature.setAttributes(feature.attributes())
                if centroid_feature.geometry() is not None:
                    provider.addFeature(centroid_feature)

        file_dir = self.folder_name
        self.output_file_name = f"{self.name}_centroids{self.ext}"
        output_path = os.path.join(file_dir, self.output_file_name)
        self.unique_output_path = self.get_unique_path(output_path)
        self.layer_name = os.path.splitext(
            os.path.basename(self.unique_output_path))[0]
        
        output_path = self.unique_output_path
        
        QgsVectorFileWriter.writeAsVectorFormat(
            centroid_layer,
            output_path,
            "utf-8",
            input_layer.crs(),
            "ESRI Shapefile"
        )

        layer_name = os.path.splitext(os.path.basename(output_path))[0]
        centroid_layer = QgsProject.instance().addMapLayer(
            QgsVectorLayer(output_path, layer_name, "ogr"), False)
        centroid_layer_id = centroid_layer.id()

        return centroid_layer_id, centroid_layer
    
    #############################################
    # Voronoi
    #########################
    def Voronoi (self):
      try:  
        self.parent.setMessage('Constructing Voronoi polygons...')
        input_layer_path = self.centroids_layer_id
        voronoi_result = processing.run("native:voronoipolygons",
                                        {'INPUT': input_layer_path,
                                         'BUFFER': 0,
                                         'TOLERANCE': 0,
                                         'COPY_ATTRIBUTES': True,
                                         'OUTPUT': 'TEMPORARY_OUTPUT'}
                                        )
        voronoi_layer = voronoi_result['OUTPUT']
        
        QgsProject.instance().addMapLayer(voronoi_layer, False)
        
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(2)
        #########################
        # Index for voronoi_layer
        #########################
        
        self.parent.setMessage('Constructing index ...')
        processing.run("native:createspatialindex",
                       {'INPUT': voronoi_layer})
        
        #########################
        # Buffer
        #########################
        self.parent.setMessage('Constructing buffers ...')
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
        self.parent.progressBar.setValue(3)
        #######################
        # Clip - voronoi_layer and buffer_layer
        ########################
        self.parent.setMessage('Clipping ...')

        clip_layer = self.make_clip(buffer_layer, voronoi_layer)
        
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(4)
        #########################
        # Saving result
        #########################
        self.parent.setMessage('Saving ...')
        file_dir = self.folder_name
        self.output_file_name = f"{self.name}_voronoi{self.ext}"
        #print (f'self.output_file_name {self.output_file_name}')
        output_path = os.path.join(file_dir, self.output_file_name)
        self.unique_output_path = self.get_unique_path(output_path)
        #print (f'self.unique_output_path {self.unique_output_path}')
        self.voronoi_layer_name = os.path.splitext(
            os.path.basename(self.unique_output_path))[0]
        QgsVectorFileWriter.writeAsVectorFormat(
            clip_layer,
            self.unique_output_path,
            "UTF-8",
            clip_layer.crs(),
            "ESRI Shapefile"
        )

        #print (f'self.voronoi_layer_name {self.voronoi_layer_name}')

        saved_layer = QgsVectorLayer(
            self.unique_output_path, self.voronoi_layer_name, "ogr")
        if saved_layer.isValid():
            QgsProject.instance().addMapLayer(saved_layer)
            self.style_polygon_layer(saved_layer)
        if self.break_on:
            return 0
        QgsProject.instance().removeMapLayer(voronoi_layer.id())
        self.parent.progressBar.setValue(5)
        
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
                self.parent.setMessage(
                    f'Clipping buffers {i + 1} to from {count_buffers} ...')

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

    """
    def make_clip(self, buffer_layer, voronoi_layer):

        result_layer = QgsVectorLayer(
            "Polygon?crs=" + voronoi_layer.crs().authid(), "Clipped Voronoi", "memory")
        result_provider = result_layer.dataProvider()
        result_provider.addAttributes(voronoi_layer.fields())
        result_layer.updateFields()
        count_buffers = buffer_layer.featureCount()

        for i, buffer_feature in enumerate(buffer_layer.getFeatures()):
            if i % 10 == 0:
                if self.break_on:
                    return 0
                self.parent.setMessage(
                    f'Clipping buffer {i + 1} from {count_buffers} ...')

            single_buffer_layer = QgsVectorLayer(
                "Polygon?crs=" + buffer_layer.crs().authid(), "Single Buffer", "memory")
            buffer_provider = single_buffer_layer.dataProvider()
            buffer_provider.addAttributes(buffer_layer.fields())
            single_buffer_layer.updateFields()

            buffer_provider.addFeature(QgsFeature(buffer_feature))

            try:
                clip_result = processing.run("native:clip",
                                             {
                                                 'INPUT': voronoi_layer.id(),
                                                 'OVERLAY': single_buffer_layer,
                                                 'OUTPUT': 'TEMPORARY_OUTPUT'
                                             }
                                             )
                clipped_layer = clip_result['OUTPUT']
                result_provider.addFeatures(clipped_layer.getFeatures())

            except Exception as e:
                print(f"Error clipped : {e}")

            finally:
                del single_buffer_layer
                del clipped_layer

        result_layer.updateExtents()
        return result_layer
    """ 
    


    def style_polygon_layer(self, layer):
        
        color_list = list(CSS4_COLORS.values())
        random_color = choice(color_list)

        if layer.geometryType() == 2:
            symbol = QgsFillSymbol.createSimple({'color': '0,0,0,0', 
                                                 'outline_color': random_color})
            layer.renderer().setSymbol(symbol)
            layer.triggerRepaint()    