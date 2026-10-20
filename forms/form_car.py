import os
import webbrowser
from datetime import datetime
import configparser
import math
from math import floor
from pathlib import Path

from qgis.core import (QgsProject, 
                       QgsMapLayerProxyModel,
                       )                       
                       
from qgis.PyQt.QtWidgets import (
                        QDialogButtonBox,
                        QDialog,
                        QFileDialog,
                        QApplication,
                        QMessageBox                        
                    )

from qgis.PyQt.QtCore import (Qt,                          
                          QEvent,
                          QVariant,
                          QTime,
                          QDate, 
                          QDateTime,
                          QTimer                          
                          )

from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt import uic

shift_mod = Qt.KeyboardModifier.ShiftModifier
role_checkstate = Qt.ItemDataRole.CheckStateRole
checked = Qt.CheckState.Checked
unchecked = Qt.CheckState.Unchecked

try:
    # QGIS 3
    from qgis.PyQt.QtCore import QRegExp
    from qgis.PyQt.QtGui import QRegExpValidator
    RegExpClass = QRegExp
    RegExpValidatorClass = QRegExpValidator
except ImportError:
    # QGIS 4
    from qgis.PyQt.QtCore import QRegularExpression
    from qgis.PyQt.QtGui import QRegularExpressionValidator
    RegExpClass = QRegularExpression
    RegExpValidatorClass = QRegularExpressionValidator

from tau_net_calc.cls.car import car_accessibility
from tau_net_calc.cls.pkl_car import pkl_car
from tau_net_calc.cls.common import (get_qgis_info,                     
                    get_prefix_alias, 
                    check_file_parameters_accessibility,
                    get_initial_directory,
                    time_to_seconds,
                    seconds_to_time,
                    get_name_columns,
                    FIELD_ID,
                    check_layer,
                    transform_log_to_dataframe,
                    fast_write_gpkg,
                    getDateTime,
                    transform_log_to_csv_text,
                    highlight_empty_fields,
                    highlight_widget,
                    highlight_widget_no,
                    get_tablename,
                    get_ids_from_voronoi,
                    get_ids_from_layer,
                    check_ids_match,
                    setup_clear_highlight_listeners,
                    install_parent_folder_dialog
                    )

from tau_net_calc.cls.AnalyzerFromTo_incremental import roundtrip_analyzer
from tau_net_calc.cls.visualization import visualization

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), '..', 'UI', 'car.ui'))

from qgis.PyQt.QtWidgets import QLabel
from qgis.PyQt.QtCore import QPoint
from qgis.PyQt.QtGui import QPainter, QColor, QPolygon, QPen

