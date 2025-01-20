import os
from datetime import datetime

from qgis.core import (
    QgsVectorLayer,
    QgsVectorLayerJoinInfo,
    QgsVectorFileWriter,
    QgsProcessingFeedback,
    QgsFeatureRequest,
    QgsExpression,
    QgsWkbTypes,
    QgsFeature,
    QgsFields,
    QgsTask,
    QgsProject
)

from PyQt5.QtCore import QSettings

from qgis import processing
from PyQt5.QtWidgets import QApplication

from common import getDateTime


class cls_clean_roads(QgsTask):
    def __init__(self, parent, begin_computation_time, layer, folder_name, task_name="Roads clean task"):
        super().__init__(task_name)
        self.parent = parent
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.initial_layer_count = self.layer.featureCount()
        self.folder_name = folder_name
        self.exception = None
        self.break_on = False

    def run(self):
       
        self.parent.progressBar.setValue(1)
        try:
            uri = self.layer.dataProvider().dataSourceUri()
            input_layer_path = uri.split("|")[0] if "|" in uri else uri
            file_name = os.path.basename(input_layer_path)
            name, ext = os.path.splitext(file_name)
            cleaned_layer_name = f"{name}_c"
            cleaned_layer_error_name = f"{name}_e"
            

            # first clean
            if self.break_on:
                return 0
            result1 = processing.run("grass7:v.clean", {
                'input': input_layer_path,
                'type': [0, 1, 2, 3, 4, 5, 6],
                'tool': [0],
                'threshold': [0.0, 0.0],
                'output': 'TEMPORARY_OUTPUT',
                'error': 'TEMPORARY_OUTPUT',
                'GRASS_REGION_PARAMETER': None,
                'GRASS_SNAP_TOLERANCE_PARAMETER': -1,
                'GRASS_MIN_AREA_PARAMETER': 0.0001,
                'flags': 'c'

            })
            if self.break_on:
                return 0
            self.parent.progressBar.setValue(2)
            QApplication.processEvents()

            cleaned_layer_path1 = result1['output']
            
            # second clean

            result2 = processing.run("grass7:v.clean", {
                'input': cleaned_layer_path1,
                'type': [0, 1, 2, 3, 4, 5, 6],
                'tool': [6],
                'threshold': [0.0],
                'output': 'TEMPORARY_OUTPUT',
                'error': 'TEMPORARY_OUTPUT',
                'GRASS_REGION_PARAMETER': None,
                'GRASS_SNAP_TOLERANCE_PARAMETER': -1,
                'GRASS_MIN_AREA_PARAMETER': 0.0001
            })
            if self.break_on:
                return 0
            self.parent.progressBar.setValue(3)
            cleaned_layer_2_path = result2['output']
            cleaned_layer_2 = QgsVectorLayer(
                cleaned_layer_2_path, cleaned_layer_name, "ogr")
            errors_layer_2_path = result2['error']
            errors_layer_2 = QgsVectorLayer(
                errors_layer_2_path, cleaned_layer_error_name, "ogr")
            error_count = len(list(errors_layer_2.getFeatures()))
            self.parent.textLog.append(
                f'<a>Number of errors: {error_count}</a>')

            # join errors
            join_info = QgsVectorLayerJoinInfo()
            join_info.setJoinLayer(errors_layer_2)
            join_info.setJoinFieldName("cat")
            join_info.setTargetFieldName("fid")
            join_info.setPrefix("e_")
            cleaned_layer_2.addJoin(join_info)
            cleaned_layer_2.triggerRepaint()

            # create a new layer in memory
            geometry_type = cleaned_layer_2.wkbType()
            geometry_string = QgsWkbTypes.displayString(geometry_type)
            filtered_layer = QgsVectorLayer(
                f"{geometry_string}?crs={cleaned_layer_2.crs().authid()}",
                f"{name}_cleaned",
                "memory"
            )
            filtered_data = filtered_layer.dataProvider()
            if self.break_on:
                return 0
            self.parent.progressBar.setValue(4)
            # add the necessary fields
            layer_field_names = {field.name() for field in self.layer.fields()}
            fields_to_add = [field for field in cleaned_layer_2.fields(
            ) if field.name() in layer_field_names]
            filtered_data.addAttributes(fields_to_add)
            filtered_layer.updateFields()

            # filter objects
            expression = QgsExpression('"e_fid" IS NULL')
            request = QgsFeatureRequest(expression)
            if self.break_on:
                return 0
            filtered_features = []
            fields = QgsFields()
            for field in fields_to_add:
                fields.append(field)

            for feature in cleaned_layer_2.getFeatures(request):
                new_feature = QgsFeature()
                new_feature.setGeometry(feature.geometry())
                new_feature.setFields(fields)
                new_feature.setAttributes(
                    [feature[field.name()] for field in fields_to_add])
                filtered_features.append(new_feature)

            filtered_data.addFeatures(filtered_features)
            filtered_layer.updateExtents()
            self.parent.progressBar.setValue(5)

            #####
            file_dir = self.folder_name
            self.output_file_name = f"{name}_topo_cleaned{ext}"
            output_path = os.path.join(file_dir, self.output_file_name)
            self.unique_output_path = self.get_unique_path(output_path)
            self.layer_name = os.path.splitext(
                os.path.basename(self.unique_output_path))[0]
            
            QgsVectorFileWriter.writeAsVectorFormat(
                filtered_layer,  
                self.unique_output_path, 
                "UTF-8",
                filtered_layer.crs(),
                "ESRI Shapefile"
            )
            saved_layer = QgsVectorLayer(
                self.unique_output_path, self.layer_name, "ogr")
            self.saved_layer_count = saved_layer.featureCount()
            if saved_layer.isValid():
                QgsProject.instance().addMapLayer(saved_layer)
            
            self.write_finish_info()
            self.parent.btnBreakOn.setEnabled(False)
            self.parent.close_button.setEnabled(True)
            return True

        except Exception as e:
            self.exception = e
            return False

    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(
            f'<a>Initial road network consists of {self.initial_layer_count} links</a>')
        self.parent.textLog.append(
            f'<a>After topological cleaning the road network consists of {self.saved_layer_count} links</a>')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(
            f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.parent.textLog.toPlainText()
        postfix = getDateTime()

        filelog_name = f'{self.folder_name}//log_roads_clean_{postfix}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)

        self.parent.textLog.append(
            f'"{self.layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')

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
        Generates a unique file path by adding an index if the file already exists.
    
        :param base_path: The original path for saving the file
        :return: A unique file path with an index
        """
        if not os.path.exists(base_path):
            return base_path

        base, ext = os.path.splitext(base_path)
        index = 1
        while os.path.exists(f"{base}_{index}{ext}"):
            index += 1
        return f"{base}_{index}{ext}"