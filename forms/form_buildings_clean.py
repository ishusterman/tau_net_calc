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

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QTimer
                          )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )

from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic

from common import (get_qgis_info, 
                    check_file_parameters_accessibility, 
                    getDateTime, 
                    insert_layer_ontop,
                    check_layer                    
                    )

from buildings_clean import cls_clean_buildings

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'buildings_clean.ui'))

class form_buildings_clean(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setMaximum(5)
        self.progressBar.setValue(0)

        self.toolButton_protocol.clicked.connect(lambda: self.showFoldersDialog(self.txtPathToProtocols))
        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog ())

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)
        
        self.cmbLayers.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.cmbLayers.installEventFilter(self)

        self.btnBreakOn.clicked.connect(self.set_break_on)

        self.run_button = self.buttonBox.addButton("Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton("Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton("Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

        self.task = None
        self.already_show_info = False

        self.show()
        self.ParametrsShow()
        self.show_info()

    def open_file_dialog(self):

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
            else:
                self.setMessage(f"Layer '{file_name}' is invalid or corrupted.")

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
        else:
            obj.setText(obj.text())

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

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False
        
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
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
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
    
    def add_layers(self, list_layer):
        
        for path_shp, name_layer in list_layer:
            saved_layer = QgsVectorLayer(path_shp, name_layer, "ogr")
            if saved_layer.isValid():
                QgsProject.instance().addMapLayer(saved_layer, False)
                insert_layer_ontop(saved_layer)
        
        QTimer.singleShot(250, self.save_project)        
        
        
    def save_log(self, need_save):
        if need_save:
            postfix = getDateTime()
            filelog_name = f'{self.folder_name}//log_roads_clean_{postfix}.txt'
            text = self.textLog.toPlainText()
            with open(filelog_name, "w") as file:
                file.write(text)

    def save_project(self):
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        
    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/building_pkl.html#topological-cleaning-of-the-road-and-building-layers"
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

        os.makedirs(self.txtPathToProtocols.text(), exist_ok=True)

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToProtocols.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the folder '{self.txtPathToProtocols.text()}' is denied")
            return False
        
        shp_files = glob.glob(os.path.join(self.txtPathToProtocols.text(), "*cleaned*.shp"))
        if shp_files:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f"The folder '{self.txtPathToProtocols.text()}' already contains layers. Continue?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.No:
                return False

        return True

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
    
    def show_info(self):
        
        html = """
        <b>The layer of buildings is topologically cleaned in four steps:</b>  <br /><br />
        <span style="color: grey;">

        1. The features with the absent (NULL) geometry, if exist in the layer, are deleted.<br />
        2. Multipart features are split into single parts, see <a href="https://docs.qgis.org/3.40/en/docs/user_manual/processing_algs/qgis/vectorgeometry.html#multipart-to-singleparts" target="_blank">QGIS Multipart to Single Parts documentation</a>.<br /> 
        3. Duplicated buildings, if exist, are found and excessive copies are deleted  
        4. The delete holes algorithm is employed to delete holes in the buildings, see <a href="https://docs.qgis.org/3.40/en/docs/user_manual/processing_algs/qgis/vectorgeometry.html#delete-holes" target="_blank">QGIS Delete Holes documentation</a>.<br /> 
        The building identifier must be unique. This condition is tested and the repeating or NULL identifiers are made unique by substituting the repeating values by MAX+1, MAX+2, etc., where MAX is the maximum value of the identifier before the test.<br />
        If the option “Create ID” is chosen, a new field <i>bldg_id</i> is created as the first field of the layer’s attribute table, and filled by the consecutive integer numbers, starting from 0.<br />
        </span>
        """
        self.textInfo.setOpenExternalLinks(False) 
        self.textInfo.setOpenLinks(False)          
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))
        
