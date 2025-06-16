import os
import webbrowser

from PyQt5.QtCore import (Qt,
                          QVariant,
                          QRegExp)
from qgis.PyQt import QtCore
from qgis.core import QgsProject
from PyQt5.QtGui import QRegExpValidator

from .form_raptor_detailed import RaptorDetailed


class RaptorSummary(RaptorDetailed):
    def __init__(self, parent,
                 mode,
                 protocol_type,
                 title,
                 timetable_mode,
                 ):
        super().__init__(parent, mode, protocol_type, title, timetable_mode)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.parent = parent

        self.fillComboBoxWithLayerFields2()
        self.cmbLayersDest.currentIndexChanged.connect(
            self.fillComboBoxWithLayerFields2)

        regex = QRegExp(r"^(1[0-9]|20|[2-9])$")
        int_validator = QRegExpValidator(regex)
        self.txtTimeInterval.setValidator(int_validator)

        self.ParametrsShow()

    def on_help_button_clicked(self):
        
        url = "https://ishusterman.github.io/tutorial/raptor_map.html"
        
        if self.mode == 1 and not(self.timetable_mode):
            section = "accessibility-from-every-location-in-the-region-fixed-time-departure"
        
        if self.mode == 2 and not(self.timetable_mode):
            section = "accessibility-to-every-location-in-the-region-fixed-time-arrival"

        if self.timetable_mode:
            section = "region-accessibility-for-the-schedule-based-departure-or-arrival"
                        
        url = f'{url}#{section}'
        webbrowser.open(url)
    
    # for widget with checkbox

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

    def saveParameters(self):

        super().saveParameters()

        project_directory = os.path.dirname(QgsProject.instance().fileName())
        f = os.path.join(project_directory, 'parameters_accessibility.txt')

        self.config.read(f)

        selected_text = ', '.join(
            self.cmbFields_ch.itemText(i)
            for i in range(self.cmbFields_ch.count())
            if self.cmbFields_ch.itemData(i, role=Qt.CheckStateRole) == Qt.Checked
        )
        self.config['Settings']['Field_ch'] = selected_text

        self.config['Settings']['TimeInterval'] = self.txtTimeInterval.text()

        with open(f, 'w') as configfile:
            self.config.write(configfile)

    def prepareRaptor(self):
        result = super().prepareRaptor()

    def ParametrsShow(self):

        super().ParametrsShow()

        if 'Field_ch' not in self.config['Settings']:
            self.config['Settings']['Field_ch'] = ''

        for i in range(self.cmbFields_ch.count()):
            item_text = self.cmbFields_ch.itemText(i)
            if item_text in self.config['Settings']['Field_ch']:
                self.cmbFields_ch.setItemData(
                    i, Qt.Checked, role=Qt.CheckStateRole)
            else:
                self.cmbFields_ch.setItemData(
                    i, Qt.Unchecked, role=Qt.CheckStateRole)

        self.txtTimeInterval.setText(self.config['Settings']['TimeInterval'])
