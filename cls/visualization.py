import os
import math
import numpy as np

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsVectorLayerJoinInfo,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
    QgsLayerTreeLayer,
    QgsClassificationEqualInterval,
    QgsFeatureRequest
    )

from common import insert_layer_ontop

from qgis.utils import iface

class visualization:
    def __init__(self,
                 parent,
                 layer_buildings_name = "",
                 mode = "",
                 fieldname_layer = "",
                 mode_compare = False,
                 schedule_mode = False
                 ):

        self.mode = mode
        self.schedule_mode = schedule_mode
        self.mode_compare = mode_compare
        

        if self.mode == 1:  # MAP
            self.fieldname_in_protocol = "Origin_ID"
        else:  # AREA
            self.fieldname_in_protocol = "Destination_ID"

        self.fieldname_layer = fieldname_layer
        self.parent = parent

        self.layer_buildings_name = layer_buildings_name
        self.layer_buildings = QgsProject.instance(
        ).mapLayersByName(self.layer_buildings_name)[0]
        
        self.style_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'styles')

        if self.mode == 2:
            style_filename = "ServiceArea.qml"
        if self.mode == 1:
            style_filename = "Region.qml"
        self.style_file = os.path.normpath(os.path.join(self.style_directory, style_filename))
        
    def make_join(self):
        
        join_info = QgsVectorLayerJoinInfo()
        join_info.setJoinLayer(self.protocol_layer)
        join_info.setJoinFieldName(self.fieldname_in_protocol)
        join_info.setTargetFieldName(self.fieldname_layer)
        join_info.setUsingMemoryCache(True)
        join_info.setPrefix('')
        join_info.setJoinFieldNamesSubset([self.targetField_base])

        if self.mode_compare:
            join_info.setJoinFieldNamesSubset(
                [self.add_name_field1, self.add_name_field2, self.targetField_base])
        else:
            join_info.setJoinFieldNamesSubset([self.targetField_base])

        self.layer_clone.addJoin(join_info)
        self.layer_clone.triggerRepaint()

        field_name = self.targetField_base

        return field_name

    def generate_gradient(self, start_color, mid_color, end_color, num_steps):
        gradient = []
        half_steps = int(num_steps / 2)
    
        # Градиент от start_color до mid_color
        start_rgb = start_color.getRgb()
        mid_rgb = mid_color.getRgb()
        for i in range(half_steps):
            t = i / (half_steps - 1) if half_steps > 1 else 0
            r = int(start_rgb[0] + (mid_rgb[0] - start_rgb[0]) * t)
            g = int(start_rgb[1] + (mid_rgb[1] - start_rgb[1]) * t)
            b = int(start_rgb[2] + (mid_rgb[2] - start_rgb[2]) * t)
            gradient.append(QColor(r, g, b).name())
    
        # Градиент от mid_color до end_color
        end_rgb = end_color.getRgb()
        for i in range(half_steps, num_steps):
            t = (i - half_steps) / (num_steps - half_steps - 1) if (num_steps - half_steps) > 1 else 0
            r = int(mid_rgb[0] + (end_rgb[0] - mid_rgb[0]) * t)
            g = int(mid_rgb[1] + (end_rgb[1] - mid_rgb[1]) * t)
            b = int(mid_rgb[2] + (end_rgb[2] - mid_rgb[2]) * t)
            gradient.append(QColor(r, g, b).name())
    
        return gradient

    def add_thematic_map(self, path_protokol, aliase, set_min_value=float('inf'), type_compare = ''):
                      
        self.type_compare = type_compare
        self.path_protokol = os.path.normpath(path_protokol)
        self.file_name = os.path.splitext(os.path.basename(path_protokol))[0]
        self.path_protokol = self.path_protokol.replace("\\", "/")

        uri = f"file:///{self.path_protokol}?type=csv&maxFields=10000&detectTypes=yes&geomType=none&subsetIndex=no&watchFile=no"

        self.protocol_layer = QgsVectorLayer(uri, aliase, "delimitedtext")
        
        fields = self.protocol_layer.fields()
        self.targetField_base = fields[-1].name()

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

            
            # filter on self.targetField_base  > 0 
            #if self.mode == 1: # Region
            #    expression = f'"{self.targetField_base}" > 0'
            #    self.protocol_layer.setSubsetString(expression)
            
            insert_layer_ontop (self.protocol_layer)
                        
            # if variation Origin_ID > 1 thne filter on first value Origin_ID 
         
            if self.mode == 2 and self.schedule_mode: # AREA
       
                #unique_count = len(self.protocol_layer.uniqueValues(self.protocol_layer.fields().indexFromName("Origin_ID")))    
                
                #if unique_count > 1:
                #    first_feature = next(self.protocol_layer.getFeatures())
                #    origin_id_value = first_feature['Origin_ID']
                #    expression = f'"Origin_ID" = {origin_id_value}'
                #    self.protocol_layer.setSubsetString(expression)
                """
                first_feature = None
                for feature in self.protocol_layer.getFeatures(QgsFeatureRequest().setLimit(1)):
                    first_feature = feature
                    break
                
                if first_feature and first_feature['Origin_ID'] is not None:
                    origin_id_value = first_feature['Origin_ID']
                    expression = f'"Origin_ID" = {origin_id_value}'
                    self.protocol_layer.setSubsetString(expression)
                """
    

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
        self.layer_clone.setName(aliase)

        QgsProject.instance().addMapLayer(self.layer_clone, False)
        insert_layer_ontop (self.layer_clone)
        
        self.parent.setMessage(f'Joining...')
        QApplication.processEvents()
        self.targetField = self.make_join()

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
        elif self.type_compare == "RatioRelative":
            style_filename = "RatioRelative.qml"
        else:
            print(f"Unknown compare type: {self.type_compare}")
            return

        self.style_file = os.path.normpath(os.path.join(self.style_directory, style_filename))
        layer = self.layer_clone

        # Особый случай для DifferenceRegion
        if self.type_compare == "DifferenceRegion" and self.max_abs_value > 0:
            new_renderer = self.get_render_DifferenceRegion()
            layer.setRenderer(new_renderer)
            layer.triggerRepaint()
            return
        
        layer.loadNamedStyle(self.style_file)
        renderer = layer.renderer()
        renderer.setClassAttribute(self.targetField_base)
        layer.triggerRepaint()


    def get_render_DifferenceRegion(self):
        layer = self.layer_clone
        layer.loadNamedStyle(self.style_file)
    
        renderer = layer.renderer()
        ranges = renderer.ranges()
        
        new_max = self.round_up_to_nearest(self.max_abs_value)  # Максимальное абсолютное значение, округлённое вверх
        new_min = -new_max  # Симметричный минимум
        num_classes = 9  # Требуется 9 диапазонов

        new_ranges = []
        new_step = (new_max - new_min) / num_classes  # Новый размер класса

        # Генерация градиента цветов
        start_color = ranges[0].symbol().color()
        mid_color = ranges[len(ranges) // 2].symbol().color()
        end_color = ranges[-1].symbol().color()
        colors = self.generate_gradient(start_color, mid_color, end_color, num_classes)

        for i in range(num_classes):
            
            lower_value = new_min + i * new_step
            upper_value = lower_value + new_step
            if upper_value > new_max:
                upper_value = new_max  # Не допускаем выхода за максимальное значение

            # Клонируем символ и создаем новый интервал
            symbol = ranges[i % len(ranges)].symbol().clone()  # Повторяем символы, если их меньше 9
            symbol.setColor(QColor(colors[i]))
            label = f"{lower_value:.0f} - {upper_value:.0f}"
            new_ranges.append(QgsRendererRange(lower_value, upper_value, symbol, label))

        # Создаём новый рендерер
        new_renderer = QgsGraduatedSymbolRenderer('', new_ranges)
        new_renderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
        new_renderer.setClassAttribute(self.targetField)
    
        return new_renderer
    


    def slyle_Region (self):
        layer = self.layer_clone
        layer.loadNamedStyle(self.style_file)
        
        renderer = layer.renderer()
        ranges = renderer.ranges()

        old_min = ranges[0].lowerValue()  # Минимальное значение
        new_max = self.round_up_to_nearest(self.max_value)  
        num_classes = len(ranges)

        new_ranges = []

        new_step = (new_max - old_min) / num_classes  # Новый размер класса

        for i in range(num_classes):
            lower_value = old_min + i * new_step
            upper_value = lower_value + new_step
            if upper_value > new_max:
                upper_value = new_max  # Не допускаем, чтобы верхняя граница выходила за максимальное значение

            # Клонируем символ и создаем новый интервал
            symbol = ranges[i].symbol().clone()
            label = f"{lower_value:.0f} - {upper_value:.0f}"
            new_ranges.append(QgsRendererRange(lower_value, upper_value, symbol, label))

        # Создаём новый рендерер
        new_renderer = QgsGraduatedSymbolRenderer('', new_ranges)
        new_renderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
        new_renderer.setClassAttribute(self.targetField)
        layer.setRenderer(new_renderer)
        layer.renderer().setClassAttribute(self.targetField_base)
        layer.triggerRepaint()
    
    def style_ServiceArea(self):
        layer = self.layer_clone
        layer.loadNamedStyle(self.style_file)
        
        renderer = layer.renderer()
        ranges = renderer.ranges()

        old_min = ranges[0].lowerValue()  # Минимальное значение
        old_step = ranges[0].upperValue() - old_min  # Размер одного класса

        new_max = self.max_value  
        num_classes = int((new_max - old_min) // old_step)
        if (new_max - old_min) % old_step != 0:
            num_classes += 1
        num_classes = max(num_classes, 2)  # Минимум 2 класса

        new_ranges = []

        # Сохраняем старые интервалы, если их максимальное значение больше или равно новому максимуму
        for num, range_ in enumerate(ranges):
            if num + 1 <= num_classes:
                new_ranges.append(range_)

        start_color = ranges[0].symbol().color()
        mid_color = ranges[len(ranges) // 2].symbol().color()
        end_color = ranges[-1].symbol().color()
        colors = self.generate_gradient(start_color, mid_color, end_color, num_classes)

        for i, range_ in enumerate(new_ranges):
            symbol = range_.symbol().clone()  # Клонируем существующий символ
            symbol.setColor(QColor(colors[i]))  # Применяем новый цвет из градиента
            new_ranges[i] = QgsRendererRange(range_.lowerValue(), range_.upperValue(), symbol, range_.label())


        # Добавляем новые интервалы, если их нет
        for i in range(len(new_ranges), num_classes):
            new_min = old_min + i * old_step
            new_max = new_min + old_step

            # Берём символ из ближайшего существующего класса
            symbol = ranges[min(i, len(ranges) - 1)].symbol().clone()
            symbol.setColor(QColor(colors[i]))

            new_min_minutes = round(new_min / 60)
            new_max_minutes = round(new_max / 60)

            new_range = QgsRendererRange(
            new_min, new_max, symbol, f"{new_min_minutes} - {new_max_minutes} min" )
            new_ranges.append(new_range)

        # Создаём новый рендерер
        new_renderer = QgsGraduatedSymbolRenderer('', new_ranges)
        #new_renderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
        new_renderer.setClassificationMethod(QgsClassificationEqualInterval())
        
        new_renderer.setClassAttribute(self.targetField)
        layer.setRenderer(new_renderer)
        layer.renderer().setClassAttribute(self.targetField_base)
        layer.triggerRepaint()
    
    def round_up_to_nearest(self, x):
        
        order_of_magnitude = 10 ** math.floor(math.log10(x))  # Порядок величины числа
        rounded_value = math.ceil(x / order_of_magnitude) * order_of_magnitude  # Округление вверх
        return rounded_value