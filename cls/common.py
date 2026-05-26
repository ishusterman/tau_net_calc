FIELD_ID = "aid"

import os
import sys
import configparser
import re
import math
import pandas as pd
from zipfile import ZipFile
from datetime import datetime
import shutil
import csv
import geopandas as gpd
from pathlib import Path


try:
    import qgis.core
    import qgis.PyQt
    import osgeo.gdal
    from qgis.core import (QgsProject,
                    QgsVectorLayer,
                    QgsWkbTypes,
                    QgsFeature,
                    QgsFields,
                    QgsProject,
                    QgsField,
                    QgsLayerTreeLayer,
                    )
    from qgis.PyQt.QtCore import QVariant
    from PyQt5.QtCore import QDate

    from qgis.utils import iface

    from PyQt5.QtWidgets import (
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QComboBox
    )

    from qgis.gui import QgsCheckableComboBox

    IN_QGIS = True
except ImportError:
    IN_QGIS = False

import pandas as pd


def transform_log_to_dataframe(raw_text):
    """
    Преобразует текстовый лог напрямую в Pandas DataFrame.
    """
    # Если текста нет, возвращаем пустой DF с нужными колонками
    columns = ["Parameter", "Value"]
    if not raw_text:
        return pd.DataFrame(columns=columns)

    lines = raw_text.strip().split('\n')
    data = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ":" in line:
            # Разделяем по первому двоеточию
            key, value = line.split(":", 1)
            data.append({
                "Parameter": key.strip(),
                "Value": value.strip()
            })
        else:
            # Если двоеточия нет, записываем только в первую колонку
            data.append({
                "Parameter": line,
                "Value": ""
            })
            
    # Создаем DataFrame из списка словарей
    return pd.DataFrame(data, columns=columns)

def transform_log_to_csv_text(raw_text):
    """
    Преобразует текстовый лог в строку формата CSV с заголовками.
    """
    if not raw_text:
        return '"Parameter","Value"'

    lines = raw_text.strip().split('\n')
    csv_rows = []
        
    csv_rows.append('"Parameter","Value"')
    
    for line in lines:
        line = line.strip()
        
        # Пропускаем пустые строки и заголовки секций в [квадратных скобках]
        #if not line or (line.startswith('[') and line.endswith(']')):
        #    continue
       
        
        if ":" in line:
            key, value = line.split(":", 1)
            
            safe_key = key.strip().replace('"', '""')
            safe_value = value.strip().replace('"', '""')
            csv_rows.append(f'"{safe_key}","{safe_value}"')
        else:
            
            safe_line = line.replace('"', '""')
            csv_rows.append(f'"{safe_line}",""')
            
    return "\n".join(csv_rows)

def check_layer(layer, FIELD_ID = ""):
    if not layer:
        return 0, "Layer is not selected" 
    if layer.featureCount() == 0:
        return 0, f"Layer '{layer.name()}' is empty"
    if FIELD_ID != "":
        if layer.fields().indexOf(FIELD_ID) == -1:
            return 0, f"Layer '{layer.name()}' does not contain required field '{FIELD_ID}'"
    return 1, ""  


