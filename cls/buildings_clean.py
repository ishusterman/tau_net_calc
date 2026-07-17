import os
from datetime import datetime

from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsTask,
    QgsProject,
    QgsFeature, QgsRectangle,
    QgsPointXY, QgsGeometry,
    edit)

from qgis.PyQt.QtCore import QObject, pyqtSignal

from qgis import processing

from common import (get_unique_path, 
                    create_and_check_field,
                    convert_meters_to_degrees,
                    FIELD_ID)

class TaskSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    set_message = pyqtSignal(str)
    save_log = pyqtSignal(bool, str)
    add_layers = pyqtSignal(list) 
    change_button_status = pyqtSignal(bool) 

class cls_clean_buildings(QgsTask):
    def __init__(self, 
                 begin_computation_time, 
                 layer, 
                 folder_name, 
                 task_name="Buildings clean task"):
        
        super().__init__(task_name)
        self.signals = TaskSignals()
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.osm_id_field = FIELD_ID
        
        self.exception = None
        self.break_on = False
        self.list_layer = []

        self.dist_buffer = 50

    def run(self):

        uri = self.layer.dataProvider().dataSourceUri()
        input_layer_path = uri.split("|")[0] if "|" in uri else uri
        file_name = os.path.basename(input_layer_path)
        self.name, self.ext = os.path.splitext(file_name)
        #input_layer = QgsVectorLayer(input_layer_path, "Layer Name", "ogr")

        input_layer = self.layer

        ################################
        self.signals.set_message.emit('Deleting holes ...')
        deleteholes_result = processing.run("qgis:deleteholes", {
            'INPUT': input_layer,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        layer_deleteholes = deleteholes_result['OUTPUT']
        if self.break_on:
            return 0
        self.signals.progress.emit(1)
        ###############################

        self.signals.set_message.emit('Removing null geometries ...')
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
        self.signals.progress.emit(2)
        ##############################

        self.signals.set_message.emit('Converting multipart to singlepart ...')
        singlepart_result = processing.run("native:multiparttosingleparts", {
            'INPUT': layer_deleteholes,
            'OUTPUT': 'memory:'
        })
        layer_singlepart = singlepart_result['OUTPUT']
        if self.break_on:
            return 0
        self.signals.progress.emit(3)

        ############################################

        self.signals.set_message.emit('Renumbering duplicated id ...')

        layer_singlepart  = create_and_check_field(layer_singlepart, self.osm_id_field, type = 'bldg')
        
        if self.break_on:
            return 0
        self.signals.progress.emit(4)

        removed_count = self.remove_duplicate_centroids(layer_singlepart)
        
        self.layer_name_single_part =  self.save_layer_single_part (layer_singlepart)

        ##############
        # 1. Вороной

        self.layer = layer_singlepart

        units = self.layer.crs().mapUnits()
        crs_grad = (units == 6)        
        # Точка для расчета искажений проекции
        first_feat = next(self.layer.getFeatures(), None)        
        if not first_feat: return False
        ref_point = first_feat.geometry().centroid().asPoint()        
            
        v_dist = self.dist_buffer
        if crs_grad: v_dist = convert_meters_to_degrees(self.dist_buffer, ref_point.y())        
        centroids_layer = self.make_centroids(self.layer)        
        self.process_voronoi(centroids_layer, v_dist)
        
        ##############
        self.write_finish_info()
        self.signals.change_button_status.emit(True)
        self.signals.progress.emit(5)
        self.signals.set_message.emit('Finished')
        
        return True
    
    def remove_duplicate_centroids(self, layer: QgsVectorLayer, precision: int = 6) -> int:
        """
        Removes features with duplicate centroids from the given polygon layer.

        :param layer: QgsVectorLayer containing polygon features (e.g., buildings)
        :param precision: Number of decimal places to round centroid coordinates for comparison
        :return: Number of removed features
        """
        if not layer.isEditable():
            layer.startEditing()

        seen_centroids = set()
        ids_to_delete = []

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue

            centroid = geom.centroid().asPoint()
            key = (round(centroid.x(), precision), round(centroid.y(), precision))

            if key in seen_centroids:
                ids_to_delete.append(feature.id())
            else:
                seen_centroids.add(key)

        layer.deleteFeatures(ids_to_delete)
        layer.commitChanges()

        return len(ids_to_delete)
    
    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.signals.log.emit(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.signals.log.emit(f'<a>Processing time: {duration_without_microseconds}</a>')
        
        self.signals.save_log.emit(True, self.layer_name_single_part)
        self.signals.log.emit(f'"{self.layer_name_single_part}.gpkg" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
        self.signals.add_layers.emit(self.list_layer)

    def cancel(self):
        try:
            self.signals.progress.emit(0)
            self.signals.set_message.emit(f'')
            self.break_on = True
            super().cancel()
        except:
            return
        
    def save_layer_single_part(self, layer_single_part):
        self.signals.set_message.emit('Saving layer of buildings...')

        file_dir = self.folder_name
        self.ext = ".gpkg"
        output_file_name = f"{self.name}_cleaned{self.ext}"
        output_path = os.path.join(file_dir, output_file_name)
        unique_output_path = get_unique_path(output_path)

        layer_name = os.path.splitext(os.path.basename(unique_output_path))[0]

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = layer_name
        # важно: если файл уже есть — создаём/перезаписываем слой, а не файл
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer_single_part,
            unique_output_path,
            QgsProject.instance().transformContext(),
            options
        )

        self.output_gpkg_path = unique_output_path
        self.list_layer.append((unique_output_path, layer_name))

        return layer_name

    def save_layer_to_gpkg(self, layer, layer_name):
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = layer_name        
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            self.output_gpkg_path,
            QgsProject.instance().transformContext(),
            options
        )
        #self.list_layer.append((self.output_gpkg_path, layer_name))    

    def process_voronoi(self, centroids, dist):

        self.signals.set_message.emit('Voronoi ...')
        ext = centroids.extent()
        b = ext.width() * 0.05
        rect = QgsRectangle(ext.xMinimum()-b, ext.yMinimum()-b, ext.xMaximum()+b, ext.yMaximum()+b)
        
        mem = QgsVectorLayer(f"Point?crs={centroids.crs().authid()}", "vor_tmp", "memory")
        mem.dataProvider().addAttributes(centroids.fields())
        mem.updateFields()
        
        feats = list(centroids.getFeatures())
        for pt in [QgsPointXY(rect.xMinimum(), rect.yMinimum()), QgsPointXY(rect.xMaximum(), rect.yMaximum())]:
            f = QgsFeature(); f.setGeometry(QgsGeometry.fromPointXY(pt))
            f.setAttributes([None]*centroids.fields().count()); feats.append(f)
        mem.dataProvider().addFeatures(feats)

        vor = processing.run("native:voronoipolygons", {'INPUT': mem, 'OUTPUT': 'memory:'})['OUTPUT']
        buf = processing.run("native:buffer", {'INPUT': self.layer, 'DISTANCE': dist, 'DISSOLVE': True, 'OUTPUT': 'memory:'})['OUTPUT']                
        clip = processing.run("native:clip", {'INPUT': vor, 'OVERLAY': buf, 'OUTPUT': 'memory:'})['OUTPUT']

        base, idx = self.split_name_and_index(self.layer_name_single_part)
        if idx:
            voronoi_name = f"{base.rpartition("_")[0]}_vor_system_{idx}"
        else:
            voronoi_name = f"{self.layer_name_single_part.rpartition("_")[0]}_vor_system"        
        self.save_layer_to_gpkg(clip, voronoi_name)

        self.signals.progress.emit(1)   

    def make_centroids(self, lyr):
        return processing.run("native:centroids", {'INPUT': lyr, 'OUTPUT': 'memory:'})['OUTPUT']
    
    def split_name_and_index(self, name):
        """
        Разделяет имя вида base_5 на ('base', '5').
        Если индекса нет — возвращает (name, None).
        """
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], parts[1]
        return name, None

                