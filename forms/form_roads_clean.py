import os
import webbrowser
import configparser
from datetime import datetime
import glob
import re

from PyQt5.QtGui import QImage

from qgis.core import (QgsApplication,
                       QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QTimer,
                          QVariant
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
                    showAllLayersInCombo_Line,
                    get_initial_directory)

#from road_layer_processor import RoadLayerProcessor

from layer_clean import cls_clean_roads

#FORM_CLASS, _ = uic.loadUiType(os.path.join(
#    os.path.dirname(__file__), 'roads_clean.ui'))

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'roads_clean.ui')
)

class form_roads_clean(QDialog, FORM_CLASS):
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

        showAllLayersInCombo_Line(self.cmbLayersRoad)
        self.cmbLayersRoad.installEventFilter(self)

        self.cmbLayers_fields.installEventFilter(self)
        self.fillComboBoxFields_Id(self.cmbLayersRoad, self.cmbLayers_fields)
        self.cmbLayersRoad.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayersRoad, self.cmbLayers_fields))

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

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong) and field_name.lower() != "maxspeed":
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
        QApplication.restoreOverrideCursor()
        self.break_on = True
        self.close_button.setEnabled(True)
        if self.task:
            self.task.cancel()  
            self.progressBar.setValue(0)  
            if not (self.already_show_info):
                self.textLog.append(f'<a><b><font color="red">Topological cleaning is interrupted by user</font> </b></a>')
                self.already_show_info = True
            self.setMessage("")

    def start_analizing_laeyers (self):
        self.run_button.setEnabled(False)

    def finish_analizing_laeyers (self):
        pass

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

        self.layer_road = QgsProject.instance().mapLayersByName(self.cmbLayersRoad.currentText())[0]
        self.layer_road_name = self.cmbLayersRoad.currentText()
        
        #self.processor_road = RoadLayerProcessor(self.layer_road, self.layer_road_name, mode = "clean")
        #self.processor_road.signals.start.connect(self.start_analizing_laeyers)
        #self.processor_road.signals.finish_clean.connect(self.finish_analizing_laeyers)
        #QgsApplication.taskManager().addTask(self.processor_road)
        
        
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

        
        self.layer_road_path = self.layer_road.dataProvider().dataSourceUri().split("|")[0]
        
        self.textLog.append(f"<a>Initial road network: {os.path.normpath(self.layer_road_path)}</a>")
        self.folder_name = self.config['Settings']['PathToProtocols_clean']
        self.textLog.append(f"<a>Folder to store clean road network: {self.folder_name}</a>")

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        self.break_on = False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        osm_id_field = self.config['Settings']['Layer_field_clean']
        self.task = cls_clean_roads(
            begin_computation_time, 
            self.layer_road, 
            self.layer_road_path,
            self.layer_road_name, 
            self.folder_name, 
            osm_id_field            
            )
                
        self.task.signals.log.connect(self.textLog.append)
        self.task.signals.progress.connect(self.progressBar.setValue)
        self.task.signals.set_message.connect(self.setMessage)
        self.task.signals.save_log.connect(self.save_log)
        self.task.signals.add_layers.connect(self.add_layers)
        self.task.signals.change_button_status.connect(self.change_button_status)
       
                
        QgsApplication.taskManager().addTask(self.task)
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

        """
        message = self.processor_road.get_message1()
        if message != "":
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle("Information")
            msgBox.setText(message)
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()
            
        message = self.processor_road.get_message2()
        if message != "":
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle("Information")
            msgBox.setText(message)
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()
        """        
            
    def save_project(self):
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        
    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        url = "https://ishusterman.github.io/tutorial/building_pkl.html#topological-cleaning-of-the-road-and-building-layers"
        webbrowser.open(url)

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_clean = os.path.join(project_directory, f'{project_name}_cleaned')
        PathToProtocols_clean = os.path.normpath(PathToProtocols_clean)
        
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'layerroad_clean' not in self.config['Settings']:
            self.config['Settings']['layerroad_clean'] = ''
        
        if 'PathToProtocols_clean' not in self.config['Settings'] or self.config['Settings']['PathToProtocols_clean'] == 'C:/':
            self.config['Settings']['PathToProtocols_clean'] = PathToProtocols_clean
        self.config['Settings']['PathToProtocols_clean'] = os.path.normpath(self.config['Settings']['PathToProtocols_clean'])

        if 'Layer_field_clean' not in self.config['Settings']:
            self.config['Settings']['Layer_field_clean'] = '' 
        

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')
        self.config['Settings']['LayerRoad_clean'] = self.cmbLayersRoad.currentText()
        self.config['Settings']['PathToProtocols_clean'] = self.txtPathToProtocols.text()
        self.config['Settings']['Layer_field_clean'] = self.cmbLayers_fields.currentText()
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):
        self.readParameters()
        self.cmbLayersRoad.setCurrentText(
            self.config['Settings']['Layerroad_clean'])
        self.txtPathToProtocols.setText(
            self.config['Settings']['PathToProtocols_clean'])
        self.cmbLayers_fields.setCurrentText(self.config['Settings']['Layer_field_clean'])

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
        
        field_names = [field.name().lower() for field in layer.fields()]
        for forbidden_field in ["fid", "cat"]:
            if forbidden_field in field_names:
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setWindowTitle("Information")

                msgBox.setText(
                            f"Layer '{self.cmbLayersRoad.currentText()}' contains the attribute '{forbidden_field}', "
                            "that is created by the system during cleaning.\n"
                            "Please rename or delete and run again."
                        )
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec_()
                return 0

        
        return 1

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
        
        html = '<b>Clean road network:</b> <br /> <br />'
        html += '<span style="color: grey;">The layer of roads is topologically cleaned by repeatedly applying different options of the <b>v.clean</b> GRASS procedure, see <a href="https://grass.osgeo.org/grass-stable/manuals/v.clean.html" target="_blank">v.clean documentation</a>. The cleaning is done in three steps:<br />'
        html += '1. The <b>v.clean</b> is applied with the <b>snap</b> option to the initial layer of roads. This stage of cleaning employed the snap threshold of 1 meter.<br />'
        html += '2. The <b>v.clean</b> is applied with the <b>break</b> option to the result of step 1, to break intersecting links at the points of intersection. New junctions are created at these points.<br />'
        html += '3. The <b>v.clean</b> is applied with the <b>rmdupl</b> option to the results of step 2, to reveal the overlapping links. Only one of them is preserved.<br /><br />'
        html += 'The road links identifier must be unique. This condition is tested, and the repeating or NULL identifiers are made unique by substituting the repeating values by MAX+1, MAX+2, etc., where MAX is the maximum value of the identifier before the test.<br />'
        html += 'If the option “Create ID” is chosen, a new field <i>link_id</i> is created as the first field of the layer’s attribute table, and filled by the consecutive integer numbers, starting from 0.'
        html += '</span>'

        self.textInfo.setOpenExternalLinks(False)  
        self.textInfo.setOpenLinks(False)          
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))
        
