import os
import sys
import configparser
import re
import math
import pandas as pd
from zipfile import ZipFile
from datetime import datetime
import shutil

from pathlib import Path

try:
    import qgis.core
    import qgis.PyQt
    import osgeo.gdal
    from qgis.core import QgsProject

    from qgis.core import (
                    QgsVectorLayer,
                    QgsWkbTypes,
                    QgsFeature,
                    QgsFields,
                    QgsProject,
                    QgsField,
                    QgsLayerTreeLayer,
                    )
    from qgis.PyQt.QtCore import QVariant

    from qgis.utils import iface

    IN_QGIS = True
except ImportError:
    IN_QGIS = False

def getDateTime():
    current_datetime = datetime.now()
    year = str(current_datetime.year)[-2:]
    month = str(current_datetime.month).zfill(2)
    day = str(current_datetime.day).zfill(2)
    hour = str(current_datetime.hour).zfill(2)
    minute = str(current_datetime.minute).zfill(2)
    second = str(current_datetime.second).zfill(2)
    return f"{year}{month}{day}_{hour}{minute}{second}"


def get_version_from_metadata():

    current_dir = os.path.dirname(
        os.path.abspath(__file__))  # path to the current file
    plugin_dir = os.path.dirname(current_dir)  # path to the plugin folder

    file_path = os.path.join(plugin_dir, 'metadata.txt')

    config = configparser.ConfigParser()
    config.read(file_path)

    if 'general' in config and 'version' in config['general']:
        return config['general']['version']

    return ""


def get_qgis_info():
    qgis_info = {}
    qgis_info['QGIS version'] = qgis.core.Qgis.QGIS_VERSION
    qgis_info['Qt version'] = qgis.PyQt.QtCore.QT_VERSION_STR
    qgis_info['Python version'] = sys.version
    qgis_info['GDAL version'] = osgeo.gdal.VersionInfo('RELEASE_NAME')
    qgis_info['Accessibility plugin version'] = get_version_from_metadata()
    return qgis_info


def is_valid_folder_name(folder_name):
    # check for the presence of invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    if re.search(invalid_chars, folder_name):
        return False

    # check the length of the folder name
    if len(folder_name) == 0 or len(folder_name) > 255:
        return False
    return True


def get_prefix_alias(PT, protocol, mode, timetable=None, field_name="", full_prefix=True):
    """
    Point/Region - P/R  (protocol 2,1)
    Forward/Backward - F/B (mode 1,2)
    Fixed/Scheduled - X/S  (false,true)
    """
    """
    P/C (Public/Car), F/T (From/To), X/S (Fixed/Scheduled time), A/R (Service Area/Region).
    """
    date_time = getDateTime()
    prefix = "P" if PT else "C"
    protocol_char = "R" if protocol == 1 else "A"
    mode_char = "F" if mode == 1 else "T"
    timetable_char = "" if timetable is None else ("S" if timetable else "X")

    result = f"{date_time}_{prefix}{mode_char}{timetable_char}{protocol_char}"
    if full_prefix:
        if field_name:
            result = f"{result}_{field_name}"
    
    return result

def zip_directory(directory):
    file_list = ['stops.txt', 'trips.txt', 'routes.txt',
                 'stop_times.txt', 'calendar.txt', 'rev_stop_times.txt']
    timestamp = getDateTime()
    zip_name = os.path.join(directory, f'gtfs_{timestamp}.zip')
    with ZipFile(zip_name, 'w') as zipf:
        for file_name in file_list:
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                relative_path = os.path.relpath(file_path, directory)
                zipf.write(file_path, relative_path)
                os.remove(file_path)

def convert_meters_to_degrees(distance_in_meters, latitude):
    # length of one degree of longitude at a given latitude in meters
    meters_per_degree_longitude = 111320 * math.cos(math.radians(latitude))
    # convert distance from meters to degrees
    return abs(distance_in_meters / meters_per_degree_longitude)


def convert_distance_to_meters(distance_in_degrees, latitude):
    return distance_in_degrees * 111132.92 * math.cos(math.radians(latitude))

def time_to_seconds(t):
    if pd.isna(t):
        return None
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s

# Convert seconds to time string (e.g., total seconds -> HH:MM:SS)
def seconds_to_time(total_seconds):
        
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def check_file_parameters_accessibility ():
    project_directory = os.path.dirname(QgsProject.instance().fileName())
    parameters_path = os.path.join(project_directory, 'parameters_accessibility.txt')
    parameters_add_path = os.path.join(project_directory, 'parameters_accessibility_add.txt')

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(current_dir, 'config')
    source_path = os.path.join(config_path, 'parameters_accessibility_shablon.txt')
    source_add_path = os.path.join(config_path, 'parameters_accessibility_add_shablon.txt')
    if not os.path.exists(parameters_path):
        shutil.copy(source_path, parameters_path)

    if not os.path.exists(parameters_add_path):
        shutil.copy(source_add_path, parameters_add_path)

