from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject
)
from PyQt5.QtCore import QVariant

# Создаём пустой слой типа LineString
layer = QgsVectorLayer("LineString?crs=EPSG:4326", "rectangle_with_diagonals", "memory")
prov = layer.dataProvider()

# Координаты вершин прямоугольника
A = QgsPointXY(0, 0)
B = QgsPointXY(10, 0)
C = QgsPointXY(10, 10)
D = QgsPointXY(0, 10)

# Список линий (каждая — список точек)
lines = [
    [A, B],  # нижняя сторона
    [B, C],  # правая сторона
    [C, D],  # верхняя сторона
    [D, A],  # левая сторона
    [A, C],  # диагональ 1
    [B, D],  # диагональ 2
]

# Добавляем линии в слой
features = []
for pts in lines:
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPolylineXY(pts))
    features.append(feat)

prov.addFeatures(features)
layer.updateExtents()

# Добавляем слой на карту
QgsProject.instance().addMapLayer(layer)

print("Слой создан: 4 стороны + 2 диагонали")
