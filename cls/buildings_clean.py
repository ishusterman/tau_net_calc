import os
from datetime import datetime

from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsTask,
    QgsProject,
    edit)

from qgis.PyQt.QtCore import QObject, pyqtSignal

from qgis import processing

class TaskSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    set_message = pyqtSignal(str)
    save_log = pyqtSignal(bool)
    add_layers = pyqtSignal(list) 
    change_button_status = pyqtSignal(bool) 

class cls_clean_buildings(QgsTask):
    def __init__(self, 
                 begin_computation_time, 
                 layer, 
                 folder_name, 
                 osm_id_field, 
                 task_name="Buildings clean task"):
        
        super().__init__(task_name)
        self.signals = TaskSignals()
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.osm_id_field = osm_id_field

        self.exception = None
        self.break_on = False
        self.signals.progress.emit(5)
        self.list_layer = []

    def run(self):

        uri = self.layer.dataProvider().dataSourceUri()
        input_layer_path = uri.split("|")[0] if "|" in uri else uri
        file_name = os.path.basename(input_layer_path)
        self.name, self.ext = os.path.splitext(file_name)
        input_layer = QgsVectorLayer(input_layer_path, "Layer Name", "ogr")

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

        self.signals.set_message.emit('Renumbering duplicated osm_id ...')

        field_name = self.osm_id_field
        used_ids = set()
        numeric_ids = []

        # Сначала собираем числовые значения для вычисления максимального
        for feature in layer_singlepart.getFeatures():
            value = feature[field_name]
            if value is None:
                continue
            value_str = str(value)
            if value_str.isdigit():
                numeric_ids.append(int(value_str))
            used_ids.add(value_str)

        max_numeric_id = max(numeric_ids) if numeric_ids else 0

        layer_singlepart.startEditing()
        seen_ids = set()

        for feature in layer_singlepart.getFeatures():
            value = feature[field_name]
            if value is None:
                new_value = str(max_numeric_id + 1)
                max_numeric_id += 1
            else:
                value_str = str(value)
                if value_str.isdigit():
                    value_int = int(value_str)
                    if value_str in seen_ids:
                        max_numeric_id += 1
                        new_value = str(max_numeric_id)
                    else:
                        new_value = value_str
                else:
                    # Текстовое значение
                    if value_str in seen_ids:
                        suffix = 1
                        while f"{value_str}_{suffix}" in used_ids or f"{value_str}_{suffix}" in seen_ids:
                            suffix += 1
                        new_value = f"{value_str}_{suffix}"
                    else:
                        new_value = value_str

            seen_ids.add(new_value)
            feature[field_name] = new_value
            layer_singlepart.updateFeature(feature)

        layer_singlepart.commitChanges()
        
        if self.break_on:
            return 0
        self.signals.progress.emit(4)
        self.layer_name_single_part =  self.save_layer_single_part (layer_singlepart)
        self.write_finish_info()
        self.signals.change_button_status.emit(True)
        self.signals.progress.emit(5)
        self.signals.set_message.emit('Finished')
        
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
        self.signals.log.emit(f'"{self.layer_name_single_part}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
        self.signals.add_layers.emit(self.list_layer)
        

    def cancel(self):
        try:
            self.signals.progress.emit(0)
            self.signals.set_message.emit(f'')
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
    
    def save_layer_single_part (self, layer_single_part):
        self.signals.set_message.emit('Saving layer of buildings...')
        file_dir = self.folder_name
        self.ext = ".shp"
        output_file_name = f"{self.name}_cleaned{self.ext}"
        output_path = os.path.join(file_dir, output_file_name)
        unique_output_path = self.get_unique_path(output_path)
        
        layer_name = os.path.splitext(os.path.basename(unique_output_path))[0]
        
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        QgsVectorFileWriter.writeAsVectorFormatV3(
                layer_single_part, 
                unique_output_path, 
                QgsProject.instance().transformContext(), 
                options)
        
        self.list_layer.append((unique_output_path, layer_name))    
        
        return layer_name   

                