import os
import webbrowser
import configparser
from datetime import datetime
import glob
import re

from qgis.PyQt import QtCore

from qgis.core import (QgsApplication,
                       QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QVariant,
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
                    showAllLayersInCombo_Polygon
                    )

from buildings_clean import cls_clean_buildings

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'buildings_clean.ui')
)

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
        self.toolButtonBuildings.setVisible(False)
        self.splitter.setSizes(
            [int(self.width() * 0.6), int(self.width() * 0.4)])

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

        showAllLayersInCombo_Polygon(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)

        self.cmbLayers_fields.installEventFilter(self)
        self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)
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

        self.task = None
        self.already_show_info = False

        #self.cmbLayers_fields.setVisible(False)
        #self.label_2.setVisible(False)

        self.show()
        self.ParametrsShow()
        self.show_info()

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

        obj_layer_fields.addItem("Create ID")

        if osm_id_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == "osm_id":
                    obj_layer_fields.setCurrentIndex(i)
                    break

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

        if not (self.check_type_layer_road()):
            self.run_button.setEnabled(True)
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

        self.layer_road = QgsProject.instance().mapLayersByName(
            self.config['Settings']['layer_clean-buildings'])[0]
        self.layer_road_path = self.layer_road.dataProvider().dataSourceUri().split("|")[
            0]
        self.textLog.append(f"<a>Initial layer of buildings: {self.layer_road_path}</a>")
        
        self.folder_name = self.config['Settings']['PathToProtocols_clean-buildings']
        self.textLog.append(f"<a>Folder to store clean layer of buildings: {self.folder_name}</a>")

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        self.break_on = False

        osm_id_field = self.config['Settings']['Layer_field_clean-buildings']
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.task = cls_clean_buildings(
            begin_computation_time, 
            self.layer_road, 
            self.folder_name, 
            osm_id_field
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
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'building_pkl.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://ishusterman.github.io/tutorial/building_pkl.html#topological-cleaning-of-the-road-and-building-layers"
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

        if 'Layer_field_clean-buildings' not in self.config['Settings']:
            self.config['Settings']['Layer_field_clean-buildings'] = ''    

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')
        self.config['Settings']['Layer_clean-buildings'] = self.cmbLayers.currentText()
        self.config['Settings']['PathToProtocols_clean-buildings'] = self.txtPathToProtocols.text()
        self.config['Settings']['Layer_field_clean-buildings'] = self.cmbLayers_fields.currentText()
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):
        self.readParameters()
        self.cmbLayers.setCurrentText(
            self.config['Settings']['Layer_clean-buildings'])
        self.txtPathToProtocols.setText(
            self.config['Settings']['PathToProtocols_clean-buildings'])
        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field_clean-buildings'])

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_type_layer_road(self):

        layer = self.cmbLayers.currentText()

        if layer == "":
            self.setMessage(f"There are no open polygon layers")
            return 0

        layer = QgsProject.instance().mapLayersByName(layer)[0]

        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f"Layer '{self.cmbLayers.currentText()}' is empty")
            return 0

        for feature in features:
            feature_geometry = feature.geometry()
            feature_geometry_type = feature_geometry.type()
            break
        
        if not (feature_geometry_type in {QgsWkbTypes.PolygonGeometry}):
            self.setMessage(f"Features in the layer '{self.cmbLayers.currentText()}' must be polygones")
            return 0

        return 1

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
        
