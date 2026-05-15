import os
#import cProfile
#import pstats

import webbrowser
import configparser
from datetime import datetime
import math
from math import floor
import os
from pathlib import Path


from PyQt5.QtCore import Qt

from qgis.core import (QgsProject,
                       QgsMapLayerProxyModel
                       )

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
                    get_prefix_alias, 
                    seconds_to_time, 
                    time_to_seconds, 
                    check_file_parameters_accessibility,
                    FIELD_ID,
                    check_layer,
                    transform_log_to_dataframe,
                    fast_write_gpkg,
                    getDateTime,
                    highlight_empty_fields                   
                    )

from visualization import visualization
from AnalyzerFromTo_incremental import roundtrip_analyzer
from common import (get_initial_directory,
                    get_name_columns,
                    transform_log_to_csv_text,
                    highlight_widget,
                    highlight_widget_no,
                    get_tablename)

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'raptor.ui'))

class RaptorDetailed(QDialog, FORM_CLASS):
    def __init__(self, 
                 parent, 
                 mode, 
                 protocol_type, 
                 title, 
                 timetable_mode, 
                 roundtrip = False):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        self.InitialNameWalk1 = "Maximum walk distance"        
        self.splitter.setSizes([int(self.width() * 0.75), int(self.width() * 0.25)])

        self.fix_size = 15* self.txtMinTransfers.fontMetrics().width('x')

        self.fix_size2 = 5* self.txtMinTransfers.fontMetrics().width('x')
        
        self.fix_size3 = 25 * self.txtMinTransfers.fontMetrics().width('x')
        self.fix_size4 = 20 * self.txtMinTransfers.fontMetrics().width('x')

        self.txtMinTransfers.setFixedWidth(self.fix_size2)
        self.txtMaxTransfers.setFixedWidth(self.fix_size2)
        self.txtMaxWalkDist1.setFixedWidth(self.fix_size2)
        self.txtMaxWalkDist2.setFixedWidth(self.fix_size2)
        self.txtMaxWalkDist3.setFixedWidth(self.fix_size2)
        self.txtSpeed.setFixedWidth(self.fix_size2)
        self.txtMaxWaitTime.setFixedWidth(self.fix_size2)
        self.txtMaxWaitTimeTransfer.setFixedWidth(self.fix_size2)
        
        
        self.fix_size2 = 7 * self.txtTimeInterval.fontMetrics().width('x')
        self.txtMaxTimeTravel.setFixedWidth(self.fix_size2)
        self.txtMaxExtraTime.setFixedWidth(self.fix_size2)
        
        self.dtStartTime.setFixedWidth(self.fix_size)
        self.dtEndTime.setFixedWidth(self.fix_size)
                
        self.txtTimeInterval.setFixedWidth(self.fix_size2)

        self.cmbFields_ch.setFixedWidth(self.fix_size4)
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()
        
        self.break_on = False
        
        self.parent = parent
        self.mode = mode
        self.protocol_type = protocol_type
        self.title = title
        self.timetable_mode = timetable_mode
        self.roundtrip = roundtrip
        # self.change_time = 1

        self.progressBar.setValue(0)
                    
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)
                
        self.cmbLayers.installEventFilter(self)
        self.cmbLayersDest.installEventFilter(self)
        
        self.cmbLayers.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.cmbLayersDest.setFilters(QgsMapLayerProxyModel.PolygonLayer)        

        self.dtStartTime.installEventFilter(self)
        self.dtEndTime.installEventFilter(self)
        self.btnBreakOn.clicked.connect(self.set_break_on)

        self.run_button = self.buttonBox.addButton("Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton("Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton("Help", QDialogButtonBox.HelpRole)

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
        self.txtMaxExtraTime.setValidator(int_validator1)
        self.txtSpeed.setValidator(int_validator3)
        self.txtMaxWaitTime.setValidator(int_validator3)
        self.txtMaxWaitTimeTransfer.setValidator(int_validator3)
        self.txtMaxTimeTravel.setValidator(int_validator3)
        
        regex = QRegExp(r"\d*")
        int_validator = QRegExpValidator(regex)
        #self.txtTimeInterval.setValidator(int_validator)
        self.txtRountrip_timedelta1.setValidator(int_validator)
        self.txtRountrip_timedelta2.setValidator(int_validator)

        self.dtRoundtripStartTime1.installEventFilter(self)
        self.dtRoundtripStartTime2.installEventFilter(self)
        self.dtRoundtripStartTime3.installEventFilter(self)
        self.dtRoundtripStartTime4.installEventFilter(self)
        
        
        self.dtRoundtripStartTime1.setFixedWidth(self.fix_size)
        self.dtRoundtripStartTime2.setFixedWidth(self.fix_size)
        self.dtRoundtripStartTime3.setFixedWidth(self.fix_size)
        self.dtRoundtripStartTime4.setFixedWidth(self.fix_size)
        self.fix_size2 = 7* self.txtMinTransfers.fontMetrics().width('x')
        self.txtRountrip_timedelta1.setFixedWidth(self.fix_size2)
        self.txtRountrip_timedelta2.setFixedWidth(self.fix_size2)
                
        
        if self.protocol_type == 2:
            self.txtTimeInterval.setVisible(False)
            self.lblTimeInterval.setVisible(False)
            self.lblMinutes.setVisible(False)
                        
            self.cmbFields_ch.setVisible(False)
            self.lblFields.setVisible(False)
                                
        self.rbFrom.toggled.connect(self.on_radio_button_changed)
        self.rbTo.toggled.connect(self.on_radio_button_changed)
        self.rbRound.toggled.connect(self.on_radio_button_changed)
                                
        self.ParametrsShow()
        self.show_info()
        self.changeInterface()

        if self.timetable_mode:
            self.lblMaxWaitInitial.setEnabled(False)
            self.txtMaxWaitTime.setEnabled(False)
        
        if  self.timetable_mode:
            self.lblRoundtrip_TestEvery1.setText("schedule-adjustment gap")
            self.lblRoundtrip_TestEvery2.setText("schedule-adjustment gap")
        else:
            self.lblRoundtrip_TestEvery1.setText("test every ")
            self.lblRoundtrip_TestEvery2.setText("test every ")
        
        
        self.dtRoundtripStartTime1.timeChanged.connect(lambda: self.update_timedelta(1))
        self.dtRoundtripStartTime2.timeChanged.connect(lambda: self.update_timedelta(1))
        self.dtRoundtripStartTime3.timeChanged.connect(lambda: self.update_timedelta(2))
        self.dtRoundtripStartTime4.timeChanged.connect(lambda: self.update_timedelta(2))
        
        self.wgFileSave.setFilter("GeoPackage (*.gpkg)")

        self.fillComboBoxWithLayerFields()
        self.cmbLayers.currentIndexChanged.connect(self.fillComboBoxWithLayerFields)
        self.cmbLayersDest.currentIndexChanged.connect(self.fillComboBoxWithLayerFields)

        self.lblEstimateTime.setText("")
        
    def move_fields_combo_to_origin(self, to_origin_layout: bool):
        # 1. Удаляем cmbFields_ch из текущего layout
        parent_layout = self.cmbFields_ch.parentWidget().layout()
        parent_layout.removeWidget(self.cmbFields_ch)
        parent_layout.removeWidget(self.lblFields)        

        # 2. Добавляем в нужный layout
        if to_origin_layout:
            self.horizontalLayout_19.addWidget(self.lblFields)
            self.horizontalLayout_19.addWidget(self.cmbFields_ch)             
        else:
            self.horizontalLayout_18.addWidget(self.lblFields)
            self.horizontalLayout_18.addWidget(self.cmbFields_ch)
            

    def update_timedelta(self, pair_index):
        if self.timetable_mode:
            return
        if pair_index == 1:
            t1, t2 = self.dtRoundtripStartTime1, self.dtRoundtripStartTime2
            output_field = self.txtRountrip_timedelta1
        else:
            t1, t2 = self.dtRoundtripStartTime3, self.dtRoundtripStartTime4
            output_field = self.txtRountrip_timedelta2
        seconds_1 = t1.time().msecsSinceStartOfDay() // 1000
        seconds_2 = t2.time().msecsSinceStartOfDay() // 1000
        # 300 сек (5 мин) за каждый час, но не более 900 сек (15 мин)
        duration_hours = math.ceil((seconds_2 - seconds_1) / 3600)
        time_delta_sec = min(900, duration_hours * 300)
               
        time_delta_min = round(time_delta_sec / 60)
        output_field.setText(str(abs(time_delta_min)))
    
    def on_radio_button_changed(self):
        
        sender = self.sender()
        if not sender.isChecked():
            return

        if sender is self.rbFrom:
            self.mode = 1
            self.roundtrip = False
        elif sender is self.rbTo:
            self.mode = 2
            self.roundtrip = False
        elif sender is self.rbRound:
            self.mode = 2
            self.roundtrip = True

        self.changeInterface()
        self.fillComboBoxWithLayerFields()

    # for widget with checkbox
    def fillComboBoxWithLayerFields(self):

        sender = self.sender()
        origin = self.mode == 2 or self.roundtrip

        if self.roundtrip:
            sender == self.cmbLayers        

        if sender == self.cmbLayers and not origin:
            return
        
        if sender == self.cmbLayersDest and origin:
            return

        self.cmbFields_ch.clear()        

        if self.mode == 1:
            layer = self.cmbLayersDest.currentLayer()
        else:
            layer = self.cmbLayers.currentLayer()
        if self.roundtrip:
            layer = self.cmbLayers.currentLayer()

        try:
            fields = [field for field in layer.fields()]
        except:
            return 0

        for field in fields:
            field_type = field.type()
            field_name = field.name()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                if field_name.lower() not in ("fid", "osm_id", "id", "aid"):
                    self.cmbFields_ch.addItem(field_name)

        if QApplication.keyboardModifiers() & Qt.ShiftModifier:
            if 'Field_ch' not in self.config['Settings']:
                self.config['Settings']['Field_ch'] = ''

            for i in range(self.cmbFields_ch.count()):
                item_text = self.cmbFields_ch.itemText(i)

                if item_text in self.config['Settings']['Field_ch']:
                    self.cmbFields_ch.setItemData(
                        i, Qt.Checked, role=Qt.CheckStateRole)
                else:
                    self.cmbFields_ch.setItemData(
                        i, Qt.Unchecked, role=Qt.CheckStateRole)

                            
    def changeInterface (self):


        if self.mode == 1:
            self.lblStartTime1.setText("Start from the origin at (hh:mm:ss)")
        if self.mode == 2:
            self.lblStartTime1.setText("Arrive to destination at (hh:mm:ss)")
        
        if self.timetable_mode and self.mode == 1:
            self.lblStartTime1.setText("The earliest start")
                        
        if self.timetable_mode and self.mode == 2:
            self.lblStartTime1.setText("The earliest arrival")
                        
        widgets_to_hide = [
                self.dtRoundtripStartTime1, self.dtRoundtripStartTime2,
                self.dtRoundtripStartTime3, self.dtRoundtripStartTime4,
                self.txtRountrip_timedelta1, self.txtRountrip_timedelta2,
                self.lblRoundtripName1, self.lblRoundtrip2, self.lblRoundtrip3,
                self.lblRoundtrip_TestEvery1, self.lblRoundtrip5, self.lblRoundtripName2,
                self.lblRoundtrip7, self.lblRoundtrip8, self.lblRoundtrip_TestEvery2,
                self.lblRoundtrip10, self.widget_spacer1, self.widget_spacer2,
                
            ]
         
        for widget in widgets_to_hide:
                
                widget.setVisible(self.roundtrip)

        
        self.dtStartTime.setVisible(not self.roundtrip)
        self.dtEndTime.setVisible(not self.roundtrip)
        self.lblStartTime1.setVisible(not self.roundtrip)
        
        self.lblStartTime3.setVisible(not self.roundtrip)
        self.lblStartTime4.setVisible(not self.roundtrip)
        self.txtMaxExtraTime.setVisible(not self.roundtrip)
        self.widget_spacer3.setVisible(not self.roundtrip)

        self.dtEndTime.setVisible(self.timetable_mode and not self.roundtrip)
        
        self.lblStartTime3.setVisible(self.timetable_mode and not self.roundtrip)
        self.lblStartTime4.setVisible(self.timetable_mode and not self.roundtrip)
        self.txtMaxExtraTime.setVisible(self.timetable_mode and not self.roundtrip)


        self.default_alias = getDateTime()
        
        self.wgFileSave.setFilePath(os.path.join(os.path.dirname(self.wgFileSave.filePath()), f"{self.default_alias}.gpkg"))
        self.dtEndTime.setVisible(False)

        to_origin = (self.mode == 2) or self.roundtrip
        self.move_fields_combo_to_origin(to_origin)
                           
    def handleMaximalWalking(self):
        self.lbMaxWalkDistanceInitial.setText(f'{self.InitialNameWalk1} (up to 800 m)')

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
    
    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False
        self.setMessage("")

        highlight_widget_no(self.wgFileSave)        


        if highlight_empty_fields(self, exclude=[self.textLog, self.cmbFields_ch]):
            self.setMessage("All required fields must be filled in")        
            self.run_button.setEnabled(True)
            return 0

        
        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        
        if self.mode == 1:
            self.layer1 = self.cmbLayers.currentLayer() 
            self.layer2 = self.cmbLayersDest.currentLayer() 
        else:
            self.layer2 = self.cmbLayers.currentLayer() 
            self.layer1 = self.cmbLayersDest.currentLayer()

        if self.roundtrip:
            self.layer2 = self.cmbLayers.currentLayer() 
            self.layer1 = self.cmbLayersDest.currentLayer() 
        
        result, text = check_layer(self.layer1, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
        
        result, text = check_layer(self.layer2, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
                        
        self.layer_path1 = os.path.normpath(self.layer1.dataProvider().dataSourceUri().split("|")[0])
        self.layer_path2 = os.path.normpath(self.layer2.dataProvider().dataSourceUri().split("|")[0])
        self.count_layer_destinations = self.layer2.featureCount()

        if self.protocol_type == 1: # cumulative
            self.layer_visualization = self.layer1
        else:
            self.layer_visualization = self.layer2
                
        self.layer_vis_field = FIELD_ID
        
        file_path = self.wgFileSave.filePath()        
        base, ext = os.path.splitext(file_path)
        if ext.lower() != ".gpkg":
            file_path = base + ".gpkg"
        self.file_name_gpkg = file_path

        folder = os.path.dirname(self.file_name_gpkg)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        if os.path.exists(self.file_name_gpkg):
            try:
                os.remove(self.file_name_gpkg)
            except PermissionError:
                self.run_button.setEnabled(True)
                highlight_widget(self.wgFileSave)
                self.setMessage(f'The file "{self.file_name_gpkg}" is locked.')
                return 0
            

        
        
        
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

        if self.mode == 1:
            mode_text = "FROM origins"
        else:
            mode_text = "TO destinations"
        if self.roundtrip:
            mode_text = "ROUNDTRIP"
        self.textLog.append(f'<a> Accessibility: {mode_text}</a>')
        
        self.textLog.append("<a style='font-weight:bold;'>[Input Layers]</a>")        
        self.textLog.append(f"<a> Transit routing database folder: {self.config['Settings']['pathtopkl']}</a>")
        self.textLog.append(f'<a> Layer of origins: {self.layer_path1} ({get_tablename(self.layer1)}) </a>')        
        self.textLog.append(f'<a> Layer of destinations: {self.layer_path2} ({get_tablename(self.layer2)})</a>')

        if self.protocol_type == 1:  # MAP mode
            if self.config['Settings']['field_ch'] != "":
                print_fields = self.config['Settings']['field_ch']
            else:
                print_fields = "NONE"
            self.textLog.append(f"<a> Opportunities' fields: {print_fields}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Time Settings]</a>")

        if not (self.roundtrip) and not self.timetable_mode:
            if self.mode == 1:
                self.textLog.append(f"Start from the origin: {self.config['Settings']['TIME']}")
            else:
                self.textLog.append(f"Arrive to destination: {self.config['Settings']['TIME']}")

        if self.timetable_mode :
            if self.mode == 1:
                if not self.roundtrip:
                    str_from = f'<a>The earliest start: {self.config['Settings']['TIME']} schedule-adjustment gap {self.config['Settings']['MaxExtraTime']} minutes</a>'                
                    self.textLog.append(str_from)

            if self.mode == 2:
                if not self.roundtrip:
                    str_to = f'<a>The earliest arrival: {self.config['Settings']['TIME']} schedule-adjustment gap {self.config['Settings']['MaxExtraTime']} minutes</a>'                
                    self.textLog.append(str_to)

        self.total_cycles_roundtrip = 1

        if self.roundtrip:
            self.time_delta_to_min = int(self.config['Settings']['time_delta_to']) 
            self.time_delta_from_min = int(self.config['Settings']['time_delta_from']) 
            self.time_delta_to  = self.time_delta_to_min * 60
            self.time_delta_from  = self.time_delta_from_min * 60

            self.from_time_start = time_to_seconds(self.config['Settings']['from_time_start'])
            self.from_time_end = time_to_seconds(self.config['Settings']['from_time_end'])
            self.to_time_start = time_to_seconds(self.config['Settings']['to_time_start'])
            self.to_time_end = time_to_seconds(self.config['Settings']['to_time_end'])

            cycles_to   = floor((self.to_time_end   - self.to_time_start)   / self.time_delta_to)   + 1
            cycles_from = floor((self.from_time_end - self.from_time_start) / self.time_delta_from) + 1
            self.total_cycles_roundtrip = cycles_to * cycles_from

            if self.timetable_mode:
                text_add = "schedule-adjustment gap"
            else:
                text_add = "test every"
                        
            str_from = f'<a>Arrive to destination between: {seconds_to_time(self.to_time_start)} and {seconds_to_time(self.to_time_end)} {text_add} {self.time_delta_to_min} minutes</a>'
            self.textLog.append(str_from)
            str_to = f'<a>Start trip back to the origin between: {seconds_to_time(self.from_time_start)} and {seconds_to_time(self.from_time_end)} {text_add} {self.time_delta_from_min} minutes</a>'
            self.textLog.append(str_to)
        
        self.textLog.append(f"<a> Maximum travel time: {self.config['Settings']['maxtimetravel']} min</a>")
                        
        self.textLog.append("<a style='font-weight:bold;'>[Transit Tolerance Thresholds]</a>")
        self.textLog.append(f"<a> Number of transfers: between {self.config['Settings']['min_transfer']} and {self.config['Settings']['max_transfer']}</a>")
        self.textLog.append(f"<a> Maximum walk distance to the initial PT stop: {self.config['Settings']['maxwalkdist1']} m</a>")
        self.textLog.append(f"<a> Maximum walk distance between at the transfer: {self.config['Settings']['maxwalkdist2']} m</a>")
        self.textLog.append(f"<a> Maximum walk distance from the last PT stop: {self.config['Settings']['maxwalkdist3']} m</a>")
        self.textLog.append(f"<a> Average walking speed: {self.config['Settings']['speed']} km/h</a>")

        if not self.timetable_mode:
            self.textLog.append(f"<a> Maximum waiting time at the initial stop: {self.config['Settings']['maxwaittime']} min</a>")
        self.textLog.append(f"<a> Maximum waiting time at the transfer stop: {self.config['Settings']['maxwaittimetransfer']} min</a>")
        
        self.textLog.append("<a style='font-weight:bold;'>[Output]</a>")
        self.textLog.append(f"<a> Output file: {self.config['Settings']['pathtoprotocols']}</a>")
        if self.protocol_type == 1:  # MAP mode
            self.textLog.append(f"<a> Save time bin: {self.config['Settings']['timeinterval']} min</a>")
        
        
        self.MaxExtraTime = 0
        if self.timetable_mode :
            self.MaxExtraTime = int(self.txtMaxExtraTime.text())*60
                
        if self.roundtrip: # and self.timetable_mode:
            #self.MaxExtraTime = int(self.config['Settings']['MaxExtraTime'])*60
            self.MaxExtraTimeTo = int(self.txtRountrip_timedelta1.text())*60
            self.MaxExtraTimeFrom = int(self.txtRountrip_timedelta2.text())*60
            
        
        
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
            self.handleMaximalWalking()
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

        if 'MaxExtraTime' not in self.config['Settings']:
            self.config['Settings']['MaxExtraTime'] = '20'
                
        if 'PathToProtocols' not in self.config['Settings'] or self.config['Settings']['PathToProtocols'] == "C:/":
            self.config['Settings']['PathToProtocols'] = PathToProtocols      
        self.config['Settings']['PathToProtocols'] = os.path.normpath(self.config['Settings']['PathToProtocols'])

        value = self.config['Settings'].get('EndTIME')
        if not value or not is_valid_time(value): 
            self.config['Settings']['EndTIME'] = '14:00:00'
    
        value = self.config['Settings'].get('time_delta_to')
        if not value or not str(value).isdigit():
            self.config['Settings']['time_delta_to'] = '15'

        value = self.config['Settings'].get('time_delta_from')
        if not value or not str(value).isdigit():
            self.config['Settings']['time_delta_from'] = '15'

        value = self.config['Settings'].get('from_time_start')
        if not value or not is_valid_time(value): 
            self.config['Settings']['from_time_start'] = '16:00:00'

        value = self.config['Settings'].get('from_time_end')
        if not value or not is_valid_time(value): 
            self.config['Settings']['from_time_end'] = '18:00:00'
        
        value = self.config['Settings'].get('to_time_start')
        if not value or not is_valid_time(value): 
            self.config['Settings']['to_time_start'] = '08:00:00'

        value = self.config['Settings'].get('to_time_end')
        if not value or not is_valid_time(value): 
            self.config['Settings']['to_time_end'] = '10:00:00'

        value = self.config['Settings'].get('radio_button_type') 
        if not value:
            self.config['Settings']['radio_button_type'] = "to"


    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToPKL'] = self.wgPathPKL.filePath()
        self.config['Settings']['PathToProtocols'] = self.wgFileSave.filePath()
        
        self.config['Settings']['Layer'] = self.cmbLayers.currentLayer().id()
        self.config['Settings']['LayerDest'] = self.cmbLayersDest.currentLayer().id()
                        
        self.config['Settings']['Min_transfer'] = self.txtMinTransfers.text()
        self.config['Settings']['Max_transfer'] = self.txtMaxTransfers.text()
                
        self.config['Settings']['MaxWalkDist1'] = self.txtMaxWalkDist1.text()
        self.config['Settings']['MaxWalkDist2'] = self.txtMaxWalkDist2.text()
        self.config['Settings']['MaxWalkDist3'] = self.txtMaxWalkDist3.text()
        self.config['Settings']['TIME'] = self.dtStartTime.dateTime().toString("HH:mm:ss")
        self.config['Settings']['EndTIME'] = self.dtEndTime.dateTime().toString("HH:mm:ss")
        self.config['Settings']['Speed'] = self.txtSpeed.text()
        if not self.timetable_mode:
            self.config['Settings']['MaxWaitTime'] = self.txtMaxWaitTime.text()
        self.config['Settings']['MaxWaitTimeTransfer'] = self.txtMaxWaitTimeTransfer.text()
        self.config['Settings']['MaxTimeTravel'] = self.txtMaxTimeTravel.text()
        self.config['Settings']['MaxExtraTime'] = self.txtMaxExtraTime.text()
        
        self.config['Settings']['to_time_start'] = self.dtRoundtripStartTime1.dateTime().toString("HH:mm:ss")
        self.config['Settings']['to_time_end'] = self.dtRoundtripStartTime2.dateTime().toString("HH:mm:ss")
        self.config['Settings']['from_time_start'] = self.dtRoundtripStartTime3.dateTime().toString("HH:mm:ss")
        self.config['Settings']['from_time_end'] = self.dtRoundtripStartTime4.dateTime().toString("HH:mm:ss")
        self.config['Settings']['time_delta_to'] = self.txtRountrip_timedelta1.text()
        self.config['Settings']['time_delta_from'] = self.txtRountrip_timedelta2.text()

        if self.rbFrom.isChecked():
            rb_state = "from"
        elif self.rbTo.isChecked():
            rb_state = "to"
        elif self.rbRound.isChecked():
            rb_state = "round"
        
        self.config['Settings']['radio_button_type'] = rb_state
        
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.default_alias = getDateTime()
        
        self.wgFileSave.setFilePath(os.path.join(os.path.dirname(self.config['Settings']['PathToProtocols']), f"{self.default_alias}.gpkg"))
        self.wgPathPKL.setFilePath(os.path.normpath(self.config['Settings']['PathToPKL']))
                
        if QApplication.keyboardModifiers() & Qt.ShiftModifier:
            self.cmbLayers.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Layer']))
            self.cmbLayersDest.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['LayerDest']))  
            self.txtMaxTimeTravel.setText(self.config['Settings']['MaxTimeTravel'])          
        else:
            self.cmbLayers.setCurrentIndex(0)
            self.cmbLayersDest.setCurrentIndex(0)            
        
        self.txtMinTransfers.setText(self.config['Settings']['Min_transfer'])
        self.txtMaxTransfers.setText(self.config['Settings']['Max_transfer'])
        self.txtMaxWalkDist1.setText(self.config['Settings']['MaxWalkDist1'])
        self.txtMaxWalkDist2.setText(self.config['Settings']['MaxWalkDist2'])
        self.txtMaxWalkDist3.setText(self.config['Settings']['MaxWalkDist3'])

        datetime = QDateTime.fromString(self.config['Settings']['TIME'], "HH:mm:ss")
        self.dtStartTime.setDateTime(datetime)

        datetime = QDateTime.fromString(self.config['Settings']['EndTIME'], "HH:mm:ss")
        self.dtEndTime.setDateTime(datetime)

        self.txtSpeed.setText(self.config['Settings']['Speed'])
        if not self.timetable_mode:
            self.txtMaxWaitTime.setText(self.config['Settings']['MaxWaitTime'])
        else:
            self.txtMaxWaitTime.setText('0') 
        self.txtMaxWaitTimeTransfer.setText(self.config['Settings']['MaxWaitTimeTransfer'])
        self.txtMaxExtraTime.setText (self.config['Settings']['MaxExtraTime'])
        
        
        self.txtRountrip_timedelta1.setText(self.config['Settings']['time_delta_to'])
        self.txtRountrip_timedelta2.setText(self.config['Settings']['time_delta_from'])

        datetime = QDateTime.fromString(self.config['Settings']['to_time_start'], "HH:mm:ss")
        self.dtRoundtripStartTime1.setDateTime(datetime)
        datetime = QDateTime.fromString(self.config['Settings']['to_time_end'], "HH:mm:ss")
        self.dtRoundtripStartTime2.setDateTime(datetime)
        datetime = QDateTime.fromString(self.config['Settings']['from_time_start'], "HH:mm:ss")
        self.dtRoundtripStartTime3.setDateTime(datetime)
        datetime = QDateTime.fromString(self.config['Settings']['from_time_end'], "HH:mm:ss")
        self.dtRoundtripStartTime4.setDateTime(datetime)

        radio_button_type_state = self.config['Settings']['radio_button_type']
        self.roundtrip = False
        if radio_button_type_state == "from":
            self.rbFrom.setChecked(True)
            self.mode = 1
        if radio_button_type_state == "to":
            self.rbTo.setChecked(True)
            self.mode = 2
        if radio_button_type_state == "round":
            self.roundtrip = True
            self.rbRound.setChecked(True)

        if QApplication.keyboardModifiers() & Qt.ShiftModifier:                    
            if self.protocol_type == 1:
                if 'Field_ch' not in self.config['Settings']:
                    self.config['Settings']['Field_ch'] = ''

                for i in range(self.cmbFields_ch.count()):
                    item_text = self.cmbFields_ch.itemText(i)                
                    if item_text in self.config['Settings']['Field_ch']:
                        self.cmbFields_ch.setItemData(
                            i, Qt.Checked, role=Qt.CheckStateRole)
                    else:
                        self.cmbFields_ch.setItemData(
                            i, Qt.Unchecked, role=Qt.CheckStateRole)

        self.txtTimeInterval.setText(self.config['Settings']['TimeInterval'])
        
        self.handleMaximalWalking()


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

        path_to_pkl = self.wgPathPKL.filePath()
        prefix = os.path.basename(path_to_pkl)

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
            'transfers_dict_projection.pkl',

            'graph_projection.pkl',
            'dict_osm_vertex.pkl',
            'dict_vertex_osm.pkl',
            'stop_ids.pkl'
        ]
        
        missing_files = []
        for file in required_files:
            
            file_with_prefix = os.path.join(path_to_pkl, f"{prefix}_{file}")
            file_without_prefix = os.path.join(path_to_pkl, file)
            if not (os.path.isfile(file_with_prefix) or os.path.isfile(file_without_prefix)):
                missing_files.append(file)

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(f"Files are missing in the '{path_to_pkl}' folder: {missing_files_message}")
            return False
                
        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def get_feature_from_layer(self, layer):
        feature_id_field = FIELD_ID
        ids = set()
        features = layer.getFeatures()
        i = 0
        for feature in features:
            i = + 1
            if i % 50000 == 0:
                QApplication.processEvents()
            ids.add(int(feature[feature_id_field]))
            
        return ids
   
    def prepareRaptor(self):
        self.break_on = False
        QApplication.processEvents()
        
        protocol_type = self.protocol_type
        timetable_mode = self.timetable_mode
        sources = self.get_feature_from_layer(self.layer1)
        destinations = self.get_feature_from_layer(self.layer2)

        if sources == 0:
            self.run_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            return 0

        run = True
        """
        if len(sources) > 10:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            take_min = round((len(sources)*2)/60)*self.total_cycles_roundtrip
            msgBox.setText(
                f"Layer contains {len(sources)} feature and it will take at least {take_min} minutes to finish the computations. Maximum 10 feature are recommended. Are you sure?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.Yes:
                run = True
            else:
                run = False
        """
        if run:
            PathToNetwork = self.config['Settings']['PathToPKL']

            #file_name = Path(self.file_name_gpkg).stem

            file_name = get_prefix_alias(True, 
                                self.protocol_type, 
                                self.mode, 
                                self.timetable_mode,
                                self.roundtrip 
                                )
            
            layer_origin = self.layer1
            layer_dest = self.layer2
            
            dictionary  = myload_all_dict(self,
                        PathToNetwork,
                        self.mode                        
                       )
            
            #analyzer_time = 0.0

            MaxExtraTime  = self.MaxExtraTime
           
            if self.roundtrip:

                dict_NUMPOINTS = {}
                first_field = None
                list_fields_aggregate = self.config['Settings']['Field_ch']
                if list_fields_aggregate:
                    fields_to_process = [v.strip() for v in list_fields_aggregate.split(',')]
                    first_field = fields_to_process[0]

                if first_field:
                    idx_aid = self.layer2.fields().lookupField('aid')
                    idx_num = self.layer2.fields().lookupField(first_field)
                    if idx_num != -1:
                        dict_NUMPOINTS = {int(f[idx_aid]): round(f[idx_num]) for f in self.layer2.getFeatures()}
               

                self.shift_mode = True
                
                self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
                begin_computation_time = datetime.now()
                begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
                self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

                
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating roundtrip accessibility</a>")

                raptor_mode = 1    
                dictionary_from = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        )
                
                raptor_mode = 2    
                dictionary_to = myload_all_dict(self,
                        PathToNetwork,
                        raptor_mode,
                        )
                
                cols_dict = get_name_columns()
                cols = cols_dict[(2, protocol_type)]
                MaxTimeTravel = float(self.config['Settings']['MaxTimeTravel'].replace(',', '.'))*60
                bin = float(self.config['Settings']['timeinterval'].replace(',', '.'))*60
                
                #duration_max = MaxTimeTravel * 1.5
                duration_max = MaxTimeTravel
                analyzer = roundtrip_analyzer(                                        
                                        duration_max=duration_max,                                                                                 
                                        service_area = (protocol_type == 2),
                                        dict_numpoints = dict_NUMPOINTS,
                                        bin = bin
                                        )
                
                
                roundtrip_cycle_current = 0
                ###########################
                #  TO
                # #########################

                #sources = self.get_feature_from_layer(self.layer1)
                #destinations = self.get_feature_from_layer(self.layer2)

                D_TIME = START_TIME = self.to_time_start
                Tf = self.to_time_end
                
                self.textLog.append(f"<a style='font-weight:bold;'> Calculating to accessibility</a>")
                
                self.mode = 2
                   
                i = 0
                while True:
                    D_TIME_str = seconds_to_time(D_TIME)
                                           
                    if self.timetable_mode:
                       self.textLog.append( f"<a style='font-weight:bold;'> Earliest arrival time: {D_TIME_str}</a>")
                    else:   
                       self.textLog.append(f"<a style='font-weight:bold;'> Arrive before: {D_TIME_str}</a>")
                                                                                
                    MaxExtraTime = self.MaxExtraTimeTo
                    roundtrip_cycle_current += 1
                    short_result= runRaptorWithProtocol(self,
                                                        self.file_name_gpkg,
                                  sources,
                                  destinations,
                                  self.mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  dictionary_to,
                                  self.shift_mode,
                                  layer_dest,
                                  layer_origin,
                                  self.layer_visualization,
                                  PathToNetwork,
                                  MaxExtraTime,
                                  roundtrip_mode = True,
                                  roundtrip_cycle_all = self.total_cycles_roundtrip,
                                  roundtrip_cycle_current = roundtrip_cycle_current,
                                  )
                    
                    if not(self.break_on):
                        #begin_analyzer_time = time.perf_counter()

                        data_to = analyzer.get_data_for_analyzer_from_to (short_result)                        
                        analyzer.add_to_data(data_to, D_TIME_str)

                        #end_analyzer_time = time.perf_counter()
                        #analyzer_time += end_analyzer_time - begin_analyzer_time  

                        #print (f'analyzer_time {analyzer_time}')

                        i += 1
                    if self.break_on:
                        self.setMessage("Roundtrip accessibility computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                    
                    D_TIME = START_TIME + i * self.time_delta_to 
                    if D_TIME >= Tf: 
                        break
                                   
                ###########################
                #  From
                # #########################
                D_TIME = START_TIME = self.from_time_start
                Tf = self.from_time_end

                self.textLog.append(f"<a style='font-weight:bold;'> Calculating from accessibility</a>")
                self.mode = 1
                                
                i = 0
                D_TIME = START_TIME
                while True:
                
                    D_TIME_str = seconds_to_time(D_TIME)
                    if self.timetable_mode:
                        self.textLog.append(f"<a style='font-weight:bold;'> Earliest start time: {D_TIME_str}</a>")
                    else:
                        self.textLog.append(f"<a style='font-weight:bold;'> Start at: {D_TIME_str}</a>")
                 
                    postfix = i + 1
                    
                    MaxExtraTime = self.MaxExtraTimeFrom
                    roundtrip_cycle_current += 1
                    short_result = runRaptorWithProtocol(self,
                                                         self.file_name_gpkg,
                                  sources,
                                  destinations,
                                  self.mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  dictionary_from,
                                  self.shift_mode,
                                  layer_dest,
                                  layer_origin,
                                  self.layer_visualization,
                                  PathToNetwork,
                                  MaxExtraTime,
                                  roundtrip_mode = True,
                                  roundtrip_cycle_all = self.total_cycles_roundtrip,
                                  roundtrip_cycle_current = roundtrip_cycle_current,
                                  )
                    
                    if not(self.break_on):
                        #begin_analyzer_time = time.perf_counter()

                        data_from = analyzer.get_data_for_analyzer_from_to (short_result)
                        
                        analyzer.add_from_data(data_from, D_TIME_str)
         
                        #end_analyzer_time = time.perf_counter()
                        #analyzer_time += end_analyzer_time - begin_analyzer_time  

                        #print (f'analyzer_time {analyzer_time}')

                    if self.break_on:
                        self.setMessage("Roundtrip accessibility computations are interrupted by user")
                        self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                        self.progressBar.setValue(0)
                        return 0
                    i += 1

                    D_TIME = START_TIME + i * self.time_delta_from 
                    if D_TIME >= Tf: 
                        break
                    
                if not(self.break_on):
            
                    #begin_analyzer_time = time.perf_counter()

                    df_rows_std, df_rows_strict, header, pivot  = analyzer.run_finalize_all()
                    
                    
                    table_name1 = f'{file_name}_fastest_trip_all'
                    df_rows_std.columns = header
                    fast_write_gpkg(self.file_name_gpkg, table_name1, df_rows_std)

                    table_name2 = f'{file_name}_fastest_trip_by_destinations'                    
                    fast_write_gpkg(self.file_name_gpkg, table_name2, pivot)
                    
                    #table_name2 = f'{file_name}_stat_strict'
                    #df_rows_strict.columns = header
                    #fast_write_gpkg(self.file_name_gpkg, table_name2, df_rows_strict)

                    #end_analyzer_time = time.perf_counter()
                    #analyzer_time += end_analyzer_time - begin_analyzer_time  

                    #print (f'analyzer_time {analyzer_time}')

                    
                    
                    vis = visualization(self, 
                            self.layer_visualization,
                            mode = protocol_type,
                            fieldname_layer=self.layer_vis_field, 
                            from_to = 1, # from
                            roundtrip = True if protocol_type == 2 else False,
                            prefix = file_name
                            )
                    #vis.add_thematic_map(PathToRep, self.alias, set_min_value=0)   

                    after_computation_time = datetime.now()
                    after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
                    self.lblEstimateTime.setText("")
                    self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
                    
                    duration_computation = after_computation_time - begin_computation_time
                    duration_without_microseconds = str(duration_computation).split('.')[0]
                    self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')
                    self.textLog.append(f'Output in file: <a href="file:///{self.file_name_gpkg}" target="_blank" > {self.file_name_gpkg}</a>')
                    
                    text = transform_log_to_dataframe(self.textLog.toPlainText())
                    table_name = f'_{file_name}_log'
                    fast_write_gpkg(self.file_name_gpkg, table_name, text)

                    folder = os.path.dirname(self.file_name_gpkg)
                    name, ext = os.path.splitext(os.path.basename(self.file_name_gpkg))
                    filelog_name = os.path.join(folder, f"{name}_log.csv")
                    text = transform_log_to_csv_text(self.textLog.toPlainText())
                    with open(filelog_name, "w") as file:
                        file.write(text)

                    vis.add_thematic_map_gpkg(self.file_name_gpkg, table_name1, table_name1)
                    #vis.add_thematic_map_gpkg(self.file_name_gpkg, table_name2, table_name2)
                    self.setMessage('Finished')



            if not (self.roundtrip):
                self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
                self.run_button.setEnabled(False)
                D_TIME = time_to_seconds(self.config['Settings']['TIME'])
                
                #pr = cProfile.Profile()
                #pr.enable()

                runRaptorWithProtocol(self,
                                  self.file_name_gpkg,    
                                  sources,
                                  destinations,
                                  self.mode,
                                  protocol_type,
                                  timetable_mode,
                                  D_TIME,
                                  dictionary,
                                  False,
                                  layer_dest,
                                  layer_origin,
                                  self.layer_visualization,
                                  PathToNetwork,
                                  MaxExtraTime
                                  )
                
                if not(self.break_on):
                    text = transform_log_to_dataframe(self.textLog.toPlainText())
                    table_name = f'_{file_name}_log'
                    fast_write_gpkg(self.file_name_gpkg, table_name, text)

                    folder = os.path.dirname(self.file_name_gpkg)
                    name, ext = os.path.splitext(os.path.basename(self.file_name_gpkg))
                    filelog_name = os.path.join(folder, f"{name}_log.csv")
                    text = transform_log_to_csv_text(self.textLog.toPlainText())
                    with open(filelog_name, "w") as file:
                        file.write(text)
                
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
        
    def show_info(self):

            hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')

            if self.timetable_mode:
                help_filename = "transit_sa_schedule.txt"
            else:
                help_filename = "transit_sa_fixed.txt"
            hlp_file = os.path.join(hlp_directory, help_filename)

            if os.path.exists(hlp_file):
                with open(hlp_file, 'r', encoding='utf-8') as f:
                    html = f.read()

            self.textInfo.setOpenExternalLinks(False)  
            self.textInfo.setOpenLinks(False)          
            self.textInfo.setHtml(html)
            self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString())) 