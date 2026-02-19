import os
import processing
from datetime import datetime

from PyQt5.QtCore import Qt

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
    QgsField,
    edit
    )

from qgis.PyQt.QtCore import QVariant, QObject, pyqtSignal

from PyQt5.QtWidgets import QMessageBox

from common import convert_meters_to_degrees, create_and_check_field, get_unique_path


class TaskSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    set_message = pyqtSignal(str)
    save_log = pyqtSignal(bool)
    add_layers = pyqtSignal(list) 
    change_button_status = pyqtSignal(bool) 
    

class cls_clean_roads(QgsTask):
    
    def __init__(self, 
                 begin_computation_time, 
                 layer, 
                 layer_path, 
                 layer_name, 
                 folder_name, 
                 osm_id_field,
                 task_name="Roads clean task"):
        
        super().__init__(task_name)
        self.signals = TaskSignals()
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.layer_path = layer_path
        self.layer_name = layer_name
        self.initial_layer_count = self.layer.featureCount()
        self.folder_name = folder_name
        self.osm_id_field = osm_id_field
        self.exception = None
        self.break_on = False
        
    def run(self):
       
        self.signals.progress.emit(0)
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

            
            self.signals.set_message.emit('Cleaning layer of roads, step 1 of 3, snapping road links’ ends...')
            
            result0 = processing.run("grass:v.clean", {'input': self.layer_path,
                                                        'type':[1],
                                                        'tool':[1],
                                                        'threshold':'0.5',
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
                                                          )

            
            if self.break_on:
                return 0
            snapped_layer_path = result0['output']
            self.signals.progress.emit(1) 

            # Добавляем в проект
            # Добавляем в проект
            snapped_layer = QgsVectorLayer(snapped_layer_path, f"{name}_snap", "ogr")
            QgsProject.instance().addMapLayer(snapped_layer)

            errors0_path = result0['error']
            errors0_layer = QgsVectorLayer(errors0_path, f"{name}_snap_errors", "ogr")
            QgsProject.instance().addMapLayer(errors0_layer)
                                    
            #######################################################
            # first clean
            
            self.signals.set_message.emit('Cleaning layer of roads, step 2 of 3, breaking overlapping links...')
            result1 = processing.run("grass:v.clean", {
                'input': snapped_layer_path,
                'type': [1],
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
            self.signals.progress.emit(2)
            
            cleaned_layer_path1 = result1['output']

            clean1_layer = QgsVectorLayer(cleaned_layer_path1, f"{name}_break", "ogr")
            QgsProject.instance().addMapLayer(clean1_layer)
            errors1_path = result1['error']
            errors1_layer = QgsVectorLayer(errors1_path, f"{name}_break_errors", "ogr")
            QgsProject.instance().addMapLayer(errors1_layer)

            
            # second clean
            self.signals.set_message.emit('Cleaning layer of roads, step 3 of 3, deleting duplicated links...')
            result2 = processing.run("grass:v.clean", {
                'input': cleaned_layer_path1,
                'type': [1],
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
            self.signals.progress.emit(3)
            cleaned_layer_2_path = result2['output']
            cleaned_layer_2 = QgsVectorLayer(
                cleaned_layer_2_path, cleaned_layer_name, "ogr")
            errors_layer_2_path = result2['error']
            errors_layer_2 = QgsVectorLayer(
                errors_layer_2_path, cleaned_layer_error_name, "ogr")
            error_count = len(list(errors_layer_2.getFeatures()))
            self.signals.log.emit(f'<a>Number of errors: {error_count}</a>')


            QgsProject.instance().addMapLayer(cleaned_layer_2)
            QgsProject.instance().addMapLayer(errors_layer_2)


            # join errors

            # 1. Join errors_layer_2 к cleaned_layer_2 по полю "cat"
            join_info = QgsVectorLayerJoinInfo()
            join_info.setJoinLayer(errors_layer_2)
            join_info.setJoinFieldName("cat")
            join_info.setTargetFieldName("cat")
            join_info.setPrefix("e_")
            join_info.setJoinFieldNamesSubset(["fid"])  
            cleaned_layer_2.addJoin(join_info)
            cleaned_layer_2.triggerRepaint()

            # 2. Создать новый memory-слой для отфильтрованных фич
            geometry_type = cleaned_layer_2.wkbType()
            crs = cleaned_layer_2.crs().authid()
            filtered_layer = QgsVectorLayer(f"{QgsWkbTypes.displayString(geometry_type)}?crs={crs}", "Filtered roads", "memory")
            filtered_provider = filtered_layer.dataProvider()

            # 3. Копировать только поля из оригинального слоя (без виртуальных e_*)
            #orig_fields = cleaned_layer_2.fields()
            orig_fields = self.layer.fields()
            filtered_provider.addAttributes(orig_fields)
            filtered_layer.updateFields()

            # 4. Отобрать только фичи, у которых нет ошибок (т.е. не присоединилось по cat)
            expression = QgsExpression('"e_fid" IS NULL')
            request = QgsFeatureRequest(expression)

            # 5. Копировать геометрию и атрибуты
            new_features = []
            for feature in cleaned_layer_2.getFeatures(request):
                new_feature = QgsFeature()
                new_feature.setGeometry(feature.geometry())
                new_feature.setFields(orig_fields)
                new_feature.setAttributes([feature[field.name()] for field in orig_fields])
                new_features.append(new_feature)

            filtered_provider.addFeatures(new_features)
            filtered_layer.updateExtents()
                        
            self.signals.progress.emit(5)
            
            
            #####
            # Список требуемых полей и их характеристик
            """
            required_fields = {
                'FCLASS': (QVariant.String, 28, 'unclassified'), 
                'ONEWAY': (QVariant.String, 1, 'B'),
                'maxspeed': (QVariant.Int, 10, 30) 
                }
            
            provider = filtered_layer.dataProvider()


            # Проверка поля ONEWAY, только если это исходное имя без суффиксов
            for field in filtered_layer.fields():
                if field.name().lower() == 'oneway':
                    base_name = field.name()
                    oneway_field_index = filtered_layer.fields().indexOf(base_name)
                    found_invalid = False

                    for feature in filtered_layer.getFeatures():
                        val = feature[oneway_field_index]
                        if val not in ('T', 'F', 'B'):
                            found_invalid = True
                            break

                    if found_invalid:
                        # Все текущие имена
                        existing_names = [f.name().lower() for f in filtered_layer.fields()]
                        new_name = base_name + "_1"
                        counter = 1
                        while new_name.lower() in existing_names:
                            counter += 1
                            new_name = f"{base_name}_{counter}"

                        provider.renameAttributes({oneway_field_index: new_name})
                        filtered_layer.updateFields()
                        self.signals.log.emit(f'<b>The "{field.name()}" field of the "{self.layer_name}" table contains irregular values and is renamed to "{new_name}"</b>')
                        self.signals.log.emit(f'<b>A new field "ONEWAY" with the default values of "B" is created</b>')
                        
                    break


            existing_field_names = [field.name() for field in filtered_layer.fields()]
            existing_field_names_lower = [name.lower() for name in existing_field_names]

            list_field_added = []
            new_fields = []

            for field_name, (field_type, length, default_value) in required_fields.items():
                if field_name.lower() not in existing_field_names_lower:
                    new_field = QgsField(field_name, field_type)
                    new_field.setLength(length)
                    new_fields.append(new_field)
                    list_field_added.append(field_name)

            if new_fields:
                provider.addAttributes(new_fields)
                filtered_layer.updateFields()

                field_indexes = {f.name(): i for i, f in enumerate(filtered_layer.fields())}
                new_field_indexes = {name: field_indexes[name] for name in list_field_added}

                attr_updates = {}

                for feature in filtered_layer.getFeatures():
                    fid = feature.id()
                    attrs = feature.attributes()

                    updated_fields = {}
                    for field_name in list_field_added:
                        idx = new_field_indexes[field_name]
                        _, _, default_value = required_fields[field_name]
                        if attrs[idx] is None and default_value is not None:
                            updated_fields[idx] = default_value

                    if updated_fields:
                        attr_updates[fid] = updated_fields

                if attr_updates:
                    with edit(filtered_layer):
                        # Массовое обновление атрибутов
                        success = provider.changeAttributeValues(attr_updates)
                        if not success:
                            print("Failed to update attributes via provider")

                added_fields_str = ", ".join(list_field_added)
                self.signals.log.emit(f'<b>Fields {added_fields_str} have been added and default values assigned</b>')

            #####
            """
            if self.osm_id_field == "":
                self.osm_id_field = "link_id"

            filtered_layer, count_modified, insert_field, name_field  = create_and_check_field(filtered_layer, self.osm_id_field, type = 'link')
            if insert_field:
                self.signals.log.emit(f'<b>Link ID field "{name_field}" is created as a first field in the cleaned table</b>')
            if not insert_field and count_modified > 0:
                self.signals.log.emit(f'<b>{count_modified} of the link IDs are not unique, updated</b>')

            self.signals.set_message.emit('Saving ...')
            file_dir = self.folder_name

            ext = '.shp'
            self.output_file_name = f"{name}_cleaned{ext}"

            output_path = os.path.join(file_dir, self.output_file_name)
            self.unique_output_path = get_unique_path(output_path)
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

            self.signals.change_button_status.emit(True)
                        
            return True

        except Exception as e:
            self.exception = e
            print (self.exception)
            return False
    
    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.signals.log.emit(f'<a>Initial road network contains {self.initial_layer_count} links</a>')
        self.signals.log.emit(f'<a>After topological cleaning the road network contains of {self.saved_layer_count} links</a>')
        self.signals.log.emit(f'<a>Finished {after_computation_str}</a>')
        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.signals.log.emit(f'<a>Processing time: {duration_without_microseconds}</a>')
       
        self.signals.save_log.emit(True)

        self.signals.log.emit(f'"{self.layer_name}.shp" in <a href="file:///{self.folder_name}" target="_blank" >folder</a>')

        self.signals.set_message.emit(f'Finished')
        self.signals.add_layers.emit(self.list_layer)


    def cancel(self):
        try:
            
            self.signals.progress.emit(0)
            self.signals.set_message.emit('')
            self.break_on = True
            super().cancel()
        except Exception as e:
            print(f"Error during cancellation: {e}")
            return
     
        