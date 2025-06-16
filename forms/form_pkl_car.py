import os
import csv
import webbrowser
import re
import urllib.parse
import configparser

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer,
                       )

from PyQt5.QtWidgets import (QDialogButtonBox,
                            QFileDialog,
                            QMessageBox,
                            QPushButton,
                            QTableWidgetItem,
                            QDialog
                            )

from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QEvent,
                          QVariant,
                          QUrl
                          )


from PyQt5.QtGui import QRegExpValidator, QDesktopServices

from qgis.PyQt import uic

from pkl_car import pkl_car
from common import (get_qgis_info, 
                    check_file_parameters_accessibility,
                    showAllLayersInCombo_Line,
                    showAllLayersInCombo_Point_and_Polygon)

from road_layer_processor import RoadLayerProcessor

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'pkl_car.ui')
)


class form_pkl_car(QDialog, FORM_CLASS):
    def __init__(self,
                 title,
                 ):
        super().__init__()
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        fix_size = 12 * self.txtSpeed.fontMetrics().width('x')
        fix_size2 = 22 * self.txtSpeed.fontMetrics().width('x')

        self.txtSpeed.setFixedWidth(fix_size)

        self.cmbLayersRoad_type_road.setFixedWidth(fix_size2)
        self.cmbFieldsDirection.setFixedWidth(fix_size2)
        self.cmbFieldsSpeed.setFixedWidth(fix_size2)

        self.splitter.setSizes([int(self.width() * 0.70), int(self.width() * 0.30)])
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.lblOSM_need_update = False

        self.progressBar.setValue(0)

        self.cbDirection.addItems(["T", "F", "B"])
        self.cbDirection.setCurrentIndex(self.cbDirection.findText("B"))
        
        showAllLayersInCombo_Line(self.cbRoads)
        self.toolButtonRoads.clicked.connect(lambda: self.open_file_dialog (type = "roads"))
        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog (type = "buildings"))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        showAllLayersInCombo_Point_and_Polygon(self.cmbLayers_buildings)

        self.cmbLayers_buildings.installEventFilter(self)

        self.cmbFieldsSpeed.installEventFilter(self)
        self.cmbLayers_buildings.installEventFilter(self)
        self.cmbFieldsDirection.installEventFilter(self)
        self.cmbLayers_buildings_fields.installEventFilter(self)

        self.btnBreakOn.clicked.connect(self.set_break_on)

        self.run_button = self.buttonBox.addButton(
            "Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton(
            "Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton(
            "Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)
        
        # Отключаем все существующие сигналы
        try:
            self.test_button.clicked.disconnect()
        except:
            pass
        self.test_button.clicked.connect(self.on_test_button_clicked)

        # floating, two digit after dot
        regex3 = QRegExp(r"^\d+(\.\d{1,2})?$")
        int_validator3 = QRegExpValidator(regex3)

        self.txtSpeed.setValidator(int_validator3)
        self.layer_road = self.get_layer_road()
        self.layer_buidings = self.get_layer_buildings()

        self.fillComboBoxFields_Id(self.cmbLayers_buildings,
                                   self.cmbLayers_buildings_fields,
                                   "osm_id"
                                   )

        self.cmbLayers_buildings.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers_buildings,
             self.cmbLayers_buildings_fields,
             "osm_id")
             )

        self.ParametrsShow()
        self.onLayerRoadChanged()
        self.cbRoads.currentIndexChanged.connect(self.onLayerRoadChanged)

        self.cmbFieldsSpeed.currentIndexChanged.connect(self.onFieldChanged)
        self.cmbFieldsDirection.currentIndexChanged.connect(self.onFieldChanged)

        self.textInfo.anchorClicked.connect(self.open_file)
        
        self.table1.setEditTriggers(self.table1.NoEditTriggers)
        self.table1.setColumnCount(2) 
        self.table1.setHorizontalHeaderLabels(['Link Type', 'Speed km/h'])
        
        self.table2.setEditTriggers(self.table2.NoEditTriggers)
        self.table2.setColumnCount(2) 
        self.table2.setHorizontalHeaderLabels(['Hour', 'CDI'])

        self.read_road_speed_default()
        self.read_factor_speed_by_hour()
        self.fill_table(self.table1,self.type_road_speed_default)    
        self.fill_table(self.table2, self.factor_speed_by_hour, mode = "CDI")    
        self.show_info()
        
        self.checkBox_show_tables.toggled.connect(self.toggle_tables_visibility)
        self.groupBox_tables.setVisible(False)

        self.cmbLayersRoad_type_road.setEnabled(False)
        self.cmbFieldsDirection.setEnabled(False)
        self.cmbFieldsSpeed.setEnabled(False)
        

    def toggle_tables_visibility(self, checked):
        self.groupBox_tables.setVisible(checked)
        
          
    def get_layer_road(self):
        selected_item = self.cbRoads.currentText()
        
        if os.path.isfile(selected_item):
            layer_road = QgsVectorLayer(selected_item, "LayerRoad", "ogr")
        else:
            layers = QgsProject.instance().mapLayersByName(selected_item)
            if layers:  
                layer_road = layers[0]
            else:
                layer_road = None  

        return layer_road
    
    def get_layer_buildings(self):
        selected_item = self.cmbLayers_buildings.currentText()
        if os.path.isfile(selected_item):
            layer_building = QgsVectorLayer(selected_item, "LayerBuildings", "ogr")
        else:
            layers = QgsProject.instance().mapLayersByName(selected_item)
            if layers:  
                layer_building = layers[0]
            else:
                layer_building = None  
        return layer_building

    def open_file_dialog(self, type):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose a File",
            "",
            "Shapefile (*.shp);"
        )

        if file_path:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                if type == "roads":
                    self.cbRoads.addItem(file_path, file_path)
                    index = self.cbRoads.findText(file_path)
                    self.cbRoads.setCurrentIndex(index)
                    self.onLayerRoadChanged()
                else:
                    self.cmbLayers_buildings.addItem(file_path, file_path)
                    index = self.cmbLayers_buildings.findText(file_path)
                    self.cmbLayers_buildings.setCurrentIndex(index)

    def show_stage_testing (self, message, progress):
        self.setMessage (message)    
        self.progressBar.setValue(progress)
    
    def on_test_button_clicked(self):   
        
        self.test_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.progressBar.setMaximum(3)
        self.layer_road = self.get_layer_road()
        self.layer_road_name = self.cbRoads.currentText()
              

        self.processor_road = RoadLayerProcessor(self,
                                                 self.layer_road, 
                                                 self.layer_road_name, 
                                                 mode = "pkl")
        
        self.lblOSM_need_update = self.processor_road.run()
        

    def onFieldChanged(self):
        pass
        #if self.lblOSM_need_update:
        #    message_type = "Source of the road layer: <b>Unknown</b>;"
        #    self.lblOSM.setText (f"{message_type} Direction: <b>{self.cmbFieldsDirection.currentData()}</b>, Speed <b>{self.cmbFieldsSpeed.currentData()}</b>")

    def onLayerRoadChanged(self):

        self.test_button.setEnabled(True)
        self.cmbFieldsSpeed.clear()
        self.cmbFieldsDirection.clear()
        self.cmbLayersRoad_type_road.clear()
        self.cmbLayersRoad_type_road.setEnabled(False)
        self.cmbFieldsDirection.setEnabled(False)
        self.cmbFieldsSpeed.setEnabled(False)
        self.lblOSM.setText ("")

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields, field_name_default):
        obj_layer_fields.clear()
        
        
        self.layer_buidings = self.get_layer_buildings()
        if not self.layer_buidings:
            return
        layer = self.layer_buidings
        fields = layer.fields()
        field_name_default_exists = False

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong):
                # add numeric fields
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == field_name_default:
                    field_name_default_exists = True
            
        if field_name_default_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == field_name_default:
                    obj_layer_fields.setCurrentIndex(i)
                    break

    def open_file(self, url):
        file_path = url.toLocalFile()
        if os.path.isfile(file_path):
            os.startfile(file_path)
        self.read_road_speed_default()
        self.read_factor_speed_by_hour()
        self.show_info()
    
    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def on_run_button_clicked(self):

        if not self.cmbFieldsSpeed.currentData() or not self.cmbFieldsDirection.currentData():
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle("Information")
            message = 'Attributes not tested yet! Push "Test attributes" button to pass the test'
            msgBox.setText(message)
            ok_button = QPushButton("Ok")
            msgBox.addButton(ok_button, QMessageBox.AcceptRole)
            msgBox.exec_()
            if msgBox.clickedButton() == ok_button:
                return 0  
            
        self.run_button.setEnabled(False)

        self.break_on = False

        self.layer_road = self.get_layer_road()
        self.layer_buildings = self.get_layer_buildings()

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        
        if not (self.check_layer_buildings()):
            self.run_button.setEnabled(True)
            return 0
        
        self.folder_name = f'{self.txtPathToProtocols.text()}'

        self.saveParameters()
        self.readParameters()
        
        if not (self.check_type_layer_road()):
            self.run_button.setEnabled(True)
            return 0

        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)

        self.save_var()

        self.close_button.setEnabled(False)
        
        self.tabWidget.setCurrentIndex(1)
        self.textLog.append("<a style='font-weight:bold;'>[System]</a>")
        qgis_info = get_qgis_info()

        info_str = "<br>".join(
            [f"{key}: {value}" for key, value in qgis_info.items()])
        self.textLog.append(f'<a> {info_str}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        self.textLog.append(f"<a> Layer of buildings: {self.layer_origins_path}</a>")

        self.textLog.append(f"<a> Layer of roads: {self.config['Settings']['Roads_car_pkl']}</a>")

        self.message_for_log = f"Direction: <b>{self.cmbFieldsDirection.currentText()}</b>, Speed: <b>{self.cmbFieldsSpeed.currentText()}</b>"
        if self.cmbLayersRoad_type_road.currentText() == "":
            message_type = "Source of the road layer: <b>Unknow</b>;"
            self.message_for_log = f'{message_type} {self.message_for_log}'
        else:
            message_type = "Source of the road layer: <b>OSM</b>;"
            self.message_for_log = f'{message_type} {self.message_for_log}, Link type: <b>{self.cmbLayersRoad_type_road.currentText()}<b>'
        self.textLog.append(self.message_for_log)        
        
        self.textLog.append(f"<a> Default direction: {self.default_direction} </a>")
        self.textLog.append(f"<a> Default speed: {self.config['Settings']['speed_car_pkl']} km/h</a>")
        

        self.textLog.append(f"<a> Folder to store car database: {self.config['Settings']['pathtoprotocols_car_pkl']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        pkl_car_calc = pkl_car(self)
        pkl_car_calc.create_files()

        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        url = "https://ishusterman.github.io/tutorial/building_pkl.html#building-database-for-car-routing"
        webbrowser.open(url)

    def showFoldersDialog(self, obj, mode_road=False):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
            if mode_road:
                self.onLayerRoadChanged()

        else:
            obj.setText(obj.text())

    def read_factor_speed_by_hour(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')

        self.file_path_factor_speed_by_hour = os.path.join(
            config_path, "cdi_index.csv")

        self.factor_speed_by_hour = {}

        with open(self.file_path_factor_speed_by_hour, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hour_item = row['hour']
                factor_item = row['cdi']
                self.factor_speed_by_hour[hour_item] = factor_item

    def read_road_speed_default(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')
        
        self.file_path_road_speed_default = os.path.join(
            config_path, "car_speed_by_link_type.csv")
        
        self.type_road_speed_default = {}

        with open(self.file_path_road_speed_default, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                type_road = row['link_type']
                speed_default = int(row['speed_km_h'])
                self.type_road_speed_default[type_road] = speed_default

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_car_pkl = os.path.join(project_directory, f'{project_name}_pkl')
        PathToProtocols_car_pkl = os.path.normpath(PathToProtocols_car_pkl)


        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToProtocols_car_pkl' not in self.config['Settings'] or self.config['Settings']['PathToProtocols_car_pkl'] == "C:/":
            self.config['Settings']['PathToProtocols_car_pkl'] = PathToProtocols_car_pkl
        self.config['Settings']['PathToProtocols_car_pkl'] = os.path.normpath (self.config['Settings']['PathToProtocols_car_pkl'])

        if 'Roads_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Roads_car_pkl'] = ''

        if 'FieldSpeed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldSpeed_car_pkl'] = '0'

        if 'FieldSpeed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldSpeed_car_pkl'] = '0'

        if 'FieldDirection_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldDirection_car_pkl'] = '0'

        if 'LayerRoad_type_road_car_pkl' not in self.config['Settings']:
            self.config['Settings']['LayerRoad_type_road_car_pkl'] = '0'

        if 'Layer_buildings_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_buildings_car_pkl'] = '0'

        if 'Layer_buildings_field_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_buildings_field_car_pkl'] = '0'

        if 'Speed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Speed_car_pkl'] = '0'

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToProtocols_car_pkl'] = self.txtPathToProtocols.text()

        self.config['Settings']['Roads_car_pkl'] = self.cbRoads.currentText()

        self.config['Settings']['FieldDirection_car_pkl'] = str(self.cmbFieldsDirection.currentData())
        self.config['Settings']['FieldSpeed_car_pkl'] = str(self.cmbFieldsSpeed.currentData())
        self.config['Settings']['LayerRoad_type_road_car_pkl'] = self.cmbLayersRoad_type_road.currentData() or ''
        
        self.config['Settings']['Layer_buildings_car_pkl'] = self.cmbLayers_buildings.currentText()
        self.config['Settings']['Layer_buildings_field_car_pkl'] = self.cmbLayers_buildings_fields.currentText()

        self.config['Settings']['Speed_car_pkl'] = self.txtSpeed.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

        layer = self.layer_buildings
       
        self.count_layer_origins = layer.featureCount()
        self.layer_origins_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToProtocols.setText(
            os.path.normpath(self.config['Settings']['PathToProtocols_car_pkl']))

        self.cmbFieldsSpeed.setCurrentText(
            self.config['Settings']['FieldSpeed_car_pkl'])
        self.cmbLayersRoad_type_road.setCurrentText(
            self.config['Settings']['LayerRoad_type_road_car_pkl'])
        self.cmbFieldsDirection.setCurrentText(
            self.config['Settings']['FieldDirection_car_pkl'])

        self.cmbLayers_buildings.setCurrentText(
            self.config['Settings']['Layer_buildings_car_pkl'])
        self.cmbLayers_buildings_fields.setCurrentText(
            self.config['Settings']['Layer_buildings_field_car_pkl'])

        self.txtSpeed.setText(self.config['Settings']['Speed_car_pkl'])

        if os.path.isfile(self.config['Settings']['Roads_car_pkl']):
            self.cbRoads.addItem(self.config['Settings']['Roads_car_pkl'])
        self.cbRoads.setCurrentText(self.config['Settings']['Roads_car_pkl'])

    def check_folder_and_file(self):

        os.makedirs(self.txtPathToProtocols.text(), exist_ok=True)
        
        file_path = os.path.join(self.txtPathToProtocols.text(), "graph.pkl")
        if  os.path.isfile(file_path):
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f"The folder '{self.txtPathToProtocols.text()}' already contains a database. Overwrite?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.No:
                return False

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the folder '{self.txtPathToProtocols.text()}' is denied")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_layer_buildings(self):

        layer = self.layer_buildings
        if layer == "":
            self.setMessage(f"Layer is empty")
            return 0
        
        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'Layer {layer} is empty')
            return 0
        
        geometryType = layer.geometryType()
        if (geometryType != QgsWkbTypes.PointGeometry and geometryType != QgsWkbTypes.PolygonGeometry):
            self.setMessage(f'Features of the layer {self.cmbLayers_buildings.currentText()} must be polylines or points')
            return 0

        return 1
    
    def check_type_layer_road(self):

        try:
            features = self.layer_road.getFeatures()
        except:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' is empty")
            return 0

        feature_count = self.layer_road.featureCount()
        if feature_count == 0:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' is empty")
            return 0
        
        
        features = self.layer_road.getFeatures()
        for feature in features:
            feature_geometry = feature.geometry()
            feature_geometry_type = feature_geometry.type()
            break

        if (feature_geometry_type != QgsWkbTypes.LineGeometry):
            self.setMessage(f"Features of the layer in '{self.cbRoads.currentText()}' must be polylines")
            return 0

        return 1

    def save_var(self):
        self.path_to_protocol = self.config['Settings']['pathtoprotocols_car_pkl']
        self.idx_field_direction = self.layer_road.fields().indexFromName(self.cmbFieldsDirection.currentData())

        self.idx_field_speed = self.layer_road.fields().indexFromName(self.cmbFieldsSpeed.currentData())
        self.speed_fieldname = self.cmbFieldsSpeed.currentData()

        self.layer_road_type_road = self.config['Settings']['LayerRoad_type_road_car_pkl']
        self.layer_road_direction = self.config['Settings']['FieldDirection_car_pkl']
        self.layer_buildings_field = self.config['Settings']['Layer_buildings_field_car_pkl']
        self.speed = float(self.config['Settings']['Speed_CAR_pkl'].replace(',', '.'))
        self.strategy_id = 1

        self.default_direction = self.cbDirection.currentText()

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)


