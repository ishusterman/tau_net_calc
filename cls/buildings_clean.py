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


class cls_clean_buildings(QgsTask):
    def __init__(self, parent, begin_computation_time, layer, folder_name, task_name="Buildings clean task"):
        super().__init__(task_name)
        self.parent = parent
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name

        self.exception = None
        self.break_on = False
        self.parent.progressBar.setMaximum(5)

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

        self.layer_name_single_part =  self.save_layer_single_part (layer_singlepart)
                
        self.write_finish_info()
        
        self.parent.btnBreakOn.setEnabled(False)
        self.parent.close_button.setEnabled(True)
        self.parent.progressBar.setValue(5)
        self.parent.setMessage('Finished')
        
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
                
        filelog_name = f'{self.folder_name}//log_{postfix}.txt'
        
        with open(filelog_name, "w") as file:
            file.write(text)
        
        self.parent.textLog.append(
            f'"{self.layer_name_single_part}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')
                
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
    
    def save_layer_single_part (self, layer_single_part):
        self.parent.setMessage('Saving buildings...')
        file_dir = self.folder_name
        output_file_name = f"{self.name}_corrected{self.ext}"
        output_path = os.path.join(file_dir, output_file_name)
        unique_output_path = self.get_unique_path(output_path)
        
        layer_name = os.path.splitext(os.path.basename(unique_output_path))[0]
        QgsVectorFileWriter.writeAsVectorFormat(
            layer_single_part,
            unique_output_path,
            "UTF-8",
            layer_single_part.crs(),
            "ESRI Shapefile"
        )
        
        saved_layer = QgsVectorLayer(
            unique_output_path, layer_name, "ogr")
        if saved_layer.isValid():
            QgsProject.instance().addMapLayer(saved_layer)
        
        return layer_name