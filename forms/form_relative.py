import os
import pandas as pd
import webbrowser
import re
import numpy as np
import configparser
from datetime import datetime
from pathlib import Path

from osgeo import ogr
import geopandas as gpd
import traceback


from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             )
from PyQt5.QtCore import (Qt,
                          QEvent,
                          )
from PyQt5.QtGui import QTextDocument, QDesktopServices
from PyQt5 import uic

from qgis.gui import QgsFileWidget
from qgis.core import (QgsProject,
                       QgsMapLayerProxyModel,
                       )

from visualization import visualization
from common import (getDateTime, 
                    get_qgis_info,                      
                    check_file_parameters_accessibility,
                    get_name_columns,
                    FIELD_ID,
                    check_layer,                    
                    fast_write_gpkg,
                    highlight_empty_fields,
                    highlight_widget,
                    highlight_widget_no,
                    FIELD_ID
                    )

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'relative.ui'))

class form_relative(QDialog, FORM_CLASS):
    def __init__(self, title, mode):
      try:  
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])


        self.fix_size = 35 * self.wgFileSave.fontMetrics().width('x')
        self.comboBox_table1.setFixedWidth(self.fix_size)
        self.comboBox_table2.setFixedWidth(self.fix_size)
        
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()
        self.break_on = False
        self.title = title
        self.mode = mode
        
        self.roundtrip = False

        self.progressBar.setValue(0)
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)
                
        self.btnBreakOn.clicked.connect(self.set_break_on)
        self.run_button = self.buttonBox.addButton("Run", QDialogButtonBox.ActionRole)
        self.close_button = self.buttonBox.addButton("Close", QDialogButtonBox.RejectRole)
        self.help_button = self.buttonBox.addButton("Help", QDialogButtonBox.HelpRole)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)
        
        self.cbVisLayers.installEventFilter(self)
        self.cbVisLayers.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.default_aliase = f'{getDateTime()}'

        self.widget_result1.setStorageMode(QgsFileWidget.GetFile)
        self.widget_result2.setStorageMode(QgsFileWidget.GetFile)
        self.widget_result1.setFilter("GeoPackage (*.gpkg)")
        self.widget_result2.setFilter("GeoPackage (*.gpkg)")
        
        self.wgFileSave.setFilter("GeoPackage (*.gpkg)")
        
        self.widget_result1.fileChanged.connect(self.on_gpkg_changed)
        self.widget_result2.fileChanged.connect(self.on_gpkg_changed)

        self.ParametrsShow()
        self.show_info()
        self.log_array = []

        if self.mode == 1:
            self.comboBox_table1.setVisible(False)            
            self.comboBox_table2.setVisible(False)
            
      except Exception:
        traceback.print_exc()
    

    def on_gpkg_changed(self, path):
        sender = self.sender()

        if sender == self.widget_result1:
            combo = self.comboBox_table1
        elif sender == self.widget_result2:
            combo = self.comboBox_table2
        else:
            return

        combo.clear()

        if not path or not path.lower().endswith(".gpkg"):
            return
        
        if not os.path.exists(path):
            return

        ds = ogr.Open(path)
        if ds is None:            
            return

        for i in range(ds.GetLayerCount()):
            layer = ds.GetLayerByIndex(i)
            name = layer.GetName()
            if not name.startswith("_") and "_by_" not in name:
                # Проверяем, что слой без геометрии
                if layer.GetGeomType() == ogr.wkbNone:
                    combo.addItem(name)
      
    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)

    def getTableName(self, path):
        ds = ogr.Open(path)
        if ds is None:
            return None
        for i in range(ds.GetLayerCount()):
            layer = ds.GetLayerByIndex(i)
            name = layer.GetName()

            # Условия:
            # 1) имя содержит "_fastest_" и НЕ содержит "_by_"
            # 3) или содержит "_stat_all"
            if ("_fastest_" in name and "_by_" not in name):
                return name  

        return None

    def on_run_button_clicked(self):
        
        self.progressBar.setMaximum(6)
        self.progressBar.setValue(0)
        self.run_button.setEnabled(False)
        self.setMessage("")                
        highlight_widget_no(self.wgFileSave)        

        if highlight_empty_fields(self, exclude=[self.textLog]):   
            self.setMessage("All required fields must be filled in")                     
            self.run_button.setEnabled(True)
            return 0

        self.break_on = False

        if not self.widget_result1.filePath():
            self.setMessage('File1 is not provided')
            self.run_button.setEnabled(True)
            return 0

        if not self.widget_result1.filePath():
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
        
        file_path = self.wgFileSave.filePath()
        base, ext = os.path.splitext(file_path)
        if ext.lower() != ".gpkg":
            file_path = base + ".gpkg"
        self.file_name_gpkg = file_path

        folder = os.path.dirname(self.file_name_gpkg)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        if os.path.exists(self.file_name_gpkg):
            try:
                os.remove(self.file_name_gpkg)
            except PermissionError:
                self.run_button.setEnabled(True)
                highlight_widget(self.wgFileSave)
                self.setMessage(f'The file "{self.file_name_gpkg}" is locked.')
                return 0
        
        self.file_name_gpkg_short = Path(self.file_name_gpkg).stem
        self.file1 = self.widget_result1.filePath()

        if not (os.path.isfile(self.file1) and self.file1.lower().endswith(".gpkg")):
            self.setMessage('Select the correct file "Result_1"')
            self.run_button.setEnabled(True)
            return 0
        
        self.file1_short = Path(self.file1).stem
        self.file2 = self.widget_result2.filePath()

        if not (os.path.isfile(self.file2) and self.file2.lower().endswith(".gpkg")):
            self.setMessage('Select the correct file "Result_2"')
            self.run_button.setEnabled(True)
            return 0
        
        self.file2_short = Path(self.file2).stem

        if self.mode == 2:
            self.table1 = self.comboBox_table1.currentText()
            self.table2 = self.comboBox_table2.currentText()
        else:
            self.table1 = self.getTableName(self.file1)
            self.table2 = self.getTableName(self.file2)
        
        prefix_result = f"{self.table1[:4]}_{self.table2[:4]}"

        if not self.table1:
            self.setMessage('Select the correct file "Result_1"')
            self.run_button.setEnabled(True)
            return 0
        
        if not self.table2:
            self.setMessage('Select the correct file "Result_2"')
            self.run_button.setEnabled(True)
            return 0
        
        cols_dict = get_name_columns()
        mode_first, self.mode_roundtrip_first, self.MAP_first, AccessibilityText_first = self.check_log_gpkg(self.file1)

        self.from_to_first = 1 if mode_first else 2
        protocol = 1 if self.MAP_first else 2
        if self.mode_roundtrip_first:
            self.from_to_first = 2
        cols = cols_dict[(self.from_to_first, protocol)]
        self.first_col_star = cols["star"]
        self.first_col_hash = cols["hash"]

        self.first_col_star_name = self.first_col_star #cols[1]
        self.first_col_hash_name = self.first_col_hash #cols[2]


        mode_second, self.mode_roundtrip_second, self.MAP_second, AccessibilityText_second = self.check_log_gpkg(self.file2)

        if AccessibilityText_first == "error":
            self.setMessage('Select the correct file "Result_1"')
            self.run_button.setEnabled(True)
            return 0
        
        if AccessibilityText_second == "error":
            self.setMessage('Select the correct file "Result_2"')
            self.run_button.setEnabled(True)
            return 0

        
        
        self.from_to_second = 1 if mode_second else 2
        protocol = 1 if self.MAP_second else 2
        if self.mode_roundtrip_second:
            self.from_to_second = 2
        
        
        cols = cols_dict[(self.from_to_second, protocol)]
        self.second_col_star = cols["star"]
        self.second_col_hash = cols["hash"]

        self.second_col_star_name = self.second_col_star #cols[1]
        self.second_col_hash_name = self.second_col_hash #cols[2]

        
        if self.mode_roundtrip_first or self.mode_roundtrip_second:
            if not (self.mode_roundtrip_first and self.mode_roundtrip_second):
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
        
        if self.mode_roundtrip_second:
            self.first_col_hash = self.second_col_hash = "Origin_aid" 
            self.first_col_star = self.second_col_star = "Destination_aid" 
       
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
        
        self.textLog.append("<a style='font-weight:bold;'>[Settings]</a>")        
        self.textLog.append(f"<a>Results_1 file: {self.file1}</a>")        
        self.textLog.append(f"<a>Results_1 table: {self.table1}")        
        self.textLog.append(f"<a>Results_2 file: {self.file2}</a>")        
        self.textLog.append(f"<a>Results_2 table: {self.table2}</a>")        

        self.textLog.append(f'<a> Output file: {self.file_name_gpkg}</a>')        
        self.textLog.append(f"<a>Visualization layer: {os.path.normpath(self.layer_vis_path)}</a>")                
        self.textLog.append(f"<a>Calculate ratio: {self.config['Settings']['calc_ratio_relative']}</a>")        
        self.textLog.append(f"<a>Calculate difference: {self.config['Settings']['calc_difference_relative']}</a>")        
        self.textLog.append(f"<a>Calculate relative difference: {self.config['Settings']['calc_relative_difference_relative']}</a>")
        
        self.log_array.append({"parameter": "[System]"})
        for key, value in qgis_info.items():
            self.log_array.append({
                "parameter": key,
                "Result_1": value
            })
        self.log_array.append({"parameter": "[Mode]"})
        self.log_array.append({"parameter": "Mode", "Result_1": self.title})
        self.log_array.append({"parameter": "[Settings]"})
        self.log_array.append({"parameter": "Results file", "Result_1": self.file1, "Result_2": self.file2})
        self.log_array.append({"parameter": "Results table", "Result_1": self.table1, "Result_2": self.table2})
        self.log_array.append({"parameter": "Output file", "Result_1": self.file_name_gpkg})
        self.log_array.append({"parameter": "Visualization layer", "Result_1": self.layer_vis_path})
        self.log_array.append({"parameter": "Calculate ratio", "Result_1": str(self.cb_ratio.isChecked())})
        self.log_array.append({"parameter": "Calculate difference", "Result_1": str(self.cb_difference.isChecked())})
        self.log_array.append({"parameter": "Calculate relative difference", "Result_1": str(self.cb_relative_difference.isChecked())})
        self.log_array.append({"parameter": "Comparison of scenarios"})
               
        fieldname_layer = FIELD_ID

        if self.MAP_first:
            mode_visualization = 1
        else:
            mode_visualization = 2
       
        result, comparison_array = self.make_log_compare_gpkg()

        if not result:
            self.progressBar.setValue(0)
            self.close_button.setEnabled(True)
            self.setMessage("")
            return
        
        
        df_comparison = pd.DataFrame(comparison_array)                
        for _, row in df_comparison.iterrows():
            self.log_array.append(row.to_dict())


        self.roundtrip_compare = False
        if self.roundtrip:
            self.roundtrip_compare = True
        vis = visualization(self,
                            LayerVis,
                            mode=mode_visualization,
                            fieldname_layer=fieldname_layer,
                            mode_compare=True,
                            from_to = self.from_to_second,
                            roundtrip_compare = self.roundtrip_compare,
                            prefix = prefix_result
                            )
        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

        self.log_array.append({"parameter": "Started", "Result_1": begin_computation_str})
        

        self.progressBar.setValue(1)
        QApplication.processEvents()

        self.df1 = gpd.read_file(self.file1, layer = self.table1)
        self.df2 = gpd.read_file(self.file2, layer = self.table2)
        
        self.alias = Path(self.file_name_gpkg).stem
        if self.cb_ratio.isChecked():
            self.mode_calc = "ratio"
            self.table_name = f'ratio_{self.file1_short}_{self.table1}_{self.file2_short}_{self.table2}'
            self.prepare()
            type_compare = "RatioRelative"
            vis.add_thematic_map_gpkg(self.file_name_gpkg, self.table_name, self.table_name,type_compare = type_compare)
            

        self.progressBar.setValue(2)
        QApplication.processEvents()
        if self.cb_difference.isChecked():
            self.mode_calc = "difference"
            self.table_name = f'diff_{self.file1_short}_{self.table1}_{self.file2_short}_{self.table2}'
            self.prepare()
            if self.MAP_first:
                type_compare = "DifferenceRegion"
            else:
                type_compare = "DifferenceServiceAreas"

            vis.add_thematic_map_gpkg(self.file_name_gpkg, self.table_name, self.table_name, type_compare = type_compare)

        self.progressBar.setValue(3)
        QApplication.processEvents()
        if self.cb_relative_difference.isChecked():
            self.mode_calc = "relative_difference"
            self.table_name = f'rel_diff_{self.file1_short}_{self.table1}_{self.file2_short}_{self.table2}'
            self.prepare()            
            type_compare = "Rel_difference"
            
            vis.add_thematic_map_gpkg(self.file_name_gpkg, self.table_name, self.table_name, type_compare = type_compare)
                       

        self.progressBar.setValue(4)
        QApplication.processEvents()
        if self.MAP_first:
            field_name1 = self.first_col_star
            field_name2 = self.second_col_star
        else:
            field_name1 = self.first_col_hash
            field_name2 = self.second_col_hash

        if self.roundtrip_compare:            
            if self.MAP_first:
                field_name1 = "Destination_aid"
                field_name2 = "Destination_aid"

        roundtrip_mode = True if (self.mode_roundtrip_first and not self.MAP_first) else False

        vis2 = visualization(self,
                             LayerVis,
                             mode=mode_visualization,
                             fieldname_layer=fieldname_layer,
                             mode_compare=False,
                             from_to = self.from_to_first,
                             roundtrip = roundtrip_mode,
                             prefix = prefix_result)
                
        for df, col in [(self.df1, field_name1), (self.df2, field_name2)]:
            df.dropna(subset=[col], inplace=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # Оставляем строки из df1, которых нет в df2 по ключевому полю
        df1_only = self.df1[~self.df1[field_name1].isin(self.df2[field_name2])].copy()
                
        # Выбираем колонки: ключи + последняя (метрика)        
        if not self.MAP_first:
            cols_to_save1 = [c for c in [self.first_col_star, self.first_col_hash, "Duration", "Duration_ave"] if c in self.df1.columns]
            df1_only = df1_only[cols_to_save1]
        # Сохранение и карта для DF1
        table = f'{self.file1_short}_{self.table1}_only'
        fast_write_gpkg(self.file_name_gpkg, table, df1_only )        
        vis2.add_thematic_map_gpkg(self.file_name_gpkg, table, table, type_compare = "CompareFirstOnly")
        
        
        self.progressBar.setValue(5)
        QApplication.processEvents()

        
        roundtrip_mode = True if (self.mode_roundtrip_second and not self.MAP_second) else False
        vis3 = visualization(self,
                             LayerVis,
                             mode=mode_visualization,
                             fieldname_layer=fieldname_layer,
                             mode_compare=False,
                             from_to = self.from_to_second,
                             roundtrip = roundtrip_mode,
                             prefix = prefix_result)
        
        # Оставляем строки из df2, которых нет в df1 по ключевому полю
        df2_only = self.df2[~self.df2[field_name2].isin(self.df1[field_name1])].copy()
        # Выбираем колонки
        if not self.MAP_first:
            cols_to_save2 = [c for c in [self.first_col_star, self.first_col_hash, "Duration", "Duration_ave"] if c in self.df2.columns]        
            df2_only = df2_only[cols_to_save2]
        # Сохранение и карта для DF2
        table = f'{self.file2_short}_{self.table2}_only'
        fast_write_gpkg(self.file_name_gpkg, table, df2_only )        
        vis3.add_thematic_map_gpkg(self.file_name_gpkg, table, table, type_compare = "CompareSecondOnly")
        
        QApplication.processEvents()
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        self.log_array.append({"parameter": "[Processing]"})
        self.log_array.append({"parameter": "Finished", "Result_1": after_computation_str})
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')
        self.log_array.append({"parameter": "Processing time", "Result_1": duration_without_microseconds})
        self.textLog.append(f'Output in file: <a href="file:///{self.file_name_gpkg}" target="_blank" > {self.file_name_gpkg}</a>')
        self.log_array.append({"parameter": "Output in file", "Result_1": self.file_name_gpkg})
                
        self.log_array_df = pd.DataFrame(self.log_array)

        folder = os.path.dirname(self.file_name_gpkg)
        name, _ = os.path.splitext(os.path.basename(self.file_name_gpkg))
        filelog_name = os.path.join(folder, f"{name}_log.csv")
        self.log_array_df.to_csv(filelog_name, sep=",", index=False, encoding="utf-8")
        
        fast_write_gpkg(self.file_name_gpkg, f"_{self.file_name_gpkg_short}_log", self.log_array_df, mode_relative = True)        

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
        
        self.config['Settings']['PathToOutput_relative'] = self.wgFileSave.filePath()
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

        self.wgFileSave.setFilePath(os.path.join(os.path.dirname(self.config['Settings']['PathToOutput_relative']), f"{self.default_aliase}.gpkg"))
        self.widget_result1.setFilePath(os.path.normpath(self.config['Settings']['PathToPT_relative']))
        self.widget_result2.setFilePath(os.path.normpath(self.config['Settings']['PathToCar_relative']))

        cb1 = self.config['Settings']['calc_ratio_relative'].lower() == "true"
        self.cb_ratio.setChecked(cb1)
        cb1 = self.config['Settings']['calc_difference_relative'].lower() == "true"
        self.cb_difference.setChecked(cb1)
        cb1 = self.config['Settings']['calc_relative_difference_relative'].lower() == "true"
        self.cb_relative_difference.setChecked(cb1)
        self.cbVisLayers.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['VisLayer_relative']))
    
    def check_log_gpkg(self, gpkg_path):

        if not os.path.isfile(gpkg_path):
            return (False, False, False, "error")

        ds = ogr.Open(gpkg_path)
        if ds is None:
            return (False, False, False, "error")

        layer = next(
                (ds.GetLayerByIndex(i) for i in range(ds.GetLayerCount())
                if ds.GetLayerByIndex(i).GetName().startswith("_")),
                None
            )
        if layer is None:
            return (False, False, False, "error")
        
        defn = layer.GetLayerDefn()
        if defn.GetFieldIndex("Parameter") < 0 or defn.GetFieldIndex("Value") < 0:
            return (False, False, False, "error")
        
        data = {}
        for feature in layer:
            param = feature.GetField("Parameter")
            value = feature.GetField("Value")
            if param:
                data[param] = value
        
        mode_from = False
        mode_roundtrip = False
        mode_cumulative = False
        accessibility_text = data.get("Accessibility", "")

        # --- Логика определения режимов ---
        if accessibility_text:
            text = accessibility_text.upper()

            if "FROM" in text:
                mode_from = True
            if "TO" in text:
                mode_from = False
            if "ROUNDTRIP" in text:
                mode_roundtrip = True
                mode_from = True

        mode_value = data.get("Mode", "")
        if "cumulative" in mode_value.lower():
            mode_cumulative = True

        return (mode_from, mode_roundtrip, mode_cumulative, accessibility_text)

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def prepare(self):

        self.break_on = False
        QApplication.processEvents()
        run = True
        if run:
            if self.MAP_first:
                self.calc_MAP(self.df1, self.df2)
            else:
                self.calc_AREA(self.df1, self.df2)
        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

    def calc_MAP(self, df1, df2):
        
        column_name1 = df1.columns[-1]
        column_name2 = df2.columns[-1]

        if self.mode_roundtrip_second and self.mode == 1:
            column_name1 = column_name2 = "Duration_ave"

       
        postfix1 = "1" #self.table1
        postfix2 = "2" #self.table2

        df1_renamed = df1.rename(columns={col: col + "_" + postfix1 for col in df1.columns if col != self.first_col_star})
        df2_renamed = df2.rename(columns={col: col  + "_" +  postfix2 for col in df2.columns if col != self.second_col_star})
        
        result_df = pd.DataFrame()

        if not self.mode_roundtrip_second:
            merged_df = pd.merge(df1_renamed, df2_renamed, left_on=self.first_col_star, right_on=self.second_col_star )
            result_df[self.first_col_star] = merged_df[self.first_col_star]
        else:
            merged_df = pd.merge(df1_renamed, df2_renamed, left_on=f'Destination_aid', right_on=f'Destination_aid')
            result_df[f'Destination_aid'] = merged_df[f'Destination_aid']
        
        col1 = f'{column_name1}_{postfix1}'
        col2 = f'{column_name2}_{postfix2}'

        if col1 + "_x" in merged_df.columns:
            col1 = col1 + "_x"                
        if col2 + "_y" in merged_df.columns:
            col2 = col2 + "_y"
        
        result_df[col1] = merged_df[col1]
        result_df[col2] = merged_df[col2]

        if self.mode_calc == "ratio":
            result_df['Ratio'] = np.where(merged_df[col2] != 0, merged_df[col1] / merged_df[col2], 0)

        elif self.mode_calc == "difference":
            result_df['Difference'] = round(merged_df[col1] - merged_df[col2])

        elif self.mode_calc == "relative_difference":
            result_df['Relative_difference'] = np.where(merged_df[col2] != 0, (merged_df[col1] - merged_df[col2]) / merged_df[col2] * 100, 0)
                
        fast_write_gpkg(self.file_name_gpkg, self.table_name, result_df)
        self.result_merge = result_df

    def calc_AREA(self, df1, df2):
        
        column_name1 = df1.columns[-1]
        column_name2 = df2.columns[-1]

        postfix1 = ""
        postfix2 = ""        

        if self.mode_roundtrip_second:
            column_name1 = "Duration_ave"    
            column_name2 = "Duration_ave"   

        if column_name1 == column_name2:
            postfix2 = "_2"
       
        df1_filtered = df1
        df2_filtered = df2
        result_df = pd.DataFrame()

        df1_filtered[self.first_col_hash] = pd.to_numeric(df1_filtered[self.first_col_hash].astype(str).str.strip(), errors="coerce")
        df2_filtered[self.second_col_hash] = pd.to_numeric(df2_filtered[self.second_col_hash].astype(str).str.strip(), errors="coerce")
        
        # joining by Destination_ID
        
        """
        if self.mode_roundtrip_second:
            
            merged_df = pd.merge(
                            df1_filtered[[self.first_col_star, self.first_col_hash,column_name1]],
                            df2_filtered[[self.second_col_star, self.second_col_hash, column_name2]],
                            left_on=self.first_col_star,
                            right_on=self.second_col_star,
                            suffixes=(postfix1, postfix2)
                        )
        else:
        """
        merged_df = pd.merge(
                                df1_filtered[[self.first_col_star, self.first_col_hash, column_name1]],
                                df2_filtered[[self.second_col_star, self.second_col_hash, column_name2]],
                                left_on=self.first_col_hash,
                                right_on=self.second_col_hash,
                                suffixes=(postfix1, postfix2)
                            )
        
        result_df[f'{self.first_col_star}_1'] = merged_df[f'{self.first_col_star}{postfix1}']
        result_df[f'{self.second_col_star_name}_2'] = merged_df[f'{self.second_col_star}{postfix2}']
        
        #result_df[self.first_col_hash] = merged_df[self.first_col_hash]             
        result_df[self.second_col_hash] = merged_df[self.first_col_hash]             
        
        result_df[f'{column_name1}_1'] = merged_df[f'{column_name1}{postfix1}']
        result_df[f'{column_name2}_2'] = merged_df[f'{column_name2}{postfix2}']

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

        fast_write_gpkg(self.file_name_gpkg, self.table_name, result_df)
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
    
    def make_log_compare_gpkg(self):
        
        params_file1 = self.parse_log_table_gpkg(self.file1)
        params_file2 = self.parse_log_table_gpkg(self.file2)

        if not params_file1 or not params_file2:
            self.textLog.append("<b style='color:red;'>[Error]: Log tables not found in GPKG files.</b>")
            return False, []

        # Собираем все уникальные ключи параметров
        all_keys = list(params_file1.keys())
        for k in params_file2.keys():
            if k not in all_keys:
                all_keys.append(k)

        comparison_array = []

        # Mode — всегда первым
        mode_v1 = params_file1.pop('Mode', '---')
        mode_v2 = params_file2.pop('Mode', '---')

        comparison_array.append({
            'parameter': 'Accessibility computation options',
            'Result_1': mode_v1,
            'Result_2': mode_v2
        })

        # -----------------------------
        # ПЕРВАЯ ПАРА: Arrive / Start
        # -----------------------------
        arrive_key = "Arrive to destination"
        start_key  = "Start from the origin"

        v1_arrive = params_file1.get(arrive_key)
        v1_start  = params_file1.get(start_key)
        v2_arrive = params_file2.get(arrive_key)
        v2_start  = params_file2.get(start_key)

        file1_has_1 = v1_arrive or v1_start
        file2_has_1 = v2_arrive or v2_start

        file1_param_1 = arrive_key if v1_arrive else (start_key if v1_start else None)
        file2_param_1 = arrive_key if v2_arrive else (start_key if v2_start else None)

        can_combine_1 = (
            file1_has_1 and file2_has_1 and
            file1_param_1 is not None and
            file2_param_1 is not None and
            file1_param_1 != file2_param_1
        )

        combined_1_added = False

        # -----------------------------
        # ВТОРАЯ ПАРА: Earliest start / Earliest arrival
        # -----------------------------
        earliest_start_key   = "The earliest start"
        earliest_arrival_key = "The earliest arrival"

        v1_es = params_file1.get(earliest_start_key)
        v1_ea = params_file1.get(earliest_arrival_key)
        v2_es = params_file2.get(earliest_start_key)
        v2_ea = params_file2.get(earliest_arrival_key)

        file1_has_2 = v1_es or v1_ea
        file2_has_2 = v2_es or v2_ea

        file1_param_2 = earliest_start_key if v1_es else (earliest_arrival_key if v1_ea else None)
        file2_param_2 = earliest_start_key if v2_es else (earliest_arrival_key if v2_ea else None)

        can_combine_2 = (
            file1_has_2 and file2_has_2 and
            file1_param_2 is not None and
            file2_param_2 is not None and
            file1_param_2 != file2_param_2
        )

        combined_2_added = False

        # -----------------------------
        # Основной цикл параметров
        # -----------------------------
        for param in all_keys:
            if param == 'Mode':
                continue

            # --- ОБЪЕДИНЕНИЕ ПЕРВОЙ ПАРЫ ---
            if param in (arrive_key, start_key) and can_combine_1 and not combined_1_added:

                v1 = v1_arrive or v1_start or '---'
                v2 = v2_arrive or v2_start or '---'

                comparison_array.append({
                    'parameter': "Start/Arrival",
                    'Result_1': v1,
                    'Result_2': v2
                })

                combined_1_added = True
                continue

            if can_combine_1 and param in (arrive_key, start_key):
                continue

            # --- ОБЪЕДИНЕНИЕ ВТОРОЙ ПАРЫ ---
            if param in (earliest_start_key, earliest_arrival_key) and can_combine_2 and not combined_2_added:

                v1 = v1_es or v1_ea or '---'
                v2 = v2_es or v2_ea or '---'

                comparison_array.append({
                    'parameter': "Earliest Start/Arrival",
                    'Result_1': v1,
                    'Result_2': v2
                })

                combined_2_added = True
                continue

            if can_combine_2 and param in (earliest_start_key, earliest_arrival_key):
                continue

            # --- Обычный параметр ---
            comparison_array.append({
                'parameter': param,
                'Result_1': params_file1.get(param, '---'),
                'Result_2': params_file2.get(param, '---')
            })

        # --- Обрезаем лог до [Processing], не включая его ---
        trimmed = []
        for row in comparison_array:
            if row.get("parameter") == "[Processing]":
                break
            trimmed.append(row)

        # Генерация HTML
        html_table = self.generate_html_table(trimmed)
        self.textLog.append("<br><b style='font-size:14px;'>Comparison of scenarios:</b>")
        self.textLog.append(html_table)

        return True, trimmed


    def generate_html_table(self, comparison_array):
        
        html = "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr bgcolor='#f2f2f2'><th>Settings</th><th>Result_1</th><th>Result_2</th></tr>"
        for entry in comparison_array:
            p = entry.get('parameter', '')
            v1 = entry.get('Result_1', '---')
            v2 = entry.get('Result_2', '---')
            html += f"<tr><td><b>{p}</b></td><td>{v1}</td><td>{v2}</td></tr>"
        html += "</table>"
        return html

    def parse_log_table_gpkg(self, gpkg_path):
        """Читает параметры из таблицы :log внутри GeoPackage."""
        if not gpkg_path or not os.path.exists(gpkg_path):
            return {}
        
        ds = ogr.Open(gpkg_path)
        if not ds: return {}
        
        layer = next(
                (ds.GetLayerByIndex(i) for i in range(ds.GetLayerCount())
                if ds.GetLayerByIndex(i).GetName().startswith("_")),
                None
            )

        if not layer: return {}

        defn = layer.GetLayerDefn()
        field_count = defn.GetFieldCount()        
        if field_count != 2:
            return {}
        
        params = {}
        for feat in layer:
            p = feat.GetField("Parameter")
            v = feat.GetField("Value")
            if p: params[p] = v
        return params