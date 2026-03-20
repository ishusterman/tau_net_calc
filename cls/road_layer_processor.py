import os
import csv

from PyQt5.QtCore import Qt

from qgis.core import (
                       QgsExpression, 
                       QgsFeatureRequest, 
                       QgsVectorLayer,
                       QgsVectorLayerJoinInfo)

from qgis.PyQt.QtCore import QVariant

from PyQt5.QtWidgets import (
                        QMessageBox,
                        QPushButton,
                        QApplication
                        )

    
class RoadLayerProcessor ():
    def __init__(self, 
                 parent,
                 layer, 
                 layer_name, 
                 osm
                 ):
        
        self.parent = parent
        self.layer = layer
        self.layer_name = layer_name

        self.osm = osm
        
        
        self.load_car_speed_by_link_type()

        self.link = "https://geosimlab.github.io/accessibility-calculator-tutorial/car_accessibility.html#building-database-for-car-accessibility-computation"            

    def set_Message (self, message, progress): 
        self.parent.setMessage (message)    
        self.parent.progressBar.setValue(progress)

    def run(self):
        #try:
            
            if not self.layer:
                return
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(current_dir, 'config')
            
            file_name1 = os.path.join(config_path, "car_speed_by_link_type.csv")
            file_name1 = file_name1.replace("\\", "/")
            uri = f"file:///{file_name1}?type=csv&maxFields=10000&detectTypes=yes&geomType=none&subsetIndex=no&watchFile=no"
            self.layer_speed_default = QgsVectorLayer(uri, "speed_default", "delimitedtext")
            #QgsProject.instance().addMapLayer(self.layer_speed_default)

            
            file_name2 = os.path.join(config_path, "directions.csv")
            file_name2 = file_name2.replace("\\", "/")
            uri = f"file:///{file_name2}?type=csv&maxFields=10000&detectTypes=yes&geomType=none&subsetIndex=no&watchFile=no"
            self.layer_directions_default = QgsVectorLayer(uri, "directions", "delimitedtext")
            #QgsProject.instance().addMapLayer(self.layer_directions_default)
            

            self.set_Message("Testing roads attributes (1 of 3)...", 1)
            self.get_oneway_fields3()

            self.set_Message("Testing roads attributes (2 of 3)...", 2)
            self.get_maxspeed_fields2()

            if self.osm:
                self.set_Message("Testing roads attributes (3 of 3)...", 3)
                self.get_fclass_fields3()

            result = self.finish_analizing_layers()

            return result, self.text_for_log


        #except Exception as e:
        #    error_message = f"An error occurred during analysis:\n{str(e)}\n\n{traceback.format_exc()}"
        #    print (error_message)
            #self.signals.error.emit(error_message)
    
        

    def get_fields_more_90(self, type, threshold=90):
        """
        Возвращает словарь полей из self.oneway_percent_dict, у которых процент > threshold.
        
        :param threshold: Пороговое значение процента (по умолчанию 90)
        :return: dict с полями и процентами
        """
        if type == "ONEWAY":
                obj = self.oneway_percent_dict
        else:
            obj = self.maxspeed_percent_dict

        result = {
                field: percent
                for field, percent in obj.items()
                if percent > threshold
            }

        if type == "ONEWAY":
            self.fields_above_90_oneway = result
        else:
            self.fields_above_90_maxspeed = result
        return result
        
    def fill_cmb_more_90(self, type, cmb):

        if type == "ONEWAY":
            fields_above_90 = self.fields_above_90_oneway
        else:
            fields_above_90 = self.fields_above_90_maxspeed

        cmb.clear()

        index_to_select = -1

        for i, (field_name, percent) in enumerate(fields_above_90.items()):
            display_text = f"{field_name} ({percent:.1f}%)"
            cmb.addItem(display_text, field_name)

            
            if field_name == type:
                index_to_select = i

        
        if index_to_select >= 0:
            cmb.setCurrentIndex(index_to_select)

    
    def check_ONEWAY_AND_MAXSPEED_more_90(self):
        """
        Проверяет, есть ли поля с процентом > 90% для ONEWAY и MAXSPEED.
        Если одно из них отсутствует — формирует сообщение с указанием отсутствующего типа.

        :return: tuple (result: bool, message: str)
        """
        missing = []

        oneway_fields = self.get_fields_more_90(type="ONEWAY")
        maxspeed_fields = self.get_fields_more_90(type="MAXSPEED")

        if not oneway_fields:
            missing.append("ONEWAY")
        if not maxspeed_fields:
            missing.append("MAXSPEED")

        if missing:
            # Преобразуем список в строку вида [ONEWAY] или [ONEWAY and MAXSPEED]
            missing_str = " and ".join(f"'{name}'" for name in missing)
            
            message = (
                f"TEST FAILED<br>"
                f"Candidate fields for {missing_str} not found<br>"
                f"Fix the table of road links and re-run<br>"
                f"See <a href='{self.link}'>tutorial</a> for more details"
            )
            return False, message
        else:
            return True, ""



    def find_exact_field_name(self, class_fields, field_name_lower):
        """
        Ищет поле по имени без учёта регистра и возвращает его оригинальное имя (с регистром), если найдено.

        :param field_name_lower: Имя поля в нижнем регистре
        :return: Полное имя поля с точным регистром, либо None, если не найдено
        """
        field_name_lower = field_name_lower.lower()
        for original_name, _ in class_fields:
            if original_name.lower() == field_name_lower:
                return original_name
        return None
    
    def get_exact_fclass_name(self):
        return self.find_exact_field_name (self.fclass_fields, "fclass")
    
    def get_exact_maxspeed_name(self):
        return self.find_exact_field_name (self.maxspeed_fields, "maxspeed")
    
    def get_exact_oneway_name(self):
        return self.find_exact_field_name (self.oneway_fields, "oneway")
    
        
    def get_message_valid_oneway_maxspeed_fclass(self):
        """
        Проверяет процент валидности значений в полях 'oneway' и 'maxspeed'.
        Возвращает предупреждение, если хотя бы одно поле содержит менее 99% валидных значений.
        В сообщении указывает только проблемные поля.
        """
        invalid_fields = []

        oneway_pct = next((v for k, v in self.oneway_percent_dict.items() if k.lower() == 'oneway'), -1)
        maxspeed_pct = next((v for k, v in self.maxspeed_percent_dict.items() if k.lower() == 'maxspeed'), -1)
        fclass_pct = next((v for k, v in self.best_fclass_percentage_dict.items() if k.lower() == 'fclass'), -1)

        if oneway_pct < 99:
            invalid_fields.append("'ONEWAY'")
        if maxspeed_pct < 99:
            invalid_fields.append("'MAXSPEED'")
        if fclass_pct < 99:
            invalid_fields.append("'FClass'")

        if invalid_fields:
            fields_str = " and ".join(invalid_fields)
            return (False,
                    f"TEST FAILED<br>"
                    f"OSM field FCLASS is found, but field(s) "
                    f"{fields_str} have more than 1% unidentified values<br>"
                    f"Fix the table of road links and re-run<br>"
                    f"See <a href='{self.link}'>tutorial</a> for more details"
                    )
        
        if not (invalid_fields):
            return (True,
                    f"TEST PASSED<br>"
                    "Source of the road layer: 'ONEWAY', 'MAXSPEED' and 'FClass' have less than 1% "
                    "of values that must be substituted by the defaults"
                    )
        
        return None, None
        

    def load_car_speed_by_link_type(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')

        self.file_path_road_speed_default = os.path.join(
            config_path, "car_speed_by_link_type.csv")
        
        speed_values = []
        self.link_types = []

        with open(self.file_path_road_speed_default, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                type_road = row['link_type']
                speed_default = int(row['speed_km_h'])
                speed_values.append(speed_default)
                self.link_types.append(type_road)
                

        self.min_speed_value = min(speed_values)
        self.max_speed_value = max(speed_values)    
        self.link_types = list(set(self.link_types))

    
    def get_maxspeed_fields2(self):
        """
        Возвращает список имён полей, значения которых:
        - числовые (int, double и т.п.)
        - либо NULL, либо равны 0, либо находятся в пределах [min_speed_value, max_speed_value]
        """
        numeric_types = {
            QVariant.Int, QVariant.Double,
            QVariant.LongLong, QVariant.UInt, QVariant.ULongLong
        }

        total_count = self.layer.featureCount()
        if total_count == 0:
            self.maxspeed_fields = []
            self.best_maxspeed_field = None
            self.best_maxspeed_percentage = -1
            return [], None

        result = []
        max_percentage = -1.0
        max_field = None

        for field in self.layer.fields():
            QApplication.processEvents()
            
            field_name = field.name()

            if self.osm:
                if field_name.lower() != "maxspeed":
                    continue

            if field.type() not in numeric_types:
                continue
            

            expr_str = (
                f'"{field_name}" = 0 OR '
                f'("{field_name}" >= {self.min_speed_value} AND "{field_name}" <= {self.max_speed_value})'
            )
            expr = QgsExpression(expr_str)
            request = QgsFeatureRequest().setFilterExpression(expr.expression())
            valid_count = sum(1 for _ in self.layer.getFeatures(request))

            percentage = (valid_count / total_count) * 100
            if percentage > 0:
                result.append((field_name, percentage))
            if percentage > max_percentage:
                max_percentage = percentage
                max_field = field_name

        self.maxspeed_fields = result
        self.best_maxspeed_field = max_field
        self.best_maxspeed_percentage = round(max_percentage, 2) if max_field else -1
        self.maxspeed_percent_dict = {fname: percent for fname, percent in self.maxspeed_fields}

        return result, max_field

    def get_oneway_fields3(self):
        
        total_count = self.layer.featureCount()
        result = []
        max_field = None
        max_percentage = -1.0

        join_field = "direction_type"
        target_field = "comment"
        join_prefix = "direction_"
        joined_field = f"{join_prefix}{target_field}"

        for field in self.layer.fields():
            QApplication.processEvents()
            
            field_name = field.name()

            if self.osm:
                if field_name.lower() != "oneway":
                    continue
            if field.typeName().lower() not in {'string', 'text'}:
                continue
                
            
            # Удалить предыдущий join (по ID слоя)
            self.layer.removeJoin(self.layer_directions_default.id())

            # Создать новый join
            join_info = QgsVectorLayerJoinInfo()
            join_info.setJoinLayer(self.layer_directions_default)
            join_info.setJoinFieldName (join_field)
            join_info.setTargetFieldName (field_name)
            join_info.setPrefix (join_prefix)
            join_info.setJoinFieldNamesSubset([target_field]) 
            join_info.setUsingMemoryCache(True)
            self.layer.addJoin(join_info)
                
            valid_count = 0
            
            expr_str = f'("{joined_field}" IS NOT NULL)'
            expr = QgsExpression(expr_str)
            request = QgsFeatureRequest().setFilterExpression(expr.expression())
            valid_count = sum(1 for _ in self.layer.getFeatures(request))
            
            percentage = (valid_count / total_count) * 100

            if percentage > 0:
                result.append((field_name, percentage))

            if percentage > max_percentage:
                max_percentage = percentage
                max_field = field_name

            # Удалить join после проверки
            self.layer.removeJoin(self.layer_directions_default.id())

        self.oneway_fields = result
        self.best_oneway_field = max_field
        self.best_oneway_percentage = round(max_percentage, 2) if max_field else -1
        self.oneway_percent_dict = {fname: percent for fname, percent in self.oneway_fields}
                       
        return result, max_field
    
    def get_fclass_fields3(self):
        
        total_count = self.layer.featureCount()
        result = []
        max_field = None
        max_percentage = -1.0

        join_field = "link_type"
        target_field = "speed_km_h"
        join_prefix = "speed_default_"
        joined_speed_field = f"{join_prefix}{target_field}"

        for field in self.layer.fields():
            QApplication.processEvents()
            
            field_name = field.name()

            if self.osm:
                if field_name.lower() != "fclass":
                    continue

            if field.typeName().lower() not in {'string', 'text'}:
                continue
            
            # Удалить предыдущий join (по ID слоя)
            self.layer.removeJoin(self.layer_speed_default.id())

            # Создать новый join
            join_info = QgsVectorLayerJoinInfo()
            join_info.setJoinLayer(self.layer_speed_default)
            join_info.setJoinFieldName (join_field)
            join_info.setTargetFieldName (field_name)
            join_info.setPrefix (join_prefix)
            join_info.setJoinFieldNamesSubset([target_field]) 
            join_info.setUsingMemoryCache(True)
            self.layer.addJoin(join_info)
                
            valid_count = 0
            
            expr_str = f'("{joined_speed_field}" IS NOT NULL)'
            expr = QgsExpression(expr_str)
            request = QgsFeatureRequest().setFilterExpression(expr.expression())
            valid_count = sum(1 for _ in self.layer.getFeatures(request))
           
            percentage = (valid_count / total_count) * 100

            if percentage > 0:
                result.append((field_name, percentage))

            if percentage > max_percentage:
                max_percentage = percentage
                max_field = field_name

            # Удалить join после проверки
            self.layer.removeJoin(self.layer_speed_default.id())

        self.fclass_fields = result
        
        self.best_fclass_field = max_field
        self.best_fclass_percentage = round(max_percentage, 2) if result else -1
        self.best_fclass_percentage_dict = {fname: percent for fname, percent in self.fclass_fields}

        return result, max_field
    
    def finish_analizing_layers (self):
                        
        self.parent.setMessage("")
        self.parent.progressBar.setValue(0)
        #self.parent.run_button.setEnabled(True)
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle("Road attributes test")
        
        #self.parent.textLog.append (f"Testing the layer of roads: {self.layer_name}")

        if self.osm:
                            
            result, message = self.get_message_valid_oneway_maxspeed_fclass()
            if result:
                
                self.parent.lblOSM.setText ('PASSED')
                exact_maxspeed_name = self.get_exact_maxspeed_name()
                self.parent.cmbFieldsSpeed.addItem(exact_maxspeed_name, exact_maxspeed_name)
                exact_oneway_name = self.get_exact_oneway_name()
                self.parent.cmbFieldsDirection.addItem(exact_oneway_name, exact_oneway_name)
                
                #msgBox.setText(message)
                #self.parent.textLog.append (message)
                #self.parent.textLog.append ("-----------")     
                self.text_for_log = message
                result = True
                #ok_button = QPushButton("Ok")
                #msgBox.addButton(ok_button, QMessageBox.AcceptRole)
                
                
                #msgBox.exec_()
                #if msgBox.clickedButton() == ok_button:
                #    return 0
            else:
                
                lbl_text = 'FAILED'
                self.parent.lblOSM.setText(lbl_text)
                msgBox.setText(message)
                #self.parent.textLog.append (lbl_text)
                #self.parent.textLog.append (message)
                #self.parent.textLog.append ("-----------")
                self.text_for_log = f'{lbl_text}\n{message}'
                result = False
                stop_button = QPushButton("Cancel")
                msgBox.addButton(stop_button, QMessageBox.AcceptRole)
                msgBox.exec_()
                if msgBox.clickedButton() == stop_button:
                    return 0
        
        #No OSM"
        else:
            
            result, message = self.check_ONEWAY_AND_MAXSPEED_more_90()
            if result:
                
                self.fill_cmb_more_90(type = "MAXSPEED", cmb = self.parent.cmbFieldsSpeed)
                self.fill_cmb_more_90(type = "ONEWAY", cmb = self.parent.cmbFieldsDirection)
                
                self.parent.cmbFieldsDirection.setEnabled(True)
                self.parent.cmbFieldsSpeed.setEnabled(True)
                lbl_text = 'PASSED'
                log_text = f"Found fields for 'Direction' and 'Speed'"
                self.parent.lblOSM.setText (lbl_text)
                #self.parent.textLog.append ("TEST PASSED")                
                #self.parent.textLog.append (log_text)                
                #self.parent.textLog.append ("-----------")                
                self.text_for_log = f'TEST PASSED\n {log_text}'
                result = True                           

            else:
                
                lbl_text = 'FAILED'
                self.parent.lblOSM.setText(lbl_text)
                msgBox.setText(message)
                #self.parent.textLog.append (lbl_text)
                #self.parent.textLog.append (message)
                #self.parent.textLog.append ("-----------")
                self.text_for_log = f'{lbl_text}\n{message}' 
                result = False                                          
                stop_button = QPushButton("Cancel")
                msgBox.addButton(stop_button, QMessageBox.AcceptRole)
                msgBox.exec_()
                if msgBox.clickedButton() == stop_button:
                   
                    return 0 
             
        self.parent.progressBar.setValue(0)
        return result