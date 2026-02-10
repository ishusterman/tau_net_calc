import os
import glob
import pandas as pd
import webbrowser
import re
import numpy as np
from datetime import datetime
import configparser

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox)

from qgis.core import (QgsProject,
                       QgsWkbTypes,
                       QgsVectorLayer
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          QVariant)
from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic

from visualization import visualization
from common import (getDateTime, 
                    get_qgis_info, 
                    is_valid_folder_name, 
                    check_file_parameters_accessibility,
                    showAllLayersInCombo_Polygon,
                    get_name_columns
                    )

#FORM_CLASS, _ = uic.loadUiType(os.path.join(
#    os.path.dirname(__file__), 'relative.ui'))

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'relative.ui')
)

class form_relative(QDialog, FORM_CLASS):
    def __init__(self, title, mode):
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
        self.mode = mode
        self.progressBar.setValue(0)
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)
        self.toolButton_Output.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToOutput))
        self.toolButton_PT.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToPT))
        self.toolButton_Car.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToCar))

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

        showAllLayersInCombo_Polygon(self.cbVisLayers)
        self.fillComboBoxFields_Id()
        self.cbVisLayers.currentIndexChanged.connect(
            self.fillComboBoxFields_Id)

        self.cbVisLayers.installEventFilter(self)
        self.cbVisLayers_fields.installEventFilter(self)

        self.cmbListFiles1.installEventFilter(self)
        self.cmbListFiles2.installEventFilter(self)

        self.default_aliase = f'{getDateTime()}'

        self.txtPathToPT.textChanged.connect(lambda:
                                             self.fill_combobox_with_csv_files
                                             (self.cmbListFiles1,
                                              self.txtPathToPT.text()))

        self.txtPathToCar.textChanged.connect(lambda:
                                              self.fill_combobox_with_csv_files
                                              (self.cmbListFiles2,
                                               self.txtPathToCar.text()))

        self.ParametrsShow()
        self.show_info()

    def fill_combobox_with_csv_files(self, obj, path):

        obj.clear()
        if os.path.exists(path):
            csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
            obj.addItems(csv_files)

    def fillComboBoxFields_Id(self):
        self.cbVisLayers_fields.clear()
        selected_layer_name = self.cbVisLayers.currentText()
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)

        if not layers:
            return
        layer = layers[0]

        fields = layer.fields()
        osm_id_exists = False

        # create a regular expression instance for integers
        digit_pattern = re.compile(r'^\d+$')

        # field type and value validation
        for field in fields:
            field_name = field.name()
            field_type = field.type()

            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong):
                # add numeric fields
                self.cbVisLayers_fields.addItem(field_name)
                if field_name == "osm_id":
                    osm_id_exists = True
            
            else:
                if field_name.lower() == "osm_id":
                    self.cbVisLayers_fields.addItem(field_name)
                    osm_id_exists = True
            """
            elif field_type == QVariant.String:
                # check the first value of the field for digits only
                first_value = None
                for feature in layer.getFeatures():
                    first_value = feature[field_name]
                    break  # stop after the first value

                if first_value is not None and digit_pattern.match(str(first_value)):
                    self.cbVisLayers_fields.addItem(field_name)
                    if field_name == "osm_id":
                        osm_id_exists = True
            """

        if osm_id_exists:
            index = self.cbVisLayers_fields.findText("osm_id")
            if index != -1:
                self.cbVisLayers_fields.setCurrentIndex(index)
 

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)

    def on_run_button_clicked(self):
        self.progressBar.setMaximum(6)
        self.progressBar.setValue(0)
        self.run_button.setEnabled(False)

        self.break_on = False

        if not (is_valid_folder_name(self.txtAliase.text())):
            self.setMessage(f"'{self.txtAliase.text()}' is not a valid  directory/file name")
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_output_folder()):
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_folder_and_file(self.txtPathToPT.text())):
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_folder_and_file(self.txtPathToCar.text())):
            self.run_button.setEnabled(True)
            return 0

        if self.cmbListFiles1.currentText() == "":
            self.setMessage('File1 is not provided')
            self.run_button.setEnabled(True)
            return 0

        if self.cmbListFiles2.currentText() == "":
            self.setMessage('File2 is not provided')
            self.run_button.setEnabled(True)
            return 0

        if self.cbVisLayers.currentText() == "":
            self.setMessage('Set the visualization layer')
            self.run_button.setEnabled(True)
            return 0

        if not (self.cb_ratio.isChecked()) \
                and not (self.cb_difference.isChecked())  \
                and not (self.cb_relative_difference.isChecked()):

            self.setMessage('Choose calculation mode')
            self.run_button.setEnabled(True)
            return 0
        
        cols_dict = get_name_columns()
        
        mode_first, self.MAP_first, max_time_travel_PT, time_interval_PT, run_aggregate_PT, field_to_aggregate_PT = self.check_log(
            self.txtPathToPT.text())
        
        self.from_to_first = 1 if mode_first else 2
        protocol = 1 if self.MAP_first else 2
        cols = cols_dict[(self.from_to_first, protocol)]
        self.first_col_star = cols["star"]
        self.first_col_hash = cols["hash"]
        


        mode_second, self.MAP_second, max_time_travel_Car, time_interval_Car, run_aggregate_Car, field_to_aggregate_Car = self.check_log(
            self.txtPathToCar.text())
        
        self.from_to_second = 1 if mode_second else 2
        protocol = 1 if self.MAP_second else 2
        cols = cols_dict[(self.from_to_second, protocol)]
        self.second_col_star = cols["star"]
        self.second_col_hash = cols["hash"]

        if self.mode == 1:
            if self.MAP_first or self.MAP_second:
                self.run_button.setEnabled(True)
                self.setMessage(
                    "First csv type: {}. Second csv type: {}. Must be type: Service area.".format(
                        "Region" if self.MAP_first else "Service area",
                        "Region" if self.MAP_second else "Service area"
                    )
                )
                return 0

        if self.mode == 2:
            if not (self.MAP_first) or not (self.MAP_second):
                self.run_button.setEnabled(True)
                self.setMessage(
                    "First csv type: {}. Second csv type: {}. Must be type: Region.".format(
                        "Region" if self.MAP_first else "Service area",
                        "Region" if self.MAP_second else "Service area"
                    )
                )
                return 0

        self.folder_name = f'{self.txtPathToOutput.text()}//{self.txtAliase.text()}'

        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)
        else:
            self.setMessage(f"Folder '{self.folder_name}' already exists")
            self.run_button.setEnabled(True)
            return 0

        """
        if not(MAP_Car):
           #self.setMessage('Car protokol is not MAP')
           self.run_button.setEnabled(True)
           return 0
        
        
        if max_time_travel_PT != max_time_travel_Car:
           #self.setMessage(f'PT mode max time travel: {max_time_travel_PT} min. Car mode max time travel: {max_time_travel_Car} min. Must be the same.')
           self.run_button.setEnabled(True)
           return 0
                
        if time_interval_PT != time_interval_Car:
           #self.setMessage(f'PT mode time interval: {time_interval_PT} min. Car mode time interval: {time_interval_Car} min. Must be the same.')
           self.run_button.setEnabled(True)
           return 0
        
        if run_aggregate_PT != run_aggregate_Car:
           #self.setMessage(f'PT mode run aggregate: {run_aggregate_PT}. Car mode run aggregate: {run_aggregate_Car}. Must be the same.')
           self.run_button.setEnabled(True)
           return 0
        
        if field_to_aggregate_PT != field_to_aggregate_Car:
           #self.setMessage(f'PT mode field to aggregate: {field_to_aggregate_PT}. Car mode field to : {field_to_aggregate_Car}. Must be the same.')
           self.run_button.setEnabled(True)
           return 0
        """
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

        layer = QgsProject.instance().mapLayersByName(
            self.config['Settings']['VisLayer_relative'])[0]
        self.layer_vis_path = layer.dataProvider().dataSourceUri().split("|")[
            0]
        self.alias = self.txtAliase.text()

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        self.textLog.append(f'<a> Scenario name: {self.alias}</a>')
        self.textLog.append(f"<a>Results_1 folder: {self.config['Settings']['PathToPT_relative']}</a>")
        self.textLog.append(f"<a>Results_2 folder: {self.config['Settings']['PathToCAR_relative']}</a>")
        self.textLog.append(f"<a>Output folder: {self.config['Settings']['PathToOutput_relative']}</a>")
        self.textLog.append(f"<a>Visualization layer: {os.path.normpath(self.layer_vis_path)}</a>")
                
        self.textLog.append(f"<a>Calculate ratio: {self.config['Settings']['calc_ratio_relative']}</a>")
        self.textLog.append(f"<a>Calculate difference: {self.config['Settings']['calc_difference_relative']}</a>")
        self.textLog.append(f"<a>Calculate relative difference: {self.config['Settings']['calc_relative_difference_relative']}</a>")

        LayerVis = self.config['Settings']['VisLayer_relative']
        fieldname_layer = self.config['Settings']['VisLayers_fields_relative']

        if self.MAP_first:
            mode_visualization = 1
        else:
            mode_visualization = 2

        self.make_log_compare()
        vis = visualization(self,
                            LayerVis,
                            mode=mode_visualization,
                            fieldname_layer=fieldname_layer,
                            mode_compare=True,
                            from_to = 1
                            )

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
        list_file_name = []

        self.progressBar.setValue(1)
        QApplication.processEvents()
        if self.cb_ratio.isChecked():
            self.mode_calc = "ratio"
            self.prepare()
            aliase_res = f'ratio_{self.alias}'
            type_compare = "RatioRelative"
            vis.add_thematic_map(self.path_output, 
                                 aliase_res, 
                                 type_compare = type_compare)
            list_file_name.append(self.path_output)

        self.progressBar.setValue(2)
        QApplication.processEvents()
        if self.cb_difference.isChecked():
            self.mode_calc = "difference"
            self.prepare()
            aliase_res = f'diff_{self.alias}'
            if self.MAP_first:
                type_compare = "DifferenceRegion"
            else:
                type_compare = "DifferenceServiceAreas"
            vis.add_thematic_map(self.path_output, 
                                 aliase_res,
                                 type_compare = type_compare)
            list_file_name.append(self.path_output)

        self.progressBar.setValue(3)
        QApplication.processEvents()
        if self.cb_relative_difference.isChecked():
            self.mode_calc = "relative_difference"
            self.prepare()
            aliase_res = f'rel_diff_{self.alias}'

            type_compare = "RatioRelative"
            
            vis.add_thematic_map(self.path_output, 
                                 aliase_res, 
                                 type_compare = type_compare)
            list_file_name.append(self.path_output)

        self.progressBar.setValue(4)
        QApplication.processEvents()
        if self.MAP_first:
            field_name1 = self.first_col_star
            field_name2 = self.second_col_star
        else:
            field_name1 = self.first_col_hash
            field_name2 = self.second_col_hash

        vis2 = visualization(self,
                             LayerVis,
                             mode=mode_visualization,
                             fieldname_layer=fieldname_layer,
                             mode_compare=False,
                             from_to = self.from_to_first)
                            
        df1 = pd.read_csv(self.file1)
        df2 = pd.read_csv(self.file2)
        
        for df, col in [(df1, field_name1), (df2, field_name2)]:
            df.dropna(subset=[col], inplace=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # Оставляем строки из df1, которых нет в df2 по ключевому полю
        df1_only = df1[~df1[field_name1].isin(df2[field_name2])].copy()
        # Выбираем колонки: ключи + последняя (метрика)
        cols_to_save1 = [c for c in [field_name1, field_name2, df1.columns[-1]] if c in df1.columns]
        df1_only = df1_only[cols_to_save1]
        # Сохранение и карта для DF1
        path1 = os.path.join(self.folder_name, f"{self.txtAliase.text()}_{self.file_name1}_only.csv")
        df1_only.to_csv(path1, index=False, na_rep='NaN')
        vis2.add_thematic_map(path1, f"{self.alias}_{self.file_name1}_only", type_compare="CompareFirstOnly")
        list_file_name.append(path1)

        self.progressBar.setValue(5)
        QApplication.processEvents()

        vis3 = visualization(self,
                             LayerVis,
                             mode=mode_visualization,
                             fieldname_layer=fieldname_layer,
                             mode_compare=False,
                             from_to = self.from_to_second)
        
        # Оставляем строки из df2, которых нет в df1 по ключевому полю
        df2_only = df2[~df2[field_name2].isin(df1[field_name1])].copy()
        # Выбираем колонки
        cols_to_save2 = [c for c in [field_name1, field_name2, df2.columns[-1]] if c in df2.columns]
        df2_only = df2_only[cols_to_save2]
        # Сохранение и карта для DF2
        path2 = os.path.join(self.folder_name, f"{self.txtAliase.text()}_{self.file_name2}_only.csv")
        df2_only.to_csv(path2, index=False, na_rep='NaN')
        vis3.add_thematic_map(path2, f"{self.alias}_{self.file_name2}_only", type_compare="CompareSecondOnly")
        list_file_name.append(path2)

        QApplication.processEvents()
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')
        text = self.textLog.toHtml()
        filelog_name = f'{self.folder_name}//log_{self.alias}.html'
        with open(filelog_name, "w") as file:
            file.write(text)
        self.textLog.append(f'<a>Output:</a>')
        for file_name in list_file_name:
            self.textLog.append(f'<a>{os.path.normpath(file_name)}</a>')

        self.textLog.append(f'<a href="file:///{self.folder_name}" target="_blank" >Protocol in folder</a>')

        self.setMessage("Finished")
        self.progressBar.setValue(6)

        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'relative_ready-made.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/relative_ready-made.html"
        webbrowser.open(url)

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
        else:
            obj.setText(obj.text())

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToOutput_relative = os.path.join(project_directory, f'{project_name}_output')
        PathToOutput_relative = os.path.normpath(PathToOutput_relative)

        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToOutput_relative' not in self.config['Settings'] or self.config['Settings']['PathToOutput_relative'] == "C:/":
            self.config['Settings']['PathToOutput_relative'] = PathToOutput_relative   
        self.config['Settings']['PathToOutput_relative'] = os.path.normpath(self.config['Settings']['PathToOutput_relative'])

        if 'PathToPT_relative' not in self.config['Settings'] or self.config['Settings']['PathToPT_relative'] == "C:/":
            self.config['Settings']['PathToPT_relative'] = PathToOutput_relative
        self.config['Settings']['PathToPT_relative'] = os.path.normpath(self.config['Settings']['PathToPT_relative'])

        if 'PathToCar_relative' not in self.config['Settings'] or self.config['Settings']['PathToCar_relative'] == "C:/":
            self.config['Settings']['PathToCar_relative'] = PathToOutput_relative   
        self.config['Settings']['PathToCar_relative'] = os.path.normpath(self.config['Settings']['PathToCar_relative'])

        if 'calc_ratio_relative' not in self.config['Settings']:
            self.config['Settings']['calc_ratio_relative'] = "True"

        if 'calc_difference_relative' not in self.config['Settings']:
            self.config['Settings']['calc_difference_relative'] = "True"

        if 'calc_relative_difference_relative' not in self.config['Settings']:
            self.config['Settings']['calc_relative_difference_relative'] = "True"

        if 'VisLayer_relative' not in self.config['Settings']:
            self.config['Settings']['VisLayer_relative'] = ''

        if 'VisLayers_fields_relative' not in self.config['Settings']:
            self.config['Settings']['VisLayers_fields_relative'] = ''

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToOutput_relative'] = self.txtPathToOutput.text()
        self.config['Settings']['PathToPT_relative'] = self.txtPathToPT.text()
        self.config['Settings']['PathToCar_relative'] = self.txtPathToCar.text()

        self.config['Settings']['calc_ratio_relative'] = str(
            self.cb_ratio.isChecked())
        self.config['Settings']['calc_difference_relative'] = str(
            self.cb_difference.isChecked())
        self.config['Settings']['calc_relative_difference_relative'] = str(
            self.cb_relative_difference.isChecked())

        self.config['Settings']['VisLayer_relative'] = self.cbVisLayers.currentText()
        self.config['Settings']['VisLayers_fields_relative'] = self.cbVisLayers_fields.currentText()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToOutput.setText(os.path.normpath(
            self.config['Settings']['PathToOutput_relative']))
        self.txtPathToPT.setText(os.path.normpath(self.config['Settings']['PathToPT_relative']))
        self.txtPathToCar.setText(os.path.normpath(
            self.config['Settings']['PathToCar_relative']))

        cb1 = self.config['Settings']['calc_ratio_relative'].lower() == "true"
        self.cb_ratio.setChecked(cb1)
        cb1 = self.config['Settings']['calc_difference_relative'].lower(
        ) == "true"
        self.cb_difference.setChecked(cb1)
        cb1 = self.config['Settings']['calc_relative_difference_relative'].lower(
        ) == "true"
        self.cb_relative_difference.setChecked(cb1)

        self.cbVisLayers.setCurrentText(
            self.config['Settings']['VisLayer_relative'])
        self.cbVisLayers_fields.setCurrentText(
            self.config['Settings']['VisLayers_fields_relative'])

        self.txtAliase.setText(self.default_aliase)

        self.fill_combobox_with_csv_files(
            self.cmbListFiles1, self.config['Settings']['PathToPT_relative'])
        self.fill_combobox_with_csv_files(
            self.cmbListFiles2, self.config['Settings']['PathToCar_relative'])

    def check_output_folder(self):
        self.setMessage("")

        os.makedirs(self.txtPathToOutput.text(), exist_ok=True)

        try:
            tmp_prefix = "write_tester"
            filename = f'{self.txtPathToOutput.text()}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the output folder '{self.txtPathToOutput.text()}' is denied")
            return False

        return True

    def parse_log_file(self, file_path):
        params = {}
        with open(file_path, 'r') as file:
            inside_mode = False
            for line in file:
                line = line.strip()
                if line.startswith('[Mode]'):
                    inside_mode = True
                    continue
                if line.startswith('Started:'):
                    break
                if inside_mode and ': ' in line:
                    param, value = line.split(': ', 1)
                    params[param] = value
        return params

    def make_log_compare(self):
        path1 = self.txtPathToPT.text()
        path2 = self.txtPathToCar.text()

        pattern = 'log_*.txt'
        file_path1 = glob.glob(os.path.join(path1, pattern))[0]
        file_path2 = glob.glob(os.path.join(path2, pattern))[0]

        # parse both files
        params_file1 = self.parse_log_file(file_path1)
        params_file2 = self.parse_log_file(file_path2)
        comparison_array = []

        # process the Mode parameter separately to ensure it is the first one
        mode_value_file1 = params_file1.pop('Mode', 'XXX')
        mode_value_file2 = params_file2.pop('Mode', 'XXX')

        comparison_array.append({
            'parameter': 'Accessibility computation options',
            'value_file1': mode_value_file1,
            'value_file2': mode_value_file2
        })

        all_params = set(params_file1.keys()).union(set(params_file2.keys()))

        # add all parameters from the first file
        for param in params_file1:
            comparison_array.append({
                'parameter': param,
                'value_file1': params_file1[param],
                'value_file2': params_file2.get(param, 'XXX')
            })

        #  add the remaining parameters from the second file that were not present in the first one
        for param in params_file2:
            if param not in [entry['parameter'] for entry in comparison_array]:
                comparison_array.append({
                    'parameter': param,
                    'value_file1': 'XXX',
                    'value_file2': params_file2[param]
                })
        
        html_table = self.generate_html_table(comparison_array)
        self.textLog.append(html_table)

    def generate_html_table(self, comparison_array):
        html = "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>Settings</th><th>File1</th><th>File2</th></tr>"

        for entry in comparison_array:
            html += f"<tr><td>{entry['parameter']}</td><td>{entry['value_file1']}</td><td>{entry['value_file2']}</td></tr>"

        html += "</table>"
        return html

    def check_log(self, path):
        pattern = 'log_*.txt'
        file_path = glob.glob(os.path.join(path, pattern))
        file_path = file_path[0]
        found_forward = False
        found_map = False
        max_time_travel = None
        time_interval = None
        run_aggregate = False
        field_to_aggregate = None

        with open(file_path, 'r') as file:

            for line in file:
                if "Mode:" in line:
                    if "From" in line:
                        found_forward = True

                    if "Region" in line:
                        found_map = True

                if "Maximal time travel:" in line:
                    max_time_travel = int(
                        line.split(':')[1].strip().split()[0])

                if "Time interval between stored maps:" in line:
                    time_interval = int(line.split(':')[1].strip().split()[0])

                if "Run aggregate:" in line:
                    run_aggregate = line.split(':')[1].strip() == 'True'

                if "Field to aggregate:" in line:
                    field_to_aggregate = line.split(':')[1].strip()

        return (found_forward,
                found_map,
                max_time_travel,
                time_interval,
                run_aggregate,
                field_to_aggregate)

    def check_folder_and_file(self, path):

        if not os.path.exists(path):
            self.setMessage(f"Folder '{path}' does not exist")
            return False

        required_patterns = ['*.csv', 'log_*.txt']
        missing_files = []

        for pattern in required_patterns:
            pattern_path = os.path.join(path, pattern)
            matching_files = glob.glob(pattern_path)
            if not matching_files:
                missing_files.append(pattern)

        if missing_files:
            missing_files_message = ", ".join(missing_files)
            self.setMessage(f"Files are missing in '{path}': {missing_files_message}")
            return False

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def prepare(self):

        self.break_on = False

        QApplication.processEvents()

        run = True

        if run:

            self.path_output = f'{self.folder_name}//{self.mode_calc}_{self.txtAliase.text()}.csv'

            self.file1 = os.path.join(
                self.txtPathToPT.text(), self.cmbListFiles1.currentText())
            self.file2 = os.path.join(
                self.txtPathToCar.text(), self.cmbListFiles2.currentText())

            self.file_name1 = os.path.splitext(os.path.basename(self.file1))[0]
            self.file_name2 = os.path.splitext(os.path.basename(self.file2))[0]

            if self.MAP_first:
                self.calc_MAP(self.file1, self.file2)
            else:
                self.calc_AREA(self.file1, self.file2)

        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

    def calc_MAP(self, file1, file2):
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)

        column_name1 = df1.columns[-1]
        column_name2 = df2.columns[-1]
       
        postfix1 = self.file_name1
        postfix2 = self.file_name2

        df1_renamed = df1.rename(
            columns={col: col + "_" + postfix1 for col in df1.columns if col != self.first_col_star})
        df2_renamed = df2.rename(
            columns={col: col  + "_" +  postfix2 for col in df2.columns if col != self.second_col_star})

        merged_df = pd.merge(df1_renamed, df2_renamed, left_on=self.first_col_star, right_on=self.second_col_star )

        result_df = pd.DataFrame()
        result_df[self.first_col_star] = merged_df[self.first_col_star]

        col1 = f'{column_name1}_{postfix1}'
        col2 = f'{column_name2}_{postfix2}'

        result_df[col1] = merged_df[col1]
        result_df[col2] = merged_df[col2]

        if self.mode_calc == "ratio":
            result_df['Ratio'] = np.where(
                merged_df[col2] != 0, merged_df[col1] / merged_df[col2], 0)

        elif self.mode_calc == "difference":
            result_df['Difference'] = merged_df[col1] - merged_df[col2]

        elif self.mode_calc == "relative_difference":
            result_df['Relative_difference'] = np.where(
                merged_df[col2] != 0, (merged_df[col1] - merged_df[col2]) / merged_df[col2] * 100, 0)
        
        result_df.to_csv(self.path_output, index=False, na_rep='NaN')
        self.result_merge = result_df

    def calc_AREA(self, file1, file2):

        df1 = pd.read_csv(file1)
        
        column_name1 = df1.columns[-1]
        df2 = pd.read_csv(file2)
        column_name2 = df2.columns[-1]

        postfix1 = ""
        postfix2 = ""
        if column_name1 == column_name2:
            postfix2 = "_2"

        # filtering data by the first value of Origin_ID
        
        origin_id = df1[self.first_col_star].iloc[0]
        
        df1_filtered = df1[df1[self.first_col_star] == origin_id]
        df2_filtered = df2[df2[self.second_col_star] == origin_id]
        result_df = pd.DataFrame()

        # Saving the Destination_ID values from the first file
        result_df[self.first_col_hash] = df1_filtered[self.first_col_hash]

        # Convert Destination_ID to numeric
        df1_filtered[self.first_col_hash] = pd.to_numeric(df1_filtered[self.first_col_hash].astype(str).str.strip(), errors="coerce")
        df2_filtered[self.second_col_hash] = pd.to_numeric(df2_filtered[self.second_col_hash].astype(str).str.strip(), errors="coerce")
        
        # joining by Destination_ID
        merged_df = pd.merge(df1_filtered[[self.first_col_star, self.first_col_hash, column_name1]],
                             df2_filtered[[self.second_col_hash, column_name2]],
                             left_on=self.first_col_hash, right_on=self.second_col_hash,
                             suffixes=(postfix1, postfix2))

        result_df = merged_df[[self.first_col_star, self.first_col_hash, self.second_col_star, self.second_col_hash]].copy()
        result_df[f'Duration_{self.file_name1}'] = merged_df[f'{column_name1}{postfix1}']
        result_df[f'Duration_{self.file_name2}'] = merged_df[f'{column_name2}{postfix2}']

        # calculating the ratio of Duration from the first file to Duration from the second file
        if self.mode_calc == "ratio":
            result_df['Ratio'] = np.where(merged_df[f'{column_name2}{postfix2}'] != 0,
                                          merged_df[f'{column_name1}{postfix1}'] /
                                          merged_df[f'{column_name2}{postfix2}'],
                                          0)

        if self.mode_calc == "difference":
            result_df['Difference'] = (
                merged_df[f'{column_name1}{postfix1}'] - merged_df[f'{column_name2}{postfix2}'])

        if self.mode_calc == "relative_difference":

            result_df['Relative_difference'] = np.where(
                merged_df[f'{column_name2}{postfix2}'] != 0,
                (merged_df[f'{column_name1}{postfix1}'] - merged_df[f'{column_name2}{postfix2}']
                 ) / merged_df[f'{column_name2}{postfix2}'] * 100,
                0
            )

        result_df.to_csv(self.path_output, index=False, na_rep='NaN')
        self.result_merge = result_df

    # if the combobox is in focus, we ignore the mouse wheel scroll event
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

        
        if self.mode == 1: 
                help_filename = "compare_sa.txt"
        if self.mode == 2:
                help_filename = "compare_reg.txt"
                    
            
        hlp_file = os.path.join(hlp_directory, help_filename)
        hlp_file = os.path.normpath(hlp_file)
        self.load_text_with_bold_first_line (hlp_file)