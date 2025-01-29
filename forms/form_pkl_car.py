import os
import csv
import webbrowser
import re
import urllib.parse
import configparser

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QFileDialog,
    )

from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QEvent,
                          QVariant
                          )

from PyQt5.QtGui import QRegExpValidator, QDesktopServices
from PyQt5 import uic

from pkl_car import pkl_car
from common import get_qgis_info, check_file_parameters_accessibility


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
#FORM_CLASS, _ = uic.loadUiType(os.path.join(
#    os.path.dirname(__file__), 'pkl_car.ui'))

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'pkl_car.ui')
)


class form_pkl_car(QDialog, FORM_CLASS):
    def __init__(self,
                 title,
                 ):
        super().__init__()
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        fix_size = 12 * self.txtSpeed.fontMetrics().width('x')

        self.txtSpeed.setFixedWidth(fix_size)

        self.splitter.setSizes([80, 100])

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()

        self.break_on = False

        self.title = title

        self.progressBar.setValue(0)
        self.showAllLayersInCombo_Line(self.cbRoads)
        self.toolButtonRoads.clicked.connect(lambda: self.open_file_dialog (type = "roads"))
        self.toolButtonBuildings.clicked.connect(lambda: self.open_file_dialog (type = "buildings"))

        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        

        self.showAllLayersInCombo_Point_and_Polygon(self.cmbLayers_buildings)

        self.cmbLayers_buildings.installEventFilter(self)

        self.cmbFieldsSpeed.installEventFilter(self)
        self.cmbLayers_buildings.installEventFilter(self)
        self.cmbFieldsDirection.installEventFilter(self)

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

        self.txtSpeed.setValidator(int_validator3)
        self.layer_road = self.get_layer_road()
        self.layer_buidings = self.get_layer_buildings()


        self.cbRoads.currentIndexChanged.connect(self.onLayerRoadChanged)

        self.fillComboBoxFields_Id(self.cmbLayers_buildings,
                                   self.cmbLayers_buildings_fields,
                                   "osm_id",
                                   only_digit=True)

        self.cmbLayers_buildings.currentIndexChanged.connect(
            lambda: self.fillComboBoxFields_Id
            (self.cmbLayers_buildings,
             self.cmbLayers_buildings_fields,
             "osm_id",
             only_digit=True))

        self.ParametrsShow()
        self.onLayerRoadChanged()
        
        self.textInfo.anchorClicked.connect(self.open_file)
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        if project_directory != '':
            self.read_road_speed_default()
            self.read_factor_speed_by_hour()
            self.show_info()

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
    
    def get_layer_buildings(self):
        selected_item = self.cmbLayers_buildings.currentText()
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
                    self.onLayerRoadChanged()
                else:
                    self.cmbLayers_buildings.addItem(file_path, file_path)
                    index = self.cmbLayers_buildings.findText(file_path)
                    self.cmbLayers_buildings.setCurrentIndex(index)


    def onLayerRoadChanged(self):
        # update the fields for speed
        item = None
        self.fillComboBoxFields_Id(item,
                                   self.cmbFieldsSpeed,
                                   "maxspeed",
                                   only_digit=True,
                                   mode_road=True)

        # update the fields for direction
        self.fillComboBoxFields_Id(item,
                                   self.cmbFieldsDirection,
                                   "oneway",
                                   only_digit=False,
                                   mode_road=True)

        # update the fields for type of road
        self.fillComboBoxFields_Id(item,
                                   self.cmbLayersRoad_type_road,
                                   "fclass",
                                   only_digit=False,
                                   mode_road=True)

    def fillComboBoxFields_Id(self, obj_layers, obj_layer_fields, field_name_default, only_digit=True, mode_road=False):
        obj_layer_fields.clear()

        if not (mode_road):
            self.layer_buidings = self.get_layer_buildings()
            layer = self.layer_buidings

        if mode_road:
            self.layer_road = self.get_layer_road()
            layer = self.layer_road

        if not layer:
            return

        fields = layer.fields()
        field_name_default_exists = False

        # regular expression to check for the presence of only digit
        digit_pattern = re.compile(r'^\d+$')

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                # add numeric fields
                obj_layer_fields.addItem(field_name)
                if field_name.lower() == field_name_default:
                    field_name_default_exists = True
            elif field_type == QVariant.String:
                # check the first value of the field for digits only if only_digit = True
                if only_digit:
                    first_value = None
                    for feature in layer.getFeatures():
                        first_value = feature[field_name]
                        break  # stop after the first value

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

    def open_file(self, url):
        file_path = url.toLocalFile()
        if os.path.isfile(file_path):
            os.startfile(file_path)
        self.read_road_speed_default()
        self.read_factor_speed_by_hour()
        self.show_info()

    def show_info(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        
        link = f'<a href="#" onclick="open_folder()"> plugin folder</a>'

        html = f"""
      The table of speed by the OSM type of the link, and the table of the Congestion Delay Index are in {link} and can be edited by user:
      <br>
      <a href="file:///{self.file_path_road_speed_default}" target="_blank">{self.file_path_road_speed_default}</a>
      <br>
      <a href="file:///{self.file_path_factor_speed_by_hour}" target="_blank">{self.file_path_factor_speed_by_hour}</a>
      """
        # create the first table
        table1 = "<table border='1' cellspacing='0' cellpadding='5'>"
        table1 += "<tr><th>link_type</th><th>speed km/h</th></tr>"
        i = 0
        for type_road, speed_default in self.type_road_speed_default.items():
            i += 1
            if i <= 10:
                table1 += f"<tr><td>{type_road}</td><td>{speed_default}</td></tr>"
            else:
                break
        table1 += f"<tr><td>...</td><td>...</td></tr>"
        table1 += "</table>"

        # create the second table
        table2 = "<table border='1' cellspacing='0' cellpadding='5'>"
        table2 += "<tr><th>hour</th><th>CDI</th></tr>"
        i = 0
        for hour, factor in self.factor_speed_by_hour.items():
            i += 1
            if i <= 10:
                table2 += f"<tr><td>{hour}</td><td>{factor}</td></tr>"
            else:
                break
        table2 += f"<tr><td>...</td><td>...</td></tr>"
        table2 += "</table>"

        # place the tables in one row using an HTML table
        html += f"""
      <table border='0' cellspacing='10' cellpadding='10'>
          <tr>
              <td valign='top'>{table1}</td>
              <td valign='top'>{table2}</td>
          </tr>
      </table>
      """
       
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(self.open_project_folder)

    def open_project_folder(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        current_dir = os.path.dirname((os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')
        if os.name == 'nt':  # for Windows
            os.startfile(config_path)
        elif os.name == 'posix':  # for Linux and macOS
            os.system(f'xdg-open "{config_path}"')

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def on_run_button_clicked(self):
        self.run_button.setEnabled(False)

        self.break_on = False

        self.layer_road = self.get_layer_road()
        self.layer_buildings = self.get_layer_buildings()

        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        
        if not (self.check_layer_buildings()):
            self.run_button.setEnabled(True)
            return 0
        
        self.folder_name = f'{self.txtPathToProtocols.text()}'

        self.saveParameters()
        self.readParameters()

        self.break_on = False
      
        

        if not (self.check_type_layer_road()):
            self.run_button.setEnabled(True)
            return 0

        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)

        self.save_var()

        self.close_button.setEnabled(False)
        self.textLog.clear()
        self.tabWidget.setCurrentIndex(1)
        self.textLog.append("<a style='font-weight:bold;'>[System]</a>")
        qgis_info = get_qgis_info()

        info_str = "<br>".join(
            [f"{key}: {value}" for key, value in qgis_info.items()])
        self.textLog.append(f'<a> {info_str}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        self.textLog.append(f"<a> Layer of roads: {self.config['Settings']['Roads_car_pkl']}</a>")

        self.textLog.append(f"<a>  link type: {self.config['Settings']['LayerRoad_type_road_car_pkl']}</a>")
        self.textLog.append(f"<a>  direction: {self.cmbFieldsDirection.currentText()}</a>")
        self.textLog.append(f"<a>  speed: {self.config['Settings']['FieldSpeed_car_pkl']}</a>")
        

        self.textLog.append(f"<a> Layer of buildings: {self.layer_origins_path}</a>")

        self.textLog.append(f"<a> Default speed: {self.config['Settings']['speed_car_pkl']} km/h</a>")

        self.textLog.append(f"<a> Folder to store car database: {self.config['Settings']['pathtoprotocols_car_pkl']}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")

        pkl_car_calc = pkl_car(self)
        pkl_car_calc.create_files()

        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file_path = os.path.join(module_path, 'building_pkl.html')
        #anchor = urllib.parse.quote('building-database-for-car-routing')
        #full_url = f'file:///{file_path}#{anchor}'
        #webbrowser.open(full_url)
        url = "https://ishusterman.github.io/tutorial/building_pkl.html"
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
                       not layer.name().startswith("Temp") and
                       'memory' not in layer.dataProvider().dataSourceUri()]
        cmb.clear()
        for layer in line_layers:
            cmb.addItem(layer.name(), [])

    def showAllLayersInCombo(self, cmb):
        names = [layer.name()
                 for layer in QgsProject.instance().mapLayers().values()]

        cmb.clear()
        for name in names:
            cmb.addItem(name, [])

    def showFoldersDialog(self, obj, mode_road=False):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(folder_path)
            if mode_road:
                self.onLayerRoadChanged()

        else:
            obj.setText(obj.text())

    def read_factor_speed_by_hour(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')

        self.file_path_factor_speed_by_hour = os.path.join(
            config_path, "cdi_index.csv")

        self.factor_speed_by_hour = {}

        with open(self.file_path_factor_speed_by_hour, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hour_item = row['hour']
                factor_item = row['cdi']
                self.factor_speed_by_hour[hour_item] = factor_item

    def read_road_speed_default(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')
        
        self.file_path_road_speed_default = os.path.join(
            config_path, "car_speed_by_link_type.csv")

        self.type_road_speed_default = {}

        with open(self.file_path_road_speed_default, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                type_road = row['link_type']
                speed_default = int(row['speed_km_h'])
                self.type_road_speed_default[type_road] = speed_default

    def readParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToProtocols_car_pkl' not in self.config['Settings']:
            self.config['Settings']['PathToProtocols_car_pkl'] = ''

        if 'Roads_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Roads_car_pkl'] = ''

        if 'FieldSpeed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldSpeed_car_pkl'] = '0'

        if 'FieldSpeed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldSpeed_car_pkl'] = '0'

        if 'FieldDirection_car_pkl' not in self.config['Settings']:
            self.config['Settings']['FieldDirection_car_pkl'] = '0'

        if 'LayerRoad_type_road_car_pkl' not in self.config['Settings']:
            self.config['Settings']['LayerRoad_type_road_car_pkl'] = '0'

        if 'Layer_buildings_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_buildings_car_pkl'] = '0'

        if 'Layer_buildings_field_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Layer_buildings_field_car_pkl'] = '0'

        if 'Speed_car_pkl' not in self.config['Settings']:
            self.config['Settings']['Speed_car_pkl'] = '0'

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToProtocols_car_pkl'] = self.txtPathToProtocols.text()

        self.config['Settings']['Roads_car_pkl'] = self.cbRoads.currentText()

        self.config['Settings']['FieldSpeed_car_pkl'] = str(
            self.cmbFieldsSpeed.currentText())
        self.config['Settings']['LayerRoad_type_road_car_pkl'] = self.cmbLayersRoad_type_road.currentText()

        self.config['Settings']['FieldDirection_car_pkl'] = str(
            self.cmbFieldsDirection.currentIndex())

        self.config['Settings']['Layer_buildings_car_pkl'] = self.cmbLayers_buildings.currentText()
        self.config['Settings']['Layer_buildings_field_car_pkl'] = self.cmbLayers_buildings_fields.currentText()

        self.config['Settings']['Speed_car_pkl'] = self.txtSpeed.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

        layer = self.layer_buildings
       
        self.count_layer_origins = layer.featureCount()
        self.layer_origins_path = layer.dataProvider().dataSourceUri().split("|")[
            0]

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToProtocols.setText(
            self.config['Settings']['PathToProtocols_car_pkl'])

        self.cmbFieldsSpeed.setCurrentText(
            self.config['Settings']['FieldSpeed_car_pkl'])
        self.cmbLayersRoad_type_road.setCurrentText(
            self.config['Settings']['LayerRoad_type_road_car_pkl'])
        self.cmbFieldsDirection.setCurrentText(
            self.config['Settings']['FieldDirection_car_pkl'])

        self.cmbLayers_buildings.setCurrentText(
            self.config['Settings']['Layer_buildings_car_pkl'])
        self.cmbLayers_buildings_fields.setCurrentText(
            self.config['Settings']['Layer_buildings_field_car_pkl'])

        self.txtSpeed.setText(self.config['Settings']['Speed_car_pkl'])

        if os.path.isfile(self.config['Settings']['Roads_car_pkl']):
            self.cbRoads.addItem(self.config['Settings']['Roads_car_pkl'])
        self.cbRoads.setCurrentText(self.config['Settings']['Roads_car_pkl'])

    def check_folder_and_file(self):

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

    def check_layer_buildings(self):

        layer = self.layer_buildings
        if layer == "":
            self.setMessage(f"Layer is empty")
            return 0
        
        try:
            features = layer.getFeatures()
        except:
            self.setMessage(f'Layer {layer} is empty')
            return 0
        
        geometryType = layer.geometryType()
        if (geometryType != QgsWkbTypes.PointGeometry and geometryType != QgsWkbTypes.PolygonGeometry):
            self.setMessage(f'Features of the layer {self.cmbLayers_buildings.currentText()} must be polylines or points')
            return 0

        return 1
    
    def check_type_layer_road(self):

        try:
            features = self.layer_road.getFeatures()
        except:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' is empty")
            return 0

        feature_count = self.layer_road.featureCount()
        if feature_count == 0:
            self.setMessage(f"Layer '{self.cbRoads.currentText()}' is empty")
            return 0

        features = self.layer_road.getFeatures()
        for feature in features:
            feature_geometry = feature.geometry()
            feature_geometry_type = feature_geometry.type()
            break

        if (feature_geometry_type != QgsWkbTypes.LineGeometry):
            self.setMessage(f"Features of the layer in '{self.cbRoads.currentText()}' must be polylines")
            return 0

        return 1

    def save_var(self):
        self.path_to_protocol = self.config['Settings']['pathtoprotocols_car_pkl']
        self.idx_field_direction = self.layer_road.fields(
        ).indexFromName(self.cmbFieldsDirection.currentText())
        self.idx_field_speed = self.layer_road.fields(
        ).indexFromName(self.cmbFieldsSpeed.currentText())
        self.speed_fieldname = self.cmbFieldsSpeed.currentText()

        self.layer_road_type_road = self.config['Settings']['LayerRoad_type_road_car_pkl']
        self.layer_buildings_field = self.config['Settings']['Layer_buildings_field_car_pkl']
        self.speed = float(self.config['Settings']
                           ['Speed_CAR_pkl'].replace(',', '.'))
        self.strategy_id = 1

    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)
