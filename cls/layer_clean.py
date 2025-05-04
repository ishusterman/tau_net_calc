import os
import processing
from datetime import datetime

from qgis.core import (
    QgsVectorLayer,
    QgsVectorLayerJoinInfo,
    QgsVectorFileWriter,
    QgsFeatureRequest,
    QgsExpression,
    QgsWkbTypes,
    QgsFeature,
    QgsFields,
    QgsTask,
    QgsProject,
    QgsProcessingFeedback,
    QgsField,
    edit
    )

from qgis.PyQt.QtCore import QVariant

from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QApplication

from common import getDateTime, convert_meters_to_degrees

class CustomFeedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.logs = []  # Список для хранения логов

    def pushInfo(self, info):
        self.logs.append(f"INFO: {info}")
    
    def pushCommandInfo(self, command):
        self.logs.append(f"COMMAND: {command}")

    def pushDebugInfo(self, debugInfo):
        self.logs.append(f"DEBUG: {debugInfo}")

    def pushWarning(self, warning):
        self.logs.append(f"WARNING: {warning}")

    def pushError(self, error):
        self.logs.append(f"ERROR: {error}")

class cls_clean_roads(QgsTask):
    def __init__(self, parent, begin_computation_time, layer, layer_path, folder_name, feedback, task_name="Roads clean task"):
        super().__init__(task_name)
        self.parent = parent
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.layer_path = layer_path
        self.initial_layer_count = self.layer.featureCount()
        self.folder_name = folder_name
        self.exception = None
        self.break_on = False
        self.feedback = feedback
        

    def run(self):
       
        self.parent.progressBar.setValue(0)
        try:
            self.list_layer = []
            units = self.layer.crs().mapUnits()
            crs_grad = (units == 6)
            first_feature = next(self.layer.getFeatures())
            first_point = first_feature.geometry().centroid().asPoint()
            threshold = 1
            if crs_grad:
                threshold = convert_meters_to_degrees(
                    threshold, first_point.y())
            
            file_name = os.path.basename(self.layer_path)
            name, ext = os.path.splitext(file_name)
            
            cleaned_layer_name = f"{name}_c"
            cleaned_layer_error_name = f"{name}_e"

            threshold = str (threshold)
            # snapping geometries

            
            self.parent.setMessage('Cleaning layer of roads, step 1 of 3, snapping road links’ ends...')
            #feedback = CustomFeedback()

            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            result0 = processing.run("grass:v.clean", {'input': self.layer_path,
                                                        'type':[0,1,2,3,4,5,6],
                                                        'tool':[1],
                                                        'threshold':'1',
                                                        '-b':False,
                                                        '-c':False,
                                                        'output':'TEMPORARY_OUTPUT',
                                                        'error':'TEMPORARY_OUTPUT',
                                                        'GRASS_REGION_PARAMETER':None,
                                                        'GRASS_SNAP_TOLERANCE_PARAMETER':-1,
                                                        'GRASS_MIN_AREA_PARAMETER':0.0001,
                                                        'GRASS_OUTPUT_TYPE_PARAMETER':0,
                                                        'GRASS_VECTOR_DSCO':'',
                                                        'GRASS_VECTOR_LCO':'',
                                                        'GRASS_VECTOR_EXPORT_NOCAT':False},
                                                        feedback=self.feedback
                                                        )

            
            if self.break_on:
                return 0
            snapped_layer_path = result0['output']
            self.parent.progressBar.setValue(1)  
            QApplication.processEvents()   
                        
            #######################################################
            # first clean
            
            self.parent.setMessage('Cleaning layer of roads, step 2 of 3, breaking overlapping links...')
            result1 = processing.run("grass:v.clean", {
                'input': snapped_layer_path,
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
            self.parent.setMessage('Cleaning layer of roads, step 3 of 3, deleting duplicated links...')
            result2 = processing.run("grass:v.clean", {
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
            self.parent.textLog.append(f'<a>Number of errors: {error_count}</a>')

            # join errors
            self.parent.setMessage('Filtering ...')
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
            # Список требуемых полей и их характеристик
            required_fields = {
                'FCLASS': (QVariant.String, 28, None),  # (тип, длина, значение по умолчанию)
                'ONEWAY': (QVariant.String, 1, 'B'),
                'maxspeed': (QVariant.Int, 10, None)  # 64-bit int в QGIS обозначается просто Int
                }

            provider = filtered_layer.dataProvider()
            existing_field_names = [field.name() for field in filtered_layer.fields()]

            # Добавление недостающих полей
            for field_name, (field_type, length, default_value) in required_fields.items():
                if field_name not in existing_field_names:
                    new_field = QgsField(field_name, field_type, len=length)
                    provider.addAttributes([new_field])
            
            filtered_layer.updateFields()
            with edit(filtered_layer):
                for feature in filtered_layer.getFeatures():
                    updated = False
                    for field_name, (_, _, default_value) in required_fields.items():
                        if field_name in filtered_layer.fields().names():
                            if feature[field_name] is None and default_value is not None:
                                feature[field_name] = default_value
                                updated = True
                    if updated:
                        filtered_layer.updateFeature(feature)

            #####
            self.parent.setMessage('Saving ...')
            file_dir = self.folder_name

            ext = '.shp'
            self.output_file_name = f"{name}_topo_cleaned{ext}"

            output_path = os.path.join(file_dir, self.output_file_name)
            self.unique_output_path = self.get_unique_path(output_path)
            self.layer_name = os.path.splitext(
                os.path.basename(self.unique_output_path))[0]

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "UTF-8"

            QgsVectorFileWriter.writeAsVectorFormatV3(
                filtered_layer, 
                self.unique_output_path, 
                QgsProject.instance().transformContext(), 
                options)
            
            saved_layer = QgsVectorLayer(
                self.unique_output_path, self.layer_name, "ogr")
            self.saved_layer_count = saved_layer.featureCount()

            self.list_layer.append((self.unique_output_path, self.layer_name))
                        
            self.write_finish_info()
            self.parent.btnBreakOn.setEnabled(False)
            self.parent.close_button.setEnabled(True)
            
            return True

        except Exception as e:
            self.exception = e
            print (self.exception)
            self.parent.textLog.append(f'<a> {self.exception}</a>')
            #QApplication.setOverrideCursor(Qt.ArrowCursor)
            return False
        
        finally:
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            QApplication.processEvents()

    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Initial road network contains {self.initial_layer_count} links</a>')
        self.parent.textLog.append(f'<a>After topological cleaning the road network contains of {self.saved_layer_count} links</a>')
        self.parent.textLog.append(f'<a>Finished {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.parent.textLog.toPlainText()
        postfix = getDateTime()

        filelog_name = f'{self.folder_name}//log_roads_clean_{postfix}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)

        self.parent.textLog.append(f'"{self.layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')

        self.parent.setMessage(f'Finished')


    def cancel(self):
        try:
            #self.feedback.cancel()
            self.parent.progressBar.setValue(0)
            self.parent.setMessage(f'')
            self.break_on = True
            super().cancel()
        except Exception as e:
            print(f"Error during cancellation: {e}")
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
    
    def finished(self, result):
        for path_shp, name_layer in self.list_layer:
            saved_layer = QgsVectorLayer(path_shp, name_layer, "ogr")
            if saved_layer.isValid():
                QgsProject.instance().addMapLayer(saved_layer)
                
            
        