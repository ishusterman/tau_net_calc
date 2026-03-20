import os
import csv
import webbrowser
import configparser

from qgis.core import (QgsProject,
                       QgsVectorLayer,
                       QgsMapLayerProxyModel
                       )

from PyQt5.QtWidgets import (QDialogButtonBox,
                            QFileDialog,
                            QMessageBox,
                            QTableWidgetItem,
                            QDialog,
                            QHeaderView
                            )

from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QEvent                          
                          )


from PyQt5.QtGui import QRegExpValidator, QDesktopServices

from qgis.PyQt import uic

from pkl_car import pkl_car
from common import (get_qgis_info, 
                    check_file_parameters_accessibility,
                    FIELD_ID,
                    check_layer
                    )

from road_layer_processor import RoadLayerProcessor

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'pkl_car.ui'))

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

        fix_size = 15 * self.txtSpeed.fontMetrics().width('x')
        fix_size2 = 22 * self.txtSpeed.fontMetrics().width('x')

        self.txtSpeed.setFixedWidth(fix_size)
        
        self.cmbFieldsDirection.setFixedWidth(fix_size2)
        self.cmbFieldsSpeed.setFixedWidth(fix_size2)

        self.cbDirection.setFixedWidth(fix_size2)
        
        self.splitter.setSizes([int(self.width() * 0.70), int(self.width() * 0.30)])
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setValue(0)

        self.cbDirection.addItems(["T", "F", "B"])
        self.cbDirection.setCurrentIndex(self.cbDirection.findText("B"))
        
        self.toolButtonRoads.clicked.connect(lambda: self.open_file_dialog (type = "roads"))
        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog (type = "buildings"))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_protocol.clicked.connect(lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        
        self.cmbLayers_buildings.installEventFilter(self)
        self.cbRoads.installEventFilter(self)
        self.cmbLayers_buildings.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.cbRoads.setFilters(QgsMapLayerProxyModel.LineLayer)


        self.cmbFieldsSpeed.installEventFilter(self)
        self.cmbFieldsDirection.installEventFilter(self)
                
        self.btnBreakOn.clicked.connect(self.set_break_on)

        self.run_button = self.buttonBox.addButton("Run", QDialogButtonBox.ActionRole)
        self.run_button.setEnabled(False)
        self.close_button = self.buttonBox.addButton("Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton("Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

        self.btnCheckOSM.clicked.connect(self.on_btnCheckOSM_click)
        self.test_button.clicked.connect(self.on_test_button_click)

        # floating, two digit after dot
        regex3 = QRegExp(r"^\d+(\.\d{1,2})?$")
        int_validator3 = QRegExpValidator(regex3)

        self.txtSpeed.setValidator(int_validator3)
        
        self.ParametrsShow()
        self.onLayerRoadChanged()
        self.cbRoads.currentIndexChanged.connect(self.onLayerRoadChanged)

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
        
        self.setEnabledAll(False)

        self.lblOSMInfo.setText("")
        self.lblOSM.setText("")


    def setEnabledAll (self, status):
        widgets_to_hide = [
                self.widget_candidates,
                self.lblDefault,
                self.lblDirection, self.cbDirection,
                self.lblSpeed, self.txtSpeed,

                self.lblCandidates, 
                self.lblFieldsDirection, self.cmbFieldsDirection,
                self.lblFieldsSpeed, self.cmbFieldsSpeed,
                
                self.lblFolderStore, self.txtPathToProtocols, self.toolButton_protocol,
                self.test_button,

                self.cmbFieldsDirection,
                self.cmbFieldsSpeed

            ]
        for widget in widgets_to_hide:
            widget.setEnabled(status)


    def toggle_tables_visibility(self, checked):
        self.groupBox_tables.setVisible(checked)
    
    def open_file_dialog(self, type):

        project_path = QgsProject.instance().fileName()
        initial_dir = os.path.dirname(project_path) if project_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose a File",
            initial_dir,
            "Shapefile (*.shp);"
        )
        
        if file_path:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.cmbLayers.setLayer(layer)
                if type == "roads":
                    self.cbRoads.setLayer(layer)
                else:
                    self.cmbLayers_buildings.setLayer(layer)
                    

    def show_stage_testing (self, message, progress):
        self.setMessage (message)    
        self.progressBar.setValue(progress)
    
    def on_test_button_click(self):   
        
        self.test_button.setEnabled(False)
        self.run_button.setEnabled(False)
        
        self.layer_road = self.cbRoads.currentLayer() 
        self.layer_road_name = self.layer_road.name()
              

        self.processor_road = RoadLayerProcessor(self,
                                                 self.layer_road, 
                                                 self.layer_road_name, 
                                                 self.checkOSM_result)
        
        result, self.text_for_log = self.processor_road.run()
        if result:
            self.setEnabledAll(True)
        self.run_button.setEnabled(result)

    
    def onLayerRoadChanged(self):
        
        self.textLog.clear()
        self.run_button.setEnabled(False)
        self.btnCheckOSM.setEnabled(True)
        self.cmbFieldsDirection.clear()
        self.cmbFieldsSpeed.clear()
        self.lblOSMInfo.setText("")
        self.lblOSM.setText("")
        self.setEnabledAll(False)

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
        
    def on_btnCheckOSM_click(self):
        
        self.lblOSM.setText("")
        self.lblOSMInfo.setVisible(False)
        self.layer_road = self.cbRoads.currentLayer() 
        if self.layer_road:
            self.checkOSM_result = self.checkOSM(self.layer_road)
            
            if self.checkOSM_result:
                self.progressBar.setMaximum(2)
                self.lblOSMInfo.setVisible(True)
                self.lblOSMInfo.setText("OSM (FCLASS, Direction, and MAXSPEED fields found)")
                                
            else:
                self.progressBar.setMaximum(2)
                self.lblOSMInfo.setVisible(True)
                self.lblOSMInfo.setText("Local GIS")
                
        self.btnCheckOSM.setEnabled(False)
        self.test_button.setEnabled(True)
        
    def checkOSM(self, layer):
        required_fields = {'fclass', 'oneway', 'maxspeed'}
                
        layer_field_names = {field.name().lower() for field in layer.fields()}
        
        # Проверяем, являются ли все искомые поля подмножеством полей слоя
        if required_fields.issubset(layer_field_names):
            return True
        else:
            return False
    
    def on_run_button_clicked(self):
            
        self.run_button.setEnabled(False)
        self.break_on = False
        
        self.layer_road = self.cbRoads.currentLayer() 
        self.layer_buildings = self.cmbLayers_buildings.currentLayer() 

        result, text = check_layer(self.layer_buildings, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
        
        result, text = check_layer(self.layer_road, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
                
        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
       
        
        self.folder_name = f'{self.txtPathToProtocols.text()}'

        self.saveParameters()
        self.readParameters()
        
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

        self.textLog.append("<a style='font-weight:bold;'>[Input]</a>")
        self.textLog.append(f"<a> Layer of buildings: {self.layer_origins_path}</a>")
        self.textLog.append(f"<a> Layer of roads: {self.layer_roads_path}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Verify road data]</a>")
        self.textLog.append(f"<a> Check if road layer is OSM: {self.lblOSMInfo.text()} </a>")
        self.textLog.append(f"<a> Test attributes: {self.lblOSM.text()} </a>")
        self.message_for_log = f"Direction: <b>{self.cmbFieldsDirection.currentText()}</b>, Speed: <b>{self.cmbFieldsSpeed.currentText()}</b>"
        if self.checkOSM_result:
            self.message_for_log=f'{self.message_for_log}, FClass: <b>FClass</b>' 
        self.textLog.append(self.message_for_log)        

        self.textLog.append("<a style='font-weight:bold;'>[Output]</a>")
        self.textLog.append(f"<a> Default direction: {self.default_direction} </a>")
        self.textLog.append(f"<a> Default speed: {self.config['Settings']['speed_car_pkl']} km/h</a>")
        self.textLog.append(f"<a> Folder to store car routing database: {self.config['Settings']['pathtoprotocols_car_pkl']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        pkl_car_calc = pkl_car(self)
        pkl_car_calc.create_files()

        #self.textLog.append('---------------')
        #self.textLog.append(self.text_for_log)

        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/building_pkl.html#building-database-for-car-routing"
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

        if 'FieldDirection_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldDirection_car_pkl'] = '0'

        if 'LayerRoad_type_road_car_pkl' not in self.config['Settings']:
            self.config['Settings']['LayerRoad_type_road_car_pkl'] = '0'

        if 'Layer_buildings_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_buildings_car_pkl'] = '0'

        if 'Speed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Speed_car_pkl'] = '0'

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToProtocols_car_pkl'] = self.txtPathToProtocols.text()

        self.config['Settings']['FieldDirection_car_pkl'] = str(self.cmbFieldsDirection.currentData())
        self.config['Settings']['FieldSpeed_car_pkl'] = str(self.cmbFieldsSpeed.currentData())
                
        self.config['Settings']['Roads_car_pkl'] = self.cbRoads.currentLayer().id()
        self.config['Settings']['Layer_buildings_car_pkl'] = self.cmbLayers_buildings.currentLayer().id()

        
        self.config['Settings']['Speed_car_pkl'] = self.txtSpeed.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

        layer = self.layer_buildings
       
        self.count_layer_origins = layer.featureCount()
        self.layer_origins_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])

        layer = self.layer_road 
        self.layer_roads_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToProtocols.setText(
            os.path.normpath(self.config['Settings']['PathToProtocols_car_pkl']))

        self.cmbFieldsSpeed.setCurrentText(self.config['Settings']['FieldSpeed_car_pkl'])
        self.cmbFieldsDirection.setCurrentText(self.config['Settings']['FieldDirection_car_pkl'])
        self.txtSpeed.setText(self.config['Settings']['Speed_car_pkl'])

        self.cbRoads.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Roads_car_pkl']))
        self.cmbLayers_buildings.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Layer_buildings_car_pkl']))

    def check_folder_and_file(self):

        path = self.txtPathToProtocols.text()

        os.makedirs(path, exist_ok=True)
        
        file_path = os.path.join(path, "graph.pkl")
        prefix = os.path.basename(path)
        file_path_prefix = os.path.join(path, f"{prefix}_graph.pkl")
        if  os.path.isfile(file_path) or os.path.isfile(file_path_prefix):
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f"The folder '{path}' already contains a database. Overwrite?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.No:
                return False

        try:
            tmp_prefix = "write_tester"
            filename = f'{path}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the folder '{path}' is denied")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def save_var(self):
        self.path_to_protocol = self.config['Settings']['pathtoprotocols_car_pkl']
        self.idx_field_direction = self.layer_road.fields().indexFromName(self.cmbFieldsDirection.currentData())

        self.idx_field_speed = self.layer_road.fields().indexFromName(self.cmbFieldsSpeed.currentData())
        self.speed_fieldname = self.cmbFieldsSpeed.currentData()

        #self.layer_road_type_road = self.config['Settings']['LayerRoad_type_road_car_pkl']
        if self.checkOSM_result:
            idx = self.layer_road.fields().indexOf("fclass")
            self.layer_road_type_road = self.layer_road.fields()[idx].name()
        else:
            self.layer_road_type_road = ""

        self.layer_road_direction = self.config['Settings']['FieldDirection_car_pkl']
        self.layer_buildings_field = FIELD_ID
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
            table.setHorizontalHeaderLabels(["OSM link type\n (FCLASS)", "Maximum speed, km/h\n(free flow)"])
            
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
        
        table.setWordWrap(True)
        table.horizontalHeader().setStretchLastSection(True)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
    
    def show_info(self):

            hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')
        
            help_filename = "build_car_routing_database.txt"
            hlp_file = os.path.join(hlp_directory, help_filename)

            if os.path.exists(hlp_file):
                with open(hlp_file, 'r', encoding='utf-8') as f:
                    html = f.read()

            self.textInfo.setOpenExternalLinks(False)  
            self.textInfo.setOpenLinks(False)          
            self.textInfo.setHtml(html)
            self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))  
