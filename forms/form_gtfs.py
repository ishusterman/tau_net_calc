import os
import webbrowser
import configparser
import csv
from pathlib import Path
import pandas as pd
import re
from qgis.PyQt.QtCore import Qt, QTimer, QEvent                         
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import (QDialogButtonBox,
                            QDialog,
                            QFileDialog,
                            QApplication,
                            QMessageBox,
                            QAbstractItemView,
                            QTableWidget,
                            QTableWidgetItem,
                            QHeaderView
                            )
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt import uic

from datetime import datetime
from tau_net_calc.cls.gtfs_exclude_routes import GTFSExcludeRoutes
from tau_net_calc.cls.gtfs_add_routes import GTFSAddRoutes

from tau_net_calc.cls.common import (get_qgis_info, 
                    getDateTime, 
                    check_file_parameters_accessibility, 
                    get_documents_path,
                    get_gtfs_date_range,
                    transform_log_to_csv_text,
                    highlight_empty_fields,
                    highlight_widget,
                    setup_clear_highlight_listeners
                    )

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), '..', 'UI', 'gtfs.ui')
)

class form_gtfs(QDialog, FORM_CLASS):
    def __init__(self, title, mode):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setupUi(self)
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)

        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()
        self.setWindowTitle(title)

        self.splitter.setSizes(
            [int(self.width() * 0.7), int(self.width() * 0.3)])
       
        self.tabWidget.setCurrentIndex(0)
        self.config = configparser.ConfigParser()
        self.break_on = False
        self.title = title
        self.mode = mode
        self.progressBar.setValue(0)
        self.textLog.setOpenLinks(False)
        self.textLog.anchorClicked.connect(self.openFolder)

        self.toolButton_GTFS.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToGTFS))
        self.toolButton_protocol.clicked.connect(
            lambda: self.showFoldersDialog(self.txtPathToProtocols))
        
        self.toolButtonAddRoutes.clicked.connect(
            lambda: self.showFoldersDialog(self.txtAddRoutes))

        self.break_on = False
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
        
        self.ParametrsShow()
        self.show_info()
        
        self.table1.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table2.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.btnSearch.setText("Apply")
        self.btnSearch.clicked.connect(self.btnSearch_on_click)
        
        self.btnAdd.clicked.connect(self.btnAdd_on_click) 
        self.btnRemove.clicked.connect(self.btnRemove_on_click)

        self.table1.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table2.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    
        self.txtPathToGTFS.textChanged.connect(self.on_PathToGTFS_changed)

        self.txtAddRoutes.textChanged.connect(self.on_txtAddRoutes_changed)
        self.InitTable1()
        self.InitTable2()
        self.UpdateTable1(show_all=True)

        if self.mode == 2:
            self.txtAddRoutes.hide() 
            self.toolButtonAddRoutes.hide() 
            self.lblAddLines.hide()
            parent_layout = self.horizontalLayout_11.parent()
            parent_layout.removeItem(self.horizontalLayout_11)

            self.lblNumbers.setText('List of lines’ route_id to delete (comma separated)')
        
        else:
            self.lblNumbers.setText('List of lines’ route_id to add (comma separated)')

        self.progressBar.setMaximum(5)

        setup_clear_highlight_listeners(self)

    
    def on_PathToGTFS_changed (self):
        if self.mode == 2:
            self.InitTable1()      
            self.InitTable2()      
        self.UpdateTable1(show_all=True)

    def on_txtAddRoutes_changed (self):
        
        self.InitTable1()      
        self.InitTable2()      
        self.UpdateTable1(show_all=True)

  
            
    def detect_best_description_column(self,df):
        first = df.iloc[0]
        lengths = {}
        for col in df.columns:
            val = str(first[col]) if col in df.columns else ""
            lengths[col] = len(val)
        return max(lengths, key=lengths.get)
    
    def UpdateTable1(self, show_all=True):

        self.InitTable1()

        # --- Определяем путь к GTFS --- txtPathToGTFS vs txtAddRoutes
        gtfs_path = (self.txtPathToGTFS.text().strip() if self.mode == 2 else self.txtAddRoutes.text().strip())

        if self.CheckGtfsDirectory(gtfs_path):
            search_enable = True
        else:
            search_enable = False

        self.txtSearch.setEnabled(search_enable)
        self.btnSearch.setEnabled(search_enable)
        self.layout_tables.setEnabled(search_enable)

        if not search_enable:
            return

        filename = os.path.join(gtfs_path, "routes.txt")
      
        # --- Загружаем routes.txt ---
        try:
            df = pd.read_csv(
                filename,
                encoding="utf-8-sig",
                sep=",",
                dtype=str,
                keep_default_na=False
            )

            if "route_id" not in df.columns:
                return

            # Определяем лучшую колонку описания
            best_desc_col = self.detect_best_description_column(df)

            routes = df.loc[:, ["route_id", best_desc_col]].copy()
            routes = routes.reset_index(drop=True)

        except Exception as e:
            print("Error:", e)
            return

        # --- Отображение в левой таблице ---
        self.InitTable1()
        self.table1.setRowCount(len(routes))
        for i, (_, row) in enumerate(routes.iterrows()):
            self.table1.setItem(i, 0, QTableWidgetItem(str(row["route_id"])))
            self.table1.setItem(i, 1, QTableWidgetItem(str(row["route_id"])))
            self.table1.setItem(i, 2, QTableWidgetItem(str(row[best_desc_col])))
            
        QTimer.singleShot(0, self.adjust_table1_rows) 
    
    def adjust_table1_rows(self): 
        for row in range(self.table1.rowCount()): 
            self.table1.resizeRowToContents(row)  

    def btnSearch_on_click(self):
        search_text = self.txtSearch.text().strip()
        if not search_text:
            return

        parts = re.split(r"[,\s;]+", search_text)
        search_values = {p.lower() for p in parts if p.strip()}
        if not search_values:
            return

        def is_route_in_table2(route_id):
            for r in range(self.table2.rowCount()):
                item = self.table2.item(r, 0)
                if item and item.text() == route_id:
                    return True
            return False

        # Ищем совпадения в левой таблице (не изменяя её) и сразу добавляем в правую
        for row in range(self.table1.rowCount()):
            item_id = self.table1.item(row, 0)
            if not item_id:
                continue
            route_id = item_id.text()

            if route_id.lower() in search_values:
                if is_route_in_table2(route_id):
                    continue

                name = self.table1.item(row, 1).text()
                desc = self.table1.item(row, 2).text()

                new_row = self.table2.rowCount()
                self.table2.insertRow(new_row)

                self.table2.setItem(new_row, 0, QTableWidgetItem(route_id))
                self.table2.setItem(new_row, 1, QTableWidgetItem(name))
                self.table2.setItem(new_row, 2, QTableWidgetItem(desc))

        QTimer.singleShot(0, lambda: self.adjust_rows_height(self.table2))
                

    def btnAdd_on_click(self):

        def is_route_in_table2(route_id):
            for r in range(self.table2.rowCount()):
                if self.table2.item(r, 0).text() == route_id:
                    return True
            return False

        # получаем ВСЕ выделенные строки
        selected_rows = sorted(set(idx.row() for idx in self.table1.selectedIndexes()))

        if not selected_rows:
            return

        for row in selected_rows:
            route_id = self.table1.item(row, 0).text()
            name = self.table1.item(row, 1).text()
            desc = self.table1.item(row, 2).text()

            if is_route_in_table2(route_id):
                continue

            new_row = self.table2.rowCount()
            self.table2.insertRow(new_row)

            self.table2.setItem(new_row, 0, QTableWidgetItem(route_id))
            self.table2.setItem(new_row, 1, QTableWidgetItem(name))
            self.table2.setItem(new_row, 2, QTableWidgetItem(desc))
        
        #self.table2.resizeRowsToContents()

        QTimer.singleShot(0, lambda: self.adjust_rows_height(self.table2))

    def adjust_rows_height(self, table):
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)    
 
    def btnRemove_on_click(self):

        selected_rows = sorted(
            set(idx.row() for idx in self.table2.selectedIndexes()),
            reverse=True
        )
        if not selected_rows:
            return
        sorting = self.table2.isSortingEnabled()
        self.table2.setSortingEnabled(False)
        for row in selected_rows:
            self.table2.removeRow(row)
        self.table2.setSortingEnabled(sorting)
        self.table2.resizeRowsToContents()


    def apply_table_style(self, table):
        
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        table.setWordWrap(True)
        table.setColumnHidden(0, True) # Прячем внутренний ID (колонка 0), колонка 1 отображает route_id
        
        header = table.horizontalHeader()
        resize_to_contents = QHeaderView.ResizeMode.ResizeToContents
        stretch_mode = QHeaderView.ResizeMode.Stretch
        header.setSectionResizeMode(0, resize_to_contents)
        header.setSectionResizeMode(1, resize_to_contents)
        header.setSectionResizeMode(2, stretch_mode)

    def InitTable1(self):
        self.table1.clear()
        self.table1.setRowCount(0)
        self.table1.setColumnCount(3)
        self.table1.setHorizontalHeaderLabels(["ID", "route_id", "Description"])
        self.apply_table_style(self.table1)
        
    def InitTable2(self):
        self.table2.clear()
        self.table2.setRowCount(0)
        self.table2.setColumnCount(3)
        self.table2.setHorizontalHeaderLabels(["ID", "route_id", "Description"])
        self.table2.setColumnHidden(0, True)        

        self.table2.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.table2.setWordWrap(True)
        header = self.table2.horizontalHeader()

        resize_to_contents = QHeaderView.ResizeMode.ResizeToContents
        stretch_mode = QHeaderView.ResizeMode.Stretch

        header.setSectionResizeMode(0, resize_to_contents)
        header.setSectionResizeMode(1, resize_to_contents)
        header.setSectionResizeMode(2, stretch_mode)

        
    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)

    def on_run_button_clicked(self):

        self.run_button.setEnabled(False)
        self.break_on = False

        if highlight_empty_fields(self, exclude=[self.textLog, self.txtSearch]):
            self.setMessage("All required fields must be filled in")        
            self.run_button.setEnabled(True)
            return 0

        if not (self.CheckGtfsDirectory(self.txtPathToGTFS.text())):
            self.run_button.setEnabled(True)
            return 0
        
        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0

        if self.mode == 1:    
            if self.txtAddRoutes.text():
                if not (self.CheckGtfsDirectory(self.txtAddRoutes.text())):
                    self.run_button.setEnabled(True)
                    return 0
            else:
                self.run_button.setEnabled(True)
                return 0 
            
        self.route_ids = self.get_route_ids_from_table2()     
        if not self.route_ids: #and not self.txtAddRoutes.text():
            self.run_button.setEnabled(True)
            self.setMessage("")
            return 0
        
        path = self.txtPathToProtocols.text().strip()
        if os.listdir(path):
            msgBox = QMessageBox()
            icon_question = QMessageBox.Icon.Question
            btn_yes = QMessageBox.StandardButton.Yes
            btn_no = QMessageBox.StandardButton.No            

            msgBox.setIcon(icon_question) 
            msgBox.setWindowTitle("Confirm") 
            msgBox.setText(f"The folder '{path}' already contains files. Overwrite?") 
            msgBox.setStandardButtons(btn_yes | btn_no) 
            result = msgBox.exec() 
            if result == btn_no: 
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
        self.textLog.append(f"<a> GTFS dataset folder: {self.config['Settings']['PathToGTFS_gtfs']}</a>")        
        
        if self.mode == 2:
            self.textLog.append(f"<a> Delete lines from GTFS: {self.route_ids} </a>")
        else: 
            self.textLog.append(f"<a> Add lines to GTFS: {self.route_ids} </a>")
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
        if self.mode == 1:
            url = "https://geosimlab.github.io/accessibility-calculator-tutorial/prepare_database.html#add-lines-to-gtfs"
        else:
            url = "https://geosimlab.github.io/accessibility-calculator-tutorial/prepare_database.html#delete-lines-from-gtfs"

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
        self.setMessage("")
        if not path.exists():
            self.setMessage(f"Directory {directory_path} not found")
            return False
        
        if not path.is_dir():
            self.setMessage(f"The provided path is not to a directory: {directory_path}")
            return False
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
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            self.run_button.setEnabled(True)
            highlight_widget(self.txtPathToProtocols)              
            self.setMessage(f'The path {path} is not found')
            return 0
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

        if self.mode == 2:

            if route_ids:
                self.setMessage(f'Deleting lines form GTFS ...')
                QApplication.processEvents()
                out1 = path_to_GTFS_mod #os.path.join(self.config['Settings']['PathToProtocols_gtfs'], 'GTFS_DeleteLinesOK')
                out2 = os.path.join(self.config['Settings']['PathToProtocols_gtfs'], 'GTFS_DeletedLines')
                cleaner = GTFSExcludeRoutes(parent = self,
                                            gtfs_path = path_to_GTFS, 
                                            #exclude_file_path = self.txtExcludeRoutes.text(), 
                                            exclude_ids_list = route_ids,
                                            output_path = out1,
                                            excluded_data_path = out2)
                run_ok = cleaner.run()
                path_to_GTFS = out1            

        if self.mode == 1:
            if run_ok and self.txtAddRoutes.text():

                self.setMessage(f'Adding lines to GTFS ...')
                QApplication.processEvents()
                
                out = path_to_GTFS_mod 
                                
                min_str, max_str, _ = get_gtfs_date_range(self.txtPathToGTFS.text())
                gtfs_add = GTFSAddRoutes(parent = self,
                                            gtfs_path1 = path_to_GTFS, 
                                            gtfs_path2= self.txtAddRoutes.text(), 
                                            output_path = out, 
                                            routes_to_add = route_ids, 
                                            start_date = min_str, 
                                            end_date =  max_str)


                run_ok = gtfs_add.run()
                path_to_GTFS = out

        #if run_ok:
        #    shutil.copytree(path_to_GTFS, path_to_GTFS_mod, dirs_exist_ok=True)
       
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

        text = transform_log_to_csv_text(self.textLog.toPlainText())
        postfix = getDateTime()
            
        filelog_name = os.path.join(path_to_GTFS_mod, f'log_gtfs_pt_{postfix}.csv')
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
        wheel_type = QEvent.Type.Wheel

        if event.type() == wheel_type:
            if obj.hasFocus():
                event.ignore()
                return True

        return super().eventFilter(obj, event)
        
    def show_info(self):

        hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')
        if self.mode == 1:
            help_filename = "add_lines.txt"
        else:
            help_filename = "delete_lines.txt"
        hlp_file = os.path.join(hlp_directory, help_filename)

        if os.path.exists(hlp_file):
            with open(hlp_file, 'r', encoding='utf-8') as f:
                html = f.read()

        self.textInfo.setOpenExternalLinks(False)  
        self.textInfo.setOpenLinks(False)          
        self.textInfo.setHtml(html)
        self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))  

    def closeEvent(self, event):
        self.break_on = True
        event.accept()