def get_documents_path():
    if sys.platform == "win32":
        try:
            import ctypes.wintypes

            CSIDL_PERSONAL = 5  # Мои документы
            SHGFP_TYPE_CURRENT = 0

            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

            return str(Path(buf.value))
        except Exception as e:
            # fallback in rare case
            return str(Path.home() / "Documents")
    else:
        # Linux и macOS
        xdg_docs = Path.home() / "Documents"
        user_dirs = Path.home() / ".config" / "user-dirs.dirs"

        if user_dirs.exists():
            try:
                with user_dirs.open(encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('XDG_DOCUMENTS_DIR'):
                            path_str = line.split('=')[1].strip().strip('"')
                            path_str = path_str.replace('$HOME', str(Path.home()))
                            return str(Path(path_str))
            except Exception:
                pass  # fallback

        return str(xdg_docs)

def get_initial_directory(input_path: str) -> str:

    if input_path not in ["C:\\", "C:/"]:
        return input_path

    project_path = QgsProject.instance().fileName()
    if project_path:
        project_dir = Path(project_path).parent
        pkl_dir = find_pkl_subfolder(project_dir)
        return str(pkl_dir if pkl_dir else project_dir)

    documents_path = Path(get_documents_path())
    if documents_path.exists():
        pkl_dir = find_pkl_subfolder(documents_path)
        return str(pkl_dir if pkl_dir else documents_path)

    return str(Path.home())


def find_pkl_subfolder(base_dir: Path):
    """Ищет первую подпапку, содержащую 'pkl' или 'PKL' в имени."""
    for subdir in base_dir.iterdir():
        if subdir.is_dir() and 'pkl' in subdir.name.lower():
            return subdir
    return None


def insert_field_first(layer, new_field):
    """Вставляет новое поле первым в структуру атрибутов слоя"""
    old_fields = layer.fields()
    new_fields = QgsFields()
    new_fields.append(new_field)
    for field in old_fields:
        if field.name() != new_field.name():  # Избежать дублирования, если поле уже есть
            new_fields.append(field)

    crs = layer.crs().authid()
    geometry_type = QgsWkbTypes.displayString(layer.wkbType())
    temp_layer = QgsVectorLayer(f"{geometry_type}?crs={crs}", layer.name() + "_tmp", "memory")
    temp_provider = temp_layer.dataProvider()
    temp_provider.addAttributes(new_fields)
    temp_layer.updateFields()

    for feat in layer.getFeatures():
        new_feat = QgsFeature(new_fields)
        # Проверка: если поле уже существовало — нужно взять его значение
        old_attrs = feat.attributes()
        if new_field.name() in layer.fields().names():
            idx = layer.fields().indexOf(new_field.name())
            new_val = old_attrs[idx]
        else:
            new_val = None
        new_attrs = [new_val] + [val for i, val in enumerate(old_attrs) if layer.fields()[i].name() != new_field.name()]
        new_feat.setAttributes(new_attrs)
        new_feat.setGeometry(feat.geometry())
        temp_provider.addFeature(new_feat)

    return temp_layer

def get_unique_field_name(layer, base_name):
    existing_names = set(layer.fields().names())
    new_name = base_name
    counter = 1
    while new_name in existing_names:
        new_name = f"{base_name}_{counter}"
        counter += 1
    return new_name

def create_and_check_field(layer, name_field, type = 'bldg'):

    insert_field = False       
    field_exists = name_field in layer.fields().names()
    first_field_name = layer.fields().field(0).name()

    if name_field == "Create ID":
        insert_field = True
        if type == 'bldg':
            name_field = get_unique_field_name(layer, "bldg_id")
        if type == 'link':
            name_field = get_unique_field_name(layer, "link_id")
      
    if not field_exists or first_field_name != name_field:
        layer = insert_field_first(layer, QgsField(name_field, QVariant.Int))
        
    name_field_index = layer.fields().indexOf(name_field)

    existing_ids = set()
    for f in layer.getFeatures():
        val = f[name_field_index]
        try:
            if val is not None:
                existing_ids.add(int(val))
        except:
            continue

    layer.startEditing()
    next_id = max(existing_ids) + 1 if existing_ids else 1
    assigned_ids = set()
    count_modified = 0
    for f in layer.getFeatures():
        fid = f.id()
        val = f[name_field_index]
        if val is None or not val or val in assigned_ids:
            count_modified += 1
            
            while next_id in existing_ids:
                next_id += 1
            layer.changeAttributeValue(fid, name_field_index, next_id)
            assigned_ids.add(next_id)
            
            next_id += 1
        else:
            assigned_ids.add(val)

    layer.commitChanges()

    return layer, count_modified, insert_field, name_field

def get_unique_path(base_path):
        """
        Generates a unique path by appending an index if the file already exists.
        :param base_path: The initial path for saving the file
        :return: A unique path with an appended index
        """
        if not os.path.exists(base_path):
            return base_path

        base, ext = os.path.splitext(base_path)
        index = 1
        while os.path.exists(f"{base}_{index}{ext}"):
            index += 1
        return f"{base}_{index}{ext}"

def insert_layer_ontop (layer):
    tree_view = iface.layerTreeView()
    current_node = tree_view.currentNode() if tree_view else None
    if current_node:
        if isinstance(current_node, QgsLayerTreeLayer):
            parent_group = current_node.parent()
        else:
            parent_group = current_node
        parent_group.insertChildNode(0, QgsLayerTreeLayer(layer))

def showAllLayersInCombo_Line(cmb):
        cmb.clear()
        layer_nodes = QgsProject.instance().layerTreeRoot().findLayers()
        for node in layer_nodes: 
            layer = node.layer()
            if isinstance(layer, QgsVectorLayer) and \
                layer.geometryType() == QgsWkbTypes.LineGeometry and \
                not layer.name().startswith("Temp") and \
                'memory' not in layer.dataProvider().dataSourceUri():
                cmb.addItem(layer.name(), [])

def showAllLayersInCombo_Point_and_Polygon(cmb):
        cmb.clear()
        layer_nodes = QgsProject.instance().layerTreeRoot().findLayers()
        for node in layer_nodes: 
            layer = node.layer()
            if isinstance(layer, QgsVectorLayer) and \
                (layer.geometryType() == QgsWkbTypes.PointGeometry or 
                layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                cmb.addItem(layer.name(), [])

def showAllLayersInCombo_Polygon(cmb):
        cmb.clear()
        layer_nodes = QgsProject.instance().layerTreeRoot().findLayers()
        for node in layer_nodes: 
            layer = node.layer()
            if isinstance(layer, QgsVectorLayer) and \
                (layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                cmb.addItem(layer.name(), [])

def extract_time_pattern_from_txt(txt_path):

    # Define the regex patterns with types
    time_patterns = [
        (re.compile(r"Start at \(hh:mm:ss\):\s+(\d{1,2}:\d{2}:\d{2})"), "start"),
        (re.compile(r"Earliest start time:\s+(\d{1,2}:\d{2}:\d{2})"), "start"),
        (re.compile(r"Arrive before \(hh:mm:ss\):\s+(\d{1,2}:\d{2}:\d{2})"), "end"),
        (re.compile(r"Earliest arrival time:\s+(\d{1,2}:\d{2}:\d{2})"), "end")
    ]

    # If the provided path is a directory, look for .txt files in it
    if os.path.isdir(txt_path):
        txt_files = [f for f in os.listdir(txt_path) if f.endswith('.txt')]
        if not txt_files:
            return None, None
        txt_path = os.path.join(txt_path, txt_files[0])

    # Read the .txt file
    try:
        with open(txt_path, "r", encoding="utf-8") as file:
            content = file.read()
    except (PermissionError, FileNotFoundError, UnicodeDecodeError) as e:
        print(f"Error reading file {txt_path}: {e}")
        return None, None

    # Search for the last match by scanning from the end
    last_match = None
    
    # Reverse search by checking patterns at decreasing positions
    for i in range(len(content) - 1, -1, -1):
        substring = content[i:]
        for pattern, time_type in time_patterns:
            match = pattern.search(substring)
            if match:
                # Found the last match in the file
                return match.group(1), time_type
    
    return None, None

def get_existing_path(folder_path, filename):
        """Вспомогательный метод для выбора пути: с префиксом или без."""
        prefix = os.path.basename(folder_path.rstrip('\\/'))
        path_with_prefix = os.path.join(folder_path, f'{prefix}_{filename}')
        path_without_prefix = os.path.join(folder_path, filename)

        # Если файл с префиксом существует — возвращаем его, иначе обычный
        if os.path.exists(path_with_prefix):
            return path_with_prefix
        return path_without_prefix