####
    
    def fill_table(self, table, data, mode="noCDI"):
        table.setColumnCount(2)         

        if mode == "noCDI":
            data = sorted(data.items(), key=lambda item: float(item[1]), reverse=True)
            table.setHorizontalHeaderLabels(["OSM link type\n (FCLASS)", "Maximum speed\n(free flow)"])
            
        else:
            data = data.items() 
            table.setHorizontalHeaderLabels(["Hour\n of the day", "Congestion Delay\n Index"])
            
        table.setRowCount(0) 

        for i, (field1, field2) in enumerate(data):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(str(field1))) 

            if mode == "CDI":
                value = f"{float(field2):.2f}" + "   "
            else:
                value = str(field2) + "   "
            
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            table.setItem(i, 1, item)
    
    def load_text_with_bold_first_line(self, file_path):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            if not lines:
                return  
            first_line = f"<b>{lines[0].strip()}</b>"  
            other_lines = "".join(lines[1:]) 

        other_lines_with_br = other_lines.replace("\n", "<br>")
        styled_other_lines = f'<span style="color: gray;">{other_lines_with_br}</span>'
        full_text = f"<html><body>{first_line}<br>{styled_other_lines}</body></html>"
        self.textInfo.setHtml(full_text)
    
    
    def show_info(self):
        
        file_url1 = QUrl.fromLocalFile(self.file_path_road_speed_default).toString()
        file_url2 = QUrl.fromLocalFile(self.file_path_factor_speed_by_hour).toString()
        html = f'<b>Construct databases, Car routing database:</b> <br /> <br />'
        html += '<span style="color: grey;">The car routing database is constructed based on the links’ traffic direction and maximum traffic speed, and the congestion delay coefficient that depends on the hour of a day:  <br /> <br />'
        html += f'1. If the source of the road layer is the OSM database, then maximum traffic speed along the link is retrieved, depending on the road link type, from the table of average free speed on the road links.  To edit this table, click <a href="{file_url1}" target="_blank">here</a>. If this table is edited, the new version substitutes the previous one and the user is responsible for storing the latter, if necessary.If the source is different, the maximum traffic speed is used as is. In case the data on the traffic directions on a link or maximum traffic speed are absent or incorrect, the user is asked to fix the problem and repeat the computations.<br />'
        html += f'2. The congestion delay coefficients depend on the hour of the trip’s start and are applied during the entire trip. To edit this table, click <a href="{file_url2}" target="_blank">here</a>. If this table is edited, the new version substitutes the previous one and the user is responsible for storing the latter, if necessary. <br />'
        html += '3. The data on the road network and buildings are translated into a pkl (Pickled Python Objects) binary format that allows fast accessibility computations.<br />'
        html += '</span>'
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))  

    def load_text_with_bold_first_line(self, file_path):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            if not lines:
                return  
            first_line = f"<b>{lines[0].strip()}</b>"  
            other_lines = "".join(lines[1:]) 

        other_lines_with_br = other_lines.replace("\n", "<br>")
        styled_other_lines = f'<span style="color: gray;">{other_lines_with_br}</span>'
        full_text = f"<html><body>{first_line}<br>{styled_other_lines}</body></html>"
        self.textInfo.setHtml(full_text)

    """    
    def show_info(self):
        
        hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')
        help_filename = "transit_db_car.txt"
            
        hlp_file = os.path.join(hlp_directory, help_filename)
        hlp_file = os.path.normpath(hlp_file)
        self.load_text_with_bold_first_line (hlp_file)
    """
    def closeEvent(self, event):
        self.break_on = True
        event.accept()