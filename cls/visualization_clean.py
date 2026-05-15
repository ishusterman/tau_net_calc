import os
import math
from datetime import datetime
from qgis.PyQt.QtCore import Qt, QObject, pyqtSignal, QVariant
from qgis.core import (
    QgsVectorLayer, QgsVectorFileWriter, QgsTask, QgsProject,
    QgsFeature, QgsField, QgsSpatialIndex, QgsRectangle,
    QgsPointXY, QgsGeometry
)
from qgis import processing
from PyQt5.QtWidgets import QApplication
from qgis.PyQt.QtGui import QColor

from common import (convert_meters_to_degrees, get_unique_path, FIELD_ID)

class TaskSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    set_message = pyqtSignal(str)    
    save_log = pyqtSignal(bool, str)
    add_layers = pyqtSignal(list) 
    change_button_status = pyqtSignal(bool) 

class cls_clean_visualization(QgsTask):
    def __init__(self, begin_computation_time, layer, folder_name, runVoronoi, spacing, task_name="Voronoi and Hexagons"):
        super().__init__(task_name)
        self.signals = TaskSignals()
        self.begin_computation_time = begin_computation_time
        self.layer = layer
        self.folder_name = folder_name
        self.layer_field = FIELD_ID
        self.runVoronoi = runVoronoi
        self.spacing = spacing
        self.dist_buffer = 50
        self.break_on = False
        self.list_layer = []

        self.name = self.layer.name()
        base_path = os.path.join(self.folder_name, f"{self.name}_vis_layers.gpkg")
        self.main_gpkg_path = get_unique_path(base_path)

        self.voronoi_gpkg_path = get_unique_path(os.path.join(self.folder_name, f"{self.name}_voronoi.gpkg"))

    def save_voronoi_to_gpkg(self, qgs_layer, layer_name):
        suffix = self._extract_suffix(self.voronoi_gpkg_path)
        layer_name = f"{layer_name}{suffix}"

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

        QgsVectorFileWriter.writeAsVectorFormatV3(
            qgs_layer,
            self.voronoi_gpkg_path,
            QgsProject.instance().transformContext(),
            options
        )

        layer_source = f"{self.voronoi_gpkg_path}|layername={layer_name}"
        self.list_layer.append((layer_source, layer_name))


    def save_layer_to_gpkg(self, qgs_layer, layer_name):
        suffix = self._extract_suffix(self.main_gpkg_path)
        layer_name = f"{layer_name}{suffix}"
        
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(self.main_gpkg_path) else QgsVectorFileWriter.CreateOrOverwriteFile
        
        QgsVectorFileWriter.writeAsVectorFormatV3(qgs_layer, self.main_gpkg_path, QgsProject.instance().transformContext(), options)
        layer_source = f"{self.main_gpkg_path}|layername={layer_name}"
        self.list_layer.append((layer_source, layer_name))

    def run(self):
        try:
            # Используем объект слоя, а не путь с диска
            centroids_layer = self.make_centroids(self.layer)
            if self.break_on: return False

            units = self.layer.crs().mapUnits()
            crs_grad = (units == 6)
            
            # Точка для расчета искажений проекции
            first_feat = next(self.layer.getFeatures(), None)
            if not first_feat: return False
            ref_point = first_feat.geometry().centroid().asPoint()

            # 1. Вороной
            
            if self.runVoronoi:
                v_dist = self.dist_buffer
                if crs_grad: v_dist = convert_meters_to_degrees(self.dist_buffer, ref_point.y())
                self.process_voronoi(centroids_layer, v_dist)
            
            # 2. Гексагоны
            for i, s_val in enumerate(self.spacing):
                if self.break_on: return False
                
                curr_s = float(s_val)
                s_info = round(curr_s / math.sqrt(3))
                self.signals.set_message.emit(f'Hexagons {s_info}m...')

                h_s, v_s = curr_s, curr_s
                if crs_grad:
                    h_s = convert_meters_to_degrees(curr_s, ref_point.x())
                    v_s = convert_meters_to_degrees(curr_s, ref_point.y())

                ext = self.layer.extent()
                target_ext = QgsRectangle(ext.xMinimum()-h_s, ext.yMinimum()-v_s, ext.xMaximum()+h_s, ext.yMaximum()+v_s)

                grid = processing.run("native:creategrid", {
                    'TYPE': 4, 'EXTENT': target_ext, 'HSPACING': h_s, 'VSPACING': v_s,
                    'CRS': self.layer.crs(), 'OUTPUT': 'memory:'
                })['OUTPUT']

                clean_hex = processing.run("native:retainfields", {'INPUT': grid, 'FIELDS': [id], 'OUTPUT': 'memory:'})['OUTPUT']
                
                self.filter_hexagons_by_intersection(clean_hex, self.layer)
                self.add_nearest_osm_id(clean_hex, centroids_layer)
                self.add_numeric_summaries_and_count(clean_hex, centroids_layer)

                dissolved = processing.run("native:dissolve", {'INPUT': clean_hex, 'FIELD': [self.layer_field], 'OUTPUT': 'memory:'})['OUTPUT']
                
                self.save_layer_to_gpkg(dissolved, f"{self.name}_hex_{s_info}m")
                self.signals.progress.emit(i+2)

            self.write_finish_info()
            self.signals.change_button_status.emit(True)
            return True
        except Exception as e:
            self.exception = e
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            print (self.exception)
            self.signals.log.emit(f'<a>Error: {self.exception}</a>')
            self.signals.set_message.emit(f'<a>Error: {self.exception}</a>')
            return False

    def process_voronoi(self, centroids, dist):
        ext = centroids.extent()
        b = ext.width() * 0.05
        rect = QgsRectangle(ext.xMinimum()-b, ext.yMinimum()-b, ext.xMaximum()+b, ext.yMaximum()+b)
        
        mem = QgsVectorLayer(f"Point?crs={centroids.crs().authid()}", "vor_tmp", "memory")
        mem.dataProvider().addAttributes(centroids.fields())
        mem.updateFields()
        
        feats = list(centroids.getFeatures())
        for pt in [QgsPointXY(rect.xMinimum(), rect.yMinimum()), QgsPointXY(rect.xMaximum(), rect.yMaximum())]:
            f = QgsFeature(); f.setGeometry(QgsGeometry.fromPointXY(pt))
            f.setAttributes([None]*centroids.fields().count()); feats.append(f)
        mem.dataProvider().addFeatures(feats)

        vor = processing.run("native:voronoipolygons", {'INPUT': mem, 'OUTPUT': 'memory:'})['OUTPUT']
        buf = processing.run("native:buffer", {'INPUT': self.layer, 'DISTANCE': dist, 'DISSOLVE': True, 'OUTPUT': 'memory:'})['OUTPUT']
        clip = processing.run("native:clip", {'INPUT': vor, 'OVERLAY': buf, 'OUTPUT': 'memory:'})['OUTPUT']

        self.save_voronoi_to_gpkg(clip, f"{self.name}_voronoi")

        # делаем слой прозрачным
        symbol = clip.renderer().symbol()
        symbol.setColor(QColor(255, 255, 255, 0))  # полностью прозрачная заливка
        symbol.symbolLayer(0).setStrokeColor(QColor(0, 0, 0))  # тонкая обводка
        symbol.symbolLayer(0).setStrokeWidth(0.2)
        clip.triggerRepaint()



        self.signals.progress.emit(1)

    def filter_hexagons_by_intersection(self, hex_layer, input_layer):
        idx = QgsSpatialIndex(input_layer.getFeatures())
        hex_layer.startEditing()
        ids_to_del = []
        for f in hex_layer.getFeatures():
            geom = f.geometry()
            if not any(geom.intersects(input_layer.getFeature(cid).geometry()) for cid in idx.intersects(geom.boundingBox())):
                ids_to_del.append(f.id())
        hex_layer.deleteFeatures(ids_to_del)
        hex_layer.commitChanges()
    
    """
    def add_nearest_osm_id(self, hex_layer, centroids):
        if self.layer_field not in hex_layer.fields().names():
            hex_layer.dataProvider().addAttributes([QgsField(self.layer_field, QVariant.LongLong)])
            hex_layer.updateFields()
        
        f_idx = hex_layer.fields().lookupField(self.layer_field)
        c_idx = QgsSpatialIndex(centroids.getFeatures())
        c_map = {f.id(): f for f in centroids.getFeatures()}
        
        hex_layer.startEditing()
        for f in hex_layer.getFeatures():
            near = c_idx.nearestNeighbor(f.geometry().centroid().asPoint(), 1)
            if near: hex_layer.changeAttributeValue(f.id(), f_idx, c_map[near[0]][self.layer_field])
        hex_layer.commitChanges()
    """

    def add_nearest_osm_id(self, hex_layer, centroids):
        # 1. Проверяем наличие поля
        if self.layer_field not in hex_layer.fields().names():
            hex_layer.dataProvider().addAttributes([QgsField(self.layer_field, QVariant.LongLong)])
            hex_layer.updateFields()
        
        f_idx = hex_layer.fields().lookupField(self.layer_field)
        
        # Создаем пространственный индекс для центроидов
        # Важно: индекс должен содержать ссылки на объекты
        c_idx = QgsSpatialIndex(centroids.getFeatures())
        
        # Маппинг: ID фичи в индексе -> Значение нужного нам атрибута (osm_id)
        c_map = {f.id(): f[self.layer_field] for f in centroids.getFeatures()}
        
        if not c_map:
            self.signals.log.emit("Warning: No centroids found to link IDs.")
            return

        hex_layer.startEditing()
        
        for f in hex_layer.getFeatures():
            # Используем центр гексагона для поиска ближайшего соседа
            # nearestNeighbor(point, 1) вернет список с ID одного ближайшего объекта из c_idx
            point_to_search = f.geometry().centroid().asPoint()
            near_ids = c_idx.nearestNeighbor(point_to_search, 1)
            
            if near_ids:
                nearest_centroid_id = near_ids[0]
                osm_id_value = c_map.get(nearest_centroid_id)
                
                if osm_id_value is not None:
                    hex_layer.changeAttributeValue(f.id(), f_idx, osm_id_value)
        
        hex_layer.commitChanges()


    def make_centroids(self, lyr):
        return processing.run("native:centroids", {'INPUT': lyr, 'OUTPUT': 'memory:'})['OUTPUT']

    def write_finish_info(self):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        self.signals.log.emit(f'<a>Finished: {after_computation_str}</a>')

        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.signals.log.emit(f'<a>Processing time: {duration_without_microseconds}</a>')
        self.signals.log.emit(f"Saved hexogons layers to: {self.main_gpkg_path}")        
        self.signals.save_log.emit(True, self.main_gpkg_path)
        if self.runVoronoi:
            self.signals.log.emit(f"Saved Voronoi to: {self.voronoi_gpkg_path}")
            self.signals.save_log.emit(True, self.voronoi_gpkg_path)
                
        #for _, name_layer in self.list_layer:    
        #    self.signals.log.emit(f'- {name_layer}')
        

        self.signals.add_layers.emit(self.list_layer)
        self.signals.set_message.emit("Finished")

    def add_numeric_summaries_and_count(self, hex_layer, centroids_layer):
        numeric_types = {
            QVariant.Int,
            QVariant.Double,
            QVariant.LongLong,
            QVariant.UInt,
            QVariant.ULongLong
        }

        numeric_fields = [
                f for f in centroids_layer.fields()
                if f.type() in numeric_types and f.name().lower() not in ("fid", "osm_id", "id", "aid")
            ]

        provider = hex_layer.dataProvider()
        
        if "numbuildings" not in hex_layer.fields().names():
            provider.addAttributes([QgsField("numbuildings", QVariant.Int)])
        
        for fld in numeric_fields:
            new_name = fld.name()
            if new_name not in hex_layer.fields().names():
                provider.addAttributes([QgsField(new_name, QVariant.Double)])

        hex_layer.updateFields()

        fld_idx_count = hex_layer.fields().lookupField("numbuildings")
        fld_idx_map = {
            fld.name(): hex_layer.fields().lookupField(fld.name())
            for fld in numeric_fields
        }

        field_index_map = {
            fld.name(): centroids_layer.fields().indexFromName(fld.name())
            for fld in numeric_fields
        }

        c_index = QgsSpatialIndex(centroids_layer.getFeatures())

        centroid_data = {
            f.id(): (f.geometry(), f.attributes())
            for f in centroids_layer.getFeatures()
        }

        hex_layer.startEditing()

        for hex_feat in hex_layer.getFeatures():
            geom = hex_feat.geometry()
            engine = QgsGeometry.createGeometryEngine(geom.constGet())
            engine.prepareGeometry()

            candidate_ids = c_index.intersects(geom.boundingBox())

            sums = {fld.name(): 0.0 for fld in numeric_fields}
            count = 0

            for cid in candidate_ids:
                c_geom, attrs = centroid_data[cid]

                if engine.intersects(c_geom.constGet()):
                    count += 1
                    for fld in numeric_fields:
                        idx = field_index_map[fld.name()]
                        val = attrs[idx]
                        if val is not None:
                            sums[fld.name()] += float(val)

            hex_layer.changeAttributeValue(hex_feat.id(), fld_idx_count, count)

            for name, value in sums.items():
                hex_layer.changeAttributeValue(hex_feat.id(), fld_idx_map[name], value)

        hex_layer.commitChanges()


    def _extract_suffix(self, path):
        base = os.path.splitext(os.path.basename(path))[0]
        parts = base.split("_")
        if parts[-1].isdigit():
            return f"_{parts[-1]}"
        return ""



        