def get_gtfs_date_range(gtfs_path):
        if not os.path.isdir(gtfs_path):
            return None, None, False

        calendar_path = os.path.join(gtfs_path, 'calendar.txt')
        calendar_dates_path = os.path.join(gtfs_path, 'calendar_dates.txt')
        
        
        dates_found = False
        
        min_date_qdate = QDate(9999, 12, 31) 
        max_date_qdate = QDate(1, 1, 1)      
        
        if os.path.exists(calendar_path):
            with open(calendar_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for key in ['start_date', 'end_date']:
                        date_str = row.get(key)
                        if date_str:
                            d = QDate.fromString(date_str, "yyyyMMdd")
                            if d.isValid():
                                dates_found = True
                                if d < min_date_qdate: min_date_qdate = d
                                if d > max_date_qdate: max_date_qdate = d

        # 2. Читаем calendar_dates.txt
        if os.path.exists(calendar_dates_path):
            with open(calendar_dates_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = row.get('date')
                    if date_str:
                        d = QDate.fromString(date_str, "yyyyMMdd")
                        if d.isValid():
                            dates_found = True
                            if d < min_date_qdate: min_date_qdate = d
                            if d > max_date_qdate: max_date_qdate = d

        # Итоговая проверка
        if not dates_found:
            # Если ни в одном файле дат нет — возвращаем текущую дату и False
            today = QDate.currentDate().toString("yyyyMMdd")
            return today, today, False
        
        return min_date_qdate.toString("yyyyMMdd"), max_date_qdate.toString("yyyyMMdd"), True

def get_name_columns():

        # ({from-to}, protokol) ....
        return {
            (1, 2): {
                "star": "Origin_aid", "hash": "Destination_aid",
                1: "Origin_aid", 2: "Destination_aid",                
            },
            (2, 2): {
                 "star": "Destination_aid", "hash": "Origin_aid",
                1: "Origin_aid", 2: "Destination_aid",                
            },
            (1, 1): {
                 "star": "Origin_aid", "hash": "Destination_aid",
                1: "Origin_aid", 2: "Destination_aid",                
            },
            (2, 1): {
                 "star": "Destination_aid", "hash": "Origin_aid",
                1: "Origin_aid", 2: "Destination_aid",
                
            }
        } 
 

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


def get_prefix_alias(PT, protocol, mode, timetable = None, roundtrip = False):
    """
    Point/Region - P/R  (protocol 2,1)
    Forward/Backward - F/B (mode 1,2)
    Fixed/Scheduled - X/S  (false,true)
    """
    """
    p/c (public/car), F/T/R (From/To/Roundtrip), x/s (fixed/scheduled time), A/O (Service Area/accumulated Opportunities).
    """    
    prefix = "p" if PT else "c"
    protocol_char = "O" if protocol == 1 else "A"
    mode_char = "F" if mode == 1 else "T"
    if roundtrip:
        mode_char = "R"    
    timetable_char = "x" if timetable is None else ("s" if timetable else "x")
    result = f"{prefix}{protocol_char}{timetable_char}{mode_char}"
        
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
    #parameters_add_path = os.path.join(project_directory, 'roundtrip_additional_parameters.txt')

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(current_dir, 'config')
    source_path = os.path.join(config_path, 'parameters_accessibility_shablon.txt')
    #source_add_path = os.path.join(config_path, 'roundtrip_additional_parameters_shablon.txt')
    if not os.path.exists(parameters_path):
        shutil.copy(source_path, parameters_path)

    #if not os.path.exists(parameters_add_path):
    #    shutil.copy(source_add_path, parameters_add_path)

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
    """Создает новый слой, где new_field — первое поле, остальные пустые."""
    old_fields = layer.fields()
    new_fields = QgsFields()
    
    
    if new_field.type() == QVariant.Int:
        new_field = QgsField(new_field.name(), QVariant.LongLong)
        
    new_fields.append(new_field)
    
    for field in old_fields:
        if field.name() != new_field.name():
            new_fields.append(field)

    crs = layer.crs().authid()
    geometry_type = QgsWkbTypes.displayString(layer.wkbType())
    temp_layer = QgsVectorLayer(f"{geometry_type}?crs={crs}", layer.name() + "_tmp", "memory")
    temp_provider = temp_layer.dataProvider()
    temp_provider.addAttributes(new_fields)
    temp_layer.updateFields()
   
    for feat in layer.getFeatures():
        new_feat = QgsFeature(new_fields)
        old_attrs = feat.attributes()
        
        clean_attrs = [None]
        for i, field in enumerate(old_fields):
            if field.name() != new_field.name():
                clean_attrs.append(old_attrs[i])
        
        new_feat.setAttributes(clean_attrs)
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

def create_and_check_field(layer, name_field, type='bldg'):
    next_id = 1_000_000 if type == 'bldg' else 1
    new_field_obj = QgsField(name_field, QVariant.LongLong)
    temp_layer = insert_field_first(layer, new_field_obj)
    name_field_index = temp_layer.fields().indexOf(name_field)
    temp_layer.startEditing()
    for f in temp_layer.getFeatures():
        fid = f.id()
        temp_layer.changeAttributeValue(fid, name_field_index, next_id)
        next_id += 1
    temp_layer.commitChanges()
    return temp_layer

def is_gpkg_open_in_project(gpkg_path):
    gpkg_norm = gpkg_path.replace("\\", "/")
    for layer in QgsProject.instance().mapLayers().values():
        if layer.providerType() == "ogr":
            if gpkg_norm in layer.source().replace("\\", "/"):
                return True
    return False


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


def fast_write_gpkg(file_name_gpkg, table_name, df_current, mode_relative=False):
    # Подготовка данных (числовой формат)
    if not mode_relative and not df_current.empty:
        last_col_name = df_current.columns[-1]
        if last_col_name != "Value":
            df_current[last_col_name] = pd.to_numeric(df_current[last_col_name], errors='coerce')

    # Создаем GeoDataFrame (даже если нет геометрии)
    # Это гарантирует создание правильной структуры GPKG
    gdf = gpd.GeoDataFrame(df_current)

    # Определяем режим записи
    if not os.path.exists(file_name_gpkg):
        # Создаем новый файл
        gdf.to_file(file_name_gpkg, layer=table_name, driver="GPKG")
    else:
        # Добавляем или ПЕРЕЗАПИСЫВАЕМ слой в существующем файле
        gdf.to_file(
            file_name_gpkg, 
            layer=table_name, 
            driver="GPKG",             
            mode="a", 
            layer_options={'OVERWRITE': 'YES'}
        )

"""
def create_empty_gpkg(path):
    # Создаём минимальный валидный GeoPackage
    gdf = gpd.GeoDataFrame({"id": []}, geometry=[], crs="EPSG:4326")
    gdf.to_file(path, layer="__init__", driver="GPKG")

    conn = sqlite3.connect(path)
    conn.execute("DELETE FROM gpkg_contents WHERE table_name='__init__'")
    conn.execute("DROP TABLE IF EXISTS __init__")
    conn.commit()
    conn.close()
"""

"""
def make_service_area_report_gpkg(all_frames, col_star, col_hash, mode = 1):
    df_total = pd.concat(all_frames, ignore_index=True)
    df_total['Duration'] = pd.to_numeric(df_total['Duration'], errors='coerce')
    df_total[col_star] = pd.to_numeric(df_total[col_star], errors='coerce')
    df_total[col_hash] = pd.to_numeric(df_total[col_hash], errors='coerce')
    df_min = df_total.loc[df_total.groupby(col_hash)['Duration'].idxmin()]
    short_result = {
        (int(row._asdict()[col_star]), int(row._asdict()[col_hash])): int(row.Duration)
        for row in df_min.itertuples(index=False)
    }
    return df_min, short_result
"""

def make_service_area_report_gpkg(all_frames, col_star, col_hash):
    df_total = pd.concat(all_frames, ignore_index=True)

    df_total['Duration'] = pd.to_numeric(df_total['Duration'], errors='coerce')
    df_total[col_star] = pd.to_numeric(df_total[col_star], errors='coerce')
    df_total[col_hash] = pd.to_numeric(df_total[col_hash], errors='coerce')

    df_min = df_total.loc[df_total.groupby(col_hash)['Duration'].idxmin()]

    # Определяем порядок колонок в зависимости от mode
    key_cols = (col_star, col_hash)
    
    short_result = {
        (int(row._asdict()[key_cols[0]]), int(row._asdict()[key_cols[1]])): int(row.Duration)
        for row in df_min.itertuples(index=False)
    }

    return df_min, short_result



def make_pivot_gpkg(all_frames, col_star, col_hash, max_cols=10):
    rows = [(h, s, d) for (h, s), d in all_frames.items()]
    df_total = pd.DataFrame(rows, columns=[col_star, col_hash, "Duration"])

    df_total["Duration"] = pd.to_numeric(df_total["Duration"], errors="coerce")
    df_total[col_star] = pd.to_numeric(df_total[col_star], errors="coerce")
    df_total[col_hash] = pd.to_numeric(df_total[col_hash], errors="coerce")

    # Берём только первые max_cols уникальных значений
    allowed_stars = df_total[col_star].dropna().unique()[:max_cols]
    df_total = df_total[df_total[col_star].isin(allowed_stars)]

    pivot = df_total.pivot(index=col_hash, columns=col_star, values="Duration").reset_index()

    new_cols = [pivot.columns[0]] + [f"Duration_{c}" for c in pivot.columns[1:]]
    pivot.columns = new_cols
    return pivot



def is_child_of(child, parent):
    while child is not None:
        if child is parent:
            return True
        child = child.parentWidget()   # ← ключевое исправление
    return False

def highlight_widget(widget):
    widget.setStyleSheet("background-color: #fff7cc;")

def highlight_widget_no(widget):
    widget.setStyleSheet("")

def highlight_empty_fields(widget, exclude=None) -> bool:
    if exclude is None:
        exclude = []

    found_empty = False

    for child in widget.findChildren((QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QgsCheckableComboBox)):
        
        if any(is_child_of(child, ex) for ex in exclude):
            continue

        if not child.isVisible():
            continue

        is_empty = False

        if isinstance(child, QLineEdit):
            is_empty = not child.text().strip()

        elif isinstance(child, QTextEdit):
            is_empty = not child.toPlainText().strip()

        elif isinstance(child, QPlainTextEdit):
            is_empty = not child.toPlainText().strip()

        elif isinstance(child, QComboBox):
            is_empty = child.currentIndex() < 0 or not child.currentText().strip()

        elif isinstance(child, QgsCheckableComboBox):
            is_empty = len(child.checkedItems()) == 0

        if is_empty:                        
            child.setStyleSheet("background-color: #fff7cc;")
            found_empty = True
        else:
            child.setStyleSheet("")

    return found_empty

def get_tablename(layer):
    uri = layer.dataProvider().dataSourceUri()
    for part in uri.split("|"):
        if part.startswith("layername="):
            return part.split("=", 1)[1]
    return None

