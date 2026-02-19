import os
import webbrowser
import configparser
import csv
from pathlib import Path
import pandas as pd
import io
import re

from PyQt5.QtWidgets import (QSizePolicy,
                            QTableWidget,
                            QTableWidgetItem,
                            QHeaderView)

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer,
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QVariant,
                          QRegExp,
                          QDate
                          )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )

from PyQt5.QtGui import QDesktopServices, QRegExpValidator
from PyQt5 import uic

from GTFS import GTFS
from PKL import PKL
from datetime import datetime
from gtfs_exclude_routes import GTFSExcludeRoutes
from gtfs_add_routes import GTFSAddRoutes

from common import (get_qgis_info, 
                    zip_directory, 
                    getDateTime, 
                    check_file_parameters_accessibility, 
                    get_documents_path,
                    showAllLayersInCombo_Line,
                    showAllLayersInCombo_Point_and_Polygon)

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'pkl.ui')
)

class form_pkl(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        self.splitter.setSizes(
            [int(self.width() * 0.6), int(self.width() * 0.4)])
        
        fix_size = 15* self.txtMaxPathRoad.fontMetrics().width('x')
        self.txtMaxPathRoad.setFixedWidth(fix_size)
        self.txtMaxPathAir.setFixedWidth(fix_size)
        self.calendar.setFixedWidth(fix_size)

        # [1-600]
        #regex = QRegExp(r"^(?:[1-9]|[1-9][0-9]|[1-5][0-9]{2}|600)$")
        regex = QRegExp(r"\d*")


        int_validator = QRegExpValidator(regex)
        self.txtMaxPathRoad.setValidator(int_validator)
        self.txtMaxPathAir.setValidator(int_validator)

        

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setValue(0)

        showAllLayersInCombo_Line(self.cbRoads)
        self.toolButtonRoads.clicked.connect(lambda: self.open_file_dialog (type = "roads"))
        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog (type = "buildings"))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_GTFS.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToGTFS))
        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        self.layer_road = self.get_layer_road()
        self.layer_building = self.get_layer_building()

        showAllLayersInCombo_Point_and_Polygon(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)
        self.cmbLayers_fields.installEventFilter(self)
        self.calendar.installEventFilter(self)

        self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)

        self.cbRoads.currentIndexChanged.connect(self.get_layer_road)
        self.cmbLayers.currentIndexChanged.connect(self.get_layer_building)

        self.cmbLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers, self.cmbLayers_fields))

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

        self.ParametrsShow()
        self.show_info()

        self.label_9.setWordWrap(True)
        self.setLabelDayGTFS()
        
    def setLabelDayGTFS (self):
        min_str, max_str, result = self.get_gtfs_date_range()
        msg = f"Choose a day for constructing GTFS dataset"
        if min_str and max_str:
            min_date = QDate.fromString(min_str, "yyyyMMdd")
            max_date = QDate.fromString(max_str, "yyyyMMdd")
            self.calendar.setMinimumDate(min_date)
            self.calendar.setMaximumDate(max_date)
            date_info = f"Initial GTFS dataset covers {min_date.toString('dd.MM.yyyy')} - {max_date.toString('dd.MM.yyyy')}. " if result else ""
            if date_info:
                msg = f"{date_info}  \n{msg}"
        self.label_9.setText(msg)
        self.label_9.setEnabled(result)
        self.calendar.setEnabled(result)

    def get_gtfs_date_range(self):
        gtfs_path = self.txtPathToGTFS.text()
        if not os.path.isdir(gtfs_path):
            return None, None, False

        calendar_path = os.path.join(gtfs_path, 'calendar.txt')
        calendar_dates_path = os.path.join(gtfs_path, 'calendar_dates.txt')
        
        
        dates_found = False
        
        min_date_qdate = QDate(9999, 12, 31) 
        max_date_qdate = QDate(1, 1, 1)      
        
        if os.path.exists(calendar_path):
            with open(calendar_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for key in ['start_date', 'end_date']:
                        date_str = row.get(key)
                        if date_str:
                            d = QDate.fromString(date_str, "yyyyMMdd")
                            if d.isValid():
                                dates_found = True
                                if d < min_date_qdate: min_date_qdate = d
                                if d > max_date_qdate: max_date_qdate = d

        # 2. Читаем calendar_dates.txt
        if os.path.exists(calendar_dates_path):
            with open(calendar_dates_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = row.get('date')
                    if date_str:
                        d = QDate.fromString(date_str, "yyyyMMdd")
                        if d.isValid():
                            dates_found = True
                            if d < min_date_qdate: min_date_qdate = d
                            if d > max_date_qdate: max_date_qdate = d

        # Итоговая проверка
        if not dates_found:
            # Если ни в одном файле дат нет — возвращаем текущую дату и False
            today = QDate.currentDate().toString("yyyyMMdd")
            return today, today, False
        
        return min_date_qdate.toString("yyyyMMdd"), max_date_qdate.toString("yyyyMMdd"), True

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
    
    def get_layer_building(self):
        selected_item = self.cmbLayers.currentText()
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
                else:
                    self.cmbLayers.addItem(file_path, file_path)
                    index = self.cmbLayers.findText(file_path)
                    self.cmbLayers.setCurrentIndex(index)


    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields):
       
        obj_layer_fields.clear()

        self.layer = self.get_layer_building()
        layer = self.layer

        if not layer:
            return
        fields = layer.fields()
        osm_id_exists = False


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

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)

        self.break_on = False
        self.layer_road = self.get_layer_road()
        self.layer_building = self.get_layer_building()

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        if not self.cmbLayers.currentText():
            self.run_button.setEnabled(True)
            self.setMessage("Choose the layer")
            return 0

        if not (self.check_feature_from_layer()):
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_type_layer_road()):
            self.run_button.setEnabled(True)
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

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        
        
        self.layer_buildings_path = os.path.normpath(self.layer_building.dataProvider().dataSourceUri().split("|")[0])
        self.layer_roads_path = os.path.normpath(self.layer_road.dataProvider().dataSourceUri().split("|")[0])

        self.textLog.append(f"<a> Layer of buildings: {self.layer_buildings_path}</a>")
        self.textLog.append(f"<a> Layer of roads: {self.layer_roads_path}</a>")
        self.textLog.append(f"<a> Maximal walking path on road: {self.config['Settings']['MaxPathRoad_pkl']}</a>")
        self.textLog.append(f"<a> Maximal walking path on air: {self.config['Settings']['MaxPathAir_pkl']}</a>")
        self.textLog.append(f"<a> The folder of the initial GTFS dataset: {self.config['Settings']['PathToGTFS_pkl']}</a>")
        self.textLog.append(f"<a> The day for constructing a modified GTFS dataset : {QDate.fromString(self.config['Settings']['Date_pkl'], 'yyyyMMdd').toString('dd.MM.yyyy')}</a>")
        self.textLog.append(f"<a> Folder to store transit database: {self.config['Settings']['PathToProtocols_pkl']}</a>")

        self.prepare()
        if self.break_on:
            return 0
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'building_pkl.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/building_pkl.html#building-database-for-transit-accessibility"
        webbrowser.open(url)

    def showFoldersDialog(self, obj):

        print ('showFoldersDialog')
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
                        
        else:
            obj.setText(obj.text())
        
        if obj == self.txtPathToGTFS:
            self.setLabelDayGTFS()

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_pkl = os.path.join(project_directory, f'{project_name}_pkl')
        PathToProtocols_pkl = os.path.normpath(PathToProtocols_pkl)

        documents_path = get_documents_path()
        
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToGTFS_pkl' not in self.config['Settings'] or self.config['Settings']['PathToGTFS_pkl'] == "C:/":
            self.config['Settings']['PathToGTFS_pkl'] = documents_path

        if 'PathToProtocols_pkl' not in self.config['Settings'] or self.config['Settings']['PathToProtocols_pkl'] == "C:/":
            self.config['Settings']['PathToProtocols_pkl'] = PathToProtocols_pkl
        self.config['Settings']['PathToProtocols_pkl'] = os.path.normpath(self.config['Settings']['PathToProtocols_pkl'])

        if 'Roads_pkl' not in self.config['Settings']:
            self.config['Settings']['Roads_pkl'] = ''

        if 'Layer_field_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_field_pkl'] = ''

        if 'MaxPathRoad_pkl' not in self.config['Settings']:
            self.config['Settings']['MaxPathRoad_pkl'] = '400'    

        if 'MaxPathAir_pkl' not in self.config['Settings']:
            self.config['Settings']['MaxPathAir_pkl'] = '400'        

        if 'Date_pkl' not in self.config['Settings']:
            self.config['Settings']['Date_pkl'] = '20000101'  

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config['Settings']['PathToProtocols_pkl'] = self.txtPathToProtocols.text()
        self.config['Settings']['PathToGTFS_pkl'] = self.txtPathToGTFS.text()
        self.config['Settings']['Roads_pkl'] = self.cbRoads.currentText()
        self.config['Settings']['Layer_pkl'] = self.cmbLayers.currentText()
        self.config['Settings']['Layer_field_pkl'] = self.cmbLayers_fields.currentText()
        self.config['Settings']['MaxPathRoad_pkl'] = self.txtMaxPathRoad.text()
        self.config['Settings']['MaxPathAir_pkl'] = self.txtMaxPathAir.text()
        selected_date = self.calendar.date()
        self.config['Settings']['Date_pkl'] = selected_date.toString("yyyyMMdd")

        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToGTFS.setText(os.path.normpath(self.config['Settings']['PathToGTFS_pkl']))

        #self.cmbLayers.setCurrentText(self.config['Settings']['Layer_pkl'])
        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field_pkl'])
        self.txtPathToProtocols.setText(os.path.normpath(self.config['Settings']['PathToProtocols_pkl']))
        self.txtMaxPathRoad.setText(self.config['Settings']['MaxPathRoad_pkl'])
        self.txtMaxPathAir.setText(self.config['Settings']['MaxPathAir_pkl'])

        if os.path.isfile(self.config['Settings']['Roads_pkl']):
            self.cbRoads.addItem(self.config['Settings']['Roads_pkl'])
        self.cbRoads.setCurrentText(self.config['Settings']['Roads_pkl'])


        if os.path.isfile(self.config['Settings']['Layer_pkl']):
            self.cmbLayers.addItem(self.config['Settings']['Layer_pkl'])
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_pkl'])

        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field_pkl'])

        date_string = self.config['Settings']['Date_pkl']
        qdate_object = QDate.fromString(date_string, "yyyyMMdd")
        self.calendar.setDate(qdate_object)

    def check_folder_and_file(self):

        path = self.txtPathToProtocols.text()

        if self.cbRoads.currentText() == "":
            self.setMessage(f"Layer of roads is empty")
            return False

        feature_count = self.layer_road.featureCount()
        if feature_count == 0:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' is empty")
            return False

        if not os.path.exists(self.txtPathToGTFS.text()):
            self.setMessage(f"Folder '{self.txtPathToGTFS.text()}' does not exist")
            return False

        required_files = ['stops.txt', 'trips.txt',
                          'routes.txt', 'stop_times.txt']
        missing_files = [file for file in required_files if not os.path.isfile(
            os.path.join(self.txtPathToGTFS.text(), file))]

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(f"Files are missing in the '{self.txtPathToGTFS.text()}' forlder: {missing_files_message}")
            return False

        os.makedirs(path, exist_ok=True)

        
        file_path = os.path.join(path, f"stoptimes_dict_pkl.pkl")
        prefix = os.path.basename(path)
        file_path_prefix = os.path.join(path, f"{prefix}_stoptimes_dict_pkl.pkl")
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

    def check_type_layer_road(self):

        layer = self.layer_road
        try:
            features = list(layer.getFeatures())
        except Exception:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' is empty or unreadable")
            return 0

        if not features:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' has no features")
            return 0

        feature_geometry = features[0].geometry()
        feature_geometry_type = feature_geometry.type()

        if feature_geometry_type != QgsWkbTypes.LineGeometry:
            self.setMessage(
                f"Features of the layer '{self.cbRoads.currentText()}' must be polylines"
            )
            return 0

        return 1


    def check_feature_from_layer(self):

        layer = self.layer_building
        if layer is None:
            self.setMessage("Layer is not selected")
            return 0


        try:
            features = list(layer.getFeatures())
        except Exception:
            self.setMessage(f"Layer '{self.cmbLayers.currentText()}' is unreadable")
            return 0

        if not features:
            self.setMessage(f"Layer '{self.cmbLayers.currentText()}' has no features")
            return 0

        geometryType = layer.geometryType()
        if geometryType not in (QgsWkbTypes.PointGeometry, QgsWkbTypes.PolygonGeometry):
            self.setMessage(
                f"Features of the layer '{self.cmbLayers.currentText()}' "
                f"must be points or polygons"
            )
            return 0

        return 1

    
    def prepare(self):
        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

        self.break_on = False
        
        layer_origins_field = self.config['Settings']['Layer_field_pkl']
        MaxPathRoad = self.config['Settings']['MaxPathRoad_pkl']
        MaxPathAir = self.config['Settings']['MaxPathAir_pkl']

        QApplication.processEvents()

        #gtfs_path = os.path.join(
        #    self.config['Settings']['PathToProtocols_pkl'], 'GTFS')
                
        path_to_GTFS = self.config['Settings']['PathToGTFS_pkl']
        path_to_PKL = self.config['Settings']['PathToProtocols_pkl']

        check_date = self.config['Settings']['Date_pkl']

        run_ok = True
        
        if True:
            path_to_file = os.path.join(self.config['Settings']['PathToProtocols_pkl'], 'GTFS')
            calc_GTFS = GTFS(self,
                                 path_to_file,
                                 path_to_GTFS,
                                 path_to_PKL,
                                 self.layer_building,
                                 self.layer_road,
                                 layer_origins_field,
                                 MaxPathRoad,
                                 MaxPathAir,
                                 check_date
                                 )
            run_ok = calc_GTFS.correcting_files()
                
        if run_ok:
            
            path_to_GTFS = path_to_file
            calc_PKL = PKL(self,
                                   path_to_pkl = path_to_PKL,
                                   path_to_GTFS = path_to_GTFS,
                                   layer_buildings = self.layer_building,
                                   building_id_field = layer_origins_field
                                   )
            run_ok = calc_PKL.create_files()

            zip_directory(path_to_file)

            QApplication.processEvents()
            if self.break_on:
                return 0
            after_computation_time = datetime.now()
            after_computation_str = after_computation_time.strftime(
                '%Y-%m-%d %H:%M:%S')
            self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
            duration_computation = after_computation_time - begin_computation_time
            duration_without_microseconds = str(
                duration_computation).split('.')[0]
            self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

            text = self.textLog.toPlainText()
            postfix = getDateTime()
            
            filelog_name = os.path.join(path_to_PKL, f'log_pkl_pt_{postfix}.txt')
            with open(filelog_name, "w") as file:
                file.write(text)

        if run_ok :
                self.textLog.append(f'<a href="file:///{path_to_PKL}" target="_blank" >pkl in folder</a>')

                self.setMessage(f'Finished')

        if not (run_ok):
            #self.run_button.setEnabled(True)
            #self.close_button.setEnabled(True)
            #self.textLog.clear()
            #self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

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
        help_filename = "transit_db.txt"
            
        hlp_file = os.path.join(hlp_directory, help_filename)
        hlp_file = os.path.normpath(hlp_file)
        self.load_text_with_bold_first_line (hlp_file)

    def closeEvent(self, event):
        self.break_on = True
        event.accept()
