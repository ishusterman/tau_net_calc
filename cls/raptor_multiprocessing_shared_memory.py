import os
import sys
import time
import cProfile
import pstats
import io
import pickle
from multiprocessing import Process, cpu_count
from multiprocessing.sharedctypes import RawArray, RawValue
from ctypes import c_char, c_int

from qgis.core import QgsApplication, QgsVectorLayer, QgsProject
from functools import partial

# Убедитесь, что все необходимые пути добавлены
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from query_file import myload_all_dict, runRaptorWithProtocol
from common import time_to_seconds

# --- Класс и функции для дочернего процесса ---
class config:
    def __init__(self, config_dict):
        self.config = config_dict['config']
        self.folder_name = config_dict['folder_name']
        self.alias = config_dict['alias']
        self.path_to_pkl = config_dict['path_to_pkl']

def _deserialize_from_shared_memory(data_array, size_value):
    """Десериализует данные из общей памяти."""
    data_bytes = data_array[:size_value.value]
    return pickle.loads(data_bytes)

def create_output_in_process(mode, time_str, protocol_type, timetable_mode, sources, params,
                             layer_buildings_path,
                             stops_dict_shared, stoptimes_dict_shared, footpath_dict_shared,
                             routes_by_stop_dict_shared, idx_by_route_stop_dict_shared,
                             stop_ids_set_shared, path_to_pkl, process_id):
    
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.40.2", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    layer_buildings = QgsVectorLayer(layer_buildings_path, "Layer", "ogr")
    if not layer_buildings.isValid():
        qgs.exitQgis()
        return

    if sources:
        params.alias = str(sources[0])
    else:
        params.alias = "no_source"

    D_TIME = time_to_seconds(time_str)
    
    # --- Десериализация данных из общей памяти ---
    deserialize_start = time.time()
    stops_dict = _deserialize_from_shared_memory(*stops_dict_shared)
    stoptimes_dict = _deserialize_from_shared_memory(*stoptimes_dict_shared)
    footpath_dict = _deserialize_from_shared_memory(*footpath_dict_shared)
    routes_by_stop_dict = _deserialize_from_shared_memory(*routes_by_stop_dict_shared)
    idx_by_route_stop_dict = _deserialize_from_shared_memory(*idx_by_route_stop_dict_shared)
    stop_ids_set = _deserialize_from_shared_memory(*stop_ids_set_shared)
    deserialize_end = time.time()
    print(f"[{os.getpid()}] Время на десериализацию данных из общей памяти: {deserialize_end - deserialize_start:.2f} сек.")
    
    dictionary = (
        stops_dict, stoptimes_dict, footpath_dict,
        routes_by_stop_dict, idx_by_route_stop_dict, stop_ids_set
    )
    
    # --- Профилирование runRaptorWithProtocol в дочернем процессе ---
    #pr_child = cProfile.Profile()
    #pr_child.enable()
    
    runRaptorWithProtocol(
        self=params, sources=sources, raptor_mode=mode, protocol_type=protocol_type,
        timetable_mode=timetable_mode, D_TIME=D_TIME, selected_only1=False,
        selected_only2=False, dictionary=dictionary, shift_mode=True,
        layer_dest_obj=layer_buildings, layer_origin_obj=layer_buildings,
        path_to_pkl=path_to_pkl
    )
    
    #pr_child.disable()
    
    # Сохранение результатов профилирования в читаемый текстовый файл
    #output_filename_txt = f"profile_output_{os.getpid()}_{process_id}.txt"
    #with open(output_filename_txt, "w") as f:
    #    ps = pstats.Stats(pr_child, stream=f).sort_stats('cumulative')
    #    ps.print_stats()
        
    #print(f"[{os.getpid()}] Результаты профилирования сохранены в файл: {output_filename_txt}")
    
    qgs.exitQgis()

