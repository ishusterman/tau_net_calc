import os
import webbrowser
import configparser

from qgis.core import (QgsProject,
                       QgsMapLayerProxyModel,
                       )

from qgis.PyQt.QtCore import (Qt,
                          QEvent,
                          QDate,
                          QTimer
                          )

from qgis.PyQt.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )

from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt import uic

try:
    # QGIS 3
    from qgis.PyQt.QtCore import QRegExp
    from qgis.PyQt.QtGui import QRegExpValidator
    RegExpClass = QRegExp
    RegExpValidatorClass = QRegExpValidator
except ImportError:
    # QGIS 4
    from qgis.PyQt.QtCore import QRegularExpression
    from qgis.PyQt.QtGui import QRegularExpressionValidator
    RegExpClass = QRegularExpression
    RegExpValidatorClass = QRegularExpressionValidator

from tau_net_calc.cls.GTFS import GTFS
from tau_net_calc.cls.PKL import PKL
from datetime import datetime

from tau_net_calc.cls.common import (get_qgis_info, 
                    zip_directory, 
                    getDateTime, 
                    check_file_parameters_accessibility, 
                    get_documents_path,
                    get_gtfs_date_range,
                    FIELD_ID,
                    check_layer,
                    transform_log_to_csv_text,
                    highlight_empty_fields,
                    highlight_widget,
                    setup_clear_highlight_listeners,
                    install_parent_folder_dialog
                    )

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'pkl.ui')
)

