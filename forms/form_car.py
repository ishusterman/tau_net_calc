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

from PyQt5.QtGui import (QRegExpValidator, 
                         QDesktopServices, 
                         QGuiApplication)
from PyQt5 import uic


from car import car_accessibility
from pkl_car import pkl_car
from common import (get_qgis_info, 
                    is_valid_folder_name, 
                    get_prefix_alias, 
                    check_file_parameters_accessibility,
                    showAllLayersInCombo_Point_and_Polygon,
                    showAllLayersInCombo_Polygon,
                    get_initial_directory,
                    time_to_seconds,
                    seconds_to_time,
                    get_name_columns)

from AnalyzerFromTo_incremental import roundtrip_analyzer

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'car.ui')
)

class CarAccessibility(QDialog, FORM_CLASS):
    def __init__(self,
                 mode,
                 protocol_type,
                 title,
                 roundtrip = False
                 ):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.splitter.setSizes(
            [int(self.width() * 0.75), int(self.width() * 0.25)])

        fix_size = 15 * self.txtTimeInterval.fontMetrics().width('x')

        self.txtMaxTimeTravel.setFixedWidth(fix_size)
        self.txtTimeInterval.setFixedWidth(fix_size)

        self.txtWalkToCAR.setFixedWidth(fix_size)
        self.txtWalkToDestination.setFixedWidth(fix_size)
        self.txtWalkingSpeed.setFixedWidth(fix_size)
        self.dtStartTime.setFixedWidth(fix_size)
        self.cmbFields_ch.setFixedWidth(fix_size)
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()
        
        self.break_on = False

        self.mode = mode
        self.protocol_type = protocol_type
        self.title = title
        self.roundtrip = roundtrip

        self.progressBar.setValue(0)

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        self.toolButtonPKL.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToPKL))

        showAllLayersInCombo_Point_and_Polygon(self.cmbLayers)
        showAllLayersInCombo_Point_and_Polygon(self.cmbLayersDest)

        self.cmbLayers.installEventFilter(self)
        self.cmbLayersDest.installEventFilter(self)

        showAllLayersInCombo_Polygon(self.cmbVisLayers)
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
        
        self.default_alias = get_prefix_alias(False, 
                                self.protocol_type, 
                                self.mode, 
                                full_prefix=False)

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
        
        self.show_info()


        if not (self.roundtrip):
            
            widgets_to_hide = [
                self.dtRoundtripStartTime1, self.dtRoundtripStartTime2,
                self.dtRoundtripStartTime3, self.dtRoundtripStartTime4,
                self.txtRountrip_timedelta1, self.txtRountrip_timedelta2,
                self.lblRoundtrip1, self.lblRoundtrip2, self.lblRoundtrip3,
                self.lblRoundtrip4, self.lblRoundtrip5, self.lblRoundtrip6,
                self.lblRoundtrip7, self.lblRoundtrip8, self.lblRoundtrip9,
                self.lblRoundtrip10
            ]
         
            for widget in widgets_to_hide:
                widget.setVisible(False)
                        
        else:
            # remove item time start
            self.label_11.setVisible(False)
            self.dtStartTime.setVisible(False)
            parent_layout = self.horizontalLayout_12.parent()
            parent_layout.removeItem(self.horizontalLayout_12)
        
        regex = QRegExp(r"\d*")
        int_validator = QRegExpValidator(regex)
        self.txtTimeInterval.setValidator(int_validator)

        self.dtRoundtripStartTime1.installEventFilter(self)
        self.dtRoundtripStartTime2.installEventFilter(self)
        self.dtRoundtripStartTime3.installEventFilter(self)
        self.dtRoundtripStartTime4.installEventFilter(self)
        self.txtRountrip_timedelta1.setValidator(int_validator)
        self.txtRountrip_timedelta2.setValidator(int_validator)

        
        self.dtRoundtripStartTime1.setFixedWidth(fix_size)
        self.dtRoundtripStartTime2.setFixedWidth(fix_size)
        self.dtRoundtripStartTime3.setFixedWidth(fix_size)
        self.dtRoundtripStartTime4.setFixedWidth(fix_size)
        self.fix_size2 = 7* self.txtTimeInterval.fontMetrics().width('x')
        self.txtRountrip_timedelta1.setFixedWidth(self.fix_size2)
        self.txtRountrip_timedelta2.setFixedWidth(self.fix_size2)

        self.dict_building_vertex = {} 
        self.dict_vertex_buildings = {}
  

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

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong):
                # add numeric field
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == field_name_default:
                    field_name_default_exists = True
            else:
                if field_name.lower() == "osm_id":
                    obj_layer_fields.addItem(field_name)
                    field_name_default_exists = True
            """
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
            """

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
        
        self.folder_name = f'{self.txtPathToProtocols.text()}//{self.txtAlias.text()}'

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
        self.textLog.append(f"<a> Aerial distance: {self.config['Settings']['RunOnAir_car']}</a>")

        self.textLog.append(f"<a> Maximum total travel time: {self.config['Settings']['maxtimetravel_car']} min</a>")

        self.textLog.append(f"<a> Walking distance from origin to car parking: {self.config['Settings']['Walk_to_car_car']} m</a>")
        self.textLog.append(f"<a> Walking distance from parking to destination: {self.config['Settings']['Walk_to_destination_car']} m</a>")
        self.textLog.append(f"<a> Walking speed: {self.config['Settings']['Walking_speed_car']} km/h</a>")

        if not (self.roundtrip):
            if self.mode == 1:
                self.textLog.append(f"<a> Start at (hh:mm:ss): {self.config['Settings']['Start_time_car']}</a>")
            else:
                self.textLog.append(f"<a> Arrive at (hh:mm:ss): {self.config['Settings']['Start_time_car']}</a>")
        
        if self.protocol_type == 1:  # MAP mode
            self.textLog.append("<a style='font-weight:bold;'>[Aggregation]</a>")
            self.textLog.append(f"<a> Number of bins: {self.config['Settings']['timeinterval_car']}</a>")

            if self.mode == 2:
                count_features = self.count_layer_destinations
            else:
                count_features = self.count_layer_origins
            self.textLog.append(f'<a> Count: {count_features}</a>')

            if self.config['Settings']['field_ch_car'] != "":
                print_fields = self.config['Settings']['field_ch_car']
            else:
                print_fields = "NONE"
            self.textLog.append(f'<a> Additional buildings characteristics for accessibility assessment: {print_fields}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Visualization]</a>")
        self.textLog.append(f'<a> Layer for visualization: {self.layer_visualization_path}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        self.prepare()
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/car_accessibility.html"
        
        if self.mode == 1 and self.protocol_type == 2:
            section = "from-service-locations-fixed-time-departure"
        
        if self.mode == 2 and self.protocol_type == 2:
            section = "to-service-locations-fixed-time-arrival"

        if self.mode == 1 and self.protocol_type == 1:
            section = "car-accessibility-region-maps"

        if self.mode == 2 and self.protocol_type == 1:
            section = "car-accessibility-to-every-location-in-the-region"

        url = f'{url}#{section}'

        webbrowser.open(url)

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
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
        PathToProtocols_car = os.path.join(project_directory, f'{project_name}_output')
        PathToProtocols_car = os.path.normpath(PathToProtocols_car)

        file_path = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToPKL_car' not in self.config['Settings'] or self.config['Settings']['PathToPKL_car'] == "С:/":
            self.config['Settings']['PathToPKL_car'] = self.config['Settings']['PathToProtocols_car_pkl']

        self.config['Settings']['PathToPKL_car'] = get_initial_directory(self.config['Settings']['PathToPKL_car'])

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

        if 'RunOnAir_car' not in self.config['Settings']:
            self.config['Settings']['RunOnAir_car'] = 'False'
        
        if 'PathToProtocols_car' not in self.config['Settings'] or self.config['Settings']['PathToProtocols_car'] == "C:/":
            self.config['Settings']['PathToProtocols_car'] = PathToProtocols_car
        self.config['Settings']['PathToProtocols_car'] = os.path.normpath(self.config['Settings']['PathToProtocols_car'])


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

        self.config['Settings']['SelectedOnly1_car'] = str(self.cbSelectedOnly1.isChecked())
        self.config['Settings']['LayerDest_car'] = self.cmbLayersDest.currentText()
        self.config['Settings']['SelectedOnly2_car'] = str(self.cbSelectedOnly2.isChecked())

        self.config['Settings']['MaxTimeTravel_car'] = self.txtMaxTimeTravel.text()
        self.config['Settings']['TimeInterval_car'] = self.txtTimeInterval.text()

        self.config['Settings']['LayerVis_car'] = self.cmbVisLayers.currentText()
        self.config['Settings']['VisLayer_field_car'] = self.cmbVisLayers_fields.currentText()

        self.config['Settings']['Walk_to_car_car'] = self.txtWalkToCAR.text()
        self.config['Settings']['Walk_to_destination_car'] = self.txtWalkToDestination.text()
        self.config['Settings']['Walking_speed_car'] = self.txtWalkingSpeed.text()
        self.config['Settings']['Start_time_car'] = self.dtStartTime.dateTime().toString("HH:mm:ss")

        self.config['Settings']['RunOnAir_car'] = str(self.cbRunOnAir.isChecked())


        self.config['Settings']['to_time_start'] = self.dtRoundtripStartTime1.dateTime().toString("HH:mm:ss")
        self.config['Settings']['to_time_end'] = self.dtRoundtripStartTime2.dateTime().toString("HH:mm:ss")
        self.config['Settings']['from_time_start'] = self.dtRoundtripStartTime3.dateTime().toString("HH:mm:ss")
        self.config['Settings']['from_time_end'] = self.dtRoundtripStartTime4.dateTime().toString("HH:mm:ss")
        self.config['Settings']['time_delta_to'] = self.txtRountrip_timedelta1.text()
        self.config['Settings']['time_delta_from'] = self.txtRountrip_timedelta2.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)



        self.alias = self.txtAlias.text() if self.txtAlias.text() != "" else self.default_alias

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer_car'])[0]
        self.layer_origins_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])
        if self.mode == 2:
            layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest_car'])[0]
             
        self.count_layer_origins = layer.featureCount()
        if self.cbSelectedOnly1.isChecked():
            self.count_layer_origins = layer.selectedFeatureCount()
        
        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerDest_car'])[0]
        self.layer_destinations_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])
        if self.mode == 2:
            layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['Layer_car'])[0]
        self.count_layer_destinations = layer.featureCount()
        if self.cbSelectedOnly2.isChecked():
            self.count_layer_destinations = layer.selectedFeatureCount()

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['LayerVis_car'])[0]
        self.layer_visualization_path = os.path.normpath(layer.dataProvider().dataSourceUri().split("|")[0])
        
        

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToPKL.setText(os.path.normpath(self.config['Settings']['PathToPKL_car']))
        self.txtPathToProtocols.setText(os.path.normpath(
            self.config['Settings']['PathToProtocols_car']))
        self.cmbLayers.setCurrentText(self.config['Settings']['Layer_car'])

        selected_only1 = self.config['Settings']['SelectedOnly1_car'].lower() == "true"
        self.cbSelectedOnly1.setChecked(selected_only1)

        self.cmbLayersDest.setCurrentText(
            self.config['Settings']['LayerDest_car'])
       
        selected_only2 = self.config['Settings']['SelectedOnly2_car'].lower() == "true"
        self.cbSelectedOnly2.setChecked(selected_only2)

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

        RunOnAir = self.config['Settings']['RunOnAir_car'].lower() == "true"
        self.cbRunOnAir.setChecked(RunOnAir)


        self.txtRountrip_timedelta1.setText(self.config['Settings']['time_delta_to'])
        self.txtRountrip_timedelta2.setText(self.config['Settings']['time_delta_from'])

        datetime = QDateTime.fromString(
            self.config['Settings']['to_time_start'], "HH:mm:ss")
        self.dtRoundtripStartTime1.setDateTime(datetime)
        datetime = QDateTime.fromString(
            self.config['Settings']['to_time_end'], "HH:mm:ss")
        self.dtRoundtripStartTime2.setDateTime(datetime)
        datetime = QDateTime.fromString(
            self.config['Settings']['from_time_start'], "HH:mm:ss")
        self.dtRoundtripStartTime3.setDateTime(datetime)
        datetime = QDateTime.fromString(
            self.config['Settings']['from_time_end'], "HH:mm:ss")
        self.dtRoundtripStartTime4.setDateTime(datetime)

    def check_folder_and_file(self):

        os.makedirs(self.txtPathToProtocols.text(), exist_ok=True)

        #if not os.path.exists(self.txtPathToPKL.text()):
        #    self.setMessage(f"Folder '{self.txtPathToPKL.text()}' does not exist")
        #    return False

        path_to_pkl = self.txtPathToPKL.text().rstrip('\\/') # Убираем слеши в конце, если они есть
        prefix = os.path.basename(path_to_pkl)

        required_files = ['dict_building_vertex.pkl',
                          'dict_vertex_buildings.pkl',
                          'graph.pkl',
                          'graph_rev.pkl',
                          'cdi_index.csv'
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
        isChecked = self.cbSelectedOnly1.isChecked()
        if self.mode == 2:
            layer = self.config['Settings']['LayerDest_car']
            isChecked = self.cbSelectedOnly2.isChecked()

        layer = QgsProject.instance().mapLayersByName(layer)[0]

        ids = []
        count = 0

        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'Layer {layer} is empty')

            return 0

        if isChecked:
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
        if isChecked:
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
        if self.mode == 2:
            self.layer_origins_name = self.config['Settings']['LayerDest_Car']
        layer_origins = QgsProject.instance().mapLayersByName(
            self.layer_origins_name)[0]

        layer_dest = self.config['Settings']['LayerDest_Car']
        if self.mode == 2:
            layer_dest = self.config['Settings']['Layer_Car']
        layer_dest = QgsProject.instance().mapLayersByName(layer_dest)[0]

        self.pathtopkl = self.config['Settings']['pathtopkl_car']

        self.selected_only1 = self.config['Settings']['SelectedOnly1_car'] == "True"
        self.selected_only2 = self.config['Settings']['SelectedOnly2_car'] == "True"
        if self.mode == 2:
            self.selected_only1 = self.config['Settings']['SelectedOnly2_car'] == "True"
            self.selected_only2 = self.config['Settings']['SelectedOnly1_car'] == "True"

        self.layer_origin = layer_origins
        self.layer_dest = layer_dest

        max_time_minutes = int(self.config['Settings']['MaxTimeTravel_car'])
        time_step_minutes = int(self.config['Settings']['TimeInterval_car'])

        layer_vis = self.config['Settings']['layervis_car']

        layerdest_field = self.config['Settings']['LayerDest_field_car']
        layerorig_field = self.config['Settings']['Layer_field_car']
        if self.mode == 2:
            layerdest_field = self.config['Settings']['Layer_field_car']
            layerorig_field = self.config['Settings']['LayerDest_field_car']

        self.layerorig_field = layerorig_field    

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

        self.RunOnAir = self.config['Settings']['RunOnAir_car'].lower() == "true"

        
        

        cols_dict = get_name_columns()
        cols = cols_dict[(self.mode, self.protocol_type)]
        self.col_star = cols["star"]
        self.col_hash = cols["hash"]   

        car = car_accessibility(self,
                                layer_dest,
                                self.selected_only2,
                                layerdest_field,
                                max_time_minutes,
                                time_step_minutes,
                                layer_vis,
                                layer_vis_field,
                                list_fields_aggregate,
                                )
        
        self.setMessage("Loading pkl...")
        QApplication.processEvents()

        if not (self.roundtrip):
            graph = self.read_pkl(self.mode)
            car.run(begin_computation_time, 
                    self.hour, 
                    graph,
                    write_info = True,
                    )

        if self.roundtrip:

            graph = self.read_pkl(1)
            graph_rev = self.read_pkl(2)


            
            time_delta_to_min = int(self.config['Settings']['time_delta_to']) 
            time_delta_from_min = int(self.config['Settings']['time_delta_from'])
            time_delta_to  = time_delta_to_min * 60
            time_delta_from  = time_delta_to_min * 60

            from_time_start = time_to_seconds(self.config['Settings']['from_time_start'])
            from_time_end = time_to_seconds(self.config['Settings']['from_time_end'])
            to_time_start = time_to_seconds(self.config['Settings']['to_time_start'])
            to_time_end = time_to_seconds(self.config['Settings']['to_time_end'])

            str_to = f'<a>Home -> Facilities trip start: between {seconds_to_time(to_time_start)} and {seconds_to_time(to_time_end)} test every {time_delta_to_min} minutes</a>'
            self.textLog.append(str_to)
            str_from = f'<a>Facilities -> Home trip start: between {seconds_to_time(from_time_start)} and {seconds_to_time(from_time_end)} test every {time_delta_from_min} minutes</a>'
            self.textLog.append(str_from)

            self.textLog.append(f"<a style='font-weight:bold;'> Calculating roundtrip accessibility</a>")

            self.folder_name_copy = self.folder_name
            self.folder_name_from = os.path.join(self.folder_name_copy, "from")
            os.makedirs(self.folder_name_from, exist_ok=True)

            analyzer = roundtrip_analyzer(
                                        report_path = os.path.dirname(self.folder_name_from), 
                                        duration_max=3600, 
                                        alias = self.alias,
                                        field_star = cols["star"],
                                        field_hash = cols["hash"]
                                        )
      
                
            ###########################
            #  First From + First TO
            # #########################
            # #########################
            # First From
            # #########################
            
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating first from accessibility</a>")
            D_TIME_str = seconds_to_time(from_time_start)
            self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
            postfix = 1
            self.folder_name = os.path.join(self.folder_name_from, str(postfix)) 
            os.makedirs(self.folder_name, exist_ok=True)
            
            hour = from_time_start // 3600
            short_result = car.run(begin_computation_time, 
                                   hour,
                                   graph, 
                                   write_info = False)

            if not(self.break_on):
                first_from = analyzer.get_data_for_analyzer_from_to(short_result)

            
            # #########################
            # First to
            # #########################
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating first to accessibility</a>")
            self.mode = 2
            self.folder_name_to = os.path.join(self.folder_name_copy, "to")
            os.makedirs(self.folder_name_to, exist_ok=True)
            D_TIME_str = seconds_to_time(to_time_start)
            self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
            postfix = 1
            self.folder_name = os.path.join(self.folder_name_to, str(postfix)) 
            os.makedirs(self.folder_name, exist_ok=True)
            hour = to_time_start // 3600 
            short_result = car.run(begin_computation_time, 
                                   hour,
                                   graph_rev,
                                   write_info = False)

            
            if not(self.break_on):
                first_to = analyzer.get_data_for_analyzer_from_to (short_result)
                analyzer.init_from_data(first_to, first_from)
            
            ###########################
            #  From
            # #########################
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating remained from accessibility</a>")
            self.mode = 1
            i = 1
            while True:
                
                D_TIME = from_time_start + i * time_delta_from 
                if D_TIME > from_time_end + time_delta_from / 2: 
                    break

                D_TIME_str = seconds_to_time(D_TIME)
                self.textLog.append(f"<a style='font-weight:bold;'> Start at (hh:mm:ss): {D_TIME_str}</a>")
                 
                postfix = i + 1
                self.folder_name = os.path.join(self.folder_name_from, str(postfix)) 
                os.makedirs(self.folder_name, exist_ok=True)
                hour = D_TIME // 3600 
                short_result = car.run(begin_computation_time, 
                                   hour, 
                                   graph,
                                   write_info = False)

            
                if not(self.break_on):
                    data_from = analyzer.get_data_for_analyzer_from_to (short_result)
                    analyzer.add_from_data(data_from)
            
         
                if self.break_on:
                    self.setMessage("Roundtrip accessibility computations are interrupted by user")
                    self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                    self.progressBar.setValue(0)
                    return 0
                i += 1
                
            ###########################
            #  TO
            # #########################
                
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating remained to accessibility</a>")
            self.mode = 2
            i = 1

            while True:
                D_TIME = to_time_start + i * time_delta_to 
                if D_TIME > to_time_end + time_delta_to / 2: 
                        break
                D_TIME_str = seconds_to_time(D_TIME)
                self.textLog.append(f"<a style='font-weight:bold;'> Arrive before (hh:mm:ss): {D_TIME_str}</a>")
                    
                postfix = i + 1
                self.folder_name = os.path.join(self.folder_name_to, str(postfix)) 
                os.makedirs(self.folder_name, exist_ok=True)
                hour = D_TIME // 3600                     
                short_result = car.run(begin_computation_time, 
                                   hour,
                                   graph_rev, 
                                   write_info = False)
                
                if not(self.break_on):
                    data_to = analyzer.get_data_for_analyzer_from_to (short_result)
                    analyzer.add_to_data(data_to)
                        
               
                i += 1
                if self.break_on:
                    self.setMessage("Roundtrip accessibility computations are interrupted by user")
                    self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                    self.progressBar.setValue(0)
                    return 0
                
                
            if not(self.break_on):
                    
                    analyzer.run_finalize_all()
                    self.textLog.append(f'<a href="file:///{os.path.dirname(self.folder_name_from)}" target="_blank" >Statistics in folder</a>')
                    after_computation_time = datetime.now()
                    after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
                    self.textLog.append(f'<a>Finished {after_computation_str}</a>')
                    duration_computation = after_computation_time - begin_computation_time
                    duration_without_microseconds = str(duration_computation).split('.')[0]
                    self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

                    self.setMessage(f'Finished')
                    self.progressBar.setValue(self.progressBar.maximum())
            

    def read_pkl(self, mode):
            pkl_car_reader = pkl_car()
            self.crs = self.layer_dest.crs()
            if not self.dict_building_vertex or not self.dict_vertex_buildings:
                self.dict_building_vertex, self.dict_vertex_buildings = pkl_car_reader.load_files( self.path_to_pkl)
            
            graph = pkl_car_reader.load_graph(
                mode = mode,
                pathtopkl = self.path_to_pkl,
                crs = self.crs
            )

            

            return graph

    def prepare(self):
        self.break_on = False

        QApplication.processEvents()

        sources = []

        self.points = self.get_feature_from_layer()

        if self.points == 0:
            self.run_button.setEnabled(True)
            return 0

        run = True
        if len(self.points) > 10:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            take_min = round((len(self.points)*2)/60)
            msgBox.setText(
                f"Layer contains {len(self.points)} feature and it will take at least {take_min} minutes to finish the computations. Maximum 10 feature are recommended. Are you sure?")
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

        
        if self.protocol_type == 2:
            if self.mode == 1: 
                help_filename = "car_sa_from.txt"
        if self.mode == 2:
                help_filename = "car_sa_to.txt"
                    
        if self.protocol_type == 1:
            if self.mode == 1:
                help_filename = "car_reg_from.txt"
            if self.mode == 2:
                help_filename = "car_reg_to.txt"
            
        hlp_file = os.path.join(hlp_directory, help_filename)
        hlp_file = os.path.normpath(hlp_file)
        self.load_text_with_bold_first_line (hlp_file)       
