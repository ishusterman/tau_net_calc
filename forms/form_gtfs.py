import os
import webbrowser
import configparser
import csv
from pathlib import Path
import pandas as pd
import re
import shutil

from PyQt5.QtWidgets import (QTableWidget,
                            QTableWidgetItem,
                            QHeaderView)

from qgis.core import (QgsProject,
                       QgsVectorLayer
                       )

from PyQt5.QtCore import (Qt,
                          QEvent                         
                          )

from PyQt5.QtWidgets import (QDialogButtonBox,
                             QDialog,
                             QFileDialog,
                             QApplication,
                             QMessageBox
                             )

from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic

from datetime import datetime
from gtfs_exclude_routes import GTFSExcludeRoutes
from gtfs_add_routes import GTFSAddRoutes

from common import (get_qgis_info, 
                    getDateTime, 
                    check_file_parameters_accessibility, 
                    get_documents_path,
                    )

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'gtfs.ui')
)

class form_gtfs(QDialog, FORM_CLASS):
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
        self.progressBar.setValue(0)
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_GTFS.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToGTFS))
        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        self.toolButtonAddRoutes.clicked.connect(
            lambda: self.showFoldersDialog(self.txtAddRoutes))

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

        self.ParametrsShow()
        self.show_info()

        self.table1.setSelectionBehavior(QTableWidget.SelectRows) 
        self.table2.setSelectionBehavior(QTableWidget.SelectRows)
        self.btnSearch.clicked.connect(self.btnSearch_on_click)
        self.init_table()
        self.btnAdd.clicked.connect(self.btnAdd_on_click) 
        self.btnRemove.clicked.connect(self.btnRemove_on_click)
        
        self.table1.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table2.setEditTriggers(QTableWidget.NoEditTriggers)
        self.btnSearch.setEnabled(False)
        self.txtSearch.textChanged.connect(self.on_txtSearch_textChanged)
    

    def on_txtSearch_textChanged(self, text):
        text = text.strip()
        self.btnSearch.setEnabled(bool(text))

    def detect_best_description_column(self,df):
        first = df.iloc[0]
        lengths = {}
        for col in df.columns:
            val = str(first[col]) if col in df.columns else ""
            lengths[col] = len(val)
        return max(lengths, key=lengths.get)

    def btnSearch_on_click(self):
        search_text = self.txtSearch.text().strip()
        if not search_text:
            return

        gtfs_path = self.txtPathToGTFS.text().strip()
        filename = os.path.join(gtfs_path, "routes.txt")
        if not self.CheckFileExcludeRourtes(filename):
            return

        try:
            df = pd.read_csv(
                filename,
                encoding="utf-8-sig",
                sep=",",
                dtype=str,
                keep_default_na=False
            )

            required_cols = {"route_id", "route_short_name"}
            if not required_cols.issubset(df.columns):
                return

            # Автоматически выбираем колонку с самым длинным текстом
            best_desc_col = self.detect_best_description_column(df)

            # --- НОВЫЙ ПОИСК С НЕСКОЛЬКИМИ РАЗДЕЛИТЕЛЯМИ ---
            # Разделители: запятая, точка с запятой, пробелы
            parts = re.split(r"[,\s;]+", search_text)
            search_values = [p.strip().lower() for p in parts if p.strip()]

            # Фильтрация по точному совпадению (без учета регистра)
            mask = df["route_short_name"].str.lower().isin(search_values)

            df = df[mask].reset_index(drop=True)
            routes = df[["route_id", "route_short_name", best_desc_col]]

        except Exception as e:
            print("Error:", e)
            return

        # --- ОТОБРАЖЕНИЕ В ТАБЛИЦЕ ---
        self.table1.clear()
        self.table1.setColumnCount(3)
        self.table1.setHorizontalHeaderLabels(["ID", "Name", "Description"])
        self.table1.setRowCount(len(routes))

        for r, row in routes.iterrows():
            self.table1.setItem(r, 0, QTableWidgetItem(row["route_id"]))
            self.table1.setItem(r, 1, QTableWidgetItem(row["route_short_name"]))
            self.table1.setItem(r, 2, QTableWidgetItem(row[best_desc_col]))

        self.table1.setColumnHidden(0, True)
        self.table1.setSelectionBehavior(self.table1.SelectRows)
        self.table1.setWordWrap(True)
        self.table1.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        header = self.table1.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.table1.resizeRowsToContents()

    def CheckFileExcludeRourtes(self, file_path):
        """
        Checks if the file exists, is a file, and contains the required 'route_id' column.
        Returns (True, "") if valid, or (False, "error message") otherwise.
        """
        path = Path(file_path)
        
        # 1. Check if path exists
        if not path.exists():
            self.setMessage(f"File not found: {path.name}")
            return False
        
        # 2. Check if it's a file and not a directory
        if not path.is_file():
            self.setMessage(f"The provided path {file_path} is a directory, not a file")
            return False

        # 3. Check CSV content and headers
        try:
            # Using utf-8-sig to handle potential Byte Order Mark (BOM)
            with open(path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                
                if not headers:
                    self.setMessage(f"The file {path.name} is empty")
                    return False
                
                # Clean headers from whitespace and quotes
                headers = [h.strip().replace('"', '') for h in headers]
                
                if 'route_id' not in headers:
                    self.setMessage(f"Invalid GTFS format: 'route_id' column is missing in {path.name}")
                    return False
                    
        except UnicodeDecodeError:
            return False 
        except Exception as e:
            return False

        return True, ""

    def btnAdd_on_click(self):
        def is_route_in_table2(route_id):
            for r in range(self.table2.rowCount()):
                if self.table2.item(r, 0).text() == route_id:
                    return True
            return False

        row = self.table1.currentRow()
        if row < 0:
            return  # ничего не выбрано

        # читаем данные из table1
        route_id = self.table1.item(row, 0).text()
        name = self.table1.item(row, 1).text()
        desc = self.table1.item(row, 2).text()

        if is_route_in_table2(route_id): 
            return

        # добавляем строку в table2
        new_row = self.table2.rowCount()
        self.table2.insertRow(new_row)

        self.table2.setItem(new_row, 0, QTableWidgetItem(route_id))
        self.table2.setItem(new_row, 1, QTableWidgetItem(name))
        self.table2.setItem(new_row, 2, QTableWidgetItem(desc))
 
    def btnRemove_on_click(self):
        row = self.table2.currentRow()
        if row < 0:
            return

        # Отключаем сортировку, чтобы не было скачков
        sorting = self.table2.isSortingEnabled()
        self.table2.setSortingEnabled(False)

        # Удаляем строку
        self.table2.removeRow(row)
        print ("remove")

        # Возвращаем сортировку
        self.table2.setSortingEnabled(sorting)

        # Обновляем высоту строк
        self.table2.resizeRowsToContents()


    def init_table(self):

        self.table1.setColumnCount(3)
        self.table1.setHorizontalHeaderLabels(["ID", "Name", "Description"])
        self.table1.setColumnHidden(0, True)

        self.table1.setSelectionBehavior(self.table2.SelectRows)
        self.table1.setWordWrap(True)

        header = self.table1.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.table2.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)


        self.table2.setColumnCount(3)
        self.table2.setHorizontalHeaderLabels(["ID", "Name", "Description"])
        self.table2.setColumnHidden(0, True)

        self.table2.setSelectionBehavior(self.table2.SelectRows)
        self.table2.setWordWrap(True)

        header = self.table2.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.table2.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)


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
                else:
                    self.cmbLayers.addItem(file_path, file_path)
                    index = self.cmbLayers.findText(file_path)
                    self.cmbLayers.setCurrentIndex(index)

    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False
        
        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
            
        if self.txtAddRoutes.text():
            if not (self.CheckGtfsDirectory(self.txtAddRoutes.text())):
                self.run_button.setEnabled(True)
                return 0
            
        self.route_ids = self.get_route_ids_from_table2()     
        if not self.route_ids and not self.txtAddRoutes.text():
            self.run_button.setEnabled(True)
            self.setMessage("")
            return 0
        
        path = self.txtPathToProtocols.text().strip()
        if os.listdir(path):
            msgBox = QMessageBox() 
            msgBox.setIcon(QMessageBox.Question) 
            msgBox.setWindowTitle("Confirm") 
            msgBox.setText(f"The folder '{path}' already contains files. Overwrite?") 
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No) 
            result = msgBox.exec_() 
            if result == QMessageBox.No: 
                self.run_button.setEnabled(True)
                self.setMessage("")
                return False

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
        self.textLog.append(f"<a> The folder of the initial GTFS dataset: {self.config['Settings']['PathToGTFS_gtfs']}</a>")
        
        if self.route_ids:
            self.textLog.append(f"<a> Selected lines to delete from the GTFS dataset: {self.route_ids} </a>")
        if self.config['Settings']['AddLines_gtfs']:
            self.textLog.append(f"<a> The folder of the GTFS dataset of the additional lines: {self.config['Settings']['AddLines_gtfs']} </a>")
        self.textLog.append(f"<a> Folder to store modified dataset: {self.config['Settings']['PathToProtocols_gtfs']}</a>")

        self.prepare()
        if self.break_on:
            return 0
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):
        #current_dir = os.path.dirname(os.path.abspath(__file__))
        #module_path = os.path.join(current_dir, 'help', 'build', 'html')
        #file = os.path.join(module_path, 'building_pkl.html')
        #webbrowser.open(f'file:///{file}')
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/building_pkl.html#building-database-for-transit-accessibility"
        webbrowser.open(url)

    def showFoldersDialog(self, obj):

        print ('showFoldersDialog')
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", obj.text())
        if folder_path:
            obj.setText(os.path.normpath(folder_path))
            self.table1.clear() 
            self.table1.setRowCount(0) 
            self.table1.setColumnCount(0)
            self.table2.clear() 
            self.table2.setRowCount(0) 
            self.table2.setColumnCount(0)
            self.init_table()
            
        else:
            obj.setText(obj.text())
               

    def readParameters(self):
        project_path = QgsProject.instance().fileName()
        project_directory = os.path.dirname(project_path)
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        PathToProtocols_gtfs = os.path.join(project_directory, f'{project_name}_gtfs')
        PathToProtocols_gtfs = os.path.normpath(PathToProtocols_gtfs)

        documents_path = get_documents_path()
        
        file_path = os.path.join(
            project_directory, 'parameters_accessibility.txt')

        self.config.read(file_path)

        if 'PathToGTFS_gtfs' not in self.config['Settings'] or self.config['Settings']['PathToGTFS_gtfs'] == "C:/":
            self.config['Settings']['PathToGTFS_gtfs'] = documents_path

        if 'PathToProtocols_gtfs' not in self.config['Settings'] or self.config['Settings']['PathToProtocols_gtfs'] == "C:/":
            self.config['Settings']['PathToProtocols_gtfs'] = PathToProtocols_gtfs
        self.config['Settings']['PathToProtocols_gtfs'] = os.path.normpath(self.config['Settings']['PathToProtocols_gtfs'])
        
        if 'AddLines_gtfs' not in self.config['Settings']:
            self.config['Settings']['AddLines_gtfs'] = ""


    def saveParameters(self):

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config['Settings']['PathToProtocols_gtfs'] = self.txtPathToProtocols.text()
        self.config['Settings']['PathToGTFS_gtfs'] = self.txtPathToGTFS.text()
        self.config['Settings']['AddLines_gtfs'] = self.txtAddRoutes.text()


        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        self.readParameters()

        self.txtPathToGTFS.setText(os.path.normpath(self.config['Settings']['PathToGTFS_gtfs']))
        self.txtPathToProtocols.setText(os.path.normpath(self.config['Settings']['PathToProtocols_gtfs']))
        val = self.config['Settings']['AddLines_gtfs']
        self.txtAddRoutes.setText(os.path.normpath(val) if val else "")

    def CheckGtfsDirectory(self, directory_path):
        """
        Checks if the directory exists and contains valid mandatory GTFS files.
        Interrupts execution and sets an error message at the first sign of trouble.
        """
        
        path = Path(directory_path)
        
        # 1. Check if path exists and is a directory
        if not path.exists():
            self.setMessage(f"Directory {directory_path} not found")
            return False
        
        if not path.is_dir():
            self.setMessage(f"The provided path is not to a directory: {directory_path}")
            return False
        print ('test2') 
        # 2. Define mandatory files and their required key columns
        required_files = {
            "routes.txt": "route_id",
            "stops.txt": "stop_id",
            "stop_times.txt": "trip_id",
            "trips.txt": "trip_id"
             }

        # 3. Check each file one by one
        for filename, required_column in required_files.items():
            file_path = path / filename
            
            # Immediate exit if file is missing
            if not file_path.exists():
                self.setMessage(f"GTFS dataset validation in '{directory_path}' failed: Mandatory file '{filename}' is missing")
                return False
                
            try:
                with open(file_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    
                    # Immediate exit if file is empty
                    if not headers:
                        self.setMessage(f"GTFS validation in '{directory_path}' failed: File '{filename}' is empty")
                        return False
                    
                    # Clean headers
                    headers = [h.strip().replace('"', '') for h in headers]
                    
                    # Immediate exit if required column is missing
                    if required_column not in headers:
                        self.setMessage(f"GTFS validation in '{directory_path}' failed: Field '{required_column}' is missing in the {filename} file")
                        return False
                        
            except Exception as e:
                print(f"GTFS validation in '{directory_path}' failed: Error reading {filename}")
                return False
            
            
        
        return True

    def check_folder_and_file(self):

        path = self.txtPathToProtocols.text()
        
        if not os.path.exists(self.txtPathToGTFS.text()):
            self.setMessage(f"Folder '{self.txtPathToGTFS.text()}' does not exist")
            return False

        required_files = ['stops.txt', 'trips.txt',
                          'routes.txt', 'stop_times.txt']
        missing_files = [file for file in required_files if not os.path.isfile(
            os.path.join(self.txtPathToGTFS.text(), file))]

        if missing_files:
            limited_files = missing_files[:2]
            missing_files_message = ", ".join(limited_files)
            self.setMessage(f"Files are missing in the '{self.txtPathToGTFS.text()}' forlder: {missing_files_message}")
            return False

        os.makedirs(path, exist_ok=True)
            
        try:
            tmp_prefix = "write_tester"
            filename = f'{path}//{tmp_prefix}'
            with open(filename, 'w') as f:
                f.write("test")
            os.remove(filename)
        except Exception as e:
            self.setMessage(f"Access to the folder '{path}' is denied")
            return False

        

        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def get_route_ids_from_table2(self):
        ids = []
        for row in range(self.table2.rowCount()):
            item = self.table2.item(row, 0)   # колонка 0 = route_id
            if item:
                ids.append(item.text())
        return ids


    def prepare(self):
        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

        self.break_on = False
        
        QApplication.processEvents()
        
        path_to_GTFS = self.config['Settings']['PathToGTFS_gtfs']
        path_to_GTFS_mod = self.config['Settings']['PathToProtocols_gtfs']
        run_ok = True

        route_ids = self.get_route_ids_from_table2() 


        if route_ids:
            self.setMessage(f'Deleting lines ...')
            QApplication.processEvents()
            out1 = os.path.join(self.config['Settings']['PathToProtocols_gtfs'], 'GTFS_DeleteLinesOK')
            out2 = os.path.join(self.config['Settings']['PathToProtocols_gtfs'], 'GTFS_DeletedLines')
            cleaner = GTFSExcludeRoutes(gtfs_path = path_to_GTFS, 
                                        #exclude_file_path = self.txtExcludeRoutes.text(), 
                                        exclude_ids_list = route_ids,
                                        output_path = out1,
                                        excluded_data_path = out2)
            run_ok = cleaner.run()
            path_to_GTFS = out1
            

        
        if run_ok and self.txtAddRoutes.text():

            self.setMessage(f'Adding lines ...')
            QApplication.processEvents()
            
            out = os.path.join(self.config['Settings']['PathToProtocols_gtfs'], 'GTFS_AddLinesOK')
            cleaner = GTFSAddRoutes(gtfs_path1 = path_to_GTFS, 
                                    gtfs_path2 = self.txtAddRoutes.text(), 
                                    output_path = out)
            run_ok = cleaner.run()
            path_to_GTFS = out

        if run_ok:
            shutil.copytree(path_to_GTFS, path_to_GTFS_mod, dirs_exist_ok=True)

        

        QApplication.processEvents()
        if self.break_on:
                return 0
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
                '%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(
        duration_computation).split('.')[0]
        self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

        text = self.textLog.toPlainText()
        postfix = getDateTime()
            
        filelog_name = os.path.join(path_to_GTFS_mod, f'log_gtfs_pt_{postfix}.txt')
        with open(filelog_name, "w") as file:
                file.write(text)

        if run_ok :
                self.textLog.append(f'<a href="file:///{path_to_GTFS_mod}" target="_blank" >gtfs in folder</a>')

                self.setMessage(f'Finished')

        if not (run_ok):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

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
        help_filename = "transit_db.txt"
            
        hlp_file = os.path.join(hlp_directory, help_filename)
        hlp_file = os.path.normpath(hlp_file)
        self.load_text_with_bold_first_line (hlp_file)

    def closeEvent(self, event):
        self.break_on = True
        event.accept()