class form_pkl(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)

        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        self.splitter.setSizes(
            [int(self.width() * 0.6), int(self.width() * 0.4)])
        

        fm = self.txtMaxPathRoad.fontMetrics()
        char_width = fm.horizontalAdvance("x")

        fix_size = 20 * char_width

        self.txtMaxPathRoad.setFixedWidth(fix_size)
        self.calendar.setFixedWidth(fix_size)

        # [1-600]
        #regex = QRegExp(r"^(?:[1-9]|[1-9][0-9]|[1-5][0-9]{2}|600)$")
        regex = RegExpClass(r"\d*")
        int_validator = RegExpValidatorClass(regex)
        self.txtMaxPathRoad.setValidator(int_validator)
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False
        self.title = title
        self.progressBar.setValue(0)
        
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_GTFS.clicked.connect(lambda: self.showFoldersDialog(self.txtPathToGTFS))
        self.toolButton_protocol.clicked.connect(lambda: self.showFoldersDialog(self.txtPathToProtocols))


        self.txtPathToGTFS.textChanged.connect(self.on_PathToGTFS_changed)

        self.cmbLayers.installEventFilter(self)
        self.cmbLayers.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        self.cbRoads.installEventFilter(self)
        self.cbRoads.setFilters(QgsMapLayerProxyModel.Filter.LineLayer)

        self.calendar.installEventFilter(self)
        
        self.btnBreakOn.clicked.connect(self.set_break_on)

        role_action = QDialogButtonBox.ButtonRole.ActionRole
        role_reject = QDialogButtonBox.ButtonRole.RejectRole
        role_help = QDialogButtonBox.ButtonRole.HelpRole

        self.run_button = self.buttonBox.addButton("Run", role_action)
        self.close_button = self.buttonBox.addButton("Close", role_reject)
        self.help_button = self.buttonBox.addButton("Help", role_help)


        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

        self.ParametrsShow()
        self.show_info()

        self.label_9.setWordWrap(True)
        self.setLabelDayGTFS()

        self.on_PathToGTFS_changed()

        setup_clear_highlight_listeners(self)

        QTimer.singleShot(
                            0,
                            lambda: setattr(
                                self,
                                "_pkl_filter",
                                install_parent_folder_dialog(self.txtPathToGTFS)
                            )
                        )
        
        QTimer.singleShot(
                            0,
                            lambda: setattr(
                                self,
                                "_pkl_filter",
                                install_parent_folder_dialog(self.txtPathToProtocols)
                            )
                        )


    def on_PathToGTFS_changed (self):
        path = self.txtPathToGTFS.text() + "_json"
        self.txtPathToProtocols.setText(path)

                
    def setLabelDayGTFS (self):
        min_str, max_str, result = get_gtfs_date_range(self.txtPathToGTFS.text())
        msg = f"Choose a day for constructing transit routing database"
        if min_str and max_str:
            min_date = QDate.fromString(min_str, "yyyyMMdd")
            max_date = QDate.fromString(max_str, "yyyyMMdd")
            self.calendar.setMinimumDate(min_date)
            self.calendar.setMaximumDate(max_date)
            date_info = f"GTFS dataset covers {min_date.toString('dd.MM.yyyy')} - {max_date.toString('dd.MM.yyyy')}. " if result else ""
            if date_info:
                msg = f"{date_info}  \n{msg}"
        self.label_9.setText(msg)
        self.label_9.setEnabled(result)
        self.calendar.setEnabled(result)

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)

    def on_run_button_clicked(self):

        shift_mod = Qt.KeyboardModifier.ShiftModifier

        if QApplication.keyboardModifiers() & shift_mod:
            self.to_delete_gtfs = False
        else:
            self.to_delete_gtfs = True

        self.run_button.setEnabled(False)
        self.setMessage("")                

        if highlight_empty_fields(self, exclude=[self.textLog]):    
            self.setMessage("All required fields must be filled in")                    
            self.run_button.setEnabled(True)
            return 0

        self.break_on = False
        self.layer_road = self.cbRoads.currentLayer() 
        self.layer_building = self.cmbLayers.currentLayer() 

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        
        result, text = check_layer(self.layer_building, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
        
        result, text = check_layer(self.layer_road, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
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
        self.textLog.append(f'<a> [Input]</a>')
        self.textLog.append(f"<a> Layer of buildings: {self.layer_buildings_path}</a>")
        self.textLog.append(f"<a> Layer of roads: {self.layer_roads_path}</a>")
        self.textLog.append(f"<a> Maximum length of a single walk: {self.config['Settings']['MaxPathRoad_pkl']}</a>")
        
        self.textLog.append(f"<a> GTFS dataset folder: {self.config['Settings']['PathToGTFS_pkl']}</a>")
        self.textLog.append(f"<a> The day for constructing transit routing database: {QDate.fromString(self.config['Settings']['Date_pkl'], 'yyyyMMdd').toString('dd.MM.yyyy')}</a>")
        self.textLog.append(f'<a> [Output]</a>')

        self.textLog.append(f"<a> Folder to store transit routing database: {self.config['Settings']['PathToProtocols_pkl']}</a>")

        self.prepare()
        if self.break_on:
            return 0
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):        
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/prepare_database.html#building-a-database-for-transit-accessibility-computations"
        webbrowser.open(url)
    
    def showFoldersDialog(self, obj):

        current_path = obj.text()
        start_dir = ""
        if current_path:            
            start_dir = os.path.dirname(current_path)            

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            start_dir
        )

        if folder_path:
            obj.setText(os.path.normpath(folder_path))

        if obj == self.txtPathToGTFS:
            self.setLabelDayGTFS()

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_pkl = os.path.join(project_directory, f'{project_name}_json')
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

        if 'MaxPathRoad_pkl' not in self.config['Settings']:
            self.config['Settings']['MaxPathRoad_pkl'] = '400'    

        if 'Date_pkl' not in self.config['Settings']:
            self.config['Settings']['Date_pkl'] = '20000101'  

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config['Settings']['PathToProtocols_pkl'] = self.txtPathToProtocols.text()
        self.config['Settings']['PathToGTFS_pkl'] = self.txtPathToGTFS.text()
        self.config['Settings']['Roads_pkl'] = self.cbRoads.currentLayer().id()
        self.config['Settings']['Layer_pkl'] = self.cmbLayers.currentLayer().id()
        
        self.config['Settings']['MaxPathRoad_pkl'] = self.txtMaxPathRoad.text()
        
        selected_date = self.calendar.date()
        self.config['Settings']['Date_pkl'] = selected_date.toString("yyyyMMdd")

        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToGTFS.setText(os.path.normpath(self.config['Settings']['PathToGTFS_pkl']))

        #self.txtPathToProtocols.setText(os.path.normpath(self.config['Settings']['PathToProtocols_pkl']))
        self.txtMaxPathRoad.setText(self.config['Settings']['MaxPathRoad_pkl'])
        
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_pkl'])        
        self.cbRoads.setCurrentText(self.config['Settings']['Roads_pkl'])

        self.cbRoads.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Roads_pkl']))
        self.cmbLayers.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Layer_pkl']))

        date_string = self.config['Settings']['Date_pkl']
        qdate_object = QDate.fromString(date_string, "yyyyMMdd")
        self.calendar.setDate(qdate_object)

    def check_folder_and_file(self):

        path = self.txtPathToProtocols.text()
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
       
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            self.run_button.setEnabled(True)
            highlight_widget(self.txtPathToProtocols)              
            self.setMessage(f'The path {os.path.dirname(path)} is not found')
            return False

        
        file_path = os.path.join(path, f"stoptimes.json")
        prefix = os.path.basename(path)
        file_path_prefix = os.path.join(path, f"{prefix}_stoptimes.json")
        if  os.path.isfile(file_path) or os.path.isfile(file_path_prefix):
            msgBox = QMessageBox()
                        
            icon_question = QMessageBox.Icon.Question
            btn_yes = QMessageBox.StandardButton.Yes
            btn_no = QMessageBox.StandardButton.No


            msgBox.setIcon(icon_question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f"The folder '{path}' already contains a database. Overwrite?")
            msgBox.setStandardButtons(btn_yes | btn_no)

            result = msgBox.exec()
            if result == btn_no:
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
    
    def prepare(self):
        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

        self.break_on = False
        
        layer_origins_field = FIELD_ID
        MaxPathRoad = self.config['Settings']['MaxPathRoad_pkl']
        

        QApplication.processEvents()
                
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
                                 check_date,
                                 to_delete_gtfs = self.to_delete_gtfs
                                 )
            run_ok = calc_GTFS.correcting_files()
                
        if run_ok:
            
            path_to_GTFS = path_to_file
            calc_PKL = PKL(self,
                                   path_to_pkl = path_to_PKL,
                                   path_to_GTFS = path_to_GTFS,
                                   layer_buildings = self.layer_building,
                                   building_id_field = layer_origins_field,
                                   to_delete_gtfs = self.to_delete_gtfs
                                   )
            run_ok = calc_PKL.create_files()

            if not self.to_delete_gtfs: 
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

            text = transform_log_to_csv_text(self.textLog.toPlainText())
            postfix = getDateTime()
            
            filelog_name = os.path.join(path_to_PKL, f'log_json_pt_{postfix}.csv')
            with open(filelog_name, "w") as file:
                file.write(text)

        if run_ok :
                self.textLog.append(f'<a href="file:///{path_to_PKL}" target="_blank" >dictionary in folder</a>')

                self.setMessage(f'Finished')

        if not (run_ok):
            #self.run_button.setEnabled(True)
            #self.close_button.setEnabled(True)
            #self.textLog.clear()
            #self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        wheel_type = QEvent.Type.Wheel

        if event.type() == wheel_type:
            if obj.hasFocus():
                event.ignore()
                return True

        return super().eventFilter(obj, event)
        
    def show_info(self):

        hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')
      
        help_filename = "build_transit_routing_database.txt"
        hlp_file = os.path.join(hlp_directory, help_filename)

        if os.path.exists(hlp_file):
            with open(hlp_file, 'r', encoding='utf-8') as f:
                html = f.read()

        self.textInfo.setOpenExternalLinks(False)  
        self.textInfo.setOpenLinks(False)          
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))  

    def closeEvent(self, event):
        self.break_on = True
        event.accept()
