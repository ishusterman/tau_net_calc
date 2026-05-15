import os
import math
import re 
from osgeo import ogr

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor

from PyQt5.QtCore import Qt

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsVectorLayerJoinInfo,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,    
    QgsClassificationEqualInterval,
    QgsSymbol
    )

from common import insert_layer_ontop, get_name_columns
from PyQt5.QtCore import QTimer

class visualization:
    def __init__(self,
                 parent,
                 layer_buildings = "",
                 mode = "",
                 fieldname_layer = "",
                 mode_compare = False,
                 schedule_mode = False,
                 from_to = "",
                 roundtrip = False,
                 roundtrip_compare = False,
                 prefix = "XXXX"
                 ):

        self.mode = mode
        self.schedule_mode = schedule_mode
        self.mode_compare = mode_compare
        self.roundtrip = roundtrip
        self.prefix = prefix
                
        cols_dict = get_name_columns()
        cols = cols_dict[(from_to, self.mode)]

        if self.mode == 1:  # MAP
            self.fieldname_in_protocol = cols["star"]
            self.add_joinField = cols["hash"]
        else:  # AREA
            self.fieldname_in_protocol = cols["hash"]
            self.add_joinField = cols["star"]
        
        if self.roundtrip:
            self.add_joinField = "Destination_aid"

        
        self.roundtrip_compare = roundtrip_compare
        if roundtrip_compare:
            if self.mode == 2:
                self.fieldname_in_protocol = "Destination_aid_1"
            else: 
                self.fieldname_in_protocol = "Origin_aid_1"

        
        self.fieldname_layer = fieldname_layer
        self.parent = parent

        self.layer_buildings = layer_buildings
        self.layer_buildings_name= layer_buildings.name()
        
        self.style_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'styles')

        if self.mode == 2:
            style_filename = "ServiceArea.qml"
        if self.mode == 1:
            style_filename = "Region.qml"
        self.style_file = os.path.normpath(os.path.join(self.style_directory, style_filename))

    def auto_switch_cleaned_to_voronoi(self):
        """
        Если слой зданий из GPKG и его имя содержит '_cleaned',
        но не содержит '_hex' и '_voronoi', то ищем в GPKG первый слой,
        содержащий 'voronoi' в имени, и подменяем self.layer_buildings.
        """
        
        if self.mode_compare:
            return  # логика работает только если НЕ сравнение

        # Проверяем, что слой из GPKG
        src = self.layer_buildings.dataProvider().dataSourceUri()
        if ".gpkg" not in src.lower():
            return

        layer_name = self.layer_buildings.name()

        # Проверяем условия
        if "_cleaned" not in layer_name:
            return
        if "_hex" in layer_name or "_voronoi" in layer_name:
            return

        # Путь к gpkg
        gpkg_path = src.split("|")[0]

        # Получаем список всех слоёв в GPKG
        
        ds = ogr.Open(gpkg_path)
        if ds is None:
            return

        layer_count = ds.GetLayerCount()
        voronoi_layer_name = None

        for i in range(layer_count):
            l = ds.GetLayerByIndex(i)
            if l is None:
                continue
            lname = l.GetName()
            if "voronoi" in lname.lower():
                voronoi_layer_name = lname
                break  # берём первый найденный

        if voronoi_layer_name is None:            
            return

        # Загружаем найденный слой
        uri_voronoi = f"{gpkg_path}|layername={voronoi_layer_name}"
        test_layer = QgsVectorLayer(uri_voronoi, voronoi_layer_name, "ogr")

        if test_layer.isValid():
            self.layer_buildings = test_layer
            self.layer_buildings_name = test_layer.name()
            self.parent.textLog.append(
                f'<b>Auto‑switch:</b> using <font color="green">{voronoi_layer_name}</font> instead of cleaned layer.'
            )

        ds = None  
                   
    
    def make_join(self):
        
        join_info = QgsVectorLayerJoinInfo()
        join_info.setJoinLayer(self.protocol_layer)
        

        if self.roundtrip:
            #join_info.setJoinFieldName("Destination_aid_1")            
            join_info.setJoinFieldName("Origin_aid")                        
            
        else:
            join_info.setJoinFieldName(self.fieldname_in_protocol)      

        if self.roundtrip_compare:
            if self.mode == 1:  # MAP
                join_info.setJoinFieldName("Destination_aid")                        
            else:
                join_info.setJoinFieldName("Origin_aid")                        


        join_info.setTargetFieldName(self.fieldname_layer)
        join_info.setUsingMemoryCache(True)
        join_info.setPrefix(f'{self.prefix}_')        
        
        if not self.mode_compare:
            joinField = [self.targetField_base]            
            if self.roundtrip or self.mode == 2: # roundtrip or area
                joinField =  [self.add_joinField, self.targetField_base]                
            join_info.setJoinFieldNamesSubset(joinField)

        self.layer_clone.addJoin(join_info)

        self.layer_clone.triggerRepaint()

        field_name = self.targetField_base

        return field_name

    def generate_gradient(self, start_color, mid_color, end_color, num_steps):
        gradient = []

        if num_steps <= 1:
            return [start_color.name()]

        start_rgb = start_color.getRgb()
        mid_rgb = mid_color.getRgb()
        end_rgb = end_color.getRgb()

        for i in range(num_steps):
            x = i / (num_steps - 1)  # от 0 до 1

            if x <= 0.5:
                # интерполяция между start и mid
                t = x / 0.5  # 0..1
                r = int(start_rgb[0] + (mid_rgb[0] - start_rgb[0]) * t)
                g = int(start_rgb[1] + (mid_rgb[1] - start_rgb[1]) * t)
                b = int(start_rgb[2] + (mid_rgb[2] - start_rgb[2]) * t)
            else:
                # интерполяция между mid и end
                t = (x - 0.5) / 0.5  # 0..1
                r = int(mid_rgb[0] + (end_rgb[0] - mid_rgb[0]) * t)
                g = int(mid_rgb[1] + (end_rgb[1] - mid_rgb[1]) * t)
                b = int(mid_rgb[2] + (end_rgb[2] - mid_rgb[2]) * t)

            gradient.append(QColor(r, g, b).name())

        return gradient

    def add_thematic_map_gpkg (self, path_gpkg, table_name, aliase, type_compare=''):

        self.auto_switch_cleaned_to_voronoi()

        self.type_compare = type_compare
        path_gpkg = os.path.normpath(path_gpkg).replace("\\", "/")
        self.path_protokol = path_gpkg
        self.file_name = table_name  # В данном контексте имя таблицы выступает как имя файла

        uri = f"{path_gpkg}|layername={table_name}"

        # Создаем слой через провайдер 'ogr' (используется для GPKG, Shapefile и др.)
        self.protocol_layer = QgsVectorLayer(uri, aliase, "ogr")
        
        fields = self.protocol_layer.fields()

        #print([f.name() for f in fields])
        
        self.targetField_base = fields[-1].name()
        if self.roundtrip:
            self.targetField_base = "Duration_ave"

        if self.mode_compare:
            self.add_name_field1 = fields[-3].name()
            self.add_name_field2 = fields[-2].name()

        if self.protocol_layer.featureCount() == 0:
            self.parent.textLog.append(f'<a><b><font color="red">Protocol {self.file_name} is empty. Visualization skipped.</font> </b></a>')
            return

        if self.protocol_layer.featureCount() == 1:
            self.parent.textLog.append(f'<a><b><font color="red">Protocol {self.file_name} contains 1 record only. Visualization skipped.</font> </b></a>')
            return

        if self.protocol_layer.featureCount() > 0:
            QgsProject.instance().addMapLayer(self.protocol_layer, False)
           
            insert_layer_ontop (self.protocol_layer)
         
            self.max_value = 0
            self.max_abs_value = 0
            data_provider = self.protocol_layer.dataProvider()

            for feature in data_provider.getFeatures():                
                value = feature[self.targetField_base]
                
                if value is not None:
                    if self.max_value == 0 or value > self.max_value:
                        self.max_value = value

                    abs_value = abs(value)  # Вычисляем абсолютное значение
                    if abs_value > self.max_abs_value:
                        self.max_abs_value = abs_value  # Обновляем максимальное абсолютное значение
                    
        # make clone
        self.layer_clone = self.layer_buildings.clone()
        
        self.layer_clone.setName(f'{aliase}')

        QgsProject.instance().addMapLayer(self.layer_clone, False)
        insert_layer_ontop (self.layer_clone)
        
        self.parent.setMessage(f'Joining...')
        QApplication.processEvents()
        self.targetField = self.make_join()

        self.targetField_base = f'{self.prefix}_{self.targetField_base}'

        self.parent.setMessage(f'Establishing symbology...')
        QApplication.processEvents()

        if self.type_compare != "":
            self.slyle_compare()
        else:
            if self.mode == 2:                  
                self.style_ServiceArea()            
            if self.mode == 1:
                self.slyle_Region()       
        
        
    def slyle_compare(self):
        
        if self.type_compare == "CompareFirstOnly":
            style_filename = "CompareFirstOnly.qml"
        elif self.type_compare == "CompareSecondOnly":
            style_filename = "CompareSecondOnly.qml"
        elif self.type_compare == "DifferenceRegion":
            style_filename = "DifferenceRegion.qml"
        elif self.type_compare == "DifferenceServiceAreas":
            style_filename = "DifferenceServiceAreas.qml"
        #elif self.type_compare == "RatioRelative":
        #    style_filename = "RatioRelative.qml"
        elif self.type_compare == "RatioRelative":
            style_filename = "Ratio.qml"
        elif self.type_compare == "Rel_difference":
            
            # 1. Читаем цвета из QML
            qml_path = os.path.join(self.style_directory, "Rel_difference.qml")
            colors = self.extract_colors_from_qml(qml_path)
            num_classes = len(colors)

            # 2. Квантили
            quantiles = self.compute_quantiles(self.protocol_layer, num_classes)

            # 3. Создаём рендерер
            ranges = []
            for i, (low, up) in enumerate(quantiles):
                sym = QgsSymbol.defaultSymbol(self.layer_clone.geometryType())

                r, g, b, a = map(int, colors[i])
                sym.setColor(QColor(r, g, b, a))
                sym.symbolLayer(0).setStrokeStyle(Qt.NoPen)

                label = f"{low:.1f} – {up:.1f}"
                ranges.append(QgsRendererRange(low, up, sym, label))

            renderer = QgsGraduatedSymbolRenderer(self.targetField_base, ranges)
            renderer.setMode(QgsGraduatedSymbolRenderer.Custom)

            # 4. Применяем
            layer = self.layer_clone
            layer.setRenderer(renderer)
            layer.triggerRepaint()

            QTimer.singleShot(500, lambda: self.refresh_legend(layer))
            return






            

        self.style_file = os.path.normpath(os.path.join(self.style_directory, style_filename))
        layer = self.layer_clone

        # Особый случай для DifferenceRegion
        if self.type_compare == "DifferenceRegion" and self.max_abs_value > 0:
            new_renderer = self.get_render_DifferenceRegion()
            new_renderer.setClassAttribute(self.targetField_base)
            layer.setRenderer(new_renderer)
            layer.triggerRepaint()
            layer.setCustomProperty("showFeatureCount", True)        
            QTimer.singleShot(500, lambda: self.refresh_legend(layer))
            return
        
                
        layer.loadNamedStyle(self.style_file)
        renderer = layer.renderer()
        renderer.setClassAttribute(self.targetField_base)
        layer.triggerRepaint()
        layer.setCustomProperty("showFeatureCount", True)        
        QTimer.singleShot(500, lambda: self.refresh_legend(layer))

        
        if self.type_compare == "RatioRelative":
            old_ranges = renderer.ranges()
            new_ranges = []

            for r in old_ranges:
                sym = r.symbol().clone()
                low = r.lowerValue()
                up = r.upperValue()

                # преобразуем в проценты
                low_p = low 
                up_p = up 

                label = f"{low_p:.0f}% – {up_p:.0f}%"

                new_ranges.append(
                    QgsRendererRange(low, up, sym, label)
                )

            new_renderer = QgsGraduatedSymbolRenderer(self.targetField_base, new_ranges)
            layer.setRenderer(new_renderer)
            layer.triggerRepaint()

            layer.setCustomProperty("showFeatureCount", True)
            QTimer.singleShot(500, lambda: self.refresh_legend(layer))
            return
        

        if self.type_compare in ("CompareFirstOnly", "CompareSecondOnly"):
            old_ranges = renderer.ranges()
            new_ranges = []
            for r in old_ranges:
                sym = r.symbol().clone()
                label = r.label()
                new_range = QgsRendererRange(
                    0,                      
                    self.max_value,         
                    sym,
                    label
                )
                new_ranges.append(new_range)
            new_renderer = QgsGraduatedSymbolRenderer(
                self.targetField_base,
                new_ranges
            )
            #new_renderer.setMode(renderer.mode())
            layer.setRenderer(new_renderer)
            layer.triggerRepaint()

            layer.setCustomProperty("showFeatureCount", True)        
            QTimer.singleShot(500, lambda: self.refresh_legend(layer))
        
    def get_render_DifferenceRegion(self):
        layer = self.layer_clone
        layer.loadNamedStyle(self.style_file)
    
        renderer = layer.renderer()
        ranges = renderer.ranges()
        
        new_max = self.round_up_to_nearest(self.max_abs_value)
        new_min = -new_max
        num_classes = 9

        new_ranges = []
        new_step = (new_max - new_min) / num_classes

        start_color = ranges[0].symbol().color()
        mid_color = ranges[len(ranges) // 2].symbol().color()
        end_color = ranges[-1].symbol().color()
        colors = self.generate_gradient(start_color, mid_color, end_color, num_classes)

        for i in range(num_classes):
            lower_value = new_min + i * new_step
            upper_value = lower_value + new_step
            if upper_value > new_max:
                upper_value = new_max

            symbol = ranges[i % len(ranges)].symbol().clone()
            
            # --- Настройка отсутствия рамки и цвета ---
            if symbol.symbolLayerCount() > 0:
                symbol_layer = symbol.symbolLayer(0)
                symbol_layer.setFillColor(QColor(colors[i]))
                symbol_layer.setStrokeStyle(Qt.NoPen) # Убираем рамку
            # ------------------------------------------

            label = f"{lower_value:.0f} - {upper_value:.0f}"
            new_ranges.append(QgsRendererRange(lower_value, upper_value, symbol, label))

        new_renderer = QgsGraduatedSymbolRenderer('', new_ranges)
        #new_renderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
        new_renderer.setClassificationMethod(QgsClassificationEqualInterval())
        new_renderer.setClassAttribute(self.targetField)
    
        return new_renderer
    
    def slyle_Region(self):

        layer = self.layer_clone
        layer.loadNamedStyle(self.style_file)
        
        renderer = layer.renderer()
        ranges = renderer.ranges()

        #old_min = ranges[0].lowerValue()
        old_min = 0
        new_max = self.round_up_to_nearest(self.max_value)  
        num_classes = len(ranges)

        new_ranges = []
        new_step = (new_max - old_min) / num_classes

        for i in range(num_classes):
            lower_value = old_min + i * new_step
            upper_value = lower_value + new_step
            if upper_value > new_max:
                upper_value = new_max

            # Клонируем символ из исходного стиля
            symbol = ranges[i].symbol().clone()
            
            # Убираем рамку и настраиваем заливку
            if symbol.symbolLayerCount() > 0:
                symbol_layer = symbol.symbolLayer(0)                
                symbol_layer.setStrokeStyle(Qt.NoPen)

            label = f"{lower_value:.0f} - {upper_value:.0f}"
            new_ranges.append(QgsRendererRange(lower_value, upper_value, symbol, label))

        # Создаём новый рендерер
        new_renderer = QgsGraduatedSymbolRenderer('', new_ranges)        
        new_renderer.setClassificationMethod(QgsClassificationEqualInterval())
        new_renderer.setClassAttribute(self.targetField)
        
        layer.setRenderer(new_renderer)
        layer.renderer().setClassAttribute(self.targetField_base)
        layer.triggerRepaint()

        layer.setCustomProperty("showFeatureCount", True)        
        QTimer.singleShot(500, lambda: self.refresh_legend(layer))


    def style_ServiceArea(self):

        layer = self.layer_clone
        layer.loadNamedStyle(self.style_file)
        
        renderer = layer.renderer()
        ranges = renderer.ranges()

        old_min = ranges[0].lowerValue()
        old_step = ranges[0].upperValue() - old_min

        new_max = self.max_value  
        num_classes = int((new_max - old_min) // old_step)
        if (new_max - old_min) % old_step != 0:
            num_classes += 1
        num_classes = max(num_classes, 2)

        start_color = ranges[0].symbol().color()
        mid_color = ranges[len(ranges) // 2].symbol().color()
        end_color = ranges[-1].symbol().color()
        colors = self.generate_gradient(start_color, mid_color, end_color, num_classes)

        new_ranges = []
        for i in range(num_classes):
            low = old_min + i * old_step
            up = low + old_step
            
            # Берем базовый символ
            symbol = ranges[min(i, len(ranges) - 1)].symbol().clone()
            
            # Настраиваем слой символа
            if symbol.symbolLayerCount() > 0:
                sl = symbol.symbolLayer(0)
                sl.setFillColor(QColor(colors[i]))
                sl.setStrokeStyle(Qt.NoPen) # Убираем рамку

            if i < len(ranges):
                label = ranges[i].label()
            else:
                label = f"{round(low/60)} - {round(up/60)} min"

            new_ranges.append(QgsRendererRange(low, up, symbol, label))

        new_renderer = QgsGraduatedSymbolRenderer('', new_ranges)
        new_renderer.setClassificationMethod(QgsClassificationEqualInterval())
        new_renderer.setClassAttribute(self.targetField)
        
        layer.setRenderer(new_renderer)
        layer.renderer().setClassAttribute(self.targetField_base)
        layer.triggerRepaint()

        layer.setCustomProperty("showFeatureCount", True)        
        QTimer.singleShot(500, lambda: self.refresh_legend(layer))

    def refresh_legend(self, layer):
            root = QgsProject.instance().layerTreeRoot()
            node = root.findLayer(layer.id())
            if node:                
                node.setCustomProperty("showFeatureCount", True)                
                root.customPropertyChanged.emit(node, "showFeatureCount")

    def round_up_to_nearest(self, x):
        
        if x <= 0:
            return 0
        order_of_magnitude = 10 ** math.floor(math.log10(x))  # Порядок величины числа
        rounded_value = math.ceil(x / order_of_magnitude) * order_of_magnitude  # Округление вверх
        return rounded_value
    
    def compute_quantiles(self, layer, num_classes=7):
        """
        Вычисляет квантильные интервалы по последнему полю слоя.
        Возвращает список пар (low, up).
        """

        # Берём имя последнего поля
        field_name = layer.fields()[-1].name()

        values = []
        for f in layer.getFeatures():
            v = f[field_name]
            if v is not None:
                try:
                    values.append(float(v))
                except:
                   pass


        values.sort()
        n = len(values)
        step = n / num_classes

        boundaries = []
        for i in range(num_classes + 1):
            idx = int(round(i * step))
            if idx >= n:
                idx = n - 1
            boundaries.append(values[idx])

        ranges = []
        for i in range(num_classes):
            ranges.append((boundaries[i], boundaries[i+1]))

        return ranges


    def extract_colors_from_qml(self, qml_path):
        
        # читаем файл
        with open(qml_path, "r", encoding="utf-8") as f:
            text = f.read()

        # находим блок <symbols>...</symbols>
        symbols_match = re.search(
            r"<symbols>(.*?)</symbols>",
            text,
            flags=re.S
        )
        if not symbols_match:
            raise ValueError("No <symbols> block found in QML")

        symbols_block = symbols_match.group(1)

        # ищем символы name="0"…"6" и их цвета
        matches = re.findall(
            r'<symbol[^>]+name="(\d+)"[\s\S]*?<Option[^>]+name="color" value="([^"]+)"',
            symbols_block
        )

        if not matches:
            raise ValueError("No symbol colors found in QML")

        # создаём массив нужной длины
        max_idx = max(int(idx) for idx, _ in matches)
        colors = [None] * (max_idx + 1)

        # заполняем
        for idx, color in matches:
            rgba = color.split(",")[:4]  # R,G,B,A
            colors[int(idx)] = rgba

        # проверяем, что все цвета есть
        if any(c is None for c in colors):
            raise ValueError(f"Missing colors for some symbols: {colors}")

        return colors

