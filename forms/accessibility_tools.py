# -*- coding: utf-8 -*-
import subprocess
from PyQt5.QtWidgets import (QApplication,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QVBoxLayout,
                             QWidget
                             )
from qgis.PyQt.QtGui import QIcon, QFont
import os
import webbrowser
from qgis.core import QgsProject

from .form_raptor_detailed import RaptorDetailed
from .form_raptor_summary import RaptorSummary
from .form_car import CarAccessibility
from .form_gtfs import form_gtfs
from .form_pkl import form_pkl
from .form_pkl_car import form_pkl_car
from .form_relative import form_relative

from .form_roads_clean import form_roads_clean
from .form_visualization_clean import form_visualization_clean
from .form_buildings_clean import form_buildings_clean

class AccessibilityTools(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.tree_widget = QTreeWidget()

        self.path_to_pkl = ""
        self.dict_footpath_b_b = {}
        self.dict_footpath = {}

        font = QFont()
        font.setBold(True)

        # change the setting to absolute paths if it is not already set.
        project = QgsProject.instance()
        is_absolute, _ = project.readBoolEntry("Paths", "Absolute")
        if not is_absolute:
            project.writeEntry("Paths", "Absolute", True)
            project.write()

        self.tree_widget.setHeaderHidden(True)
        group1 = QTreeWidgetItem(self.tree_widget, ['Data preprocessing'])
        group1.setExpanded(True)
        self.item2 = QTreeWidgetItem(group1, ['Clean road network'])
        self.item20 = QTreeWidgetItem(group1, ['Clean layer of buildings'])
        self.item19 = QTreeWidgetItem(group1, ['Prepare visualisation layers'])
        self.item27 = QTreeWidgetItem(group1, ['Add lines to GTFS'])
        self.item28 = QTreeWidgetItem(group1, ['Delete lines from GTFS'])
        self.item3 = QTreeWidgetItem(group1, ['Build transit routing database'])
        self.item17 = QTreeWidgetItem(group1, ['Build car routing database'])
        

        group2 = QTreeWidgetItem(self.tree_widget, ['Transit accessibility computations'])
        group2.setExpanded(True)
        
        group3 = QTreeWidgetItem(group2, ['Transit service area maps'])
        self.item4 = QTreeWidgetItem(group3, ['fixed arrival/departure time'])
        self.item5 = QTreeWidgetItem(group3, ['schedule-based arrival/departure time'])
        group3.setExpanded(True)

        group4 = QTreeWidgetItem(group2, ['Transit cumulative opportunities maps'])
        self.item8 = QTreeWidgetItem(group4, ['fixed arrival/departure time'])
        self.item9 = QTreeWidgetItem(group4, ['schedule-based arrival/departure time'])
                
        group4.setExpanded(True)

        group5 = QTreeWidgetItem(self.tree_widget, ['Car accessibility computations'])
        group8 = QTreeWidgetItem(group5, ['Car service area map'])
        self.item12 = QTreeWidgetItem(group8, ['fixed arrival/departure time'])
        group5.setExpanded(True)
        group8.setExpanded(True)

        group6 = QTreeWidgetItem(group5, ['Car cumulative opportunities maps'])
        self.item14 = QTreeWidgetItem(group6, ['fixed arrival/departure time'])
                
        group6.setExpanded(True)

        group7 = QTreeWidgetItem(self.tree_widget, ['Compare accessibility maps'])
        self.item16 = QTreeWidgetItem(group7, ['Service areas maps'])
        self.item18 = QTreeWidgetItem(group7, ['Cumulative opportunities maps'])
        group7.setExpanded(True)

        self.item1 = QTreeWidgetItem(self.tree_widget, ['Help and tutorial'])
      
        icon1 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'folder.png') # icon for groups
        icon2 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'ring.png') # icon for elements 

        for group_index in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(group_index)
            group_item.setIcon(0, QIcon(icon1))

            # process second-level elements
            for child_index in range(group_item.childCount()):
                child_item = group_item.child(child_index)

                # if an element has child elements, we consider it a group
                if child_item.childCount() > 0:
                    # icon for a group (folder)
                    child_item.setIcon(0, QIcon(icon1))

                    # process third-level elements
                    for item_index in range(child_item.childCount()):
                        item = child_item.child(item_index)
                        # icon for elements (ring)
                        item.setIcon(0, QIcon(icon2))
                else:
                    # If it is not a group, but a regular element
                    # icon for elements (ring)
                    child_item.setIcon(0, QIcon(icon2))
        
        icon3 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'help.png')
        self.item1.setIcon(0, QIcon(icon3))
       
        layout.addWidget(self.tree_widget)

        self.setLayout(layout)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_clicked)

        self.titles = ["Data preprocessing. Clean road network", 
                       "Data preprocessing. Clean layer of buildings", 
                       "Data preprocessing. Prepare visualisation layers",
                       "Data preprocessing. Build transit routing database", 
                       "Data preprocessing. Add lines to GTFS", 
                       "Data preprocessing. Delete lines from GTFS", 
                       "Data preprocessing. Build car routing database", 

                       "Transit accessibility computations. Transit service area map - fixed arrival/departure time",
                       "Transit accessibility computations. Transit service area map - schedule-based arrival/departure time", 
                       "Transit accessibility computations. Transit cumulative opportunities map - fixed arrival/departure time", 
                       "Transit accessibility computations. Transit cumulative opportunities map - schedule-based arrival/departure time", 
                       
                       "Car accessibility computations. Car service area map - fixed arrival/departure time", 
                       "Car accessibility computations. Car cumulative opportunities map - fixed arrival/departure time",
                       
                       "Compare accessibility. Service areas maps",
                       "Compare accessibility. Cumulative opportunities maps",
                   ]
        
    """ Проверяет, есть ли уже открытое окно с указанным заголовком. """
    def get_existing_window(self, titles):
        
        for widget in QApplication.topLevelWidgets():
            if widget.windowTitle() in self.titles:
                if widget.isMinimized():
                    widget.showNormal()
                widget.raise_()
                widget.activateWindow()
                widget.show()
                return widget
        return None
    
    def on_tree_item_clicked(self, item, column):

        if item == self.item1:
            
            url = "https://geosimlab.github.io/accessibility-calculator-tutorial/introduction.html"
            
            webbrowser.open(url)
            
        if item == self.item2:
            title="Data preprocessing. Clean road network"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                roads_clean = form_roads_clean(title = title)
                roads_clean.exec_()

        if item == self.item20:
            title="Data preprocessing. Clean layer of buildings"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                buildings_clean = form_buildings_clean( title = title)
                buildings_clean.exec_()

        if item == self.item19:
            title="Data preprocessing. Prepare visualisation layers"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                visualization_clean = form_visualization_clean(title = title)
                visualization_clean.exec_()    

        if item == self.item27:
            title="Data preprocessing. Add lines to GTFS"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                gtfs = form_gtfs(title = title, mode = 1)
                gtfs.show()
        
        if item == self.item28:
            title="Data preprocessing. Delete lines from GTFS"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                gtfs = form_gtfs(title = title, mode = 2)
                gtfs.show()

        if item == self.item3:
            title="Data preprocessing. Build transit routing database"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                pkl = form_pkl(title = title)
                pkl.show()

        if item == self.item17:
            title="Data preprocessing. Build car routing database"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                pkl_car = form_pkl_car(title = title)
                pkl_car.show()

        if item == self.item4:
            title="Transit accessibility computations. Transit service area map - fixed arrival/departure time"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                raptor_detailed = RaptorDetailed(self, mode=2,
                                             protocol_type=2,
                                             title= title,
                                             timetable_mode=False)
                raptor_detailed.show()

        if item == self.item5:
            title="Transit accessibility computations. Transit service area map - schedule-based arrival/departure time"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                raptor_detailed = RaptorDetailed(self, mode=2,
                                             protocol_type=2,
                                             title=title,
                                             timetable_mode=True)
                raptor_detailed.show()

        if item == self.item8:
            title="Transit accessibility computations. Transit cumulative opportunities map - fixed arrival/departure time"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                raptor_summary = RaptorSummary(self, mode=2,
                                           protocol_type=1,
                                           title=title,
                                           timetable_mode=False
                                           )
                raptor_summary.show()

        if item == self.item9:
            title="Transit accessibility computations. Transit cumulative opportunities map - schedule-based arrival/departure time"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                raptor_summary = RaptorSummary(self, mode=2,
                                           protocol_type=1,
                                           title=title,
                                           timetable_mode=True)
                raptor_summary.show()
        
        if item == self.item12:
            title="Car accessibility computations. Car service area map - fixed arrival/departure time"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                car_accessibility = CarAccessibility(mode=2,
                                                 protocol_type=2,
                                                 title=title)
                car_accessibility.show()

        if item == self.item14:
            title="Car accessibility computations. Car cumulative opportunities map - fixed arrival/departure time"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                car_accessibility = CarAccessibility(mode=2,
                                                 protocol_type=1,
                                                 title=title)
                car_accessibility.show()
        

        if item == self.item16:
            title="Compare accessibility. Service areas maps"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                relative = form_relative(
                                        title=title, 
                                        mode=1)
                relative.show()

        if item == self.item18:
            title="Compare accessibility. Cumulative opportunities maps"
            existing_window = self.get_existing_window(title)
            if not (existing_window):
                relative = form_relative(
                                        title=title, 
                                        mode=2)
                relative.show()       