class raptor_multiprocessing:
    def __init__(self, params, layer_buildings_path):
        self.params = params
        self.layer_buildings_path = layer_buildings_path
                
    def run_parallel(self, gen_instance, mode, time_start_str, protocol_type, timetable_mode, all_sources, num_processes=None):
        if num_processes is None:
            num_processes = cpu_count()
        
        # Замер времени загрузки словарей
        dict_load_start = time.time()
        (stops_dict, stoptimes_dict, footpath_dict, routes_by_stop_dict, idx_by_route_stop_dict, stop_ids_set) = myload_all_dict(
            self=None,
            PathToNetwork=gen_instance.params.path_to_pkl,
            mode=mode,
            RunOnAir=(gen_instance.params.config['Settings']['RunOnAir'] == "True"),
        )
        dict_load_end = time.time()
        print(f"Словари загружены. Время загрузки: {dict_load_end - dict_load_start:.2f} сек.")

        # --- Сериализация и создание общей памяти ---
        shared_memory_creation_start = time.time()
        
        stops_dict_bytes = pickle.dumps(stops_dict)
        stoptimes_dict_bytes = pickle.dumps(stoptimes_dict)
        footpath_dict_bytes = pickle.dumps(footpath_dict)
        routes_by_stop_dict_bytes = pickle.dumps(routes_by_stop_dict)
        idx_by_route_stop_dict_bytes = pickle.dumps(idx_by_route_stop_dict)
        stop_ids_set_bytes = pickle.dumps(stop_ids_set)
        
        # Создаем массивы в общей памяти
        stops_dict_array = RawArray(c_char, len(stops_dict_bytes))
        stops_dict_array[:] = stops_dict_bytes
        stops_dict_size = RawValue(c_int, len(stops_dict_bytes))

        stoptimes_dict_array = RawArray(c_char, len(stoptimes_dict_bytes))
        stoptimes_dict_array[:] = stoptimes_dict_bytes
        stoptimes_dict_size = RawValue(c_int, len(stoptimes_dict_bytes))

        footpath_dict_array = RawArray(c_char, len(footpath_dict_bytes))
        footpath_dict_array[:] = footpath_dict_bytes
        footpath_dict_size = RawValue(c_int, len(footpath_dict_bytes))

        routes_by_stop_dict_array = RawArray(c_char, len(routes_by_stop_dict_bytes))
        routes_by_stop_dict_array[:] = routes_by_stop_dict_bytes
        routes_by_stop_dict_size = RawValue(c_int, len(routes_by_stop_dict_bytes))

        idx_by_route_stop_dict_array = RawArray(c_char, len(idx_by_route_stop_dict_bytes))
        idx_by_route_stop_dict_array[:] = idx_by_route_stop_dict_bytes
        idx_by_route_stop_dict_size = RawValue(c_int, len(idx_by_route_stop_dict_bytes))

        stop_ids_set_array = RawArray(c_char, len(stop_ids_set_bytes))
        stop_ids_set_array[:] = stop_ids_set_bytes
        stop_ids_set_size = RawValue(c_int, len(stop_ids_set_bytes))

        shared_memory_creation_end = time.time()
        print(f"Общая память создана. Время создания: {shared_memory_creation_end - shared_memory_creation_start:.2f} сек.")

        num_processes = 8
        chunk_size = (len(all_sources) + num_processes - 1) // num_processes
        source_chunks = [all_sources[i:i + chunk_size] for i in range(0, len(all_sources), chunk_size)]

        # --- Замеры времени на создание и завершение процессов ---
        process_creation_start = time.time()
        processes = []
        for i, chunk in enumerate(source_chunks):
            p = Process(
                target=create_output_in_process,
                args=(
                    mode, time_start_str, protocol_type, timetable_mode, chunk, gen_instance.params,
                    gen_instance.layer_buildings_path, 
                    (stops_dict_array, stops_dict_size), 
                    (stoptimes_dict_array, stoptimes_dict_size), 
                    (footpath_dict_array, footpath_dict_size),
                    (routes_by_stop_dict_array, routes_by_stop_dict_size), 
                    (idx_by_route_stop_dict_array, idx_by_route_stop_dict_size), 
                    (stop_ids_set_array, stop_ids_set_size),
                    gen_instance.params.path_to_pkl, i
                )
            )
            processes.append(p)
            p.start()
        process_creation_end = time.time()
        print(f"Время создания процессов: {process_creation_end - process_creation_start:.2f} сек.")

        process_join_start = time.time()
        for p in processes:
            p.join()
        process_join_end = time.time()
        print(f"Время ожидания завершения процессов: {process_join_end - process_join_start:.2f} сек.")

# --- Основной блок с профилированием родительского процесса ---
if __name__ == '__main__':
    pr = cProfile.Profile()
    pr.enable() # Запускаем cProfile в родительском процессе
    
    start_time = time.time()
    
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.40.2", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    path_to_result = r'c:\temp\test_generator'
    os.makedirs(path_to_result, exist_ok=True)
    
    config_dict = {
        'config': {'Settings': {'Min_transfer': "0", 'Max_transfer': "2", 'MaxExtraTime': "10",
                                 'Speed': "3.6", 'MaxWalkDist1': "400", 'MaxWalkDist2': "300",
                                 'MaxWalkDist3': "400", 'MaxTimeTravel': "40", 'MaxWaitTime': "15",
                                 'MaxWaitTimeTransfer': "15", 'TimeInterval': "1", 'Layer': "Layer",
                                 'Layer_field': "", 'LayerDest': "LayerDest", 'LayerDest_field': "osm_id",
                                 'LayerViz': "", 'LayerViz_field': "osm_id", 'Field_ch': "", 'RunOnAir': "False"}},
        'folder_name': path_to_result, 'alias': 'output1', 'path_to_pkl': r'c:\doc\Igor\GIS\PKL\exp_08_2025\ISR_2018'
    }
    params = config(config_dict)
    
    filename = r"c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_visio\TLV_buildings_hex_200m.shp"
    layer = QgsVectorLayer(filename, "buildings", "ogr")
    
    osm_ids = []
    count = 0
    for feature in layer.getFeatures():
        count += 1
        if count > 100:
            break
        osm_ids.append(feature["osm_id"])
    sources = osm_ids
    
    mode_raptor = 1
    time_start_str = "07:59:59"
    protocol_type = 2
    timetable_mode = False
    
    file_path = r"c:\doc\Igor\GIS\prj\exp_08_2025\TAMA_buildings.shp"
    
    gen = raptor_multiprocessing(params, file_path)
    gen.run_parallel(gen, mode_raptor, time_start_str, protocol_type, timetable_mode, sources)
    
    qgs.exitQgis()
    
    elapsed = time.time() - start_time
    print(f"Finish. Общее время выполнения: {elapsed:.2f} сек.")

    # --- Завершаем профилирование и выводим результаты ---
    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(15)
    print("\n--- Профилирование родительского процесса ---")
    print(s.getvalue())