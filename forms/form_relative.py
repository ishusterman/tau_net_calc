import os
import pandas as pd
import webbrowser
import numpy as np
import configparser
import sqlite3
from datetime import datetime
from pathlib import Path

from osgeo import ogr
import geopandas as gpd

from qgis.PyQt.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             )
from qgis.PyQt.QtCore import (Qt,
                          QEvent,
                          )
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt import uic

from qgis.gui import QgsFileWidget
from qgis.core import (QgsProject,
                       QgsMapLayerProxyModel,
                       QgsVectorLayer,
                       QgsFieldProxyModel,
                       )
from qgis.PyQt.QtCore import QRegularExpression
from qgis.core import QgsVectorLayer, QgsFields

from tau_net_calc.cls.visualization import visualization
from tau_net_calc.cls.common import (getDateTime, 
                    get_qgis_info,                      
                    check_file_parameters_accessibility,
                    get_name_columns,                    
                    check_layer,                                        
                    highlight_empty_fields,
                    highlight_widget,
                    highlight_widget_no,
                    FIELD_ID,
                    setup_clear_highlight_listeners
                    )

shift_mod = Qt.KeyboardModifier.ShiftModifier

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'relative.ui'))

class form_relative(QDialog, FORM_CLASS):
    def __init__(self, title, mode):
      
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setupUi(self)
        self.setModal(False)        
        self.setWindowFlags(Qt.WindowType.Window)


        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

        fm = self.wgFileSave.fontMetrics()
        char_width = fm.horizontalAdvance("x")

        #self.fix_size = 35 * char_width

        #self.comboBox_table1.setFixedWidth(self.fix_size)
        #self.comboBox_table2.setFixedWidth(self.fix_size)
        
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

        role_action = QDialogButtonBox.ButtonRole.ActionRole
        role_reject = QDialogButtonBox.ButtonRole.RejectRole
        role_help = QDialogButtonBox.ButtonRole.HelpRole

        self.run_button = self.buttonBox.addButton("Run", role_action)
        self.close_button = self.buttonBox.addButton("Close", role_reject)
        self.help_button = self.buttonBox.addButton("Help", role_help)

        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.close_button.clicked.connect(self.on_close_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

        self.cbVisLayers.installEventFilter(self)
        self.cbVisLayers.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)

        self.default_aliase = f'{getDateTime()}'

        self.widget_result1.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.widget_result2.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.widget_result1.setFilter("GeoPackage (*.gpkg)")
        self.widget_result2.setFilter("GeoPackage (*.gpkg)")
        
        self.wgFileSave.setFilter("GeoPackage (*.gpkg)")
        
        self.widget_result1.fileChanged.connect(self.on_gpkg_changed)
        self.widget_result2.fileChanged.connect(self.on_gpkg_changed)

        self.comboBox_table1.currentTextChanged.connect(self.on_table1_changed)
        self.comboBox_table2.currentTextChanged.connect(self.on_table2_changed)

        self.ParametrsShow()
        self.show_info()
        self.log_array = []

        setup_clear_highlight_listeners(self)
         

    def on_gpkg_changed(self, path):
        sender = self.sender()

        if sender == self.widget_result1:
            combo = self.comboBox_table1
            field_combo = self.comboBox_field1
        elif sender == self.widget_result2:
            combo = self.comboBox_table2
            field_combo = self.comboBox_field2
        else:
            return

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        field_combo.clear()

        if not path or not path.lower().endswith(".gpkg") or not os.path.exists(path):
            combo.blockSignals(False)
            return

        ds = ogr.Open(path)
        if ds is None:
            combo.blockSignals(False)
            return

        for i in range(ds.GetLayerCount()):
            layer = ds.GetLayerByIndex(i)
            name = layer.GetName()
            if not name.startswith("_"):
                # Проверяем, что слой без геометрии
                if layer.GetGeomType() == ogr.wkbNone:
                    combo.addItem(name)

        combo.blockSignals(False)
        
        # Загружаем поля для первой выбранной таблицы (если таблицы нашлись)
        if combo.count() > 0:
            self.update_fields_for_table(path, combo.currentText(), field_combo)
    


    def update_fields_for_table(self, gpkg_path, table_name, field_combo):
        field_combo.setAllowEmptyFieldName(True)
        if not gpkg_path or not os.path.exists(gpkg_path) or not table_name:
            field_combo.blockSignals(True)
            field_combo.setFields(QgsFields())
            field_combo.blockSignals(False)
            return

        uri = f"{gpkg_path}|layername={table_name}"
        layer = QgsVectorLayer(uri, table_name, "ogr")

        if layer.isValid():
            # Сохраняем слой в self от сборщика мусора
            if field_combo == self.comboBox_field1:
                self.layer_table1 = layer
            elif field_combo == self.comboBox_field2:
                self.layer_table2 = layer

            excluded = {"fid", "origin_aid", "destination_aid"}

            # Создаем контейнер полей QGIS
            filtered_fields = QgsFields()

            for field in layer.fields():
                # Проверяем, что числовое и не входит в список исключений
                if field.isNumeric() and field.name().lower() not in excluded:
                    filtered_fields.append(field)

            # Блокируем сигналы, чтобы автовыбор поля при загрузке 
            # не активировал listener очистки стиля раньше времени:
            field_combo.blockSignals(True)
            field_combo.setFields(filtered_fields)
            field_combo.blockSignals(False)
        else:
            field_combo.blockSignals(True)
            field_combo.setFields(QgsFields())
            field_combo.blockSignals(False)

    def on_table1_changed(self, table_name):
        path = self.widget_result1.filePath()
        self.update_fields_for_table(path, table_name, self.comboBox_field1)

    def on_table2_changed(self, table_name):
        path = self.widget_result2.filePath()
        self.update_fields_for_table(path, table_name, self.comboBox_field2)
      
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
            # 1) имя содержит "_triptime" и НЕ содержит "_by_"
            
            if ("_triptime" in name or "_fastest_" in name) and "_by_" not in name:
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

        if not (self.cb_difference.isChecked()) and not (self.cb_relative_difference.isChecked()):
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
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                self.run_button.setEnabled(True)
                highlight_widget(self.wgFileSave)              
                self.setMessage(f'The path {os.path.dirname(self.file_name_gpkg)} is not found')
                return 0

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
            self.setMessage('Select correct "Result_1"')
            self.run_button.setEnabled(True)
            return 0
        
        self.file1_short = Path(self.file1).stem
        self.file2 = self.widget_result2.filePath()

        if not (os.path.isfile(self.file2) and self.file2.lower().endswith(".gpkg")):
            self.setMessage('Select correct "Result_2"')
            self.run_button.setEnabled(True)
            return 0
        
        self.file2_short = Path(self.file2).stem

        self.table1 = self.comboBox_table1.currentText()
        self.table2 = self.comboBox_table2.currentText()

        # if self.mode == 2:
        #     self.table1 = self.comboBox_table1.currentText()
        #     self.table2 = self.comboBox_table2.currentText()
        # else:
        #     self.table1 = self.getTableName(self.file1)
        #     self.table2 = self.getTableName(self.file2)
        
        if not self.table1:
            self.setMessage('Select correct table 1')
            self.run_button.setEnabled(True)
            return 0
        
        if not self.table2:
            self.setMessage('Select correct table 2')
            self.run_button.setEnabled(True)
            return 0
        
        prefix_result = f"{self.table1[:4]}_{self.table2[:4]}"

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
            self.setMessage('Select correct "Result_1"')
            self.run_button.setEnabled(True)
            return 0
        
        if AccessibilityText_second == "error":
            self.setMessage('Select correct "Result_2"')
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

        self.mode_by = False
        text = self.comboBox_table1.currentText()
        if "_by_destinations" in text:
            self.first_col_hash = self.first_col_star = "Origin_aid"
            self.mode_by = True 
        if "_by_origins" in text:
            self.first_col_hash = self.first_col_star = "Destination_aid" 
            self.mode_by = True 

        text = self.comboBox_table2.currentText()
        if "_by_destinations" in text:
            self.second_col_hash = self.second_col_star = "Origin_aid" 
        if "_by_origins" in text:
            self.second_col_hash = self.second_col_star = "Destination_aid" 
            
       
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
        self.textLog.append(f"<a>Results_1 field: {self.config['Settings']['field1_relative']}")        
        self.textLog.append(f"<a>Results_2 file: {self.file2}</a>")        
        self.textLog.append(f"<a>Results_2 table: {self.table2}</a>")        
        self.textLog.append(f"<a>Results_2 field: {self.config['Settings']['field2_relative']}")        

        self.textLog.append(f'<a> Output file: {self.file_name_gpkg}</a>')        
        self.textLog.append(f"<a>Visualization layer: {os.path.normpath(self.layer_vis_path)}</a>")                
        
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
        self.log_array.append({"parameter": "File", "Result_1": self.file1, "Result_2": self.file2})
        self.log_array.append({"parameter": "Table", "Result_1": self.table1, "Result_2": self.table2})
        self.log_array.append({"parameter": "Field", "Result_1": self.config['Settings']['field1_relative'], "Result_2": self.config['Settings']['field2_relative']})
        self.log_array.append({"parameter": "Output file", "Result_1": self.file_name_gpkg})
        self.log_array.append({"parameter": "Visualization layer", "Result_1": self.layer_vis_path})        
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
                            prefix = prefix_result,
                            mode_by= self.mode_by
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
        
        self.progressBar.setValue(2)
        QApplication.processEvents()
        if self.cb_difference.isChecked():
            self.mode_calc = "difference"
            self.table_name = f'DIFF_{self.table1}_VERSUS_{self.table2}'
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
            self.table_name = f'REL_DIFF_{self.table1}_VERSUS_{self.table2}'
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
                             prefix = prefix_result,
                             mode_by= self.mode_by)
                
        for df, col in [(self.df1, field_name1), (self.df2, field_name2)]:
            df.dropna(subset=[col], inplace=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # Оставляем строки из df1, которых нет в df2 по ключевому полю
        df1_only = self.df1[~self.df1[field_name1].isin(self.df2[field_name2])].copy()
                
        # Выбираем колонки: ключи + последняя (метрика)        
        # Выбираем колонки: ключи + метрика (убирая дублирующиеся имена)
        if not self.MAP_first:
            raw_cols1 = [self.first_col_star, self.first_col_hash, "Duration", "Duration_ave"]
            cols_to_save1 = list(dict.fromkeys([c for c in raw_cols1 if c in self.df1.columns]))
            df1_only = df1_only[cols_to_save1]
            # Гарантируем уникальность названий колонок
            df1_only = df1_only.loc[:, ~df1_only.columns.duplicated()].copy()
        # Сохранение и карта для DF1
        table = f'ONLY_{self.table1}'        
        self.write_compare_gpkg(table, df1_only)
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
                             prefix = prefix_result,
                             mode_by= self.mode_by)
        
        # Оставляем строки из df2, которых нет в df1 по ключевому полю
        df2_only = self.df2[~self.df2[field_name2].isin(self.df1[field_name1])].copy()
        # Выбираем колонки
        # Выбираем колонки: ключи + метрика (убирая дублирующиеся имена)
        if not self.MAP_first:
            raw_cols2 = [self.second_col_star, self.second_col_hash, "Duration", "Duration_ave"]
            cols_to_save2 = list(dict.fromkeys([c for c in raw_cols2 if c in self.df2.columns]))        
            df2_only = df2_only[cols_to_save2]
            # Гарантируем уникальность названий колонок
            df2_only = df2_only.loc[:, ~df2_only.columns.duplicated()].copy()
        # Сохранение и карта для DF2
        table = f'ONLY_{self.table2}'
        self.write_compare_gpkg(table, df2_only)
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
        self.write_compare_gpkg(f"_{self.file_name_gpkg_short}_log", self.log_array_df, is_log=True)       

        self.setMessage("Finished")
        self.progressBar.setValue(6)

        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/relative_ready-made.html"
        webbrowser.open(url)

    def showFoldersDialog(self, obj):

        current_path = obj.text()
        start_dir = ""
        if current_path:            
            start_dir = os.path.dirname(current_path)            

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            start_dir
        )

        if folder_path:
            obj.setText(os.path.normpath(folder_path))

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
        
        if 'table1_relative' not in self.config['Settings']:
            self.config['Settings']['table1_relative'] = ''
        if 'table2_relative' not in self.config['Settings']:
            self.config['Settings']['table2_relative'] = ''

        if 'field1_relative' not in self.config['Settings']:
            self.config['Settings']['field1_relative'] = ''
        if 'field2_relative' not in self.config['Settings']:
            self.config['Settings']['field2_relative'] = ''

    # update config file

    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)
        
        self.config['Settings']['PathToOutput_relative'] = self.wgFileSave.filePath()
        self.config['Settings']['PathToPT_relative'] = self.widget_result1.filePath()
        self.config['Settings']['PathToCar_relative'] = self.widget_result2.filePath()

        self.config['Settings']['table1_relative'] = self.comboBox_table1.currentText()
        self.config['Settings']['table2_relative'] = self.comboBox_table2.currentText()

        self.config['Settings']['field1_relative'] = self.comboBox_field1.currentText()
        self.config['Settings']['field2_relative'] = self.comboBox_field2.currentText()

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

        if QApplication.keyboardModifiers() & shift_mod:
            index = self.comboBox_table1.findText(self.config['Settings']['table1_relative'])
            if index != -1:
                self.comboBox_table1.setCurrentIndex(index)
            index = self.comboBox_table2.findText(self.config['Settings']['table2_relative'])
            if index != -1:
                self.comboBox_table2.setCurrentIndex(index)
            self.comboBox_field1.setField(self.config['Settings']['field1_relative'])
            self.comboBox_field2.setField(self.config['Settings']['field2_relative'])

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

        column_name1 = self.comboBox_field1.currentField()
        column_name2 = self.comboBox_field2.currentField()
        
        postfix1 = "1"
        postfix2 = "2"

        df1_renamed = df1.rename(columns={col: col + "_" + postfix1 for col in df1.columns if col != self.first_col_star})
        df2_renamed = df2.rename(columns={col: col + "_" + postfix2 for col in df2.columns if col != self.second_col_star})
        
        result_df = pd.DataFrame()

        if not self.mode_roundtrip_second:
            merged_df = pd.merge(df1_renamed, df2_renamed, left_on=self.first_col_star, right_on=self.second_col_star)
            result_df[self.first_col_star] = merged_df[self.first_col_star]
        else:
            merged_df = pd.merge(df1_renamed, df2_renamed, left_on='Destination_aid', right_on='Destination_aid')
            result_df['Destination_aid'] = merged_df['Destination_aid']
        
        col1 = f'{column_name1}_{postfix1}'
        col2 = f'{column_name2}_{postfix2}'

        if col1 + "_x" in merged_df.columns:
            col1 = col1 + "_x"                
        if col2 + "_y" in merged_df.columns:
            col2 = col2 + "_y"
        
        # Формируем новые имена сравниваемых полей: [12 от файла]#[6 от слоя]#[6 от поля]
        new_col1_name = f"{self.file1_short[:12]}#{self.table1[:6]}#{column_name1[:6]}"
        new_col2_name = f"{self.file2_short[:12]}#{self.table2[:6]}#{column_name2[:6]}"
        
        # Защита на случай, если обе строки оказались полностью идентичными
        if new_col1_name == new_col2_name:
            new_col1_name += "_1"
            new_col2_name += "_2"

        result_df[new_col1_name] = merged_df[col1]
        result_df[new_col2_name] = merged_df[col2]

        if self.mode_calc == "difference":
            result_df['Difference'] = round(merged_df[col1] - merged_df[col2])

        elif self.mode_calc == "relative_difference":
            result_df['Relative_difference'] = np.where(
                merged_df[col2] != 0, 
                (merged_df[col1] - merged_df[col2]) / merged_df[col2] * 100, 
                0
            )
        
        result_df = result_df.round(3)
                
        self.write_compare_gpkg(self.table_name, result_df)
        self.result_merge = result_df

    def calc_AREA(self, df1, df2):
         
        column_name1 = self.comboBox_field1.currentField()
        column_name2 = self.comboBox_field2.currentField()

        postfix1 = ""
        postfix2 = ""        

        if column_name1 == column_name2:
            postfix2 = "_2"
       
        df1_filtered = df1
        df2_filtered = df2
        result_df = pd.DataFrame()

        df1_filtered[self.first_col_hash] = pd.to_numeric(df1_filtered[self.first_col_hash].astype(str).str.strip(), errors="coerce")
        df2_filtered[self.second_col_hash] = pd.to_numeric(df2_filtered[self.second_col_hash].astype(str).str.strip(), errors="coerce")
        
        # Исключаем дубликаты столбцов в срезах
        cols1 = list(dict.fromkeys([self.first_col_star, self.first_col_hash, column_name1]))
        cols2 = list(dict.fromkeys([self.second_col_star, self.second_col_hash, column_name2]))

        merged_df = pd.merge(
            df1_filtered[cols1],
            df2_filtered[cols2],
            left_on=self.first_col_hash,
            right_on=self.second_col_hash,
            suffixes=(postfix1, postfix2)
        )
        
        # Заполнение результирующего DataFrame:
        # 1. Если это агрегированные таблицы (_by_origins / _by_destinations)
        if self.first_col_star == self.first_col_hash and self.second_col_star == self.second_col_hash:
            result_df[self.first_col_hash] = merged_df[self.first_col_hash]
        else:
            # 2. Обычный случай детальной матрицы
            col_star_1 = f'{self.first_col_star}{postfix1}' if f'{self.first_col_star}{postfix1}' in merged_df.columns else self.first_col_star
            col_star_2 = f'{self.second_col_star}{postfix2}' if f'{self.second_col_star}{postfix2}' in merged_df.columns else self.second_col_star

            result_df[f'{self.first_col_star}_1'] = merged_df[col_star_1]
            result_df[f'{self.second_col_star_name}_2'] = merged_df[col_star_2]
            result_df[self.second_col_hash] = merged_df[self.first_col_hash]

        # Имена столбцов с метриками с учетом суффиксов во временном merged_df
        val_col1 = f'{column_name1}{postfix1}' if f'{column_name1}{postfix1}' in merged_df.columns else column_name1
        val_col2 = f'{column_name2}{postfix2}' if f'{column_name2}{postfix2}' in merged_df.columns else column_name2

        # Формируем новые имена сравниваемых полей: [12 от файла]#[6 от слоя]#[6 от поля]
        new_col1_name = f"{self.file1_short[:12]}#{self.table1[:6]}#{column_name1[:6]}"
        new_col2_name = f"{self.file2_short[:12]}#{self.table2[:6]}#{column_name2[:6]}"

        # Защита на случай, если обе строки оказались полностью идентичными
        if new_col1_name == new_col2_name:
            new_col1_name += "_1"
            new_col2_name += "_2"

        result_df[new_col1_name] = merged_df[val_col1]
        result_df[new_col2_name] = merged_df[val_col2]

        # Расчет метрик       
        if self.mode_calc == "difference":
            result_df['Difference'] = merged_df[val_col1] - merged_df[val_col2]

        if self.mode_calc == "relative_difference":
            result_df['Relative_difference'] = np.where(
                merged_df[val_col2] != 0,
                (merged_df[val_col1] - merged_df[val_col2]) / merged_df[val_col2] * 100,
                0
            )
        
        result_df = result_df.round(3)

        self.write_compare_gpkg(self.table_name, result_df)
        self.result_merge = result_df      
       
    # if the combobox is in focus, we ignore the mouse wheel scroll event
    def eventFilter(self, obj, event):
        wheel_type = QEvent.Type.Wheel

        if event.type() == wheel_type:
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
    
    def write_compare_gpkg(self, table_name, df_current, is_log=False):
        if df_current is None or df_current.empty:
            return

        df_clean = df_current.copy()

        # Удаляем служебные колонки fid и geometry, если они пришли из gpd.read_file()
        cols_to_drop = [
            c for c in df_clean.columns 
            if c.lower() in ('fid', 'geometry')
        ]
        if cols_to_drop:
            df_clean.drop(columns=cols_to_drop, inplace=True)

        # Приводим последнюю колонку (метрику) к числовому типу (кроме таблицы логов)
        if not is_log and not df_clean.empty:
            last_col = df_clean.columns[-1]
            df_clean[last_col] = pd.to_numeric(df_clean[last_col], errors='coerce')

        # Если файла GPKG еще нет — создаем пустой контейнер GPKG со всеми служебными таблицами
        if not os.path.exists(self.file_name_gpkg):
            driver = ogr.GetDriverByName("GPKG")
            ds = driver.CreateDataSource(self.file_name_gpkg)
            ds = None

        # Записываем таблицу напрямую в SQLite без создания колонки fid
        with sqlite3.connect(self.file_name_gpkg) as conn:
            df_clean.to_sql(table_name, conn, if_exists='replace', index=False)
            conn.execute("""
                INSERT OR REPLACE INTO gpkg_contents 
                (table_name, data_type, identifier, description, last_change)
                VALUES (?, 'attributes', ?, '', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """, (table_name, table_name))
            conn.commit()