import os
import glob
import pandas as pd
import webbrowser
import re
import numpy as np
from datetime import datetime
import configparser
import csv

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             )

from qgis.core import (QgsProject,
                       QgsVectorLayer,
                       QgsMapLayerProxyModel,
                       )

from PyQt5.QtCore import (Qt,
                          QEvent,
                          )
from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic
from qgis.gui import QgsFileWidget

from visualization import visualization
from common import (getDateTime, 
                    get_qgis_info, 
                    is_valid_folder_name, 
                    check_file_parameters_accessibility,
                    get_name_columns,
                    FIELD_ID,
                    check_layer
                    )

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'relative.ui'))

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
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

        self.fix_size3 = 25 * self.txtPathToOutput.fontMetrics().width('x')
        self.txtAlias.setFixedWidth(self.fix_size3)

        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()
        self.break_on = False
        self.title = title
        self.mode = mode
        
        self.roundtrip = False

        self.progressBar.setValue(0)
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)
        self.toolButton_Output.clicked.connect(lambda: self.showFoldersDialog(self.txtPathToOutput))
        
        self.btnBreakOn.clicked.connect(self.set_break_on)
        self.run_button = self.buttonBox.addButton("Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton("Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton("Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)
        
        self.cbVisLayers.installEventFilter(self)
        self.cbVisLayers.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.toolButtonViz.clicked.connect(lambda: self.open_file_dialog ())

        self.default_aliase = f'{getDateTime()}'

        self.widget_result1.setStorageMode(QgsFileWidget.GetFile)
        self.widget_result2.setStorageMode(QgsFileWidget.GetFile)
        self.widget_result1.setFilter("CSV files (*.csv);")
        self.widget_result2.setFilter("CSV files (*.csv);")

        self.ParametrsShow()
        self.show_info()

        self.lblAlias.setVisible(False)
        self.txtAlias.setVisible(False)

    def open_file_dialog(self):
        project_path = QgsProject.instance().fileName()
        initial_dir = os.path.dirname(project_path) if project_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose a File",
            initial_dir,
            "All supported (*.shp *.gpkg);;Shapefile (*.shp);;GeoPackage (*.gpkg)"
        )
        if not file_path:
            return

        added_layers = []
        if file_path.lower().endswith(".gpkg"):
            temp_layer = QgsVectorLayer(file_path, "temp_discovery", "ogr")
            if not temp_layer.isValid():
                return
            sublayers = temp_layer.dataProvider().subLayers()
            for sub_info in sublayers:
                parts = sub_info.split('!!::!!')
                if len(parts) >= 2:
                    layer_name = parts[1]
                    uri = f"{file_path}|layername={layer_name}"
                    new_layer = QgsVectorLayer(uri, layer_name, "ogr")
                    if new_layer.isValid():
                        QgsProject.instance().addMapLayer(new_layer)
                        added_layers.append(new_layer)
        else:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            layer = QgsVectorLayer(file_path, file_name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                added_layers.append(layer)
        if added_layers:
            target_layer = added_layers[-1] 
            self.cbVisLayers.setLayer(target_layer)
      
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

        if not (is_valid_folder_name(self.txtAlias.text())):
            self.setMessage(f"'{self.txtAlias.text()}' is not a valid  directory/file name")
            self.run_button.setEnabled(True)
            return 0

        if not (self.check_output_folder()):
            self.run_button.setEnabled(True)
            return 0

        if not self.widget_result1.filePath():
            self.setMessage('File1 is not provided')
            self.run_button.setEnabled(True)
            return 0

        if not self.widget_result1.filePath():
            self.setMessage('File2 is not provided')
            self.run_button.setEnabled(True)
            return 0

        if not os.path.isfile(self.widget_result1.filePath()):
            self.setMessage('File1 is not provided')
            self.run_button.setEnabled(True)
            return 0

        if not os.path.isfile(self.widget_result2.filePath()):
            self.setMessage('File2 is not provided')
            self.run_button.setEnabled(True)
            return 0

        result, text = check_layer(self.cbVisLayers.currentLayer(), FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0

        if not (self.cb_ratio.isChecked()) \
                and not (self.cb_difference.isChecked())  \
                and not (self.cb_relative_difference.isChecked()):

            self.setMessage('Choose calculation mode')
            self.run_button.setEnabled(True)
            return 0
        
        cols_dict = get_name_columns()
        
        mode_first, mode_roundtrip_first, self.MAP_first, AccessibilityText_first = self.check_log(os.path.dirname(self.widget_result1.filePath()))
        
        self.from_to_first = 1 if mode_first else 2
        protocol = 1 if self.MAP_first else 2
        cols = cols_dict[(self.from_to_first, protocol)]
        self.first_col_star = cols["star"]
        self.first_col_hash = cols["hash"]

        mode_second, mode_roundtrip_second, self.MAP_second, AccessibilityText_second = self.check_log(os.path.dirname(self.widget_result2.filePath()))
        
        self.from_to_second = 1 if mode_second else 2
        protocol = 1 if self.MAP_second else 2
        cols = cols_dict[(self.from_to_second, protocol)]
        self.second_col_star = cols["star"]
        self.second_col_hash = cols["hash"]

        
        if mode_roundtrip_first or mode_roundtrip_second:
            if not (mode_roundtrip_first and mode_roundtrip_second):
                self.run_button.setEnabled(True)
                self.setMessage("First csv type: {}. Second csv type: {}. Must be type: ROUNDTRIP".format(
                                        AccessibilityText_first,AccessibilityText_second                       
                                        )
                )
                return 0
            else:
                self.roundtrip = True

        if self.mode == 1:
            if self.MAP_first or self.MAP_second:
                self.run_button.setEnabled(True)
                self.setMessage(
                    "First csv type: {}. Second csv type: {}. Must be type: Service area".format(
                        "Cumulative opportunities" if self.MAP_first else "Service area",
                        "Cumulative opportunities" if self.MAP_second else "Service area"
                    )
                )
                return 0

        if self.mode == 2:
            if not (self.MAP_first) or not (self.MAP_second):
                self.run_button.setEnabled(True)
                self.setMessage(
                    "First csv type: {}. Second csv type: {}. Must be type: Cumulative opportunities.".format(
                        "Cumulative opportunities" if self.MAP_first else "Service area",
                        "Cumulative opportunities" if self.MAP_second else "Service area"
                    )
                )
                return 0

        self.folder_name = f'{self.txtPathToOutput.text()}//{self.txtAlias.text()}'

        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)
        else:
            self.setMessage(f"Folder '{self.folder_name}' already exists")
            self.run_button.setEnabled(True)
            return 0

       
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

        LayerVis = self.cbVisLayers.currentLayer()
        self.layer_vis_path = LayerVis.dataProvider().dataSourceUri().split("|")[0]
        self.alias = self.txtAlias.text()

        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")
        self.textLog.append(f'<a> Scenario name: {self.alias}</a>')
        self.textLog.append(f"<a>Results_1 folder: {self.config['Settings']['PathToPT_relative']}</a>")
        self.textLog.append(f"<a>Results_2 folder: {self.config['Settings']['PathToCAR_relative']}</a>")
        self.textLog.append(f"<a>Output folder: {self.config['Settings']['PathToOutput_relative']}</a>")
        self.textLog.append(f"<a>Visualization layer: {os.path.normpath(self.layer_vis_path)}</a>")
                
        self.textLog.append(f"<a>Calculate ratio: {self.config['Settings']['calc_ratio_relative']}</a>")
        self.textLog.append(f"<a>Calculate difference: {self.config['Settings']['calc_difference_relative']}</a>")
        self.textLog.append(f"<a>Calculate relative difference: {self.config['Settings']['calc_relative_difference_relative']}</a>")
       
        fieldname_layer = FIELD_ID

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
                            from_to = self.from_to_first
                            )

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
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
        path1 = os.path.join(self.folder_name, f"{self.txtAlias.text()}_{self.file_name1}_only.csv")
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
        path2 = os.path.join(self.folder_name, f"{self.txtAlias.text()}_{self.file_name2}_only.csv")
        df2_only.to_csv(path2, index=False, na_rep='NaN')
        vis3.add_thematic_map(path2, f"{self.alias}_{self.file_name2}_only", type_compare="CompareSecondOnly")
        list_file_name.append(path2)

        QApplication.processEvents()
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
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
        
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/relative_ready-made.html"
        webbrowser.open(url)

    def showFoldersDialog(self, obj):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", obj.text())
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

        file_path = os.path.join(project_directory, 'parameters_accessibility.txt')

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

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        self.config['Settings']['PathToOutput_relative'] = self.txtPathToOutput.text()
        self.config['Settings']['PathToPT_relative'] = self.widget_result1.filePath()
        self.config['Settings']['PathToCar_relative'] = self.widget_result2.filePath()

        self.config['Settings']['calc_ratio_relative'] = str(self.cb_ratio.isChecked())
        self.config['Settings']['calc_difference_relative'] = str(self.cb_difference.isChecked())
        self.config['Settings']['calc_relative_difference_relative'] = str(self.cb_relative_difference.isChecked())

        self.config['Settings']['VisLayer_relative'] = self.cbVisLayers.currentLayer().id()
        
        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToOutput.setText(os.path.normpath(self.config['Settings']['PathToOutput_relative']))
        self.widget_result1.setFilePath(os.path.normpath(self.config['Settings']['PathToPT_relative']))
        self.widget_result2.setFilePath(os.path.normpath(self.config['Settings']['PathToCar_relative']))

        cb1 = self.config['Settings']['calc_ratio_relative'].lower() == "true"
        self.cb_ratio.setChecked(cb1)
        cb1 = self.config['Settings']['calc_difference_relative'].lower() == "true"
        self.cb_difference.setChecked(cb1)
        cb1 = self.config['Settings']['calc_relative_difference_relative'].lower() == "true"
        self.cb_relative_difference.setChecked(cb1)
        self.cbVisLayers.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['VisLayer_relative']))
        self.txtAlias.setText(self.default_aliase)


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
        """Парсит CSV-лог от [Mode] до [Processing], исключая заголовки разделов."""
        params = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, quotechar='"', delimiter=',')
                
                start_recording = False
                
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    
                    param_name = row[0].strip()
                    param_value = row[1].strip()

                    # Включаем запись, когда дошли до раздела [Mode]
                    if param_name == "[Mode]":
                        start_recording = True
                        continue # Пропускаем саму строку заголовка
                    
                    # Выключаем запись, когда дошли до раздела [Processing]
                    if param_name == "[Processing]":
                        break
                    
                    if start_recording:
                        # Игнорируем любые другие заголовки разделов внутри диапазона (например, [Input], [Output])
                        if param_name.startswith("[") and param_name.endswith("]"):
                            continue
                        
                        # Сохраняем параметр, если у него есть имя
                        if param_name:
                            params[param_name] = param_value
                            
        except Exception as e:
            print(f"Error parsing log file {file_path}: {e}")
            
        return params

    def make_log_compare(self):
        path1 = os.path.dirname(self.widget_result1.filePath())
        path2 = os.path.dirname(self.widget_result2.filePath())
        pattern = 'log_*.csv'
        files1 = glob.glob(os.path.join(path1, pattern))
        files2 = glob.glob(os.path.join(path2, pattern))
        if not files1 or not files2:
            self.textLog.append("<b style='color:red;'>[Error] Log CSV files not found for comparison.</b>")
            return

        file_path1 = files1[0]
        file_path2 = files2[0]
        params_file1 = self.parse_log_file(file_path1)
        params_file2 = self.parse_log_file(file_path2)
        comparison_array = []
        mode_v1 = params_file1.pop('Mode', 'N/A')
        mode_v2 = params_file2.pop('Mode', 'N/A')
        comparison_array.append({
            'parameter': 'Accessibility computation options',
            'value_file1': mode_v1,
            'value_file2': mode_v2
        })

        # Добавляем все параметры из первого файла
        for param in params_file1:
            comparison_array.append({
                'parameter': param,
                'value_file1': params_file1[param],
                'value_file2': params_file2.get(param, '---')
            })

        # Добавляем параметры из второго файла, которых нет в первом
        for param in params_file2:
            if not any(entry['parameter'] == param for entry in comparison_array):
                comparison_array.append({
                    'parameter': param,
                    'value_file1': '---',
                    'value_file2': params_file2[param]
                })
       
        html_table = self.generate_html_table(comparison_array)
        self.textLog.append("<br><b style='font-size:14px;'>Comparison of scenarios:</b>")
        self.textLog.append(html_table)

    def generate_html_table(self, comparison_array):
        html = "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>Settings</th><th>File1</th><th>File2</th></tr>"

        for entry in comparison_array:
            html += f"<tr><td>{entry['parameter']}</td><td>{entry['value_file1']}</td><td>{entry['value_file2']}</td></tr>"

        html += "</table>"
        return html



    def check_log(self, path):
        pattern = 'log_*.csv'
        files = glob.glob(os.path.join(path, pattern))
        if not files:
            return (False, False, False, "")
        
        file_path = files[0]
        
        # Инициализация флагов
        mode_from = False
        mode_roundtrip = False
        mode_cumulative = False
        accessibility_text = ""

        with open(file_path, 'r', encoding='utf-8') as f:
            
            reader = csv.reader(f, quotechar='"', delimiter=',')
            # (Пропускаем заголовок "Parameter","Value")
            data = {row[0]: row[1] for row in reader if len(row) >= 2}

        
        if "Accessibility" in data:
            accessibility_text = data["Accessibility"]
            if "FROM" in accessibility_text.upper():
                mode_from = True
            if "TO" in accessibility_text.upper():
                mode_from = False
            if "ROUNDTRIP" in accessibility_text.upper():
                mode_roundtrip = True
                mode_from = True

        if "Mode" in data:
            if "cumulative" in data["Mode"].lower():
                mode_cumulative = True
        
        print (mode_from,
                mode_roundtrip,
                mode_cumulative,
                accessibility_text)

        return (mode_from,
                mode_roundtrip,
                mode_cumulative,
                accessibility_text
                )


    def setMessage(self, message):
        self.lblMessages.setText(message)

    def prepare(self):

        self.break_on = False

        QApplication.processEvents()

        run = True

        if run:

            self.path_output = f'{self.folder_name}//{self.mode_calc}_{self.txtAlias.text()}.csv'

            self.file1 = self.widget_result1.filePath()
            self.file2 = self.widget_result2.filePath()

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

        df1_renamed = df1.rename(columns={col: col + "_" + postfix1 for col in df1.columns if col != self.first_col_star})
        df2_renamed = df2.rename(columns={col: col  + "_" +  postfix2 for col in df2.columns if col != self.second_col_star})

        merged_df = pd.merge(df1_renamed, df2_renamed, left_on=self.first_col_star, right_on=self.second_col_star )

        result_df = pd.DataFrame()
        result_df[self.first_col_star] = merged_df[self.first_col_star]

        col1 = f'{column_name1}_{postfix1}'
        col2 = f'{column_name2}_{postfix2}'

        result_df[col1] = merged_df[col1]
        result_df[col2] = merged_df[col2]

        if self.mode_calc == "ratio":
            result_df['Ratio'] = np.where(merged_df[col2] != 0, merged_df[col1] / merged_df[col2], 0)

        elif self.mode_calc == "difference":
            result_df['Difference'] = merged_df[col1] - merged_df[col2]

        elif self.mode_calc == "relative_difference":
            result_df['Relative_difference'] = np.where(merged_df[col2] != 0, (merged_df[col1] - merged_df[col2]) / merged_df[col2] * 100, 0)
        
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
        
        #origin_id = df1[self.first_col_star].iloc[0]
                
        #df1_filtered = df1[df1[self.first_col_star] == origin_id]
        #df2_filtered = df2[df2[self.second_col_star] == origin_id]
        df1_filtered = df1
        df2_filtered = df2
        result_df = pd.DataFrame()

        # Saving the Destination_ID values from the first file
        #result_df[self.first_col_hash] = df1_filtered[self.first_col_hash]

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
        
    def show_info(self):

            hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')

            if self.mode == 1: 
                help_filename = "compare_sa.txt"
            else:
                help_filename = "compare_cumulative.txt"
            hlp_file = os.path.join(hlp_directory, help_filename)

            if os.path.exists(hlp_file):
                with open(hlp_file, 'r', encoding='utf-8') as f:
                    html = f.read()

            self.textInfo.setOpenExternalLinks(False)  
            self.textInfo.setOpenLinks(False)          
            self.textInfo.setHtml(html)
            self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))           