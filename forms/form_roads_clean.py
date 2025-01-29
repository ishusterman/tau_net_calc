import os
import webbrowser
import configparser
from time import sleep
from datetime import datetime

from qgis.PyQt import QtCore

from qgis.core import (QgsApplication,
                       QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             )

from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic


from common import get_qgis_info, check_file_parameters_accessibility
from layer_clean import cls_clean_roads

#FORM_CLASS, _ = uic.loadUiType(os.path.join(
#    os.path.dirname(__file__), 'roads_clean.ui'))

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'roads_clean.ui')
)

class form_roads_clean(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setMaximum(5)
        self.progressBar.setValue(0)

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.showAllLayersInCombo_Line(self.cmbLayersRoad)
        self.cmbLayersRoad.installEventFilter(self)

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

        self.task = None
        self.already_show_info = False

        self.show()
        self.ParametrsShow()

    def showAllLayersInCombo_Line(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        line_layers = [layer for layer in layers
                       if isinstance(layer, QgsVectorLayer) and
                       layer.geometryType() in {QgsWkbTypes.LineGeometry} and
                       not layer.name().startswith("Temp") and
                       'memory' not in layer.dataProvider().dataSourceUri()]
        cmb.clear()
        for layer in line_layers:
            cmb.addItem(layer.name(), [])

    def EnableComboBox(self, state):

        if state == QtCore.Qt.Checked:
            self.cmbFields.setEnabled(True)
        else:
            self.cmbFields.setEnabled(False)
    
    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(folder_path)
        else:
            obj.setText(obj.text())

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        QApplication.restoreOverrideCursor()
        self.break_on = True
        self.close_button.setEnabled(True)
        if self.task:
            self.task.cancel()  
            self.progressBar.setValue(0)  
            if not (self.already_show_info):
                self.textLog.append(f'<a><b><font color="red">Process of topological cleaning is interrupted by user</font> </b></a>')
                self.already_show_info = True
            self.setMessage("")

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_type_layer_road()):
            self.run_button.setEnabled(True)
            return 0

        self.saveParameters()
        self.readParameters()

        self.setMessage("Cleaning layer of roads ...")
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

        self.layer_road = QgsProject.instance().mapLayersByName(
            self.config['Settings']['layerroad_clean'])[0]
        self.layer_road_path = self.layer_road.dataProvider().dataSourceUri().split("|")[
            0]
        self.textLog.append(f"<a>Initial road network: {self.layer_road_path}</a>")
        self.folder_name = self.config['Settings']['PathToProtocols_clean']
        self.textLog.append(f"<a>Folder to store clean road network: {self.folder_name}</a>")

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        self.break_on = False

        self.task = cls_clean_roads(
            self, begin_computation_time, self.layer_road, self.layer_road_path, self.folder_name)
        QgsApplication.taskManager().addTask(self.task)
        QApplication.processEvents()

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'building_pkl.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://ishusterman.github.io/tutorial/building_pkl.html"
        webbrowser.open(url)

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'layerroad_clean' not in self.config['Settings']:
            self.config['Settings']['layerroad_clean'] = ''

        if 'PathToProtocols_clean' not in self.config['Settings']:
            self.config['Settings']['PathToProtocols_clean'] = 'C:/'

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')
        self.config['Settings']['LayerRoad_clean'] = self.cmbLayersRoad.currentText()
        self.config['Settings']['PathToProtocols_clean'] = self.txtPathToProtocols.text()
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):
        self.readParameters()
        self.cmbLayersRoad.setCurrentText(
            self.config['Settings']['Layerroad_clean'])
        self.txtPathToProtocols.setText(
            self.config['Settings']['PathToProtocols_clean'])

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_type_layer_road(self):

        layer = self.cmbLayersRoad.currentText()
        if layer == "":
            self.setMessage(f"Layer is empty")
            return 0

        layer = QgsProject.instance().mapLayersByName(layer)[0]

        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f"Layer '{self.cmbLayersRoad.currentText()}' is empty")
            return 0

        for feature in features:
            feature_geometry = feature.geometry()
            feature_geometry_type = feature_geometry.type()
            break
        
        if not (feature_geometry_type in {QgsWkbTypes.LineGeometry}):
            self.setMessage(f"Features of the layer '{self.cmbLayersRoad.currentText()}' must be polylines")
            return 0

        return 1

    def check_folder_and_file(self):

        if not os.path.exists(self.txtPathToProtocols.text()):
            self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' does not exist")
            return False

        """
        # check for the presence of .shp files in the folder
        if os.path.isdir(self.txtPathToProtocols.text()):
        
            for file in os.listdir(self.txtPathToProtocols.text()):
                if file.lower().endswith('.shp'):
                    self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' is not empty")
                    return False
        """

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

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
