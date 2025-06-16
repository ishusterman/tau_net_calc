import os
import webbrowser
import configparser
from datetime import datetime
import glob
import re
import math

from random import choice
from matplotlib.colors import CSS4_COLORS

from qgis.PyQt import QtCore

from qgis.core import (QgsApplication,
                       QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer,
                       QgsFillSymbol
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QRegExp,
                          QVariant,
                          QTimer
                          )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox,
                             )

from PyQt5.QtGui import (QRegExpValidator,
                        QDesktopServices)

from PyQt5 import uic

from common import (get_qgis_info, 
                   check_file_parameters_accessibility, 
                   getDateTime,
                   insert_layer_ontop,
                   showAllLayersInCombo_Polygon
                    )
from visualization_clean import cls_clean_visualization

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'visualization_clean.ui')
)    

class form_visualization_clean(QDialog, FORM_CLASS):
    def __init__(self, title):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.label.setText("Folder to store layers for visualization")
        self.label_3.setText("Layer of buildings")

        self.splitter.setSizes(
            [int(self.width() * 0.6), int(self.width() * 0.4)])
        
        fix_size = 10 * self.txtAddHex.fontMetrics().width('x')
        self.txtAddHex.setFixedWidth(fix_size)

        #  create a regular expression instance for integers
        regex1 = QRegExp(r"0|[1-9]\d{0,3}|10000")
        int_validator1 = QRegExpValidator(regex1)
        self.txtAddHex.setValidator(int_validator1)

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        #self.progressBar.setMaximum(5)
        self.progressBar.setValue(0)

        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog ())

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        showAllLayersInCombo_Polygon(self.cmbLayers)
        self.cmbLayers.installEventFilter(self)

        self.cmbLayers_fields.installEventFilter(self)
        
        
        
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

        file_path = self.cmbLayers.currentText()
        if self.is_file_path(file_path):
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                if self.cmbLayers.findText(file_path) == -1:
                    self.cmbLayers.addItem(file_path, file_path)
                index = self.cmbLayers.findText(file_path)
                self.cmbLayers.setCurrentIndex(index)

                self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields) 
        self.cmbLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers, self.cmbLayers_fields))
        
        self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)
        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field_clean-visualization'])
        #self.ParametrsShow()

        self.show_info()

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields):
        obj_layer_fields.clear()
        selected_layer_name = obj_layers.currentText()
        selected_layer_name = os.path.splitext(os.path.basename(selected_layer_name))[0]
        
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

        if osm_id_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == "osm_id":
                    obj_layer_fields.setCurrentIndex(i)
                    break    
            
    def get_layer_buildings(self):
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
    
    def open_file_dialog(self):
        
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
                self.cmbLayers.addItem(file_path, file_path)
                index = self.cmbLayers.findText(file_path)
                self.cmbLayers.setCurrentIndex(index)

                self.fillComboBoxFields_Id(self.cmbLayers, self.cmbLayers_fields)
    
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

        if not (self.check_add_hex()):
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        
        if not (self.check_type_layer_buildings()):
            self.run_button.setEnabled(True)
            return 0
        
        spacing = []
        if self.cb50.isChecked():
            spacing.append(50 * math.sqrt(3))
        if self.cb100.isChecked():
            spacing.append(100 * math.sqrt(3))    
        if self.cb200.isChecked():
            spacing.append(200 * math.sqrt(3))    
        if self.cb400.isChecked():
            spacing.append(400 * math.sqrt(3))    
        if self.cb800.isChecked():
            spacing.append(800 * math.sqrt(3))   
        if self.cbLength.isChecked():
            spacing.append(int (self.txtAddHex.text()) * math.sqrt(3))  
        
        if spacing == [] and not self.cbVoronoi.isChecked():
            self.setMessage(f"No checkbox is selected")
            self.run_button.setEnabled(True)
            return 0


        self.layer_buildings  = self.get_layer_buildings()
        self.layer_buildings_path = os.path.normpath(self.layer_buildings.dataProvider().dataSourceUri().split("|")[0])
        
        self.saveParameters()
        self.readParameters()

        self.setMessage("Build visualizalization layers ...")
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

        #self.layer_buildings = QgsProject.instance().mapLayersByName(
        #    self.config['Settings']['layer_clean-visualization'])[0]
        
        self.add_hex = self.config['Settings']['AddHex_clean-visualization']
        self.textLog.append(f"<a>Layer of buildings: {self.layer_buildings_path}</a>")
        
        if self.cbLength.isChecked() :
            self.textLog.append(f"<a>The layer of hexagons with a side of {self.add_hex}m</a>")        
        self.folder_name = self.config['Settings']['PathToProtocols_clean-visualization']
        self.textLog.append(f"<a>Folder to store layers for visualization: {self.folder_name}</a>")

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        self.break_on = False

        self.layer_field = self.cmbLayers_fields.currentText()
        runVoronoi = self.cbVoronoi.isChecked()

        progress_max = (1 + (len(spacing)-1) *5)
        if runVoronoi:
            progress_max += 4
        self.progressBar.setMaximum(progress_max)

             
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.task = cls_clean_visualization(
            begin_computation_time, 
            self.layer_buildings, 
            self.folder_name, 
            self.layer_field, 
            runVoronoi, 
            spacing)
        
        self.task.signals.log.connect(self.textLog.append)
        self.task.signals.progress.connect(self.progressBar.setValue)
        self.task.signals.set_message.connect(self.setMessage)
        self.task.signals.save_log.connect(self.save_log)
        self.task.signals.add_layers.connect(self.add_layers)
        self.task.signals.change_button_status.connect(self.change_button_status)
        QgsApplication.taskManager().addTask(self.task)
        
    def change_button_status (self, need_change):
        if need_change:
            self.btnBreakOn.setEnabled(False)
            self.close_button.setEnabled(True)
    
    def add_layers(self, list_layer):
        for path_shp, name_layer in list_layer:
            saved_layer = QgsVectorLayer(path_shp, name_layer, "ogr")
            if saved_layer.isValid():
                QgsProject.instance().addMapLayer(saved_layer, False)
                self.style_polygon_layer(saved_layer)
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
        url= "https://ishusterman.github.io/tutorial/building_pkl.html#building-layers-for-visualization"
        webbrowser.open(url)

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_clean_visualization = os.path.join(project_directory, f'{project_name}_visio')
        PathToProtocols_clean_visualization = os.path.normpath(PathToProtocols_clean_visualization)

        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'layer_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['layer_clean-visualization'] = ''

        if 'PathToProtocols_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['PathToProtocols_clean-visualization'] = PathToProtocols_clean_visualization
        self.config['Settings']['PathToProtocols_clean-visualization'] = os.path.normpath (self.config['Settings']['PathToProtocols_clean-visualization'])
        

        if 'AddHex_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['AddHex_clean-visualization'] = '500'    

        if 'Mode_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['Mode_clean-visualization'] = '1'   

        if 'Layer_field_clean-visualization' not in self.config['Settings']:
            self.config['Settings']['Layer_field_clean-visualization'] = ''         

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')
        self.config['Settings']['Layer_clean-visualization'] = self.cmbLayers.currentText()
        self.config['Settings']['PathToProtocols_clean-visualization'] = self.txtPathToProtocols.text()
        self.config['Settings']['AddHex_clean-visualization'] = self.txtAddHex.text()

        self.config['Settings']['Layer_field_clean-visualization'] = self.cmbLayers_fields.currentText()    


        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def is_file_path(self, text):
        return os.path.isfile(text) and os.path.splitext(text)[1] in ['.shp', '.geojson', '.kml', '.gpx']
        

    def ParametrsShow(self):
        self.readParameters()

        if os.path.isfile(self.config['Settings']['Layer_clean-visualization']):
            self.cmbLayers.addItem(self.config['Settings']['Layer_clean-visualization'])
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_clean-visualization'])
        
        self.txtPathToProtocols.setText(self.config['Settings']['PathToProtocols_clean-visualization'])
        self.txtAddHex.setText(self.config['Settings']['AddHex_clean-visualization'])
        
        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field_clean-visualization'])

        
        
    def setMessage(self, message):
        self.lblMessages.setText(message)

    def check_type_layer_buildings(self):
        
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

    def check_add_hex(self):

        if self.cbLength.isChecked() and self.txtAddHex.text() == "":
            self.setMessage(f"Value of side length is empty")
            return False
        
        return True 
    def check_folder_and_file(self):

        os.makedirs(self.txtPathToProtocols.text(), exist_ok=True)

        #if not os.path.exists(self.txtPathToProtocols.text()):
        #    self.setMessage(f"Folder '{self.txtPathToProtocols.text()}' does not exist")
        #    return False

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
        

        shp_files = glob.glob(os.path.join(self.txtPathToProtocols.text(), "*_vor*.shp"))
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
        <b>Data preprocessing, Build visualization layers:</b><br /><br />
        <span style="color: grey;">Five default layers of hexagons are constructed for visualization, in 4 steps: <br />
        Five default layers of hexagons, each covering the full extent of the layer of buildings, can be constructed for visualization: 
        1. Four layers of hexagons with the default side of 50, 100, 200, 400, and 800 m sides. <br />
        2. The hexagons that do not overlap any building are deleted from each layer. <br />
        3. The identifier of each hexagon is set equal to the identifier of the building that is closest to its centroid. If several buildings are at the same distance from the centroid, the minimal identifier is chosen. <br />
        4. The hexagons with the same identifier are dissolved into one. <br /><br />

        Additional layers of hexagons with the arbitrary length of the side can be also constructed. If you need several additional layers of hexagons, employ this command several times.<br /><br />
        The hexagon layers are constructed applying <a href="https://docs.qgis.org/3.40/en/docs/user_manual/processing_algs/qgis/vectorcreation.html#create-grid" target="_blank">QGIS Create Grid documentation</a>. 
        </span>
        """
        self.textInfo.setOpenExternalLinks(False) 
        self.textInfo.setOpenLinks(False)         
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))
    
    def closeEvent(self, event):
        self.task = None
        event.accept()

    def style_polygon_layer(self, layer):
        from tempfile import NamedTemporaryFile
        
        color_list = [color for color in CSS4_COLORS.values() if color.lower() != '#ffffff']
        random_color = choice(color_list)
        
        if layer.geometryType() == 2:

            symbol = QgsFillSymbol.createSimple({'color': '0,0,0,0', 
                                                 'outline_color': random_color})
            layer.renderer().setSymbol(symbol)
            layer.triggerRepaint()    

            with NamedTemporaryFile(suffix=".qml", delete=False) as tmpfile:
                style_path = tmpfile.name
            layer.saveNamedStyle(style_path)

        
            layer.loadNamedStyle(style_path)
            layer.triggerRepaint()    

