import os
import webbrowser
from datetime import datetime

from PyQt5.QtCore import (Qt,
                          QRegExp,
                          QDateTime)
from qgis.core import QgsProject
from PyQt5.QtGui import QRegExpValidator

from .form_raptor_summary import RaptorSummary


class RaptorRoundtrip(RaptorSummary):
    def __init__(self, parent,
                 mode,
                 protocol_type,
                 title,
                 timetable_mode,
                 roundtrip = True
                 ):
        super().__init__(parent, mode, protocol_type, title, timetable_mode, roundtrip)
        self.setAttribute(Qt.WA_DeleteOnClose)

        regex = QRegExp(r"\d*")
        int_validator = QRegExpValidator(regex)
        self.txtTimeInterval.setValidator(int_validator)

        self.dtRoundtripStartTime1.installEventFilter(self)
        self.dtRoundtripStartTime2.installEventFilter(self)
        self.dtRoundtripStartTime3.installEventFilter(self)
        self.dtRoundtripStartTime4.installEventFilter(self)
        self.txtRountrip_timedelta1.setValidator(int_validator)
        self.txtRountrip_timedelta2.setValidator(int_validator)
        
        self.dtRoundtripStartTime1.setFixedWidth(self.fix_size)
        self.dtRoundtripStartTime2.setFixedWidth(self.fix_size)
        self.dtRoundtripStartTime3.setFixedWidth(self.fix_size)
        self.dtRoundtripStartTime4.setFixedWidth(self.fix_size)
        self.fix_size2 = 7* self.txtMinTransfers.fontMetrics().width('x')
        self.txtRountrip_timedelta1.setFixedWidth(self.fix_size2)
        self.txtRountrip_timedelta2.setFixedWidth(self.fix_size2)

        self.dtStartTime.setVisible(False)
        self.dtEndTime.setVisible(False)
        self.lblStartTime1.setVisible(False)
        self.lblStartTime2.setVisible(False)
        self.lblStartTime3.setVisible(False)
        parent_layout = self.horizontalLayout_9.parent()
        parent_layout.removeItem(self.horizontalLayout_9)

        
        
        
        self.ParametrsShow()

    def on_help_button_clicked(self):
        
        url = "https://geosimlab.github.io/accessibility-calculator-tutorial/raptor_map.html"
        
        if self.mode == 1 and not(self.timetable_mode):
            section = "accessibility-from-every-location-in-the-region-fixed-time-departure"
        
        if self.mode == 2 and not(self.timetable_mode):
            section = "accessibility-to-every-location-in-the-region-fixed-time-arrival"

        if self.timetable_mode:
            section = "region-accessibility-for-the-schedule-based-departure-or-arrival"
                        
        url = f'{url}#{section}'
        webbrowser.open(url)
           

    def saveParameters(self):

        super().saveParameters()

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)
        self.config['Settings']['to_time_start'] = self.dtRoundtripStartTime1.dateTime().toString("HH:mm:ss")
        self.config['Settings']['to_time_end'] = self.dtRoundtripStartTime2.dateTime().toString("HH:mm:ss")
        self.config['Settings']['from_time_start'] = self.dtRoundtripStartTime3.dateTime().toString("HH:mm:ss")
        self.config['Settings']['from_time_end'] = self.dtRoundtripStartTime4.dateTime().toString("HH:mm:ss")
        self.config['Settings']['time_delta_to'] = self.txtRountrip_timedelta1.text()
        self.config['Settings']['time_delta_from'] = self.txtRountrip_timedelta2.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def ParametrsShow(self):

        super().ParametrsShow()

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


    def readParameters(self):

        def is_valid_time(t): 
            try: 
                datetime.strptime(t, "%H:%M:%S") 
                return True 
            except Exception: 
                return False 

        super().readParameters()

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