class CalloutBubble(QLabel):
    """Неисчезающее желтое облачко с хвостиком, которое закрывается только программно."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tail_height = 8
        self.tail_x = 20  
        self.setContentsMargins(10, 6, 10, 6 + self.tail_height)
        self.setStyleSheet("color: #856404; font-weight: bold; background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor("#FFF3CD")     
        border_color = QColor("#E0A800") 

        rect = self.rect().adjusted(1, 1, -1, -self.tail_height - 1)

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, 6, 6)

        tail_x = max(14, min(self.width() - 14, self.tail_x))
        points = QPolygon([
            QPoint(tail_x - 6, rect.bottom()),
            QPoint(tail_x + 6, rect.bottom()),
            QPoint(tail_x, rect.bottom() + self.tail_height)
        ])

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(points)
        painter.setPen(QPen(border_color, 1))
        painter.drawLine(points[0], points[2])
        painter.drawLine(points[1], points[2])

        super().paintEvent(event)

class CarAccessibility(QDialog, FORM_CLASS):
    def __init__(self,
                 mode,
                 protocol_type,
                 title,
                 roundtrip = False
                 ):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setupUi(self)
        
        # Сначала создаем вкладку параметров и облачка, ДО вызова changeInterface()
        self.param_tab = self.tabWidget.widget(0)
        self.bubbleTimeBack = CalloutBubble(self.param_tab)
        self.bubbleTimeOrder = CalloutBubble(self.param_tab)

        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)

        self.user_home = os.path.expanduser("~")
        check_file_parameters_accessibility()

        self.setWindowTitle(title)

        if protocol_type == 2:
            self.resize(self.width() - 100, self.height())

        self.splitter.setSizes([int(self.width() * 0.75), int(self.width() * 0.25)])

        fm = self.txtTimeInterval.fontMetrics()
        
        char_width = fm.horizontalAdvance("x")

        fix_size  = 15 * char_width
        fix_size2 = 5  * char_width
        fix_size4 = 20 * char_width

        self.txtTimeInterval.setFixedWidth(fix_size2)

        self.txtWalkToCAR.setFixedWidth(fix_size2)
        self.txtWalkToDestination.setFixedWidth(fix_size2)        
        self.txtWalkingSpeed.setFixedWidth(fix_size2)
        self.txtMinimalDistance.setFixedWidth(fix_size2)
        self.txtMaxTimeTravel.setFixedWidth(fix_size2)
        self.txtImbalance.setFixedWidth(fix_size2)
        self.txtTimeBack.setFixedWidth(fix_size2)

        self.dtStartTime.setFixedWidth(fix_size)
        self.cmbFields_ch.setFixedWidth(fix_size4)
        
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

        self.cmbLayers.installEventFilter(self)
        self.cmbLayersDest.installEventFilter(self)        

        self.cmbLayers.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer|QgsMapLayerProxyModel.Filter.PointLayer)
        self.cmbLayersDest.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer|QgsMapLayerProxyModel.Filter.PointLayer)
        
        self.dtStartTime.installEventFilter(self)

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

        regex3 = RegExpClass(r"^\d+(\.\d{1,2})?$")
        int_validator3 = RegExpValidatorClass(regex3)

        regex4 = RegExpClass(r"^([1-9]|[1-5][0-9]|60)$")
        int_validator4 = RegExpValidatorClass(regex4)

        self.txtMaxTimeTravel.setValidator(int_validator3)
        self.txtTimeInterval.setValidator(int_validator4)
        self.txtImbalance.setValidator(int_validator3)

        self.txtWalkToCAR.setValidator(int_validator3)
        self.txtWalkToDestination.setValidator(int_validator3)
        self.txtWalkingSpeed.setValidator(int_validator3)
        self.txtMinimalDistance.setValidator(int_validator3) 

        regex1 = RegExpClass(r"\d*")
        int_validator1 = RegExpValidatorClass(regex1)
        self.txtTimeBack.setValidator(int_validator1)     
          
        self.ParametrsShow()
        self.cmbLayers.currentIndexChanged.connect(self.onLayerDestChanged)
        self.cmbLayersDest.currentIndexChanged.connect(self.onLayerDestChanged)

        if self.protocol_type == 1:            
            self.onLayerDestChanged()

        if self.protocol_type == 2:
            self.txtTimeInterval.setVisible(False)
            self.lblTimeInterval.setVisible(False)
            self.lblTimeInterval2.setVisible(False)
            self.cmbFields_ch.setVisible(False)
            self.lblFields.setVisible(False)            
        
        self.show_info()
        
        regex = RegExpClass(r"\d*")
        int_validator = RegExpValidatorClass(regex)
        
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
        self.fix_size2 = 7 * char_width
        self.txtRountrip_timedelta1.setFixedWidth(self.fix_size2)
        self.txtRountrip_timedelta2.setFixedWidth(self.fix_size2)
        self.txtMaxTimeTravel.setFixedWidth(self.fix_size2)        
        self.txtTimeBack.setFixedWidth(self.fix_size2)
        
        self.dict_building_vertex = {} 
        self.dict_vertex_buildings = {}

        self.rbFrom.toggled.connect(self.on_radio_button_changed)
        self.rbTo.toggled.connect(self.on_radio_button_changed)
        self.rbRound.toggled.connect(self.on_radio_button_changed)
        self.changeInterface()        

        self.dtRoundtripStartTime1.timeChanged.connect(lambda: self.update_timedelta(1))
        self.dtRoundtripStartTime2.timeChanged.connect(lambda: self.update_timedelta(1))
        self.dtRoundtripStartTime3.timeChanged.connect(lambda: self.update_timedelta(2))
        self.dtRoundtripStartTime4.timeChanged.connect(lambda: self.update_timedelta(2))

        # Подключаем фильтры событий и сигналы для облачков и проверок
        self.txtTimeBack.installEventFilter(self)

        self.txtTimeBack.textChanged.connect(self.check_time_back)
        self.dtRoundtripStartTime1.timeChanged.connect(self.check_time_back)
        self.dtRoundtripStartTime4.timeChanged.connect(self.check_time_back)

        self.dtRoundtripStartTime1.timeChanged.connect(self.check_time_order)
        self.dtRoundtripStartTime3.timeChanged.connect(self.check_time_order)

        self.splitter.splitterMoved.connect(lambda: self.update_bubble_position())

        self.tabWidget.currentChanged.connect(
            lambda idx: (
                self.bubbleTimeBack.setVisible(idx == 0 and not self.check_time_back()),
                self.bubbleTimeOrder.setVisible(idx == 0 and not self.check_time_order())
            )
        )

        self.wgFileSave.setFilter("GeoPackage (*.gpkg)")

        setup_clear_highlight_listeners(self)

        QTimer.singleShot(
                            0,
                            lambda: setattr(
                                self,
                                "_pkl_filter",
                                install_parent_folder_dialog(self.wgPathPKL)
                            )
                        )
        
        self.wgFileSave.lineEdit().setReadOnly(True)

    def update_bubble_position(self):
        if hasattr(self, 'bubbleTimeBack') and self.bubbleTimeBack.isVisible():
            pos = self.txtTimeBack.mapTo(self.param_tab, QPoint(0, 0))
            target_center_x = pos.x() + (self.txtTimeBack.width() // 2)
            bubble_w = self.bubbleTimeBack.width()
            parent_w = self.param_tab.width()
            x = min(target_center_x - 20, parent_w - bubble_w - 8)
            x = max(8, x)
            y = pos.y() - self.bubbleTimeBack.height() - 2
            self.bubbleTimeBack.tail_x = target_center_x - x
            self.bubbleTimeBack.move(x, max(0, y))
            self.bubbleTimeBack.update()
            self.bubbleTimeBack.raise_()

        if hasattr(self, 'bubbleTimeOrder') and self.bubbleTimeOrder.isVisible():
            pos = self.dtRoundtripStartTime3.mapTo(self.param_tab, QPoint(0, 0))
            target_center_x = pos.x() + (self.dtRoundtripStartTime3.width() // 2)
            bubble_w = self.bubbleTimeOrder.width()
            parent_w = self.param_tab.width()
            x = min(target_center_x - 20, parent_w - bubble_w - 8)
            x = max(8, x)
            y = pos.y() - self.bubbleTimeOrder.height() - 2
            self.bubbleTimeOrder.tail_x = target_center_x - x
            self.bubbleTimeOrder.move(x, max(0, y))
            self.bubbleTimeOrder.update()
            self.bubbleTimeOrder.raise_()

    def check_time_order(self):
        if not self.roundtrip:
            self.dtRoundtripStartTime3.setStyleSheet("")
            if hasattr(self, 'bubbleTimeOrder'):
                self.bubbleTimeOrder.hide()
            return True

        arrival_sec = self.dtRoundtripStartTime1.time().msecsSinceStartOfDay() // 1000
        back_start_sec = self.dtRoundtripStartTime3.time().msecsSinceStartOfDay() // 1000

        if back_start_sec <= arrival_sec:
            warning_text = "Trip back start must be later than arrival time"
            self.dtRoundtripStartTime3.setStyleSheet("background-color: #FFFF99;")
            self.bubbleTimeOrder.setText(warning_text)
            self.bubbleTimeOrder.adjustSize()
            self.bubbleTimeOrder.show()
            self.update_bubble_position()
            return False
        else:
            self.dtRoundtripStartTime3.setStyleSheet("")
            self.bubbleTimeOrder.hide()
            return True

    def check_time_back(self):
        if not self.roundtrip:
            self.txtTimeBack.setStyleSheet("")
            if hasattr(self, 'bubbleTimeBack'):
                self.bubbleTimeBack.hide()
            return True

        text_val = self.txtTimeBack.text().strip()
        if not text_val:
            self.txtTimeBack.setStyleSheet("")
            if hasattr(self, 'bubbleTimeBack'):
                self.bubbleTimeBack.hide()
            return True

        try:
            time_back_min = int(text_val)
        except ValueError:
            return False

        earliest_arrival_sec = self.dtRoundtripStartTime1.time().msecsSinceStartOfDay() // 1000
        latest_back_sec = self.dtRoundtripStartTime4.time().msecsSinceStartOfDay() // 1000

        max_allowed_min = (latest_back_sec - earliest_arrival_sec) // 60 - 30

        if time_back_min > max_allowed_min:
            warning_text = f"Cannot exceed {max_allowed_min} minutes, see tutorial"
            self.txtTimeBack.setStyleSheet("background-color: #FFFF99;")
            self.bubbleTimeBack.setText(warning_text)
            self.bubbleTimeBack.adjustSize()
            self.bubbleTimeBack.show()
            self.update_bubble_position()
            return False
        else:
            self.txtTimeBack.setStyleSheet("")
            self.bubbleTimeBack.hide()
            return True

    def move_fields_combo_to_origin(self, to_origin_layout: bool):
        # 1. Удаляем cmbFields_ch из текущего layout
        parent_layout = self.cmbFields_ch.parentWidget().layout()
        parent_layout.removeWidget(self.cmbFields_ch)
        parent_layout.removeWidget(self.lblFields)        

        # 2. Добавляем в нужный layout
        if to_origin_layout:
            self.horizontalLayout_25.addWidget(self.lblFields)
            self.horizontalLayout_25.addWidget(self.cmbFields_ch)             
        else:
            self.horizontalLayout_26.addWidget(self.lblFields)
            self.horizontalLayout_26.addWidget(self.cmbFields_ch)

    def update_timedelta(self, pair_index):
        if pair_index == 1:
            t1, t2 = self.dtRoundtripStartTime1, self.dtRoundtripStartTime2
            output_field = self.txtRountrip_timedelta1
        else:
            t1, t2 = self.dtRoundtripStartTime3, self.dtRoundtripStartTime4
            output_field = self.txtRountrip_timedelta2
        seconds_1 = t1.time().msecsSinceStartOfDay() // 1000
        seconds_2 = t2.time().msecsSinceStartOfDay() // 1000
        # 300 сек (5 мин) за каждый час, но не более 900 сек (15 мин)
        duration_hours = math.ceil((seconds_2 - seconds_1) / 3600)
        time_delta_sec = min(900, duration_hours * 300)
               
        time_delta_min = round(time_delta_sec / 60)
        output_field.setText(str(abs(time_delta_min)))

    def on_radio_button_changed(self):
        sender = self.sender()
        if not sender.isChecked():
            return

        if sender is self.rbFrom:
            self.mode = 1
            self.roundtrip = False
        elif sender is self.rbTo:
            self.mode = 2
            self.roundtrip = False
        elif sender is self.rbRound:
            self.mode = 2
            self.roundtrip = True

        self.changeInterface()
        self.onLayerDestChanged()

    def changeInterface (self):
        if self.mode == 1:
            self.lblStartTime.setText("Start from the origin at (hh:mm:ss)")
        if self.mode == 2:
            self.lblStartTime.setText("Arrive to destination at (hh:mm:ss)")
            
        widgets_to_hide = [
            # Первая строка (Arrive to destination)
            self.lblRoundtrip1,
            self.spacer_roundtrip1,
            self.rightContainer1,

            # Вторая строка (Start trip back)
            self.lblRoundtrip6,
            self.spacer_roundtrip2,
            self.rightContainer2,

            # Параметры Roundtrip внизу
            self.lblImbalance,
            self.txtImbalance,
            self.lblMinTimeTripBack,
            self.widget_2,
            self.txtTimeBack,
            self.lblMinGap
        ]
         
        for widget in widgets_to_hide:
                widget.setVisible(self.roundtrip)

        # remove item time start
        self.lblStartTime.setVisible(not self.roundtrip)
        self.dtStartTime.setVisible(not self.roundtrip)

        prefix = get_prefix_alias(False, 
                                self.protocol_type, 
                                self.mode,
                                False,                                
                                self.roundtrip 
                                )
        self.default_alias = f'{prefix}_{getDateTime()}'
                
        self.wgFileSave.setFilePath(os.path.join(os.path.dirname(self.wgFileSave.filePath()), f"{self.default_alias}.gpkg"))
        to_origin = (self.mode == 2) or self.roundtrip
        self.move_fields_combo_to_origin(to_origin)
        
        if hasattr(self, 'bubbleTimeBack'):
            self.check_time_back()
            self.check_time_order()
                
    def onLayerDestChanged(self):
        sender = self.sender()
        origin = self.mode == 2 or self.roundtrip

        if self.roundtrip:
            sender == self.cmbLayers

        if sender == self.cmbLayers and not origin:
            return
        
        if sender == self.cmbLayersDest and origin:
            return

        self.cmbFields_ch.clear()
        
        if self.mode == 1:
            layer = self.cmbLayersDest.currentLayer()
        else:
            layer = self.cmbLayers.currentLayer()
        if self.roundtrip:
            layer = self.cmbLayers.currentLayer()

        if not layer:
            return 0

        try:
            fields = [field for field in layer.fields()]
        except Exception:
            return 0
        
        for field in fields:
            field_type = field.type()
            field_name = field.name()
            
            if field_type in (QVariant.Int, QVariant.Double, QVariant.LongLong):
                if field_name.lower() not in ("fid", "osm_id", "id", "aid"):
                    self.cmbFields_ch.addItem(field_name)

        if QApplication.keyboardModifiers() & shift_mod:
            if 'Field_ch_car' not in self.config['Settings']:
                self.config['Settings']['Field_ch_car'] = ''

            for i in range(self.cmbFields_ch.count()):
                item_text = self.cmbFields_ch.itemText(i)
                if item_text in self.config['Settings']['Field_ch_car']:
                    self.cmbFields_ch.setItemData(i, checked, role=role_checkstate)
                else:
                    self.cmbFields_ch.setItemData(i, unchecked, role=role_checkstate)
        
    def openFolder(self, url):
        QDesktopServices.openUrl(url)

    def set_break_on(self):
        self.break_on = True
        self.close_button.setEnabled(True)
        
    def on_run_button_clicked(self):        
        self.run_button.setEnabled(False)
        self.break_on = False
        self.setMessage("")                

        highlight_widget_no(self.wgFileSave)        

        if highlight_empty_fields(self, exclude=[self.textLog, self.cmbFields_ch]):
            self.setMessage("All required fields must be filled in")                        
            self.run_button.setEnabled(True)
            return 0
        
        if self.roundtrip:
            if not (self.check_imbalance()):
                self.run_button.setEnabled(True)            
                return 0
            
            # Блокировка запуска Run, пока активна хотя бы одна ошибка в Roundtrip
            if not self.check_time_back() or not self.check_time_order():
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
        
        if not (self.check_folder_and_file()):
            self.run_button.setEnabled(True)
            return 0
        
        if self.mode == 1:
            self.layer1 = self.cmbLayers.currentLayer() 
            self.layer2 = self.cmbLayersDest.currentLayer() 
        else:
            self.layer2 = self.cmbLayers.currentLayer() 
            self.layer1 = self.cmbLayersDest.currentLayer()
        
        if self.roundtrip:
            self.layer2 = self.cmbLayers.currentLayer() 
            self.layer1 = self.cmbLayersDest.currentLayer()
        
        if self.protocol_type == 1: # cumulative
            self.layer_visualization = self.layer1
        else:
            self.layer_visualization = self.layer2        

        result, text = check_layer(self.layer1, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
        
        result, text = check_layer(self.layer2, FIELD_ID = FIELD_ID)
        if not result:
            self.run_button.setEnabled(True)
            self.setMessage(text)
            return 0
        
        if self.mode == 2 or self.roundtrip:
            ids_vor = get_ids_from_voronoi (self.cmbLayers.currentLayer())
            ids = get_ids_from_layer (self.cmbLayersDest.currentLayer())
        else: 
            ids_vor = get_ids_from_voronoi (self.cmbLayersDest.currentLayer())
            ids = get_ids_from_layer (self.cmbLayers.currentLayer())
                
        result, text = check_ids_match (ids, ids_vor, self.mode)        
        if not result:
            msgBox = QMessageBox()
            rich_text = Qt.TextFormat.RichText
            text_browser_interaction = Qt.TextInteractionFlag.TextBrowserInteraction
            icon_question = QMessageBox.Icon.Question
            btn_ok = QMessageBox.StandardButton.Ok
            msgBox.setIcon(icon_question)           
            msgBox.setTextFormat(rich_text)
            msgBox.setTextInteractionFlags(text_browser_interaction)
            msgBox.setWindowTitle("Warning")
            msgBox.setText(text)
            msgBox.setStandardButtons(btn_ok )
            msgBox.exec()            
            self.run_button.setEnabled(True)            
            return 0
        
        if self.protocol_type == 2:             
            ids1 = get_ids_from_layer (self.cmbLayers.currentLayer())
            ids2 = get_ids_from_layer (self.cmbLayersDest.currentLayer())        
            result = not (ids1 == ids2)        
            if not result:
                highlight_widget(self.cmbLayers)            
                highlight_widget(self.cmbLayersDest)            
                text = (
                    f"A service area analysis can be performed when your origin and destination layers are distinct.<br>"
                    f"Please review your layers and ensure they are different."
                    )            
                msgBox = QMessageBox()
                rich_text = Qt.TextFormat.RichText
                text_browser_interaction = Qt.TextInteractionFlag.TextBrowserInteraction
                icon_question = QMessageBox.Icon.Question
                btn_ok = QMessageBox.StandardButton.Ok
                msgBox.setIcon(icon_question)           
                msgBox.setTextFormat(rich_text)
                msgBox.setTextInteractionFlags(text_browser_interaction)
                msgBox.setWindowTitle("Warning")
                msgBox.setText(text)
                msgBox.setStandardButtons(btn_ok )
                msgBox.exec()            
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
        if self.mode == 1:
            mode_text = "FROM origins"
        else:
            mode_text = "TO destinations"
        if self.roundtrip:
            mode_text = "ROUNDTRIP"
        self.textLog.append(f'<a> Accessibility: {mode_text}</a>')

        self.textLog.append("<a style='font-weight:bold;'>[Input Layers]</a>")
        self.textLog.append(f"<a> Car routing database folder: {self.config['Settings']['PathToPKL_car']}</a>")
        
        if self.roundtrip or self.mode == 2:
            origins_layer = self.layer2
            destinations_layer = self.layer1
        else:
            origins_layer = self.layer1
            destinations_layer = self.layer2

        self.textLog.append(
            f'<a> Layer of origins: {os.path.normpath(origins_layer.dataProvider().dataSourceUri().split("|")[0])} '
            f'({get_tablename(origins_layer)})</a>'
        )
        self.textLog.append(
            f'<a> Layer of destinations: {os.path.normpath(destinations_layer.dataProvider().dataSourceUri().split("|")[0])} '
            f'({get_tablename(destinations_layer)})</a>'
        )

        if self.protocol_type == 1:  # MAP mode
            if self.config['Settings']['field_ch_car'] != "":
                print_fields = self.config['Settings']['field_ch_car']
            else:
                print_fields = "NONE"
            self.textLog.append(f"<a> Opportunities' fields: {print_fields}</a>")

        self.textLog.append("<a style='font-weight:bold;'>[Time Settings]</a>")
        if not (self.roundtrip):
            if self.mode == 1:
                self.textLog.append(f"<a> Start from origin at: {self.config['Settings']['Start_time_car']}</a>")
            else:
                self.textLog.append(f"<a> Arrive to destination: {self.config['Settings']['Start_time_car']}</a>")

        self.total_cycles_roundtrip = 1

        if self.roundtrip:
            self.from_time_start = time_to_seconds(self.config['Settings']['from_time_start'])
            self.from_time_end = time_to_seconds(self.config['Settings']['from_time_end'])
            self.to_time_start = time_to_seconds(self.config['Settings']['to_time_start'])
            self.to_time_end = time_to_seconds(self.config['Settings']['to_time_end'])

            self.time_delta_to_min = int(self.config['Settings']['time_delta_to']) 
            self.time_delta_from_min = int(self.config['Settings']['time_delta_from']) 
            self.time_delta_to  = self.time_delta_to_min * 60
            self.time_delta_from  = self.time_delta_from_min * 60

            cycles_to   = floor((self.to_time_end   - self.to_time_start)   / self.time_delta_to)   + 1
            cycles_from = floor((self.from_time_end - self.from_time_start) / self.time_delta_from) + 1            
            self.total_cycles_roundtrip = cycles_to + cycles_from

            str_to = f'<a> Arrive to destination between: {seconds_to_time(self.to_time_start)} and {seconds_to_time(self.to_time_end)} schedule-adjustment gap {self.time_delta_to_min} minutes</a>'
            self.textLog.append(str_to)
            str_from = f'<a>Start trip back to the origin between: {seconds_to_time(self.from_time_start)} and {seconds_to_time(self.from_time_end)} schedule-adjustment gap {self.time_delta_from_min} minutes</a>'
            self.textLog.append(str_from)

        if self.roundtrip:            
            self.textLog.append(f"<a> Minimum time gap between arrival and trip back: {self.txtTimeBack.text()} min</a>")         
            
        self.textLog.append(f"<a> Maximum travel time: {self.config['Settings']['maxtimetravel_car']} min</a>")  

        self.textLog.append("<a style='font-weight:bold;'>[Walking distances and speed, Tolerances]</a>")
        self.textLog.append(f"<a> Average walking distance from the origin building to the parking place: {self.config['Settings']['Walk_to_car_car']} m</a>")
        self.textLog.append(f"<a> Average walking distance from the parking place to the destination building: {self.config['Settings']['Walk_to_destination_car']} m</a>")
        self.textLog.append(f"<a> Average walking speed: {self.config['Settings']['Walking_speed_car']} km/h</a>")
        self.textLog.append(f"<a> Minimal distance that is worth driving: {self.config['Settings']['Minimal_distance_car']} m</a>")
        if self.roundtrip:
            self.textLog.append(f"<a> Maximum lag imbalance ratio (k): {self.config['Settings']['CAR_imbalance']}</a>")
            
        self.textLog.append("<a style='font-weight:bold;'>[Output]</a>")                
        self.textLog.append(f"<a> Output file: {self.config['Settings']['pathtoprotocols_car']}</a>")
        if self.protocol_type == 1:  # MAP mode
            self.textLog.append(f"<a> Save time bin: {self.config['Settings']['timeinterval']} min</a>")        
        
        self.prepare()
        self.close_button.setEnabled(True)

    def on_close_button_clicked(self):
        self.reject()

    def on_help_button_clicked(self):        
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/car_accessibility.html"
        
        if self.mode == 1 and self.protocol_type == 2:
            section = "car-service-area-maps-parameters-and-computation-execution"
        if self.mode == 2 and self.protocol_type == 2:
            section = "car-service-area-maps-parameters-and-computation-execution"
        if self.mode == 1 and self.protocol_type == 1:
            section = "cumulative-number-of-opportunities-accessible-by-car"
        if self.mode == 2 and self.protocol_type == 1:
            section = "cumulative-number-of-opportunities-accessible-by-car"

        url = f'{url}#{section}'
        webbrowser.open(url)

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
            self.config['Settings']['Walk_to_car_car'] = '100'

        if 'Walk_to_destination_car' not in self.config['Settings']:
            self.config['Settings']['Walk_to_destination_car'] = '100'

        if 'Walking_speed_car' not in self.config['Settings']:
            self.config['Settings']['Walking_speed_car'] = '3.6'

        if 'Start_time_car' not in self.config['Settings']:
            self.config['Settings']['Start_time_car'] = '08:00:00'

        if 'Minimal_distance_car' not in self.config['Settings']:
            self.config['Settings']['Minimal_distance_car'] = '800'                
        
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

        value = self.config['Settings'].get('radio_button_type_car') 
        if not value:
            self.config['Settings']['radio_button_type_car'] = "to"        

        if 'CAR_imbalance' not in self.config['Settings']:
            self.config['Settings']['CAR_imbalance'] = '2'                
    
    def saveParameters(self):
        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        selected_text = ', '.join(
            self.cmbFields_ch.itemText(i)
            for i in range(self.cmbFields_ch.count())
            if self.cmbFields_ch.itemData(i, role=role_checkstate) == checked
        )

        self.config['Settings']['Field_ch_car'] = selected_text

        self.config['Settings']['PathToPKL_car'] = self.wgPathPKL.filePath()
        self.config['Settings']['PathToProtocols_car'] = self.wgFileSave.filePath()

        self.path_to_pkl = self.wgPathPKL.filePath()
        self.layer_field = FIELD_ID

        self.config['Settings']['Layer_car'] = self.cmbLayers.currentLayer().id()
        self.config['Settings']['LayerDest_car'] = self.cmbLayersDest.currentLayer().id()
                
        self.config['Settings']['MaxTimeTravel_car'] = self.txtMaxTimeTravel.text()
        self.config['Settings']['TimeInterval_car'] = self.txtTimeInterval.text()

        self.config['Settings']['Walk_to_car_car'] = self.txtWalkToCAR.text()
        self.config['Settings']['Walk_to_destination_car'] = self.txtWalkToDestination.text()
        self.config['Settings']['Walking_speed_car'] = self.txtWalkingSpeed.text()
        self.config['Settings']['Minimal_distance_car'] = self.txtMinimalDistance.text()

        self.config['Settings']['Start_time_car'] = self.dtStartTime.time().toString("HH:mm:ss")        
        self.config['Settings']['to_time_start'] = self.dtRoundtripStartTime1.time().toString("HH:mm:ss")
        self.config['Settings']['to_time_end'] = self.dtRoundtripStartTime2.time().toString("HH:mm:ss")
        self.config['Settings']['from_time_start'] = self.dtRoundtripStartTime3.time().toString("HH:mm:ss")
        self.config['Settings']['from_time_end'] = self.dtRoundtripStartTime4.time().toString("HH:mm:ss")
        self.config['Settings']['time_delta_to'] = self.txtRountrip_timedelta1.text()
        self.config['Settings']['time_delta_from'] = self.txtRountrip_timedelta2.text()

        if self.rbFrom.isChecked():
            rb_state = "from"
        elif self.rbTo.isChecked():
            rb_state = "to"
        elif self.rbRound.isChecked():
            rb_state = "round"
        
        self.config['Settings']['radio_button_type_car'] = rb_state
        self.config['Settings']['CAR_imbalance'] = self.txtImbalance.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

        self.layer1_path = os.path.normpath(self.layer1.dataProvider().dataSourceUri().split("|")[0])        
        self.layer2_path = os.path.normpath(self.layer2.dataProvider().dataSourceUri().split("|")[0])
        self.layer_vis_field = FIELD_ID

    def ParametrsShow(self):
        self.readParameters()

        prefix = get_prefix_alias(False, 
                                self.protocol_type, 
                                self.mode,
                                False,                                
                                self.roundtrip 
                                )        
        self.default_alias = f'{prefix}_{getDateTime()}'
        
        self.wgFileSave.setFilePath(os.path.join(os.path.dirname(self.config['Settings']['PathToProtocols_car']), f"{self.default_alias}.gpkg"))
        self.wgPathPKL.setFilePath(os.path.normpath(self.config['Settings']['PathToPKL_car']))
       
        if QApplication.keyboardModifiers() & shift_mod:
            self.cmbLayers.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['Layer_car']))
            self.cmbLayersDest.setLayer(QgsProject.instance().mapLayer(self.config['Settings']['LayerDest_car']))    
            self.txtMaxTimeTravel.setText(self.config['Settings']['MaxTimeTravel_car'])        
        else:
            self.cmbLayers.setCurrentIndex(0)
            self.cmbLayersDest.setCurrentIndex(0)       
        
        self.txtTimeInterval.setText(self.config['Settings']['TimeInterval_car'])
                          
        if QApplication.keyboardModifiers() & shift_mod:
            if 'Field_ch_car' not in self.config['Settings']:
                self.config['Settings']['Field_ch_car'] = ''

            for i in range(self.cmbFields_ch.count()):
                item_text = self.cmbFields_ch.itemText(i)
                if item_text in self.config['Settings']['Field_ch_car']:
                    self.cmbFields_ch.setItemData(i, checked, role=role_checkstate)
                else:
                    self.cmbFields_ch.setItemData(i, unchecked, role=role_checkstate)

        self.txtWalkToCAR.setText(self.config['Settings']['Walk_to_car_car'])
        self.txtWalkToDestination.setText(self.config['Settings']['Walk_to_destination_car'])
        self.txtWalkingSpeed.setText(self.config['Settings']['Walking_speed_car'])
        self.txtMinimalDistance.setText(self.config['Settings']['Minimal_distance_car'])

        datetime = QTime.fromString(self.config['Settings']['Start_time_car'], "HH:mm:ss")
        dt = QDateTime(QDate(2000, 1, 1), datetime, Qt.TimeSpec.UTC)
        self.dtStartTime.setDateTime(dt)

        self.txtRountrip_timedelta1.setText(self.config['Settings']['time_delta_to'])
        self.txtRountrip_timedelta2.setText(self.config['Settings']['time_delta_from'])

        datetime = QTime.fromString(self.config['Settings']['to_time_start'], "HH:mm:ss")
        dt = QDateTime(QDate(2000, 1, 1), datetime, Qt.TimeSpec.UTC)
        self.dtRoundtripStartTime1.setDateTime(dt)
        datetime = QTime.fromString(self.config['Settings']['to_time_end'], "HH:mm:ss")
        dt = QDateTime(QDate(2000, 1, 1), datetime, Qt.TimeSpec.UTC)
        self.dtRoundtripStartTime2.setDateTime(dt)
        datetime = QTime.fromString(self.config['Settings']['from_time_start'], "HH:mm:ss")
        dt = QDateTime(QDate(2000, 1, 1), datetime, Qt.TimeSpec.UTC)
        self.dtRoundtripStartTime3.setDateTime(dt)
        datetime = QTime.fromString(self.config['Settings']['from_time_end'], "HH:mm:ss")
        dt = QDateTime(QDate(2000, 1, 1), datetime, Qt.TimeSpec.UTC)
        self.dtRoundtripStartTime4.setDateTime(dt)

        radio_button_type_state = self.config['Settings']['radio_button_type_car']
        self.roundtrip = False
        if radio_button_type_state == "from":
            self.rbFrom.setChecked(True)
            self.mode = 1
        if radio_button_type_state == "to":
            self.rbTo.setChecked(True)
            self.mode = 2
        if radio_button_type_state == "round":
            self.roundtrip = True
            self.rbRound.setChecked(True)
        
        self.txtImbalance.setText(self.config['Settings']['CAR_imbalance'])

    def check_imbalance(self):
        if float(self.txtImbalance.text()) <= 1: 
            highlight_widget (self.txtImbalance)
            msgBox = QMessageBox()
            rich_text = Qt.TextFormat.RichText
            text_browser_interaction = Qt.TextInteractionFlag.TextBrowserInteraction
            icon_question = QMessageBox.Icon.Question
            btn_ok = QMessageBox.StandardButton.Ok

            msgBox.setIcon(icon_question)           
            msgBox.setTextFormat(rich_text)
            msgBox.setTextInteractionFlags(text_browser_interaction)
            msgBox.setWindowTitle("Warning")
            msgBox.setText(
                f"The value of k must be greater than 1.<br>"
                f"The recommended value of k is 2 or greater"                
                )
            msgBox.setStandardButtons(btn_ok )
            msgBox.exec()
            return False
        return True
    
    def check_folder_and_file(self):
        path_to_pkl = self.wgPathPKL.filePath()
        prefix = os.path.basename(path_to_pkl)

        required_files = ['dict_building_vertex.json',                          
                          'graph.json',
                          'graph_rev.json',
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
            self.setMessage(f"Files are missing in '{path_to_pkl}' folder: {missing_files_message}")
            return False
        return True

    def setMessage(self, message):
        self.lblMessages.setText(message)

    def get_feature_from_layer(self, layer):              
        ids = []
        count = 0
        feature_id_field = self.layer_field

        features = layer.getFeatures()

        for feature in features:
            count += 1
            id = feature[feature_id_field]
            if count % 50000 == 0:
                QApplication.processEvents()
                self.setMessage(f'Reading list of ficilities...')

            ids.append(int(id))

        return ids

    def call_car_accessibility(self):
        self.pathtopkl = self.config['Settings']['pathtopkl_car']
        self.layer_origin = self.layer1
        self.layer_dest = self.layer2
        
        layer_vis = self.layer_visualization

        max_time_minutes = int(self.config['Settings']['MaxTimeTravel_car'])
        imbalance = float(self.config['Settings']['CAR_imbalance'].replace(',', '.'))
        if self.roundtrip: 
            max_time_minutes = round(max_time_minutes * imbalance/(imbalance+1))

        time_step_minutes = int(self.config['Settings']['TimeInterval_car'])
        
        layer_vis_field = layerdest_field = self.layerorig_field = FIELD_ID

        if 'Field_ch_car' in self.config['Settings']:
            list_fields_aggregate = self.config['Settings']['Field_ch_car']
        else:
            list_fields_aggregate = ""

        self.walk_on_start_m = int(self.config['Settings']['Walk_to_car_car'])
        self.walk_on_finish_m = int(self.config['Settings']['Walk_to_destination_car'])
        walk_speed_km_h = float(self.config['Settings']['Walking_speed_car'])
        self.walk_speed_m_s = walk_speed_km_h/3.6
        self.walk_time_start = round(self.walk_on_start_m/self.walk_speed_m_s)
        self.walk_time_finish = round(self.walk_on_finish_m/self.walk_speed_m_s)

        self.MinimalDistance = int(self.config['Settings']['Minimal_distance_car'])
        start_time = QTime.fromString(self.config['Settings']['Start_time_car'], "HH:mm:ss")        
        self.hour = start_time.hour()

        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
       
        cols_dict = get_name_columns()
        cols = cols_dict[(self.mode, self.protocol_type)]
        self.col_star = cols["star"]
        self.col_hash = cols["hash"]   

        car = car_accessibility(self,
                                self.layer_dest,
                                layerdest_field,
                                max_time_minutes,
                                time_step_minutes,
                                layer_vis,
                                layer_vis_field,
                                list_fields_aggregate                                
                                )
        
        self.setMessage("Loading dictionary...")
        QApplication.processEvents()
        
        file_name = Path(self.file_name_gpkg).stem
        start_time = time_to_seconds(self.config['Settings']['Start_time_car'])

        if not (self.roundtrip):
            self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
            self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

            graph = self.read_pkl(self.mode)
            car.run(begin_computation_time, 
                    self.hour, 
                    graph,
                    start_time,
                    write_info = True,
                    )
            
            text = transform_log_to_dataframe(self.textLog.toPlainText())
            table_name = f'_{file_name}_log'
            fast_write_gpkg(self.file_name_gpkg, table_name, text)

            folder = os.path.dirname(self.file_name_gpkg)
            name, ext = os.path.splitext(os.path.basename(self.file_name_gpkg))
            filelog_name = os.path.join(folder, f"{name}_log.csv")
            text = transform_log_to_csv_text(self.textLog.toPlainText())
            with open(filelog_name, "w") as file:
                file.write(text)        

        if self.roundtrip:
            dict_FIELDS = {}   
            if self.protocol_type == 1:
                    list_fields_aggregate = self.config['Settings']['Field_ch_car']
                    if list_fields_aggregate:
                        fields_to_process = [v.strip() for v in list_fields_aggregate.split(',')]
                        idx_aid = self.layer2.fields().lookupField('aid')
                        for field_name in fields_to_process:
                            idx_num = self.layer2.fields().lookupField(field_name)
                            if idx_num != -1:
                                dict_FIELDS[field_name] = {
                                    int(f[idx_aid]): round(f[idx_num])
                                    for f in self.layer2.getFeatures()
                                }

            self.textLog.append("<a style='font-weight:bold;'>[Processing]</a>")
            self.textLog.append(f'<a>Started: {begin_computation_str}</a>')
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating roundtrip accessibility</a>")

            duration_max = int(self.config['Settings']['MaxTimeTravel_car']) * 60
            cols_dict = get_name_columns()
            cols = cols_dict[(2, self.protocol_type)]
            bin = time_step_minutes * 60
            self.txtTimeBack_sec = int(self.txtTimeBack.text()) * 60
            analyzer = roundtrip_analyzer(                                        
                                        duration_max = duration_max,                                                                                 
                                        service_area = (self.protocol_type == 2),
                                        dict_numpoints = dict_FIELDS,
                                        bin = bin,
                                        imbalance = imbalance,
                                        min_activity_duration = self.txtTimeBack_sec, 
                                        check_min_activity_duration = True                                        
                                        )
      
            graph = self.read_pkl(1)
            graph_rev = self.read_pkl(2)
            roundtrip_cycle_current = 0
                
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating to accessibility</a>")
            self.mode = 2
            i = 0
            D_TIME = self.to_time_start

            while True:
                D_TIME_str = seconds_to_time(D_TIME)
                self.textLog.append(f"<a style='font-weight:bold;'> Arrive before: {D_TIME_str}</a>")
                
                hour = D_TIME // 3600  
                roundtrip_cycle_current += 1                   
                short_result = car.run(begin_computation_time, 
                                   hour,
                                   graph_rev, 
                                   D_TIME,
                                   write_info = False,                                   
                                   roundtrip_cycle_all = self.total_cycles_roundtrip,
                                   roundtrip_cycle_current =  roundtrip_cycle_current)
                
                if not(self.break_on):
                    data_to = analyzer.get_data_for_analyzer_from_to (short_result)                    
                    analyzer.add_to_data(data_to, D_TIME_str)
                                       
                i += 1
                if self.break_on:
                    self.setMessage("Roundtrip accessibility computations are interrupted by user")
                    self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                    self.progressBar.setValue(0)
                    return 0                               
                               
                D_TIME = self.to_time_start + i * self.time_delta_to 
                if D_TIME >= self.to_time_end: 
                    break            
                        
            self.textLog.append(f"<a style='font-weight:bold;'> Calculating from accessibility</a>")
            self.mode = 1
            i = 0
            D_TIME = self.from_time_start
            while True:
                D_TIME_str = seconds_to_time(D_TIME)
                self.textLog.append(f"<a style='font-weight:bold;'> Start at: {D_TIME_str}</a>")
                
                hour = D_TIME // 3600 
                roundtrip_cycle_current += 1
                short_result = car.run(begin_computation_time, 
                                   hour, 
                                   graph,
                                   D_TIME,
                                   write_info = False,
                                   roundtrip_cycle_all = self.total_cycles_roundtrip,
                                   roundtrip_cycle_current =  roundtrip_cycle_current)
                            
                if not(self.break_on):
                    data_from = analyzer.get_data_for_analyzer_from_to (short_result)                             
                    analyzer.add_from_data(data_from, D_TIME_str)            

                if self.break_on:
                    self.setMessage("Roundtrip accessibility computations are interrupted by user")
                    self.textLog.append(f'<a><b><font color="red">Roundtrip accessibility computations are interrupted by user</font> </b></a>')
                    self.lblEstimateTime.setText("")
                    self.progressBar.setValue(0)
                    return 0
                i += 1                               

                D_TIME = self.from_time_start + i * self.time_delta_from 
                if D_TIME >= self.from_time_end: 
                    break

            if not(self.break_on):
                    list_tables_to_visualize = []
                    df_rows_std, _, header, pivot  = analyzer.run_finalize_all()

                    if header is not None:                   
                        if self.protocol_type == 1:
                            for field_name, df_rows in df_rows_std.items():
                                df_rows.columns = header
                                table_name = f"{file_name}_{field_name}"
                                list_tables_to_visualize.append(table_name)
                                fast_write_gpkg(self.file_name_gpkg, table_name, df_rows)

                        if self.protocol_type == 2:
                            df_rows_std.columns = header
                            table_name1 = f'{file_name}_triptime_all'
                            fast_write_gpkg(self.file_name_gpkg, table_name1, df_rows_std)
                            list_tables_to_visualize.append(table_name1)

                            table_name2 = f'{file_name}_triptime_by_destinations'                    
                            fast_write_gpkg(self.file_name_gpkg, table_name2, pivot)
                        
                        vis = visualization(self, 
                                self.layer_visualization,
                                mode = self.protocol_type, 
                                fieldname_layer = self.layer_vis_field, 
                                from_to = 1, 
                                roundtrip = True, 
                                prefix = file_name                            
                                )
                        for table_name in list_tables_to_visualize:
                            vis.add_thematic_map_gpkg(self.file_name_gpkg, table_name, table_name)
                    self.lblEstimateTime.setText("")
                    after_computation_time = datetime.now()
                    after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
                    self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
                    duration_computation = after_computation_time - begin_computation_time
                    duration_without_microseconds = str(duration_computation).split('.')[0]
                    self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

                    text = transform_log_to_dataframe(self.textLog.toPlainText())
                    table_name = f'_{file_name}_log'
                    fast_write_gpkg(self.file_name_gpkg, table_name, text)

                    folder = os.path.dirname(self.file_name_gpkg)
                    name, ext = os.path.splitext(os.path.basename(self.file_name_gpkg))
                    filelog_name = os.path.join(folder, f"{name}_log.csv")
                    text = transform_log_to_csv_text(self.textLog.toPlainText())
                    with open(filelog_name, "w") as file:
                        file.write(text)

                    self.setMessage(f'Finished')                    
                    self.textLog.append(f'Output in file: <a href="file:///{self.file_name_gpkg}" target="_blank" > {self.file_name_gpkg}</a>')                    
                    self.progressBar.setValue(self.progressBar.maximum())

    def read_pkl(self, mode):
            pkl_car_reader = pkl_car()
            self.crs = self.layer_dest.crs()
            if not self.dict_building_vertex or not self.dict_vertex_buildings:
                self.dict_building_vertex, self.dict_vertex_building = pkl_car_reader.load_files(self.path_to_pkl)
            
            graph = pkl_car_reader.load_graph(
                mode = mode,
                pathtopkl = self.path_to_pkl,
                crs = self.crs
            )
            return graph

    def prepare(self):
        self.break_on = False
        QApplication.processEvents()
        self.points = self.get_feature_from_layer(self.layer1)

        if self.points == 0:
            self.run_button.setEnabled(True)
            return 0

        run = True
        if run:
            self.call_car_accessibility()

        if not (run):
            self.run_button.setEnabled(True)
            self.close_button.setEnabled(True)
            self.textLog.clear()
            self.tabWidget.setCurrentIndex(0)
            self.setMessage("")

    def eventFilter(self, obj, event):
        wheel_type = QEvent.Type.Wheel

        if event.type() == wheel_type:
            if obj.hasFocus():
                event.ignore()
                return True

        if obj == self.txtTimeBack and event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
            self.update_bubble_position()

        return super().eventFilter(obj, event)
    
    def show_info(self):
            hlp_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'help')

            if self.protocol_type == 1:
                help_filename = "car_cumulative.txt"
            else:
                help_filename = "car_sa.txt"
            hlp_file = os.path.join(hlp_directory, help_filename)

            if os.path.exists(hlp_file):
                with open(hlp_file, 'r', encoding='utf-8') as f:
                    html = f.read()

            self.textInfo.setOpenExternalLinks(False)  
            self.textInfo.setOpenLinks(False)          
            self.textInfo.setHtml(html)
            self.textInfo.anchorClicked.connect(lambda url: webbrowser.open(url.toString()))