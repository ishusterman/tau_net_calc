import os
import csv
import webbrowser
import configparser

from qgis.core import (QgsProject,
                       QgsVectorLayer,
                       QgsMapLayerProxyModel,
                       QgsFieldProxyModel
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
                    check_layer,
                    highlight_empty_fields
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
       

        self.cmbFieldsDirection.setFilters(QgsFieldProxyModel.String)
        self.cmbFieldsSpeed.setFilters(QgsFieldProxyModel.Numeric)
        self.cmbFieldsDirection.fieldChanged.connect(self.on_field_changed)
        self.cmbFieldsSpeed.fieldChanged.connect(self.on_field_changed)

        self.progressBar.setMaximum(2)

        self.test_button.setFixedWidth(185)       
        self.btnCheckOSM.setFixedWidth(185)       

        self.run_completed = False
        

    def on_field_changed (self):
        if self.cmbFieldsSpeed.count() > 0 and self.cmbFieldsDirection.count() > 0:
            self.test_button.setEnabled(True)
            self.test_button.setText("Test road atributes")
            self.test_button.setEnabled(True)
            self.test_button.setStyleSheet("")
        
        self.txtSpeed.setEnabled(False)
        self.txtPathToProtocols.setEnabled(False)       
        
                
    def setEnabledAll (self, status):
        widgets_to_hide = [
                
                self.lblDefault,
                self.lblDirection, 
                self.lblSpeed, self.txtSpeed,

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
    
    def show_stage_testing (self, message, progress):
        self.setMessage (message)    
        self.progressBar.setValue(progress)
    
    def on_test_button_click(self):   
        
        self.test_button.setEnabled(False)
        self.run_button.setEnabled(False)
        
        self.layer_road = self.cbRoads.currentLayer() 
        
        field_name_direction = self.cmbFieldsDirection.currentField()
        field_name_maxspeed = self.cmbFieldsSpeed.currentField()
              
        self.processor_road = RoadLayerProcessor(self,
                                                 self.layer_road, 
                                                 field_name_direction,
                                                 field_name_maxspeed
                                                 )
        
        result, oneway_pct, maxspeed_pct = self.processor_road.run()        
        #self.lblDirection_prc.setText(f'direction: {str(round(oneway_pct))}% correct')
        self.str_info1 = f'direction: {str(round(oneway_pct))}% correct'
        #self.lblMaxspeed_prc.setText(f'speed: {str(round(maxspeed_pct))}% correct')
        self.str_info2 = f'speed: {str(round(maxspeed_pct))}% correct'
        if result:            
            self.test_button.setText('Road attributes test: PASSED!')
            self.test_button.setStyleSheet("background-color: #A1C935; color: black;")            
            self.setEnabledAll(True)
            if self.checkOSM_result:
                self.cmbFieldsDirection.setEnabled(False)
                self.cmbFieldsSpeed.setEnabled(False)
        else:
            self.test_button.setText(f"Road attributes test: FAILED!({100 - min(oneway_pct,maxspeed_pct)}%)")
            self.test_button.setStyleSheet("background-color: #d9534f; color: white;")
            

        
        self.test_button.setEnabled(False)
        self.run_button.setEnabled(result)

    
    def onLayerRoadChanged(self):
        
        self.textLog.clear()
        self.run_button.setEnabled(False)
        self.btnCheckOSM.setEnabled(True)
        self.cmbFieldsDirection.clear()
        self.cmbFieldsSpeed.clear()
        self.lblOSMInfo.setText("")        
        self.setEnabledAll(False)

        self.cmbFieldsSpeed.setLayer(None)
        self.cmbFieldsDirection.setLayer(None)
        #self.lblDirection_prc.setText("")
        #self.lblMaxspeed_prc.setText("")

        self.btnCheckOSM.setText("Check if road layer is OSM")
        self.test_button.setText("Test road atributes")        
        self.test_button.setStyleSheet("")
        self.btnCheckOSM.setStyleSheet("")
    
    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def on_btnCheckOSM_click(self):
                
        self.lblOSMInfo.setVisible(False)
        self.layer_road = self.cbRoads.currentLayer()
        self.cmbFieldsDirection.setLayer(self.layer_road)
        self.cmbFieldsSpeed.setLayer(self.layer_road)
        if self.layer_road:
            self.checkOSM_result, self.name_fclass = self.checkOSM(self.layer_road)
            
            if self.checkOSM_result:
                
                self.lblOSMInfo.setVisible(True)
                self.lblOSMInfo.setText("FCLASS field is found,")

                self.btnCheckOSM.setText("Road layer sorce is OSM")
                
                                                
            else:
                
                self.lblOSMInfo.setVisible(True)
                self.lblOSMInfo.setText("Local GIS, Choose attributes for")
                self.btnCheckOSM.setText("Road layer sorce is NOT OSM")
                self.cmbFieldsDirection.setEnabled(True)
                self.cmbFieldsSpeed.setEnabled(True)

                self.lblFieldsDirection.setEnabled(True)
                self.lblFieldsSpeed.setEnabled(True)


            self.set_field_case_insensitive(self.cmbFieldsSpeed, "maxspeed")
            self.set_field_case_insensitive(self.cmbFieldsDirection, "oneway")

            
        #self.btnCheckOSM.setStyleSheet("background-color: #d9534f; color: white;")
        #self.btnCheckOSM.setStyleSheet("background-color: #A1C935; color: black;")

        if self.cmbFieldsSpeed.count() > 0 and self.cmbFieldsDirection.count():
            self.test_button.setEnabled(True)

        self.btnCheckOSM.setEnabled(False)
        

    def set_field_case_insensitive(self, combo_widget, field_name):
        idx = self.layer_road.fields().lookupField(field_name)
        if idx != -1:
            real_name = self.layer_road.fields().at(idx).name()
            combo_widget.setField(real_name)
        
        
    def checkOSM(self, layer):
        required_fields = {'fclass', 'oneway', 'maxspeed'}
                
        layer_field_names = {field.name().lower() for field in layer.fields()}

        name_fclass = ""
        for field in layer.fields():
            if field.name().lower() == "fclass":
                name_fclass = field.name()
                break

        # Проверяем, являются ли все искомые поля подмножеством полей слоя
        if required_fields.issubset(layer_field_names):
            return True, name_fclass
        else:
            return False, name_fclass
    
    def on_run_button_clicked(self):
            
        self.run_button.setEnabled(False)
        self.break_on = False
        self.setMessage("")                

        if highlight_empty_fields(self, exclude=[self.textLog]):
            self.setMessage("All required fields must be filled in")                        
            self.run_button.setEnabled(True)
            return 0
        
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
        
        if self.checkOSM_result:
            self.textLog.append(f"<a> Type of layer road: OSM</a>")
        else:
            self.textLog.append(f"<a> Type of layer road: Local GIS</a>")

        self.textLog.append(f"<a> Direction: {self.cmbFieldsDirection.currentText()}</a>") 
        self.textLog.append(f"<a> Speed: {self.cmbFieldsSpeed.currentText()}</a>")
        if self.checkOSM_result:
            self.textLog.append(f"<a> FCLASS: {self.name_fclass}</a>")
        
        self.textLog.append(f"<a> {self.str_info1} </a>")
        self.textLog.append(f"<a> {self.str_info2} </a>")
        self.textLog.append(f"<a> Default direction: {self.default_direction} </a>")
        self.textLog.append(f"<a> Default speed: {self.config['Settings']['speed_car_pkl']} km/h</a>")
        
        self.textLog.append("<a style='font-weight:bold;'>[Output]</a>")
        
        self.textLog.append(f"<a> Folder to store car routing database: {self.config['Settings']['pathtoprotocols_car_pkl']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        pkl_car_calc = pkl_car(self)
        pkl_car_calc.create_files()

        self.close_button.setEnabled(True)
        self.run_completed = True

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
       

        self.idx_field_direction = self.layer_road.fields().indexFromName(self.cmbFieldsDirection.currentField())

        self.idx_field_speed = self.layer_road.fields().indexFromName(self.cmbFieldsSpeed.currentField())
        self.speed_fieldname = self.cmbFieldsSpeed.currentField()

        #self.layer_road_type_road = self.config['Settings']['LayerRoad_type_road_car_pkl']
        if self.checkOSM_result:
            self.layer_road_type_road = self.name_fclass
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
