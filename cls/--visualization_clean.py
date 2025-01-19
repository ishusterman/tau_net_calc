import os
from datetime import datetime

from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsTask,
    QgsProject,
    QgsFeature,
    edit)

from qgis import processing

from common import getDateTime, convert_meters_to_degrees


class cls_clean_visualization(QgsTask):
    def __init__(self, parent, begin_computation_time, layer, folder_name, task_name="Voronoi Task"):
        super().__init__(task_name)
        self.parent = parent
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.exception = None
        self.break_on = False
        self.parent.progressBar.setMaximum(10)

    def run(self):

        uri = self.layer.dataProvider().dataSourceUri()
        input_layer_path = uri.split("|")[0] if "|" in uri else uri
        file_name = os.path.basename(input_layer_path)
        self.name, self.ext = os.path.splitext(file_name)
        input_layer = QgsVectorLayer(input_layer_path, "Layer Name", "ogr")

        ################################
        self.parent.setMessage('Delete holes ...')
        deleteholes_result = processing.run("qgis:deleteholes", {
            'INPUT': input_layer,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        layer_deleteholes = deleteholes_result['OUTPUT']
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(1)
        ###############################

        self.parent.setMessage('Remove null geometries ...')
        empty_geometry_features = []

        for feature in layer_deleteholes.getFeatures():
            if feature.geometry().isNull():
                empty_geometry_features.append(feature)

        if empty_geometry_features:
            with edit(layer_deleteholes):
                for feature in empty_geometry_features:
                    layer_deleteholes.deleteFeature(feature.id())

        if self.break_on:
            return 0
        self.parent.progressBar.setValue(2)
        ##############################

        self.parent.setMessage('Converting multipart to singlepart ...')
        singlepart_result = processing.run("native:multiparttosingleparts", {
            'INPUT': layer_deleteholes,
            'OUTPUT': 'memory:'
        })
        layer_singlepart = singlepart_result['OUTPUT']
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(3)

        ############################################

        self.parent.setMessage('Renumbering repeated osm_id ...')
        osm_id_counter = {}
        layer_singlepart.startEditing()

        for feature in layer_singlepart.getFeatures():
            osm_id = feature['osm_id']
            if osm_id in osm_id_counter:
                osm_id_counter[osm_id] += 1
                new_id = f"{osm_id}_{osm_id_counter[osm_id]}"
            else:

                osm_id_counter[osm_id] = 1
                new_id = osm_id
            feature['osm_id'] = new_id
            layer_singlepart.updateFeature(feature)
        layer_singlepart.commitChanges()
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(4)
        #############################################
        self.parent.setMessage('Constructing centroids ...')
        input_layer_path, self.centoids_layer_name, dist_buffer = self.make_centroids(
            layer_singlepart)
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(5)
        #############################################
        # Voronoi
        #########################
        self.parent.setMessage('Constructing Voronoi polygones ...')

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
        self.parent.progressBar.setValue(6)
        #########################
        # Index for voronoi_layer
        #########################
        self.parent.progressBar.setValue(6)
        self.parent.setMessage('Constructing index ...')
        processing.run("native:createspatialindex",
                       {'INPUT': voronoi_layer})
        #########################
        # Buffer
        #########################
        self.parent.setMessage('Constructing buffer ...')
        buffer_result = processing.run("native:buffer",
                                       {'INPUT': input_layer_path,
                                        'DISTANCE': dist_buffer,
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
        self.parent.progressBar.setValue(7)
        #######################
        # Clip - voronoi_layer and buffer_layer
        ########################
        self.parent.setMessage('Clipping ...')

        clip_layer = self.make_clip(buffer_layer, voronoi_layer)
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(8)
        #########################
        # Saving result
        #########################
        self.parent.setMessage('Saving ...')
        file_dir = self.folder_name
        self.output_file_name = f"{self.name}_voronoi{self.ext}"
        output_path = os.path.join(file_dir, self.output_file_name)
        self.unique_output_path = self.get_unique_path(output_path)
        self.layer_name = os.path.splitext(
            os.path.basename(self.unique_output_path))[0]
        QgsVectorFileWriter.writeAsVectorFormat(
            clip_layer,
            self.unique_output_path,
            "UTF-8",
            clip_layer.crs(),
            "ESRI Shapefile"
        )
        saved_layer = QgsVectorLayer(
            self.unique_output_path, self.layer_name, "ogr")
        if saved_layer.isValid():
            QgsProject.instance().addMapLayer(saved_layer)
        if self.break_on:
            return 0
        self.parent.progressBar.setValue(9)
        ###################################
        self.write_finish_info()
        QgsProject.instance().removeMapLayer(voronoi_layer)
        self.parent.btnBreakOn.setEnabled(False)
        self.parent.close_button.setEnabled(True)
        self.parent.setMessage('Finished')
        self.parent.progressBar.setValue(10)
        return True

    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(
            f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.parent.textLog.toPlainText()
        postfix = getDateTime()

        filelog_name = f'{self.folder_name}//log_visualization_database_{postfix}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)

        self.parent.textLog.append(
            f'"{self.layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
        self.parent.textLog.append(
            f'"{self.centoids_layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')

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
            QgsVectorLayer(output_path, layer_name, "ogr"))
        input_layer_path = centroid_layer.id()

        first_feature = next(centroid_layer.getFeatures())
        first_point = first_feature.geometry().centroid().asPoint()
        units = centroid_layer.crs().mapUnits()
        crs_grad = (units == 6)
        dist_buffer = 50
        if crs_grad:
            dist_buffer = convert_meters_to_degrees(
                dist_buffer, first_point.y())

        return input_layer_path, layer_name, dist_buffer

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
                print(f"Error: {e}")

            finally:
                del single_buffer_layer
                del clipped_layer

        result_layer.updateExtents()
        return result_layer
