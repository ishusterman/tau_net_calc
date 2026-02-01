import os
#import cProfile
#import pstats
#import io
import webbrowser
import re
import configparser
from datetime import datetime
#import pickle
#import time
#from collections import Counter

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication

from qgis.core import QgsProject

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )
from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QDateTime,
                          QEvent,
                          QVariant
                          )
from PyQt5.QtGui import QRegExpValidator, QDesktopServices
from PyQt5 import uic

from query_file import runRaptorWithProtocol, myload_all_dict
from tau_net_calc.cls.common import ( 
                    get_qgis_info, 
                    is_valid_folder_name, 
                    get_prefix_alias, 
                    seconds_to_time, 
                    time_to_seconds, 
                    check_file_parameters_accessibility
                    )
#from stat_destination import DayStat_DestinationID
#from stat_from_to import StatFromTo
#from AnalyzerFromTo2 import TripAnalyzer
from AnalyzerFromTo_incremental import roundtrip_analyzer
#from TimeMarkGenerator import TimeMarkGenerator

from common import (showAllLayersInCombo_Point_and_Polygon,
                    showAllLayersInCombo_Polygon,
                    get_initial_directory)

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'raptor.ui')
)

class RaptorDetailed(QDialog, FORM_CLASS):

    

    def __init__(self, parent, mode, protocol_type, title, timetable_mode):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        self.txtPathToPKL.setReadOnly(True)

        self.InitialNameWalk1 = "Maximum walk distance to the initial PT stop, m"
        self.InitialNameWalk2 = "Maximum walk distance at the transfer, m"
        self.InitialNameWalk3 = "Maximum walk distance from the  last PT stop, m"
        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])

        fix_size = 15* self.txtMinTransfers.fontMetrics().width('x')

        self.txtMinTransfers.setFixedWidth(fix_size)
        self.txtMaxTransfers.setFixedWidth(fix_size)
        self.txtMaxWalkDist1.setFixedWidth(fix_size)
        self.txtMaxWalkDist2.setFixedWidth(fix_size)
        self.txtMaxWalkDist3.setFixedWidth(fix_size)

        self.dtStartTime.setFixedWidth(fix_size)
        
        self.txtMaxExtraTime.setFixedWidth(fix_size)
        self.txtSpeed.setFixedWidth(fix_size)
        self.txtMaxWaitTime.setFixedWidth(fix_size)

        self.txtMaxWaitTimeTransfer.setFixedWidth(fix_size)
        self.txtMaxTimeTravel.setFixedWidth(fix_size)
        self.txtTimeInterval.setFixedWidth(fix_size)

        self.cmbFields_ch.setFixedWidth(fix_size)
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()
        self.config_add = configparser.ConfigParser()

        self.break_on = False

        self.shift_mode = False
        self.shift_ctrl_mode =  False

        self.parent = parent
        self.mode = mode
        self.protocol_type = protocol_type
        self.title = title
        self.timetable_mode = timetable_mode
        # self.change_time = 1

        self.progressBar.setValue(0)

        if self.protocol_type == 2:
            self.txtTimeInterval.setVisible(False)
            self.lblTimeInterval.setVisible(False)
            parent_layout = self.horizontalLayout_16.parent()
            parent_layout.removeItem(self.horizontalLayout_16)

        if self.protocol_type == 2:
            self.cmbFields_ch.setVisible(False)
            self.lblFields.setVisible(False)

            parent_layout = self.horizontalLayout_6.parent()
            parent_layout.removeItem(self.horizontalLayout_6)

        if not timetable_mode:

            self.lblMaxExtraTime.setVisible(False)
            self.txtMaxExtraTime.setVisible(False)
                        
            parent_layout = self.horizontalLayout_11.parent()
            parent_layout.removeItem(self.horizontalLayout_11)

        if timetable_mode:
            self.lblMaxWaitTime.setVisible(False)
            self.txtMaxWaitTime.setVisible(False)
            parent_layout = self.horizontalLayout_13.parent()
            parent_layout.removeItem(self.horizontalLayout_13)
        
        if self.mode == 2:
            self.label_21.setText("Arrive before (hh:mm:ss)")
            self.label_17.setText("Layer of origins")
            self.label_5.setText("Layer of facilities")
        
        if self.protocol_type == 1:    
            if self.mode == 2:
                self.label_5.setText("Layer of all destinations in the region")
            if self.mode == 1:    
                self.label_17.setText("Layer of all origins in the region")

        
        if timetable_mode and self.mode == 1:
            self.label_21.setText("Earliest start time")
            self.lblMaxExtraTime.setText("Latest start time is T minutes later, T =")
            
        if timetable_mode and self.mode == 2:

            self.label_21.setText("Earliest arrival time")
            self.lblMaxExtraTime.setText(
                "Latest arrival time is T minutes later, T = ")
            
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_PKL.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToPKL))
        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        self.cbRunOnAir.clicked.connect(lambda: self.handleRunOnAirClick())

        showAllLayersInCombo_Point_and_Polygon(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)
        showAllLayersInCombo_Point_and_Polygon(self.cmbLayersDest)
        self.cmbLayersDest.installEventFilter(self)
        showAllLayersInCombo_Polygon(self.cmbVizLayers)
        self.cmbVizLayers.installEventFilter(self)
        self.dtStartTime.installEventFilter(self)

        self.cmbLayers_fields.installEventFilter(self)
        self.cmbLayersDest_fields.installEventFilter(self)
        self.cmbVizLayers_fields.installEventFilter(self)

        self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)
        self.cmbLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers, self.cmbLayers_fields))

        self.fillComboBoxFields_Id(
            self.cmbLayersDest, self.cmbLayersDest_fields)
        self.cmbLayersDest.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayersDest, self.cmbLayersDest_fields))

        self.fillComboBoxFields_Id(self.cmbVizLayers, self.cmbVizLayers_fields)
        self.cmbVizLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbVizLayers, self.cmbVizLayers_fields))

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

        #  create a regular expression instance for integers
        regex1 = QRegExp(r"\d*")

        int_validator1 = QRegExpValidator(regex1)

        # 0,1,2
        regex2 = QRegExp(r"[0-2]{1}")
        int_validator2 = QRegExpValidator(regex2)

        # floating, two digit after dot
        regex3 = QRegExp(r"^\d+(\.\d{1,2})?$")
        int_validator3 = QRegExpValidator(regex3)

        self.txtMinTransfers.setValidator(int_validator2)
        self.txtMaxTransfers.setValidator(int_validator2)
        self.txtMaxWalkDist1.setValidator(int_validator1)
        self.txtMaxWalkDist2.setValidator(int_validator1)
        self.txtMaxWalkDist3.setValidator(int_validator1)
        self.txtSpeed.setValidator(int_validator3)
        self.txtMaxWaitTime.setValidator(int_validator3)
        self.txtMaxWaitTimeTransfer.setValidator(int_validator3)
        self.txtMaxTimeTravel.setValidator(int_validator3)
        self.txtMaxExtraTime.setValidator(int_validator3)
                
        self.default_alias = get_prefix_alias(True, 
                                self.protocol_type, 
                                self.mode, 
                                self.timetable_mode, 
                                full_prefix=False)
        
        self.ParametrsShow()
        self.show_info()

    def handleRunOnAirClick(self):
        self.RunOnAir = False
        if self.cbRunOnAir.isChecked():
            self.RunOnAir = True
        latest_log = self.find_latest_log (self.txtPathToPKL.text())
        result = self.extract_parameters(latest_log)
        if self.RunOnAir:
            self.UpperBoundMaxWalkDist = result.get("Maximal walking path on air", 0)
        else:
            self.UpperBoundMaxWalkDist = result.get("Maximal walking path on road", 0)
        
        
        if self.UpperBoundMaxWalkDist > 0:
            self.lbMaxWalkDistanceInitial.setText(f'{self.InitialNameWalk1} (max =  {self.UpperBoundMaxWalkDist})')
            self.lbMaxWalkDistanceTransfer.setText(f'{self.InitialNameWalk2} (max =  {self.UpperBoundMaxWalkDist})')
            self.lbMaxWalkDistanceFinish.setText(f'{self.InitialNameWalk3} (max =  {self.UpperBoundMaxWalkDist})')
        
        else:
            self.lbMaxWalkDistanceInitial.setText(f'{self.InitialNameWalk1}')
            self.lbMaxWalkDistanceTransfer.setText(f'{self.InitialNameWalk2}')
            self.lbMaxWalkDistanceFinish.setText(f'{self.InitialNameWalk3}')

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields):
        obj_layer_fields.clear()
        selected_layer_name = obj_layers.currentText()
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)

        if not layers:
            return
        layer = layers[0]

        fields = layer.fields()
        osm_id_exists = False

        # regular expression to check for the presence of only digit
        digit_pattern = re.compile(r'^\d+$')

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong):
                # add numeric fields
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == "osm_id":
                    osm_id_exists = True
            else:
                if field_name.lower() == "osm_id":
                    obj_layer_fields.addItem(field_name)
                    osm_id_exists = True
            """
            elif field_type == QVariant.String:
                # check the first value of the field for digits only
                first_value = None
                for feature in layer.getFeatures():
                    first_value = feature[field_name]
                    break  # stop after the first value

                if first_value is not None and digit_pattern.match(str(first_value)):
                    obj_layer_fields.addItem(field_name)
                    if field_name.lower() == "osm_id":
                        osm_id_exists = True
            """

        if osm_id_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == "osm_id":
                    obj_layer_fields.setCurrentIndex(i)
                    break

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def checkLayer_type(self, layer_name):
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        if layer.wkbType() != 1:  # QgsWkbTypes.PointGeometry:
            return 0
        else:
            return 1

    def on_run_button_clicked(self):

        modifiers = QGuiApplication.keyboardModifiers()
        if (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier) and self.protocol_type == 2:
            self.shift_mode = True

        if modifiers == (Qt.ShiftModifier | Qt.ControlModifier) and self.protocol_type == 2 and self.mode == 1 :
            self.shift_ctrl_mode = True    

        self.run_button.setEnabled(False)
        self.break_on = False

        if not (is_valid_folder_name(self.txtAliase.text())):
            self.setMessage(f"'{self.txtAliase.text()}' is not a valid directory/file name")
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        if not self.cmbLayers.currentText():
            self.run_button.setEnabled(True)
            self.setMessage("Choose layer")
            return 0
        
        if not (self.check_max_foothpath()):
            self.run_button.setEnabled(True)
            return 0

        self.folder_name = f'{self.txtPathToProtocols.text()}//{self.txtAliase.text()}'
        self.alias = self.txtAliase.text()

        self.saveParameters()
        self.readParameters()

        self.setMessage("Starting ...")
        self.close_button.setEnabled(False)
        self.textLog.clear()
        self.tabWidget.setCurrentIndex(1)
        self.textLog.append("<a style='font-weight:bold;'>[System]</a>")
        qgis_info = get_qgis_info()

        info_str = "<br>".join(
            [f"{key}: {value}" for key, value in qgis_info.items()])
        self.textLog.append(f'<a> {info_str}</a>')
        self.textLog.append("<a style='font-weight:bold;'>[Mode]</a>")
        self.textLog.append(f'<a> Mode: {self.title}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        self.textLog.append(f'<a> Output alias: {self.alias}</a>')
        self.textLog.append(f"<a> Transit routing database folder: {self.config['Settings']['pathtopkl']}</a>")
        self.textLog.append(f"<a> Output folder: {self.config['Settings']['pathtoprotocols']}</a>")
        
        if self.protocol_type == 2:
            if self.mode == 1:
                name1 = "facilities"
                name2 = "destinations"
            else:
                name2 = "facilities"
                name1 = "origins"

        if self.protocol_type == 1:
            if self.mode == 1:
                name1 = "all origins in the region"
                name2 = "destinations"
            else:
                name2 = "all destinations in the region"
                name1 = "origins"    
        self.textLog.append(f'<a> Layer of {name1}: {self.layer_origins_path}</a>')
        self.textLog.append(f"<a> Selected {name1}: {self.config['Settings']['SelectedOnly1']}</a>")
        self.textLog.append(f'<a> Layer of {name2}: {self.layer_destinations_path}</a>')
        self.textLog.append(f"<a> Selected {name2}: {self.config['Settings']['SelectedOnly2']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Parameters of a trip]</a>")
        self.textLog.append(f"<a> Aerial distance: {self.config['Settings']['RunOnAir']}</a>")
        self.textLog.append(f"<a> Minimum number of transfers: {self.config['Settings']['min_transfer']}</a>")
        self.textLog.append(f"<a> Maximum number of transfers: {self.config['Settings']['max_transfer']}</a>")
        self.textLog.append(f"<a> Maximum walk distance to the initial PT stop: {self.config['Settings']['maxwalkdist1']} m</a>")

        self.textLog.append(f"<a> Maximum walk distance between at the transfer: {self.config['Settings']['maxwalkdist2']} m</a>")
        self.textLog.append(f"<a> Maximum walk distance from the last PT stop: {self.config['Settings']['maxwalkdist3']} m</a>")
        self.textLog.append(f"<a> Walking speed: {self.config['Settings']['speed']} km/h</a>")

        if not self.timetable_mode:
            self.textLog.append(f"<a> Maximum waiting time at the initial stop: {self.config['Settings']['maxwaittime']} min</a>")

        self.textLog.append(f"<a> Maximum waiting time at the transfer stop: {self.config['Settings']['maxwaittimetransfer']} min</a>")

        if not self.timetable_mode and not self.shift_ctrl_mode:
            if self.mode == 1:
                self.textLog.append(f"<a> Start at (hh:mm:ss): {self.config['Settings']['time']}</a>")
            else:
                self.textLog.append(f"<a> Arrive before (hh:mm:ss): {self.config['Settings']['time']}</a>")
        self.textLog.append(f"<a> Maximum travel time: {self.config['Settings']['maxtimetravel']} min</a>")
        if self.protocol_type == 1:  # MAP mode
            self.textLog.append("<a style='font-weight:bold;'>[Aggregation]</a>")
            self.textLog.append(f"<a> Number of bins: {self.config['Settings']['timeinterval']}</a>")

            if self.mode == 2:
                count_features = self.count_layer_destinations
            else:
                count_features = self.count_layer_origins
            self.textLog.append(f'<a> Count: {count_features}</a>')

            if self.config['Settings']['field_ch'] != "":
                print_fields = self.config['Settings']['field_ch']
            else:
                print_fields = "NONE"
            self.textLog.append(f'<a> Additional buildings characteristics for accessibility assessment: {print_fields}</a>')

        if self.timetable_mode :
            self.textLog.append("<a style='font-weight:bold;'>[Time schedule]</a>")

            if self.mode == 1:
                if not self.shift_ctrl_mode:
                    self.textLog.append(f"<a> Earliest start time: {self.config['Settings']['time']}</a>")
                self.textLog.append(f"<a> Latest start time is T minutes later, T = {self.config['Settings']['maxextratime']} min</a>")
                
            if self.mode == 2:
                if not self.shift_ctrl_mode:
                    self.textLog.append(f"<a> Earliest arrival time: {self.config['Settings']['time']}</a>")
                self.textLog.append(f"<a> Latest arrival time is T minutes later, T = {self.config['Settings']['maxextratime']} min</a>")
                
        self.textLog.append("<a style='font-weight:bold;'>[Visualization]</a>")
        self.textLog.append(f'<a> Visualization layer: {self.layer_visualization_path}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        self.prepareRaptor()
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/raptor_area.html"

        if self.mode == 1 and not(self.timetable_mode):
            section = "from-service-locations-fixed-time-departure"
        
        if self.mode == 2 and not(self.timetable_mode):
            section = "to-service-locations-fixed-time-arrival"

        if self.timetable_mode:
            section = "service-area-for-schedule-based-departure-or-arrival"

        url = f'{url}#{section}'
        
        webbrowser.open(url)

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
            self.handleRunOnAirClick()
        else:
            obj.setText(obj.text())
        
     

    def readParameters(self):

        def is_valid_time(t): 
            try: 
                datetime.strptime(t, "%H:%M:%S") 
                return True 
            except Exception: 
                return False   
        
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols = os.path.join(project_directory, f'{project_name}_output')
        PathToProtocols = os.path.normpath(PathToProtocols)

        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')
        
        file_path_add = os.path.join(
            project_directory, 'parameters_accessibility_add.txt')
        
        self.config.read(file_path)

        

        if 'PathToPKL' not in self.config['Settings'] or self.config['Settings']['PathToPKL'] == "С:/":
            self.config['Settings']['PathToPKL'] = self.config['Settings']['PathToProtocols_pkl']
        
        self.config['Settings']['PathToPKL'] = get_initial_directory(self.config['Settings']['PathToPKL'])
            
        if 'Layer_field' not in self.config['Settings']:
            self.config['Settings']['Layer_field'] = ''

        if 'LayerDest_field' not in self.config['Settings']:
            self.config['Settings']['LayerDest_field'] = ''

        if 'LayerViz_field' not in self.config['Settings']:
            self.config['Settings']['LayerViz_field'] = ''

        if 'RunOnAir' not in self.config['Settings']:
            self.config['Settings']['RunOnAir'] = 'False'
                
        if 'PathToProtocols' not in self.config['Settings'] or self.config['Settings']['PathToProtocols'] == "C:/":
            self.config['Settings']['PathToProtocols'] = PathToProtocols      
        self.config['Settings']['PathToProtocols'] = os.path.normpath(self.config['Settings']['PathToProtocols'])

        self.config_add.read(file_path_add)

        value = self.config_add['Settings'].get('time_delta')
        if not value or not str(value).isdigit():
            self.config_add['Settings']['time_delta'] = '900'

        value = self.config_add['Settings'].get('from_time_start')
        if not value or not is_valid_time(value): 
            self.config_add['Settings']['from_time_start'] = '16:00:00'

        value = self.config_add['Settings'].get('from_time_end')
        if not value or not is_valid_time(value): 
            self.config_add['Settings']['from_time_end'] = '18:00:00'
        
        value = self.config_add['Settings'].get('to_time_start')
        if not value or not is_valid_time(value): 
            self.config_add['Settings']['to_time_start'] = '08:00:00'

        value = self.config_add['Settings'].get('to_time_end')
        if not value or not is_valid_time(value): 
            self.config_add['Settings']['to_time_end'] = '10:00:00'
       

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToPKL'] = self.txtPathToPKL.text()
        self.config['Settings']['PathToProtocols'] = self.txtPathToProtocols.text()
        self.config['Settings']['Layer'] = self.cmbLayers.currentText()
        self.config['Settings']['Layer_field'] = self.cmbLayers_fields.currentText()
        if hasattr(self, 'cbSelectedOnly1'):
            self.config['Settings']['SelectedOnly1'] = str(
                self.cbSelectedOnly1.isChecked())
        self.config['Settings']['LayerDest'] = self.cmbLayersDest.currentText()
        self.config['Settings']['LayerDest_field'] = self.cmbLayersDest_fields.currentText()

        if hasattr(self, 'cbSelectedOnly2'):
            self.config['Settings']['SelectedOnly2'] = str(
                self.cbSelectedOnly2.isChecked())

        self.config['Settings']['LayerViz'] = self.cmbVizLayers.currentText()
        self.config['Settings']['LayerViz_field'] = self.cmbVizLayers_fields.currentText()

        self.config['Settings']['Min_transfer'] = self.txtMinTransfers.text()
        self.config['Settings']['Max_transfer'] = self.txtMaxTransfers.text()
        self.config['Settings']['MaxExtraTime'] = self.txtMaxExtraTime.text()
        
        self.config['Settings']['MaxWalkDist1'] = self.txtMaxWalkDist1.text()
        self.config['Settings']['MaxWalkDist2'] = self.txtMaxWalkDist2.text()
        self.config['Settings']['MaxWalkDist3'] = self.txtMaxWalkDist3.text()
        self.config['Settings']['TIME'] = self.dtStartTime.dateTime().toString(
            "HH:mm:ss")
        self.config['Settings']['Speed'] = self.txtSpeed.text()
        self.config['Settings']['MaxWaitTime'] = self.txtMaxWaitTime.text()
        self.config['Settings']['MaxWaitTimeTransfer'] = self.txtMaxWaitTimeTransfer.text()
        self.config['Settings']['MaxTimeTravel'] = self.txtMaxTimeTravel.text()
        self.config['Settings']['RunOnAir'] = str(self.cbRunOnAir.isChecked())
        
        with open(f, 'w') as configfile:
            self.config.write(configfile)

        self.alias = self.txtAliase.text(
        ) if self.txtAliase.text() != "" else self.default_alias

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer'])[0]
        self.layer_origins_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])
        if self.mode == 2:
            layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest'])[0]
        self.count_layer_origins = layer.featureCount()

        if self.cbSelectedOnly1.isChecked():
            self.count_layer_origins = layer.selectedFeatureCount()
                  
        
        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest'])[0]
        self.layer_destinations_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])
        if self.mode == 2:
            layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer'])[0]
        self.count_layer_destinations = layer.featureCount()

        if self.cbSelectedOnly2.isChecked():
            self.count_layer_destinations = layer.selectedFeatureCount()    

        
        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerViz'])[0]
        self.layer_visualization_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])

        
        

    def ParametrsShow(self):

        self.readParameters()
        self.txtPathToPKL.setText(os.path.normpath(self.config['Settings']['PathToPKL']))
        self.txtPathToProtocols.setText(os.path.normpath(self.config['Settings']['PathToProtocols']))

        
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer'])

        SelectedOnly1 = self.config['Settings']['SelectedOnly1'].lower() == "true"
        self.cbSelectedOnly1.setChecked(SelectedOnly1)

        self.cmbLayersDest.setCurrentText(self.config['Settings']['LayerDest'])

        layer = self.config.get('Settings', 'LayerViz', fallback=None)
        if isinstance(layer, str) and layer.strip():
            self.cmbVizLayers.setCurrentText(layer)

        SelectedOnly2 = self.config['Settings']['SelectedOnly2'].lower() == "true"
        self.cbSelectedOnly2.setChecked(SelectedOnly2)

        self.txtMinTransfers.setText(self.config['Settings']['Min_transfer'])
        self.txtMaxTransfers.setText(self.config['Settings']['Max_transfer'])
        self.txtMaxWalkDist1.setText(self.config['Settings']['MaxWalkDist1'])
        self.txtMaxWalkDist2.setText(self.config['Settings']['MaxWalkDist2'])
        self.txtMaxWalkDist3.setText(self.config['Settings']['MaxWalkDist3'])

        datetime = QDateTime.fromString(
            self.config['Settings']['TIME'], "HH:mm:ss")
        self.dtStartTime.setDateTime(datetime)

        self.txtSpeed.setText(self.config['Settings']['Speed'])
        self.txtMaxWaitTime.setText(self.config['Settings']['MaxWaitTime'])
        self.txtMaxWaitTimeTransfer.setText(self.config['Settings']['MaxWaitTimeTransfer'])
        self.txtMaxTimeTravel.setText(self.config['Settings']['MaxTimeTravel'])
        
        max_extra_time = self.config['Settings'].get('maxextratime', '30')
        self.txtMaxExtraTime.setText(max_extra_time)

        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field'])
        self.cmbLayersDest_fields.setCurrentText(self.config['Settings']['LayerDest_field'])
        self.cmbVizLayers_fields.setCurrentText(self.config['Settings']['LayerViz_field'])

        RunOnAir = self.config['Settings']['RunOnAir'].lower() == "true"
        self.cbRunOnAir.setChecked(RunOnAir)

        self.txtAliase.setText(self.default_alias)

        self.handleRunOnAirClick()


    def check_max_foothpath(self):

        if self.UpperBoundMaxWalkDist > 0 and (int(self.txtMaxWalkDist1.text()) > self.UpperBoundMaxWalkDist
                                               or int(self.txtMaxWalkDist2.text()) > self.UpperBoundMaxWalkDist
                                               or int(self.txtMaxWalkDist3.text()) > self.UpperBoundMaxWalkDist):

            if self.txtMaxWalkDist1.text() and int(self.txtMaxWalkDist1.text()) > self.UpperBoundMaxWalkDist:
                self.txtMaxWalkDist1.setText(str(self.UpperBoundMaxWalkDist))
            if self.txtMaxWalkDist2.text() and int(self.txtMaxWalkDist2.text()) > self.UpperBoundMaxWalkDist:
                self.txtMaxWalkDist2.setText(str(self.UpperBoundMaxWalkDist))
            if self.txtMaxWalkDist3.text() and int(self.txtMaxWalkDist3.text()) > self.UpperBoundMaxWalkDist:
                self.txtMaxWalkDist3.setText(str(self.UpperBoundMaxWalkDist)) 

            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setTextFormat(Qt.RichText)
            msgBox.setTextInteractionFlags(Qt.TextBrowserInteraction)
            msgBox.setWindowTitle("Warning")
            msgBox.setText(
                f"The value 'Maximum walk distance' exceeds {self.UpperBoundMaxWalkDist} meters –<br>"
                f"the maximum allowed walking distance used for the database construction.<br>"
                f"If you want to continue with the new value of the maximum distance,<br>"
                f"the transit routing database must be rebuilt (see "
                f"<a href='https://geosimlab.github.io/accessibility-calculator-tutorial/building_pkl.html#building-database-for-transit-accessibility'>tutorial</a>).<br><br>"
                f"Currently trimmed to {self.UpperBoundMaxWalkDist} meters."
                )
            msgBox.setStandardButtons(QMessageBox.Ok )
            msgBox.exec_()
           
            return False

        return True
    
    def check_folder_and_file(self):

        os.makedirs(self.txtPathToProtocols.text(), exist_ok=True)

        required_files = [  # 'dict_building_vertex.pkl',
            # 'dict_vertex_buildings.pkl',
            # 'graph_footpath.pkl',
            'idx_by_route_stop.pkl',

            'rev_idx_by_route_stop.pkl',
            'routes_by_stop.pkl',
            'routesindx_by_stop.pkl',

            'stops_dict_pkl.pkl',
            'stops_dict_reversed_pkl.pkl',
            'stoptimes_dict_pkl.pkl',

            'stoptimes_dict_reversed_pkl.pkl',
            'transfers_dict_air.pkl',
            'transfers_dict_projection.pkl',

            'graph_projection.pkl',
            'dict_osm_vertex.pkl',
            'dict_vertex_osm.pkl',
            'stop_ids.pkl'
        ]
        missing_files = [file for file in required_files if not os.path.isfile(
            os.path.join(self.txtPathToPKL.text(), file))]

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(f"Files are missing in the '{self.txtPathToPKL.text()}' forlder: {missing_files_message}")
            return False
        
        if not os.path.exists(self.txtPathToProtocols.text()):
            self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' does not exist")
            return False

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the '{self.txtPathToProtocols.text()}' folder is denied")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def get_feature_from_layer(self):
        layer = self.config['Settings']['Layer']
        feature_id_field = self.config['Settings']['Layer_field']
        isChecked = self.cbSelectedOnly1.isChecked()

        if self.mode == 2:
            layer = self.config['Settings']['LayerDest']
            feature_id_field = self.config['Settings']['LayerDest_field']
            isChecked = self.cbSelectedOnly2.isChecked()
        
        layer = QgsProject.instance().mapLayersByName(layer)[0]
        ids = []
        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'Layer {layer} is empty')
            return 0

        if isChecked:
            features = layer.selectedFeatures()
            if len(features) == 0:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setText(
                    f"'Selected features only' option is chosen but selection set is empty.")
                msgBox.setWindowTitle("Information")
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec_()
                self.setMessage('')
                return 0

        features = layer.getFeatures()
        if isChecked:
            features = layer.selectedFeatures()

        i = 0
        for feature in features:
            i = + 1
            if i % 50000 == 0:
                QApplication.processEvents()
            id = feature[feature_id_field]
            ids.append((int(id)))

        return ids
   
    def prepareRaptor(self):
        self.break_on = False
        QApplication.processEvents()
        
        protocol_type = self.protocol_type
        timetable_mode = self.timetable_mode
        sources = self.get_feature_from_layer()

        if sources == 0:
            self.run_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            return 0

        run = True
        
        if len(sources) > 10:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            take_min = round((len(sources)*2)/60)
            msgBox.setText(
                f"Layer contains {len(sources)} feature and it will take at least {take_min} minutes to finish the computations. Maximum 10 feature are recommended. Are you sure?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.Yes:
                run = True
            else:
                run = False

        if run:
            PathToNetwork = self.config['Settings']['PathToPKL']
            raptor_mode = self.mode
            
            RunOnAir = self.config['Settings']['RunOnAir'] == 'True'

            Layer = self.config['Settings']['Layer']
            LayerDest = self.config['Settings']['LayerDest']

            if self.mode == 2:
                Layer = self.config['Settings']['LayerDest']
                LayerDest = self.config['Settings']['Layer']

            layer_origin = QgsProject.instance().mapLayersByName(Layer)[0]
            layer_dest = QgsProject.instance().mapLayersByName(LayerDest)[0]    
                        
            if not os.path.exists(self.folder_name):
                os.makedirs(self.folder_name)
            else:
                self.setMessage(f"Folder '{self.folder_name}' already exists")
                self.run_button.setEnabled(True)
                self.close_button.setEnabled(True)
                self.textLog.clear()
                self.tabWidget.setCurrentIndex(0)
                self.progressBar.setValue(0)
                return 0
            
            dictionary  = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        RunOnAir
                        )
            
            """
            if self.shift_mode:
                self.folder_name_copy = self.folder_name
                
                generator = TimeMarkGenerator(
                    start_hour=7,
                    end_hour=19,
                    marks_per_hour=2,
                    n_experiments=1,
                    )
                times = generator.run()
                self.textLog.append(f"Times: {times}")
                
                for i, source in enumerate(sources):
                
                    source = [source]
                    
                    if i % 10 == 0:
                        self.textLog.append(f"Num {i}")
                   
                  
                    for idx, D_TIME_str in enumerate(times):                    
                        
                        t = datetime.strptime(D_TIME_str, '%H:%M:%S')
                        D_TIME = t.hour * 3600 + t.minute * 60 + t.second

                        if not self.timetable_mode:
                            if self.mode == 1:
                                self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
                            else:
                                self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
                        if self.timetable_mode:
                            if self.mode == 1:
                                self.textLog.append(f"<a style='font-weight:bold;'> Earliest start time: {D_TIME_str}</a>")
                            else:
                                self.textLog.append( f"<a style='font-weight:bold;'> Earliest arrival time: {D_TIME_str}</a>")
                
                 
                        postfix = i + 1 
                        self.folder_name = os.path.join(f'{self.folder_name_copy}_{source}', f'{self.txtAliase.text()}-{postfix}')

                        os.makedirs(self.folder_name, exist_ok=True)
        
                        runRaptorWithProtocol(self,
                                  source,
                                  mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  dictionary,
                                  self.shift_mode,
                                  layer_dest,
                                  layer_origin,
                                  PathToNetwork
                                  )
                        i += 1
                    
                        if self.break_on:
                            self.setMessage("Statistic computations are interrupted by user")
                            self.textLog.append(f'<a><b><font color="red">Statistic computations are interrupted by user</font> </b></a>')
                            self.progressBar.setValue(0)
                            break
                            #return 0
                    
                    #base_path = f'{self.folder_name_copy}_{source}' # os.path.dirname(self.folder_name) #self.folder_name_copy
                    #output_path = os.path.join(os.path.dirname(base_path), f"stat_{source}_{self.alias}.csv")
                    #processor = DayStat_DestinationID(base_path, output_path)
                    #processor.process_files()
                    #self.textLog.append(f'<a href="file:///{base_path}" target="_blank" >Statistics in folder</a>')
            """
            #analyzer_time = 0.0
            if self.shift_ctrl_mode:
                
                begin_computation_time = datetime.now()
                begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
                self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
                                
                time_delta = int(self.config_add['Settings']['time_delta'])

                from_time_start = time_to_seconds(self.config_add['Settings']['from_time_start'])
                from_time_end = time_to_seconds(self.config_add['Settings']['from_time_end'])
                to_time_start = time_to_seconds(self.config_add['Settings']['to_time_start'])
                to_time_end = time_to_seconds(self.config_add['Settings']['to_time_end'])

                self.textLog.append(f'<a>Time step: {self.config_add['Settings']['time_delta']} sec</a>')
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating roundtrip accessibility</a>")

                raptor_mode = 1    
                dictionary_from = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        RunOnAir,
                        )
                
                raptor_mode = 2    
                dictionary_to = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        RunOnAir,
                        )
                
                
                ###########################
                #  First From + First TO
                # #########################
                # #########################
                # First From
                # #########################
                #self.folder_name_from = f'{self.folder_name}_from'
                self.folder_name_copy = self.folder_name
                self.folder_name_from = os.path.join(self.folder_name_copy, "from")
                os.makedirs(self.folder_name_from, exist_ok=True)

                analyzer = roundtrip_analyzer(
                                        report_path = os.path.dirname(self.folder_name_from), 
                                        duration_max=3600, 
                                        alias = self.alias)

                START_TIME = from_time_start

                self.textLog.append(f"<a style='font-weight:bold;'> Calculating first from accessibility</a>")
                self.mode = 1
                raptor_mode = 1 
                D_TIME = START_TIME
                    
                D_TIME_str = seconds_to_time(D_TIME)
                if self.timetable_mode:
                        self.textLog.append(f"<a style='font-weight:bold;'> Earliest start time: {D_TIME_str}</a>")
                else:
                        self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
                 
                postfix = 1
                self.folder_name = os.path.join(self.folder_name_from, str(postfix)) 
                os.makedirs(self.folder_name, exist_ok=True)
                
                short_result = runRaptorWithProtocol(self,
                                  sources,
                                  raptor_mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  dictionary_from,
                                  self.shift_ctrl_mode,
                                  layer_dest,
                                  layer_origin,
                                  PathToNetwork                                  
                                  )
                
                if not(self.break_on):
                    #begin_analyzer_time = time.perf_counter()
                    first_from = analyzer.get_data_for_analyzer_from_to(short_result)
                    #end_analyzer_time = time.perf_counter()
                    #analyzer_time += end_analyzer_time - begin_analyzer_time  

                # #########################
                # First to
                # #########################
                START_TIME = to_time_start
                                
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating first to accessibility</a>")
                
                self.mode = 2
                raptor_mode = 2    
                
                self.folder_name_to = os.path.join(self.folder_name_copy, "to")
                os.makedirs(self.folder_name_to, exist_ok=True)

                D_TIME = START_TIME
                                 
                D_TIME_str = seconds_to_time(D_TIME)
                                           
                if self.timetable_mode:
                       self.textLog.append( f"<a style='font-weight:bold;'> Earliest arrival time: {D_TIME_str}</a>")
                else:   
                       self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
                    
                postfix = 1
                self.folder_name = os.path.join(self.folder_name_to, str(postfix)) 
                os.makedirs(self.folder_name, exist_ok=True)
                                        
                short_result = runRaptorWithProtocol(self,
                                  sources,
                                  raptor_mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  dictionary_to,
                                  self.shift_ctrl_mode,
                                  layer_dest,
                                  layer_origin,
                                  PathToNetwork                                  
                                  )

                if not(self.break_on):
                    #begin_analyzer_time = time.perf_counter()

                    first_to = analyzer.get_data_for_analyzer_from_to (short_result)
                    analyzer.init_from_data(first_to, first_from)

                    #end_analyzer_time = time.perf_counter()
                    #analyzer_time += end_analyzer_time - begin_analyzer_time
                    #print (f'analyzer_time {analyzer_time}')  
                
                ###########################
                #  From
                # #########################
                START_TIME = from_time_start
                Tf = from_time_end

                self.textLog.append(f"<a style='font-weight:bold;'> Calculating remained from accessibility</a>")
                self.mode = 1
                raptor_mode = 1 
                
                i = 1
                while True:
                
                    D_TIME = START_TIME + i * time_delta 
                    #if D_TIME > Tf:
                    #        break 
                    
                    if D_TIME > Tf + time_delta / 2: 
                        break

                    D_TIME_str = seconds_to_time(D_TIME)
                    if self.timetable_mode:
                        self.textLog.append(f"<a style='font-weight:bold;'> Earliest start time: {D_TIME_str}</a>")
                    else:
                        self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
                 
                    postfix = i + 1
                    self.folder_name = os.path.join(self.folder_name_from, str(postfix)) 
                    os.makedirs(self.folder_name, exist_ok=True)
                    short_result = runRaptorWithProtocol(self,
                                  sources,
                                  raptor_mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  dictionary_from,
                                  self.shift_ctrl_mode,
                                  layer_dest,
                                  layer_origin,
                                  PathToNetwork
                                  )
                    
                    if not(self.break_on):
                        #begin_analyzer_time = time.perf_counter()

                        data_from = analyzer.get_data_for_analyzer_from_to (short_result)
                        analyzer.add_from_data(data_from)
         
                        #end_analyzer_time = time.perf_counter()
                        #analyzer_time += end_analyzer_time - begin_analyzer_time  

                        #print (f'analyzer_time {analyzer_time}')

                    if self.break_on:
                        self.setMessage("Roundtrip accessibility computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                    i += 1
                
                ###########################
                #  TO
                # #########################
                START_TIME = to_time_start
                Tf = to_time_end
                
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating remained to accessibility</a>")
                
                self.mode = 2
                raptor_mode = 2    
                

                i = 1

                while True:
                    D_TIME = START_TIME + i * time_delta 
                    
                    #if D_TIME > Tf:
                    #        break
                                        
                    if D_TIME > Tf + time_delta / 2: 
                        break
                   
                    D_TIME_str = seconds_to_time(D_TIME)
                                           
                    if self.timetable_mode:
                       self.textLog.append( f"<a style='font-weight:bold;'> Earliest arrival time: {D_TIME_str}</a>")
                    else:   
                       self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
                    
                    postfix = i + 1
                    self.folder_name = os.path.join(self.folder_name_to, str(postfix)) 
                    os.makedirs(self.folder_name, exist_ok=True)
                                        
                    short_result= runRaptorWithProtocol(self,
                                  sources,
                                  raptor_mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  dictionary_to,
                                  self.shift_ctrl_mode,
                                  layer_dest,
                                  layer_origin,
                                  PathToNetwork
                                  )
                    if not(self.break_on):
                        #begin_analyzer_time = time.perf_counter()

                        data_to = analyzer.get_data_for_analyzer_from_to (short_result)
                        analyzer.add_to_data(data_to)

                        #end_analyzer_time = time.perf_counter()
                        #analyzer_time += end_analyzer_time - begin_analyzer_time  

                        #print (f'analyzer_time {analyzer_time}')

                        i += 1
                    if self.break_on:
                        self.setMessage("Roundtrip accessibility computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                
                
                if not(self.break_on):
                    
                    """
                    processor = StatFromTo(self,
                                           self.folder_name_from, 
                                           self.folder_name_to, 
                                           os.path.dirname(self.folder_name_from), 
                                           ""
                                           )
                    processor.process_files()
                    
                    analyzer = TripAnalyzer(self,
                                    path_from = self.folder_name_from,
                                    path_to = self.folder_name_to,
                                    duration_max = 60*60,  # 60 минут
                                    )
                    result_path1 = os.path.join(os.path.dirname(self.folder_name_from),"result_bin.csv")
                    result_path2 = os.path.join(os.path.dirname(self.folder_name_from),"result_round_trip.csv")
                    result = analyzer.run(result_path1, result_path2, mode = "duration")
                    """

                    #begin_analyzer_time = time.perf_counter()

                    analyzer.run_finalize_all()

                    #end_analyzer_time = time.perf_counter()
                    #analyzer_time += end_analyzer_time - begin_analyzer_time  

                    #print (f'analyzer_time {analyzer_time}')

                    self.textLog.append(f'<a href="file:///{os.path.dirname(self.folder_name_from)}" target="_blank" >Statistics in folder</a>')

                    after_computation_time = datetime.now()
                    after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
                    self.textLog.append(f'<a>Finished {after_computation_str}</a>')
                    duration_computation = after_computation_time - begin_computation_time
                    duration_without_microseconds = str(duration_computation).split('.')[0]
                    self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')
                

            if not(self.shift_mode) and not (self.shift_ctrl_mode):
                
                self.run_button.setEnabled(False)
                D_TIME = time_to_seconds(self.config['Settings']['TIME'])
                
                #pr = cProfile.Profile()
                #pr.enable()

                runRaptorWithProtocol(self,
                                  sources,
                                  raptor_mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  self.cbSelectedOnly1.isChecked(),
                                  self.cbSelectedOnly2.isChecked(),
                                  dictionary,
                                  False,
                                  layer_dest,
                                  layer_origin,
                                  PathToNetwork
                                  )
                
                #pr.disable()
                #s = io.StringIO()
                #sortby = 'cumulative'
                #ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                #ps.print_stats()
                
                #with open(r"c:\temp\profile_output.txt", "w") as f:
                #    f.write(s.getvalue())

            
            return 1

        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")
            return 0

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
    
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
        
        hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')

        if self.protocol_type == 2:
            if self.mode == 1 and  self.timetable_mode:
                help_filename = "pt_sa_from_sh.txt"
            if self.mode == 1 and  not (self.timetable_mode):
                help_filename = "pt_sa_from_fix.txt"
            if self.mode == 2 and  self.timetable_mode:
                help_filename = "pt_sa_to_sh.txt"
            if self.mode == 2 and  not (self.timetable_mode):
                help_filename = "pt_sa_to_fix.txt"
        
        if self.protocol_type == 1:
            if self.mode == 1 and  self.timetable_mode:
                help_filename = "pt_reg_from_sh.txt"
            if self.mode == 1 and  not (self.timetable_mode):
                help_filename = "pt_reg_from_fix.txt"
            if self.mode == 2 and  self.timetable_mode:
                help_filename = "pt_reg_to_sh.txt"
            if self.mode == 2 and  not (self.timetable_mode):
                help_filename = "pt_reg_to_fix.txt"

        hlp_file = os.path.join(hlp_directory, help_filename)
        hlp_file = os.path.normpath(hlp_file)
        self.load_text_with_bold_first_line (hlp_file)
    
    def find_latest_log(self, directory):

        if not os.path.exists(self.txtPathToPKL.text()):
            return False
        
        pattern = re.compile(r'log_pkl_pt_(\d{6}_\d{6})\.txt$')
        latest_file = None
        latest_timestamp = None
    
        for filename in os.listdir(directory):
            match = pattern.match(filename)
            if match:
                timestamp = match.group(1)
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp
                    latest_file = filename
    
        return os.path.join(directory, latest_file) if latest_file else None

    def extract_parameters(self, file_path):
        params = {
            "Maximal walking path on road": 0,
            "Maximal walking path on air": 0
        }
    
        if not file_path or not os.path.exists(file_path):
            return params
    
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                for key in params.keys():
                    if line.startswith(key):
                        try:
                            params[key] = int(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
    
        return params
        

