import os
import webbrowser
import re
from datetime import datetime
import configparser

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QFileDialog,
    QApplication,
    QMessageBox
)

from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QEvent,
                          QVariant,
                          QDateTime
                          )

from PyQt5.QtGui import QRegExpValidator, QDesktopServices
from PyQt5 import uic

from car import car_accessibility
from common import getDateTime, get_qgis_info, is_valid_folder_name, get_prefix_alias, check_file_parameters_accessibility

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'car.ui')
)

class CarAccessibility(QDialog, FORM_CLASS):
    def __init__(self,
                 mode,
                 protocol_type,
                 title,
                 ):
        super().__init__()
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])

        fix_size = 12 * self.txtTimeInterval.fontMetrics().width('x')

        self.txtMaxTimeTravel.setFixedWidth(fix_size)
        self.txtTimeInterval.setFixedWidth(fix_size)

        self.txtWalkToCAR.setFixedWidth(fix_size)
        self.txtWalkToDestination.setFixedWidth(fix_size)
        self.txtWalkingSpeed.setFixedWidth(fix_size)
        self.dtStartTime.setFixedWidth(fix_size)
        self.txtTimeGap.setFixedWidth(fix_size)

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.mode = mode
        self.protocol_type = protocol_type
        self.title = title

        self.folder_name_Car = ""

        self.progressBar.setValue(0)

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        self.toolButtonPKL.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToPKL))

        self.showAllLayersInCombo_Point_and_Polygon(self.cmbLayers)
        self.showAllLayersInCombo_Point_and_Polygon(self.cmbLayersDest)

        self.cmbLayers.installEventFilter(self)
        self.cmbLayersDest.installEventFilter(self)

        self.showAllLayersInCombo_Polygon(self.cmbVisLayers)
        self.cmbVisLayers.installEventFilter(self)

        self.dtStartTime.installEventFilter(self)

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

        # floating, two digit after dot
        regex3 = QRegExp(r"^\d+(\.\d{1,2})?$")
        int_validator3 = QRegExpValidator(regex3)

        # [1-20]
        regex4 = QRegExp(r"^(1[0-9]|20|[2-9])$")
        int_validator4 = QRegExpValidator(regex4)

        self.txtMaxTimeTravel.setValidator(int_validator3)
        self.txtTimeGap.setValidator(int_validator3)
        self.txtTimeInterval.setValidator(int_validator4)

        self.txtWalkToCAR.setValidator(int_validator3)
        self.txtWalkToDestination.setValidator(int_validator3)
        self.txtWalkingSpeed.setValidator(int_validator3)

        self.onLayerDestChanged()
        self.cmbLayersDest.currentIndexChanged.connect(self.onLayerDestChanged)
        
        self.fillComboBoxFields_Id(self.cmbLayers,
                                   self.cmbLayers_fields,
                                   "osm_id",
                                   only_digit=True)

        self.cmbLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers,
             self.cmbLayers_fields,
             "osm_id",
             only_digit=True))

        self.fillComboBoxFields_Id(self.cmbVisLayers,
                                   self.cmbVisLayers_fields,
                                   "osm_id",
                                   only_digit=True)
        self.cmbVisLayers.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbVisLayers,
             self.cmbVisLayers_fields,
             "osm_id",
             only_digit=True))

        if self.protocol_type == 2:
            self.fillComboBoxWithLayerFields2()

        if self.protocol_type == 2:

            self.txtTimeInterval.setVisible(False)
            self.label_6.setVisible(False)

            self.cmbFields_ch.setVisible(False)
            self.label.setVisible(False)

            parent_layout = self.horizontalLayout_6.parent()
            parent_layout.removeItem(self.horizontalLayout_7)

        self.default_alias = f'{getDateTime()}'

        self.ParametrsShow()

        if mode == 2:
            self.label_17.setText("Layer of origins")
            self.label_5.setText("Layer of facilities")
            self.label_11.setText("Arrive at (hh:mm:ss)")
        
        if self.protocol_type == 1:    
            if self.mode == 2:
                self.label_5.setText("Layer of all destinations in the region")
            if self.mode == 1:    
                self.label_17.setText("Layer of all origins in the region")
  

    def fillComboBoxWithLayerFields2(self):
        self.cmbFields_ch.clear()
        selected_layer_name = self.cmbLayersDest.currentText()
        selected_layer = QgsProject.instance().mapLayersByName(selected_layer_name)

        if selected_layer:
            layer = selected_layer[0]

        try:
            fields = [field for field in layer.fields()]
        except:
            return 0

        for field in fields:
            field_type = field.type()
            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                self.cmbFields_ch.addItem(field.name())

    def onLayerDestChanged(self):

        self.fillComboBoxFields_Id(self.cmbLayersDest,
                                   self.cmbLayersDest_fields,
                                   "osm_id",
                                   only_digit=True)

        self.fillComboBoxWithLayerFields2()

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields, field_name_default, only_digit=True):
        obj_layer_fields.clear()
        selected_layer_name = obj_layers.currentText()
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)

        if not layers:
            return
        layer = layers[0]

        fields = layer.fields()
        field_name_default_exists = False

        # regular expression to check for the presence of only digits
        digit_pattern = re.compile(r'^\d+$')

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                # add numeric field
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == field_name_default:
                    field_name_default_exists = True
            elif field_type == QVariant.String:
                # check the first value of the field for digits only if only_digit = True.
                if only_digit:
                    first_value = None
                    for feature in layer.getFeatures():
                        first_value = feature[field_name]
                        break  #  stop after the first value

                    if first_value is not None and digit_pattern.match(str(first_value)):
                        obj_layer_fields.addItem(field_name)
                        if field_name.lower() == field_name_default:
                            field_name_default_exists = True
                else:
                    # if the check is disabled, we simply add string fields
                    obj_layer_fields.addItem(field_name)
                    if field_name.lower() == field_name_default:
                        field_name_default_exists = True

        if field_name_default_exists:
            # iterate through all the items in the combobox and compare them with "osm_id", 
            # ignoring the case
            for i in range(obj_layer_fields.count()):
                if obj_layer_fields.itemText(i).lower() == field_name_default:
                    obj_layer_fields.setCurrentIndex(i)
                    break

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def on_run_button_clicked(self):
        self.run_button.setEnabled(False)

        if not (is_valid_folder_name(self.txtAlias.text())):
            self.setMessage(f"'{self.txtAlias.text()}' is not a valid directory/file name")
            self.run_button.setEnabled(True)
            return 0

        self.break_on = False
        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        if not self.cmbLayers.currentText():
            self.run_button.setEnabled(True)
            self.setMessage("Select the layer")
            return 0

        prefix = get_prefix_alias(
            False, self.protocol_type, self.mode, full_prefix=False)
        self.folder_name = f'{self.txtPathToProtocols.text()}//{self.txtAlias.text()}_{prefix}'

        self.file_name = self.txtAlias.text()

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
        self.textLog.append(f"<a> Output alias: {self.alias}</a>")

        self.textLog.append(f"<a> Car routing database folder: {self.config['Settings']['PathToPKL_car']}</a>")
        self.textLog.append(f"<a> Output folder: {self.config['Settings']['pathtoprotocols_car']}</a>")

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
        self.textLog.append(f"<a> Selected {name1}: {self.config['Settings']['selectedonly1_car']}</a>")
        self.textLog.append(f"<a> Layer of {name2}: {self.layer_destinations_path}</a>")
        self.textLog.append(f"<a> Selected {name2}: {self.config['Settings']['selectedonly2_car']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Parameters of a trip]</a>")

        self.textLog.append(f"<a> Maximum total travel time: {self.config['Settings']['maxtimetravel_car']} min</a>")

        self.textLog.append(f"<a> Walking distance from origin to car parking: {self.config['Settings']['Walk_to_car_car']} m</a>")
        self.textLog.append(f"<a> Walking distance from parking to destination: {self.config['Settings']['Walk_to_destination_car']} m</a>")
        self.textLog.append(f"<a> Walking speed: {self.config['Settings']['Walking_speed_car']} km/h</a>")
        if self.mode == 1:
            self.textLog.append(f"<a> Start at (hh:mm:ss): {self.config['Settings']['Start_time_car']}</a>")
        else:
            self.textLog.append(f"<a> Arrive at (hh:mm:ss): {self.config['Settings']['Start_time_car']}</a>")

        self.textLog.append(f"<a> Driving start/finish gap: {self.config['Settings']['timegap_car']} s</a>")
        if self.protocol_type == 1:  # MAP mode
            self.textLog.append("<a style='font-weight:bold;'>[Aggregation]</a>")
            self.textLog.append(f"<a> Number of bins: {self.config['Settings']['timeinterval_car']}</a>")

            if self.mode == 1:
                count_features = self.count_layer_destinations
            else:
                count_features = self.count_layer_origins
            self.textLog.append(f'<a> Count: {count_features}</a>')

            if self.config['Settings']['field_ch_car'] != "":
                print_fields = self.config['Settings']['field_ch_car']
            else:
                print_fields = "NONE"
            self.textLog.append(f'<a> Aggregated fields: {print_fields}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Visualization]</a>")
        self.textLog.append(f'<a> Layer for visualization: {self.layer_visualization_path}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        self.prepare()
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'car_accessibility.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://ishusterman.github.io/tutorial/car_accessibility.html"
        webbrowser.open(url)

    def showAllLayersInCombo_Point_and_Polygon(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        point_layers = [layer for layer in layers
                        if isinstance(layer, QgsVectorLayer) and
                        (layer.geometryType() == QgsWkbTypes.PointGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry)]
        cmb.clear()
        for layer in point_layers:
            cmb.addItem(layer.name(), [])

    def showAllLayersInCombo_Polygon(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        polygon_layers = [layer for layer in layers
                          if isinstance(layer, QgsVectorLayer) and
                          layer.geometryType() == QgsWkbTypes.PolygonGeometry and
                          layer.featureCount() > 1]
        cmb.clear()
        for layer in polygon_layers:
            cmb.addItem(layer.name(), [])

    def showAllLayersInCombo_Line(self, cmb):
        layers = QgsProject.instance().mapLayers().values()
        line_layers = [layer for layer in layers
                       if isinstance(layer, QgsVectorLayer) and
                       layer.geometryType() == QgsWkbTypes.LineGeometry and
                       not layer.name().startswith("Temp")]
        cmb.clear()
        for layer in line_layers:
            cmb.addItem(layer.name(), [])

    def showAllLayersInCombo(self, cmb):
        names = [layer.name()
                 for layer in QgsProject.instance().mapLayers().values()]

        cmb.clear()
        for name in names:
            cmb.addItem(name, [])

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(folder_path)
        else:
            obj.setText(obj.text())

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToPKL_car' not in self.config['Settings']:
            self.config['Settings']['PathToPKL_car'] = ''

        if 'Layer_field_car' not in self.config['Settings']:
            self.config['Settings']['Layer_field_car'] = '0'

        if 'LayerDest_field_car' not in self.config['Settings']:
            self.config['Settings']['LayerDest_field_car'] = '0'

        if 'VisLayer_field_car' not in self.config['Settings']:
            self.config['Settings']['VisLayer_field_car'] = '0'

        if 'Walk_to_car_car' not in self.config['Settings']:
            self.config['Settings']['Walk_to_car_car'] = '0'

        if 'Walk_to_destination_car' not in self.config['Settings']:
            self.config['Settings']['Walk_to_destination_car'] = '0'

        if 'Walking_speed_car' not in self.config['Settings']:
            self.config['Settings']['Walking_speed_car'] = '3.6'

        if 'Start_time_car' not in self.config['Settings']:
            self.config['Settings']['Start_time_car'] = '08:00:00'

        if 'TimeGap_car' not in self.config['Settings']:
            self.config['Settings']['TimeGap_car'] = '0'

    # update config file
    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        selected_text = ', '.join(
            self.cmbFields_ch.itemText(i)
            for i in range(self.cmbFields_ch.count())
            if self.cmbFields_ch.itemData(i, role=Qt.CheckStateRole) == Qt.Checked
        )
        self.config['Settings']['Field_ch_car'] = selected_text

        self.config['Settings']['PathToProtocols_car'] = self.txtPathToProtocols.text()
        self.config['Settings']['PathToPKL_car'] = self.txtPathToPKL.text()
        self.path_to_pkl = self.txtPathToPKL.text()
        self.config['Settings']['Layer_car'] = self.cmbLayers.currentText()
        self.config['Settings']['Layer_field_car'] = self.cmbLayers_fields.currentText()

        self.layer_field = self.config['Settings']['Layer_field_car']

        self.config['Settings']['LayerDest_car'] = self.cmbLayersDest.currentText()
        self.config['Settings']['LayerDest_field_car'] = self.cmbLayersDest_fields.currentText()

        if hasattr(self, 'cbSelectedOnly1'):
            self.config['Settings']['SelectedOnly1_car'] = str(
                self.cbSelectedOnly1.isChecked())
        self.config['Settings']['LayerDest_car'] = self.cmbLayersDest.currentText()
        if hasattr(self, 'cbSelectedOnly2'):
            self.config['Settings']['SelectedOnly2_car'] = str(
                self.cbSelectedOnly2.isChecked())

        self.config['Settings']['MaxTimeTravel_car'] = self.txtMaxTimeTravel.text()
        self.config['Settings']['TimeInterval_car'] = self.txtTimeInterval.text()

        self.config['Settings']['LayerVis_car'] = self.cmbVisLayers.currentText()
        self.config['Settings']['VisLayer_field_car'] = self.cmbVisLayers_fields.currentText()

        self.config['Settings']['Walk_to_car_car'] = self.txtWalkToCAR.text()
        self.config['Settings']['Walk_to_destination_car'] = self.txtWalkToDestination.text()
        self.config['Settings']['Walking_speed_car'] = self.txtWalkingSpeed.text()
        self.config['Settings']['Start_time_car'] = self.dtStartTime.dateTime(
        ).toString("HH:mm:ss")

        self.config['Settings']['TimeGap_car'] = self.txtTimeGap.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

        self.alias = self.txtAlias.text() if self.txtAlias.text() != "" else self.default_alias

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer_car'])[0]
        self.count_layer_origins = layer.featureCount()
        self.layer_origins_path = layer.dataProvider().dataSourceUri().split("|")[
            0]

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest_car'])[0]
        self.layer_destinations_path = layer.dataProvider().dataSourceUri().split("|")[
            0]
        self.count_layer_destinations = layer.featureCount()

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerVis_car'])[0]
        self.layer_visualization_path = layer.dataProvider().dataSourceUri().split("|")[
            0]

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToPKL.setText(self.config['Settings']['PathToPKL_car'])
        self.txtPathToProtocols.setText(
            self.config['Settings']['PathToProtocols_car'])
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_car'])

        try:
            SelectedOnly1 = self.config['Settings']['SelectedOnly1_car'].lower(
            ) == "true"
        except:
            SelectedOnly1 = False
        self.cbSelectedOnly1.setChecked(SelectedOnly1)

        self.cmbLayersDest.setCurrentText(
            self.config['Settings']['LayerDest_car'])

        try:
            self.SelectedOnly2 = self.config['Settings']['SelectedOnly2_car'].lower(
            ) == "true"
        except:
            self.SelectedOnly2 = False
        self.cbSelectedOnly2.setChecked(self.SelectedOnly2)

        self.txtMaxTimeTravel.setText(
            self.config['Settings']['MaxTimeTravel_car'])
        self.txtTimeInterval.setText(
            self.config['Settings']['TimeInterval_car'])

        layer = self.config.get('Settings', 'LayerVis_car', fallback=None)
        if isinstance(layer, str) and layer.strip():
            self.cmbVisLayers.setCurrentText(layer)

        self.cmbLayers_fields.setCurrentText(
            self.config['Settings']['Layer_field_car'])
        self.cmbLayersDest_fields.setCurrentText(
            self.config['Settings']['LayerDest_field_car'])
        self.cmbVisLayers_fields.setCurrentText(
            self.config['Settings']['VisLayer_field_car'])
        self.txtTimeGap.setText(self.config['Settings']['TimeGap_car'])

        self.txtAlias.setText(self.default_alias)

        if 'Field_ch_car' not in self.config['Settings']:
            self.config['Settings']['Field_ch_car'] = ''

        for i in range(self.cmbFields_ch.count()):
            item_text = self.cmbFields_ch.itemText(i)
            if item_text in self.config['Settings']['Field_ch_car']:
                self.cmbFields_ch.setItemData(
                    i, Qt.Checked, role=Qt.CheckStateRole)
            else:
                self.cmbFields_ch.setItemData(
                    i, Qt.Unchecked, role=Qt.CheckStateRole)

        self.txtWalkToCAR.setText(self.config['Settings']['Walk_to_car_car'])
        self.txtWalkToDestination.setText(
            self.config['Settings']['Walk_to_destination_car'])
        self.txtWalkingSpeed.setText(
            self.config['Settings']['Walking_speed_car'])

        datetime = QDateTime.fromString(
            self.config['Settings']['Start_time_car'], "HH:mm:ss")
        self.dtStartTime.setDateTime(datetime)

    def check_folder_and_file(self):

        if not os.path.exists(self.txtPathToPKL.text()):
            self.setMessage(f"Folder '{self.txtPathToPKL.text()}' does not exist")
            return False

        required_files = ['dict_building_vertex.pkl',
                          'dict_vertex_buildings.pkl',
                          'graph.pkl',
                          'graph_rev.pkl',
                          'cdi_index.csv'
                          ]
        missing_files = [file for file in required_files if not os.path.isfile(
            os.path.join(self.txtPathToPKL.text(), file))]

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(f"Files are missing in  '{self.txtPathToPKL.text()}' folder: {missing_files_message}")
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
            self.setMessage(f"Access to the folder '{self.txtPathToProtocols.text()}' is denied")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def get_feature_from_layer(self):

        layer = self.config['Settings']['Layer_car']

        layer = QgsProject.instance().mapLayersByName(layer)[0]

        ids = []
        count = 0

        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'Layer {layer} is empty')

            return 0

        if self.cbSelectedOnly1.isChecked():
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

        feature_id_field = self.layer_field

        features = layer.getFeatures()
        if self.cbSelectedOnly1.isChecked():
            features = layer.selectedFeatures()

        for feature in features:
            count += 1
            id = feature[feature_id_field]
            if count % 50000 == 0:
                QApplication.processEvents()
                self.setMessage(f'Reading list of origins...')

            ids.append(int(id))

        return ids

    def call_car_accessibility(self):

        self.layer_origins_name = self.config['Settings']['Layer_Car']
        layer_origins = QgsProject.instance().mapLayersByName(
            self.layer_origins_name)[0]

        layer_dest = self.config['Settings']['LayerDest_Car']
        layer_dest = QgsProject.instance().mapLayersByName(layer_dest)[0]

        self.pathtopkl = self.config['Settings']['pathtopkl_car']
        self.selected_only1 = self.config['Settings']['SelectedOnly1_car'] == "True"
        self.selected_only2 = self.config['Settings']['SelectedOnly2_car'] == "True"

        self.layer_origins = layer_origins
        self.layer_dest = layer_dest

        self.time_gap = int(self.config['Settings']['TimeGap_car'])

        max_time_minutes = int(self.config['Settings']['MaxTimeTravel_car'])
        time_step_minutes = int(self.config['Settings']['TimeInterval_car'])

        layer_vis = self.config['Settings']['layervis_car']
        layerdest_field = self.config['Settings']['LayerDest_field_car']
        layer_vis_field = self.config['Settings']['VisLayer_field_car']

        if 'Field_ch_car' in self.config['Settings']:
            list_fields_aggregate = self.config['Settings']['Field_ch_car']
        else:
            list_fields_aggregate = ""

        self.walk_on_start_m = int(self.config['Settings']['Walk_to_car_car'])
        self.walk_on_finish_m = int(
            self.config['Settings']['Walk_to_destination_car'])
        walk_speed_km_h = float(self.config['Settings']['Walking_speed_car'])
        self.walk_speed_m_s = walk_speed_km_h/3.6
        self.walk_time_start = round(self.walk_on_start_m/self.walk_speed_m_s)
        self.walk_time_finish = round(
            self.walk_on_finish_m/self.walk_speed_m_s)
        start_time = QDateTime.fromString(
            self.config['Settings']['Start_time_car'], "HH:mm:ss")
        self.hour = start_time.time().hour()

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

        car = car_accessibility(self,
                                layer_dest,
                                self.SelectedOnly2,
                                layerdest_field,
                                max_time_minutes,
                                time_step_minutes,
                                layer_vis,
                                layer_vis_field,
                                list_fields_aggregate,
                                )
        car.run(begin_computation_time)
      

    def prepare(self):
        self.break_on = False

        QApplication.processEvents()

        sources = []

        self.points = self.get_feature_from_layer()

        if self.points == 0:
            # self.setMessage (f"No features in the layer '{self.cmbLayers.currentText()}'")
            self.run_button.setEnabled(True)
            return 0

        run = True
        if len(self.points) > 10:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f"Layer contains {len(self.points)+1} feature. Maximum 10 feature are recommended. Are you sure?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.Yes:
                run = True
            else:
                run = False

        if run:
            if not os.path.exists(self.folder_name):
                os.makedirs(self.folder_name)
            else:
                self.setMessage(f"Folder '{self.folder_name}' already exists")
                self.run_button.setEnabled(True)
                return 0

            self.call_car_accessibility()

        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

    # If the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
