import os
import csv

from PyQt5.QtCore import Qt

from qgis.core import (
                       QgsExpression, 
                       QgsFeatureRequest, 
                       QgsVectorLayer,
                       QgsVectorLayerJoinInfo)

from PyQt5.QtWidgets import (
                        QMessageBox,
                        QPushButton,
                        QApplication
                        )
    
class RoadLayerProcessor ():
    def __init__(self, 
                 parent,
                 layer,                  
                 field_name_direction,
                 field_name_maxspeed
                 ):
        
        self.parent = parent
        self.layer = layer        
        

        self.field_name_direction = field_name_direction
        self.field_name_maxspeed = field_name_maxspeed

        self.load_car_speed_by_link_type()
        self.link = "https://geosimlab.github.io/accessibility-calculator-tutorial/car_accessibility.html#building-database-for-car-accessibility-computation"            

    def set_Message (self, message, progress): 
        self.parent.setMessage (message)    
        self.parent.progressBar.setValue(progress)

    def run(self):
        
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
            
    
            self.set_Message("Testing roads attributes (1 of 2)...", 1)
            self.get_oneway_fields(self.field_name_direction)

            self.set_Message("Testing roads attributes (2 of 2)...", 2)
            self.get_maxspeed_fields(self.field_name_maxspeed)

            """
            if self.osm:
                self.set_Message("Testing roads attributes (3 of 3)...", 3)
                self.get_fclass_fields()
            """
            result = self.finish_analizing_layers()

            return result, self.oneway_percentage, self.maxspeed_percentage
        
    def get_message_valid_oneway_maxspeed_fclass(self):
      
        invalid_fields = []

        oneway_pct = self.oneway_percentage
        maxspeed_pct = self.maxspeed_percentage
        #fclass_pct = self.fclass_percentage

        if oneway_pct < 99:
            invalid_fields.append(f"'{self.field_name_direction}'")
        if maxspeed_pct < 99:
            invalid_fields.append(f"'{self.field_name_maxspeed}'")
        #if fclass_pct < 99:
        #    invalid_fields.append("'FClass'")

        if invalid_fields:
            fields_str = " and ".join(invalid_fields)
            return (False, 
                    f"TEST FAILED<br>"
                    f"Field(s) {fields_str} have more than 1% unidentified values<br>"
                    f"Fix the table of road links and re-run<br>"
                    f"See <a href='{self.link}'>tutorial</a> for more details"
                    )
        
        if not (invalid_fields):
            return (True,
                    f"TEST PASSED<br>"
                    "Source of the road layer: 'ONEWAY', 'MAXSPEED' have less than 1% "
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
    
    def get_maxspeed_fields(self, field_name_check):
        total_count = self.layer.featureCount()
        if total_count == 0:
            self.maxspeed_percentage = -1
            return False
        
        for field in self.layer.fields():
            QApplication.processEvents()
            field_name = field.name()
            if field_name.lower() != field_name_check.lower():
                    continue

            expr_str = (
                f'"{field_name}" = 0 OR '
                f'("{field_name}" >= {self.min_speed_value} AND "{field_name}" <= {self.max_speed_value})'
            )
            expr = QgsExpression(expr_str)
            request = QgsFeatureRequest().setFilterExpression(expr.expression())
            valid_count = sum(1 for _ in self.layer.getFeatures(request))
            
            percentage= (valid_count / total_count) * 100
            
        self.maxspeed_percentage = percentage
        return True
       
    def get_oneway_fields(self, field_name_check):
        
        total_count = self.layer.featureCount()
        if total_count == 0:
            self.oneway_percentage = -1
            return False
        
        join_field = "direction_type"
        target_field = "comment"
        join_prefix = "direction_"
        joined_field = f"{join_prefix}{target_field}"

        for field in self.layer.fields():
            QApplication.processEvents()
            
            field_name = field.name()
            if field_name.lower() != field_name_check.lower():
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
            
            expr_str = f'("{joined_field}" IS NOT NULL)'
            expr = QgsExpression(expr_str)
            request = QgsFeatureRequest().setFilterExpression(expr.expression())
            valid_count = sum(1 for _ in self.layer.getFeatures(request))
            percentage = (valid_count / total_count) * 100
            # Удалить join после проверки
            self.layer.removeJoin(self.layer_directions_default.id())
        
        self.oneway_percentage = percentage
                       
        return True
    
    def finish_analizing_layers (self):
                        
        self.parent.setMessage("")
        self.parent.progressBar.setValue(0)
        #self.parent.run_button.setEnabled(True)
        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle("Road attributes test")
        
        result, message = self.get_message_valid_oneway_maxspeed_fclass()
        if result:
                pass
                #self.parent.lblOSM.setText ('PASSED')
                
        else:
                #self.parent.lblOSM.setText('FAILED')
                msgBox.setText(message)                
                stop_button = QPushButton("Cancel")
                msgBox.addButton(stop_button, QMessageBox.AcceptRole)
                msgBox.exec_()
                if msgBox.clickedButton() == stop_button:
                    result = False

        self.parent.progressBar.setValue(0)
        return result