# -*- coding: utf-8 -*-

import os
import py_compile
import shutil
import configparser

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from PyQt5.QtWidgets import QDockWidget,  QAction
from qgis.core import QgsProject

from .forms.accessibility_tools import AccessibilityTools

current_dir = os.path.dirname(os.path.abspath(__file__))

module_path = os.path.join(current_dir, 'cls')
config_path = os.path.join(current_dir, 'config')
user_home = os.path.expanduser("~")

class TAUNetCalc():

    def __init__(self, iface):

        self.widget_visible = False
        self.dock_widget = None
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
       

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Accessibility calculator')

        self.first_start = None

        plugin_dir = os.path.dirname(__file__)
        self.clean_pyc(plugin_dir)
        self.compile_all_py(plugin_dir)
    

    def tr(self, message):
        return QCoreApplication.translate('Accessibility calculator', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)

        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def get_version_from_metadata(self):

        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'metadata.txt')

        config = configparser.ConfigParser()
        config.read(file_path)

        if 'general' in config and 'version' in config['general']:
            return config['general']['version']

        return ""

    def initGui(self):

        cache_dir = os.path.expanduser('~/.qgis2/cache/tau_net_calc')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        icon_accessibility_path = os.path.join(
            os.path.dirname(__file__), 'img', 'app.png')

        version = self.get_version_from_metadata()
        name_plugin = f'Accessibility calculator v.{version}'

        self.add_action(
            icon_path=icon_accessibility_path,
            text=self.tr(name_plugin),
            callback=self.runAccessibility_tools,
            parent=self.iface.mainWindow())
        self.first_start_accessibility = True

    """Recursively compiles all .py files in the specified directory"""

    def compile_all_py(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    py_compile.compile(file_path)

    def clean_pyc(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))

    def unload(self):

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Accessibility calculator'),
                action)
            self.iface.removeToolBarIcon(action)
    
    def runAccessibility_tools(self):
        if self.dock_widget and self.dock_widget.isVisible():
            self.dock_widget.hide()
            self.widget_visible = False
        else:
            if not self.dock_widget:
                project_path = QgsProject.instance().fileName()
                if project_path:
                    project_directory = os.path.dirname(project_path)
                else:
                    project_directory = os.path.expanduser('~')

                parameters_path = os.path.join(
                    project_directory, 'parameters_accessibility.txt')
                source_path = os.path.join(
                    config_path, 'parameters_accessibility_shablon.txt')

                try:
                    if not os.path.exists(parameters_path):
                        shutil.copy(source_path, parameters_path)
                except Exception as e:
                    self.iface.messageBar().pushWarning(
                        "Accessibility calculator",
                        f"Failed to create settings file: {e}"
                    )

                my_widget = AccessibilityTools()
                self.dock_widget = QDockWidget("Accessibility calculator")
                self.dock_widget.setWidget(my_widget)
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

            self.dock_widget.show()
            self.widget_visible = True
        
