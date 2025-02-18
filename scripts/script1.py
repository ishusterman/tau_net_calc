import osmnx as ox

# Определяем bounding box (запад, юг, восток, север)
bbox = (34.73, 32.02, 34.85, 32.15)

# Загружаем граф дорог
G = ox.graph.graph_from_bbox(bbox=bbox, network_type="all")

# Сохранение графа в Shapefile
ox.io.save_graph_geopackage(G, filepath=r"c:\doc\Игорь\GIS\Sumo\data\v3\tel_aviv_2.gpkg")
