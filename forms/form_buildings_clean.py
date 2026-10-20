import os
import webbrowser
import configparser
from datetime import datetime
import glob

from qgis.core import (QgsApplication,
                       QgsProject,
                       QgsVectorLayer,
                       QgsMapLayerProxyModel
                       )

from qgis.PyQt.QtCore import (Qt,
                          QEvent,
                          QTimer
                          )

from qgis.PyQt.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )

from qgis.PyQt.QtGui import QColor

from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt import uic


from tau_net_calc.cls.common import (get_qgis_info, 
                    check_file_parameters_accessibility,                     
                    insert_layer_ontop,
                    check_layer,
                    transform_log_to_csv_text,                    
                    transform_log_to_dataframe,
                    fast_write_gpkg,
                    highlight_empty_fields,
                    highlight_widget,
                    setup_clear_highlight_listeners
                    )

from tau_net_calc.cls.buildings_clean import cls_clean_buildings

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'buildings_clean.ui'))

class form_buildings_clean(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)

        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setMaximum(10)
        self.progressBar.setValue(0)

        self.toolButton_protocol.clicked.connect(lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)
        
        self.cmbLayers.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        self.cmbLayers.installEventFilter(self)

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

        self.task = None
        self.already_show_info = False

        self.show()
        self.ParametrsShow()
        self.show_info()

        setup_clear_highlight_listeners(self)

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

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        if self.task:
            self.task.cancel() 
            self.progressBar.setValue(0) 
            if not (self.already_show_info):
                self.textLog.append(f'<a><b><font color="red">Process is interrupted by user</font> </b></a>')
                self.already_show_info = True
            self.setMessage("")
        
        cursor_arrow = Qt.CursorShape.ArrowCursor

        QApplication.setOverrideCursor(cursor_arrow)

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False
        self.setMessage("")        
        
        if highlight_empty_fields(self, exclude=[self.textLog]):
            self.setMessage("All required fields must be filled in")                
            self.run_button.setEnabled(True)
            return 0
        
        result, text = check_layer(self.cmbLayers.currentLayer())
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        self.saveParameters()
        self.readParameters()

        self.setMessage("Constructing buildings database  ...")
        self.folder_name = f'{self.txtPathToProtocols.text()}'
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

        self.layer = self.cmbLayers.currentLayer()
        self.layer_path = self.layer.dataProvider().dataSourceUri().split("|")[0]

        self.textLog.append(f"<a>Initial layer of buildings: {self.layer_path}</a>")
        self.folder_name = self.config['Settings']['PathToProtocols_clean-buildings']
        self.textLog.append(f"<a>Folder to store clean layer of buildings: {self.folder_name}</a>")

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        self.break_on = False
        cursor_wait = Qt.CursorShape.WaitCursor        

        QApplication.setOverrideCursor(cursor_wait)

        self.task = cls_clean_buildings(
            begin_computation_time, 
            self.layer, 
            self.folder_name
            )
        QgsApplication.taskManager().addTask(self.task)
        self.task.signals.log.connect(self.textLog.append)
        self.task.signals.progress.connect(self.progressBar.setValue)
        self.task.signals.set_message.connect(self.setMessage)
        self.task.signals.save_log.connect(self.save_log)
        self.task.signals.add_layers.connect(self.add_layers)
        self.task.signals.change_button_status.connect(self.change_button_status)
        QApplication.processEvents()

    def change_button_status (self, need_change):
        if need_change:
            self.btnBreakOn.setEnabled(False)
            self.close_button.setEnabled(True)
    
    
    def set_no_fill_style(self, layer):
        symbol = layer.renderer().symbol()

        # Прозрачная заливка
        symbol.setColor(QColor(0, 0, 0, 0))

        # Обводка (можно настроить)
        symbol.symbolLayer(0).setStrokeColor(QColor(0, 0, 0))
        symbol.symbolLayer(0).setStrokeWidth(0.3)

        layer.triggerRepaint()

    def add_layers(self, list_layer):
        for path_shp, name_layer in list_layer:
            uri = f"{path_shp}|layername={name_layer}"
            saved_layer = QgsVectorLayer(uri, name_layer, "ogr")

            if saved_layer.isValid():
                
                self.set_no_fill_style(saved_layer)

                QgsProject.instance().addMapLayer(saved_layer, False)
                insert_layer_ontop(saved_layer)

        QTimer.singleShot(250, self.save_project)       
        

    def save_log(self, need_save, log_name) :
        if need_save:            
            filelog_name = os.path.join(self.folder_name, f"{log_name}_log.csv")
            file_name_gpkg = os.path.join(self.folder_name, f"{log_name}.gpkg")            

            text = transform_log_to_csv_text(self.textLog.toPlainText())
            with open(filelog_name, "w") as file:
                file.write(text)

            text = transform_log_to_dataframe(self.textLog.toPlainText())
            table_name = f'_{log_name}_log'                        
            fast_write_gpkg(file_name_gpkg, table_name, text)

 

    def save_project(self):
        cursor_arrow = Qt.CursorShape.ArrowCursor
        QApplication.setOverrideCursor(cursor_arrow)

        
    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/data_preprocessing.html#cleaning-the-layer-of-buildings-foundations"
        webbrowser.open(url)

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_clean_buildings = os.path.join(project_directory, f'{project_name}_cleaned')
        PathToProtocols_clean_buildings = os.path.normpath(PathToProtocols_clean_buildings)
        
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'layer_clean-buildings' not in self.config['Settings']:
            self.config['Settings']['layer_clean-buildings'] = ''

        if 'PathToProtocols_clean-buildings' not in self.config['Settings']:
            self.config['Settings']['PathToProtocols_clean-buildings'] = PathToProtocols_clean_buildings
        self.config['Settings']['PathToProtocols_clean-buildings'] = os.path.normpath(self.config['Settings']['PathToProtocols_clean-buildings'])

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')
        self.config['Settings']['Layer_clean-buildings'] = self.cmbLayers.currentLayer().id()
        self.config['Settings']['PathToProtocols_clean-buildings'] = self.txtPathToProtocols.text()
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):
        self.readParameters()
        self.cmbLayers.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Layer_clean-buildings']))
        self.txtPathToProtocols.setText(self.config['Settings']['PathToProtocols_clean-buildings'])
        
    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_folder_and_file(self):

        try:
            os.makedirs(self.txtPathToProtocols.text(), exist_ok=True)
        except OSError:
            self.run_button.setEnabled(True)
            highlight_widget(self.txtPathToProtocols)              
            self.setMessage(f'The path {self.txtPathToProtocols.text()} is not found')
            return 0

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the folder '{self.txtPathToProtocols.text()}' is denied")
            return False
        
        """
        shp_files = glob.glob(os.path.join(self.txtPathToProtocols.text(), "*cleaned*.gpkg"))
        if shp_files:

            icon_question = QMessageBox.Icon.Question
            btn_yes = QMessageBox.StandardButton.Yes
            btn_no = QMessageBox.StandardButton.No

            msgBox = QMessageBox()
            msgBox.setIcon(icon_question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f"The folder '{self.txtPathToProtocols.text()}' already contains layers. Continue?")
            msgBox.setStandardButtons(btn_yes | btn_no)

            result = msgBox.exec()
            if result == btn_no:
                return False
        """

        return True

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
        help_filename = "clean_buildings_layer.txt"
        hlp_file = os.path.join(hlp_directory, help_filename)

        if os.path.exists(hlp_file):
            with open(hlp_file, 'r', encoding='utf-8') as f:
                html = f.read()

        self.textInfo.setOpenExternalLinks(False)  
        self.textInfo.setOpenLinks(False)          
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))    
        
