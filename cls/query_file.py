import os
from pathlib import Path
import pickle
from datetime import datetime
import pandas as pd
from collections import defaultdict

from osgeo import ogr, gdal
import gc

import cProfile
import pstats
#from collections import Counter
from report import (make_protocol_detailed, 
                    make_protocol_summary                  
                    )

from PyQt5.QtWidgets import QApplication

from footpath_on_projection import cls_footpath_on_projection
from RAPTOR.std_raptor import raptor
from RAPTOR.rev_std_raptor import rev_raptor


from visualization import visualization
from common import (seconds_to_time, 
                    get_existing_path, 
                    get_name_columns,
                    FIELD_ID,
                    fast_write_gpkg,
                    make_service_area_report_gpkg,
                    get_prefix_alias,
                    make_pivot_gpkg)

def myload_all_dict(self, PathToNetwork, mode ):
        path = PathToNetwork
        
        if self is not None:
            self.setMessage("Loading walking paths ...")
            QApplication.processEvents()

        
        base_transfer = 'transfers_dict_projection.pkl'
        filename_transfer = get_existing_path(path, base_transfer)
       
        with open(filename_transfer, 'rb') as file:
            footpath_dict = pickle.load(file)
                
        stop_ids_path = get_existing_path(path, 'stop_ids.pkl')
        stop_ids = pd.read_pickle(stop_ids_path)
        stop_ids_set = set(stop_ids)

        if self is not None:
            #self.progressBar.setValue(2)
            self.setMessage("Loading transit routes ...")
            QApplication.processEvents()

        # 3. Загрузка routes_by_stop_dict
        routes_path = get_existing_path(path, 'routes_by_stop.pkl')
        with open(routes_path, 'rb') as file:
            routes_by_stop_dict = pickle.load(file)

        #if self is not None:
            #self.progressBar.setValue(3)

        # Выбор имен файлов в зависимости от режима (прямой или обратный)
        if mode == 1:
            stops_file = 'stops_dict_pkl.pkl'
            stoptimes_file = 'stoptimes_dict_pkl.pkl'
            idx_file = 'idx_by_route_stop.pkl'
        else:
            stops_file = 'stops_dict_reversed_pkl.pkl'
            stoptimes_file = 'stoptimes_dict_reversed_pkl.pkl'
            idx_file = 'rev_idx_by_route_stop.pkl'


        if self is not None:
            self.setMessage("Loading transit stops ...")
            QApplication.processEvents()
        
        with open(get_existing_path(path, stops_file), 'rb') as file:
            stops_dict = pickle.load(file)

        if self is not None:
            #self.progressBar.setValue(4)
            self.setMessage("Loading transit time schedule ...")
            QApplication.processEvents()


        with open(get_existing_path(path, stoptimes_file), 'rb') as file:
            stoptimes_dict = pickle.load(file)

        if self is not None:
            #self.progressBar.setValue(5)
            self.setMessage("Loading index ...")
            QApplication.processEvents()

        
        with open(get_existing_path(path, idx_file), 'rb') as file:
            idx_by_route_stop_dict = pickle.load(file)

        #if self is not None:
            #self.progressBar.setValue(6)

        return (
            stops_dict,
            stoptimes_dict,
            footpath_dict,
            routes_by_stop_dict,
            idx_by_route_stop_dict,
            stop_ids_set
        )

def verify_break(self):

    

    if getattr(self, 'break_on', False):
        if self.break_on:
            self.lblEstimateTime.setText("")

            self.textLog.append(f'<a><b><font color="red">Raptor Algorithm is interrupted by user</font> </b></a>')
            time_after_computation = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.textLog.append(f'<a>Interrupted at: {time_after_computation}</a>')

                
            self.progressBar.setValue(0)
            self.setMessage("Raptor Algorithm is interrupted by user")
            return True
    return False

def prepare_protocol_region(field, number_bins, time_step, time_step_last, cols_star, is_aggregate=False):
    header_parts = [cols_star]
    grades = []
    
    
    for i in range(1, number_bins + 1):
        curr_top = i * time_step
        header_parts.append(f"{curr_top}m")
        if is_aggregate:
            #header_parts.append(f"sum({field}[{curr_top}m])")
            header_parts.append(f"{curr_top}m_{field}")
        grades.append([-1, curr_top])

    
    if time_step_last > 0:
    
        max_limit = (number_bins * time_step) + time_step_last
        header_parts.append(f"{max_limit}m")
        if is_aggregate:
            header_parts.append(f"{max_limit}m_{field}")
        grades.append([-1, max_limit])

    header_parts.append(f"{field}_total\n")
    return ",".join(header_parts), grades


def runRaptorWithProtocol(self,
                          file_name_gpkg,
                          sources,
                          destinations,
                          raptor_mode,
                          protocol_type,
                          timetable_mode,
                          D_TIME,
                          dictionary,
                          shift_mode,
                          layer_dest_obj,
                          layer_origin_obj,
                          layer_viz,
                          path_to_pkl,
                          MaxExtraTime,
                          roundtrip_mode = False,
                          roundtrip_cycle_all = 1,
                          roundtrip_cycle_current = 1):

    short_result = {}

    df_min_endtime_all = []
    df_min_duration_all = []
    table_name_list = []

    header_dict = defaultdict(list)
    df_min_duration_all_dict = defaultdict(list)
    df_min_endtime_all_dict = defaultdict(list)

    #file_name = Path(file_name_gpkg).stem

    file_name = get_prefix_alias(True, 
                                protocol_type, 
                                raptor_mode, 
                                timetable_mode,
                                roundtrip_mode 
                                )
    
    count = len(sources)
    if hasattr(self, 'progressBar'):
        self.progressBar.setMaximum(count + 1)
        self.progressBar.setValue(0)

    MAX_TRANSFER = int(self.config['Settings']['Max_transfer'])
    MIN_TRANSFER = int(self.config['Settings']['Min_transfer'])
        
    Speed = float(self.config['Settings']['Speed'].replace(',', '.')) * 1000 / 3600                    # from km/h to m/sec
    # dist to time
    MaxWalkDist1 = int(self.config['Settings']['MaxWalkDist1'])/Speed
    # dist to time
    MaxWalkDist2 = int(self.config['Settings']['MaxWalkDist2'])/Speed
    # dist to time
    MaxWalkDist3 = int(self.config['Settings']['MaxWalkDist3'])/Speed

    MaxTimeTravel = float(self.config['Settings']['MaxTimeTravel'].replace(',', '.'))*60           # to sec
    if roundtrip_mode:
        MaxTimeTravel = round(2*MaxTimeTravel/3)

    
    MaxWaitTime = float(self.config['Settings']['MaxWaitTime'].replace(',', '.'))*60               # to sec
    #MaxWaitTime_copy = MaxWaitTime
    MaxWaitTimeTransfer = float(self.config['Settings']['MaxWaitTimeTransfer'].replace(',', '.'))*60

    
    CHANGE_TIME_SEC = 1
    # time_step = int (self.config['Settings']['TimeInterval'])

    """
    number_bins = int(self.config['Settings']['TimeInterval'])
    time_step = MaxTimeTravel//(number_bins*60)  # to min
    time_step_last = (MaxTimeTravel/60) % number_bins
    """
    time_step = int(self.config['Settings']['TimeInterval'])  # длительность интервала в минутах
    number_bins = int(MaxTimeTravel // (time_step *60))       # сколько интервалов помещается
    time_step_last = int((MaxTimeTravel % (time_step * 60)) / 60)
    
    #Layer = self.config['Settings']['Layer']
    #LayerDest = self.config['Settings']['LayerDest']

    layer_dest_field = layer_vis_field = FIELD_ID
    layer_dest = layer_dest_obj
    
    if 'Field_ch' in self.config['Settings']:
        list_fields_aggregate = self.config['Settings']['Field_ch']
    else:
        list_fields_aggregate = ""

    if not (shift_mode):
        begin_computation_time = datetime.now()
        begin_computation_str = begin_computation_time.strftime('%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Started: {begin_computation_str}</a>')

    if verify_break(self):
        return 0, 0
    QApplication.processEvents()


    (
        stops_dict,
        stoptimes_dict,
        footpath_dict,
        routes_by_stop_dict,
        idx_by_route_stop_dict, 
        set_stops
    ) = dictionary
    
    footpath_on_projection = None
    graph_projection = None
    dict_osm_vertex = None
    dict_vertex_osm = None

    
    Dist1 = int(self.config['Settings']['MaxWalkDist1'])

    footpath_on_projection = cls_footpath_on_projection(None, MaxPath = Dist1)
    graph_projection = footpath_on_projection.load_graph(path_to_pkl)
    dict_osm_vertex = footpath_on_projection.load_dict_osm_vertex(path_to_pkl)
    dict_vertex_osm = footpath_on_projection.load_dict_vertex_osm(path_to_pkl)
            
    if verify_break(self):
        return 0, 0
   
    fields_ok = []
    
    cols_dict = get_name_columns()
    cols = cols_dict[(raptor_mode, protocol_type)]
    if protocol_type == 2:

        ss = f"{cols[1]},Start_time"
        ss += ",Walk_time1,BStop_ID1,Wait_time1,Bus_start_time1,Line_ID1,Ride_time1,AStop_ID1,Bus_finish_time1"
        ss += ",Walk_time2,BStop_ID2,Wait_time2,Bus_start_time2,Line_ID2,Ride_time2,AStop_ID2,Bus_finish_time2"
        ss += ",Walk_time3,BStop_ID3,Wait_time3,Bus_start_time3,Line_ID3,Ride_time3,AStop_ID3,Bus_finish_time3"
        ss += f",DestWalk_time,{cols[2]},Destination_time"
        if raptor_mode == 2:            
            if timetable_mode:
                ss += ",Earlest_arrival_time"
            if not(timetable_mode):
                ss += ",Arrive_before"
        ss += ",Legs,Duration"
        protocol_header = ss + "\n"

        header_list = protocol_header.strip().split(',')
    
    suffixes = ["_min_duration.csv"]
    
    if protocol_type == 1:
        aggregate_dict_all = {}
        
        # 1. Обработка базового поля "bldg"        
        hex = "_hex_" in layer_dest.name().lower()
        
        field_bldg = "nbldg"
        header, grades = prepare_protocol_region(field_bldg, number_bins, time_step, time_step_last, cols ["star"])
        if not (hex and list_fields_aggregate):                                        
            header_dict[field_bldg] = header.strip().split(',')            
            fields_ok.append(field_bldg)
            aggregate_dict_all[field_bldg] = {}
        
        # 2. Обработка агрегируемых полей
        if list_fields_aggregate:
            fields_to_process = [v.strip() for v in list_fields_aggregate.split(',')]
            
            for field in fields_to_process:
                if hasattr(self, 'setMessage'):
                    self.setMessage(f"Building dictionary for '{field}' ...")
                    QApplication.processEvents()

                # Собираем данные из слоя (только если числовые)
                features = layer_dest.getFeatures()
                try:
                    # Быстрая проверка и сборка словаря
                    attribute_dict = {
                        int(feat[layer_dest_field]): int(feat[field]) 
                        for feat in features 
                        if isinstance(feat[field], (int, float)) or str(feat[field]).isdigit()
                    }
                except (ValueError, KeyError):
                    self.textLog.append(f'<a><b><font color="red"> WARNING: The field "{field}" is not numeric, excluded from aggregation</font> </b></a>')
                    continue

                # Если поле пустое или не числовое (проверка по первому элементу или через исключение выше)
                if not attribute_dict:
                    continue

                aggregate_dict_all[field] = attribute_dict
                fields_ok.append(field)

                # Генерируем заголовки с суммами
                header, _ = prepare_protocol_region(field, number_bins, time_step, time_step_last, cols ["star"],is_aggregate=True)
                header_dict[field] = header.strip().split(',')
                
    
    if not (shift_mode):

        vis = visualization(self, 
                            layer_viz, 
                            mode=protocol_type,
                            fieldname_layer=layer_vis_field, 
                            schedule_mode = timetable_mode, 
                            from_to = raptor_mode,
                            prefix = file_name
                            )
    else:
        vis = None 
    
    """
    pr_child = cProfile.Profile()
    pr_child.enable()
    """
    
    if timetable_mode:
        stop_times_index = preprocess_stop_times(stoptimes_dict)

    i = 0

    if raptor_mode == 1:
        name = 'origin'
    else:
        name = 'destination' 

    
    if timetable_mode:
        MaxTimeTravel = MaxTimeTravel + MaxExtraTime 
    
    time_estimate_start = datetime.now()
    total_tasks = count * roundtrip_cycle_all

    ###  exp
    # список множеств зданий, найденных для каждого source
    #buildings_per_source = []
    # временное хранилище line1/2/3_id для каждого source
    #lines_per_source = []

    for source in sources:

        if i > 0 and i%10 == 0:          
            tasks_done = ((roundtrip_cycle_current - 1) * count) + i                    
            # 3. Среднее время на одну задачу
            elapsed = datetime.now() - time_estimate_start
            avg_time_per_task = elapsed / i                
            # 4. Сколько задач осталось
            tasks_remaining = total_tasks - tasks_done                
            # 5. Итоговое время            
            remaining_duration = avg_time_per_task * tasks_remaining                            
            display_time = str(remaining_duration).split('.')[0]            
            self.lblEstimateTime.setText(f'Time remaining: {display_time}')
   
           
            
        i = i + 1

        #if i == 10:
        #    break
        if hasattr(self, 'progressBar'):
            self.progressBar.setValue(i)
            self.setMessage(f'Calculating №{i} of {count}')
            QApplication.processEvents()
        SOURCE = source


        ##########################################
        # experiment
        """
        trans_info = footpath_dict.get(str(SOURCE), [])
        trans_info = [(stop_id, walk_time) for stop_id, walk_time in trans_info if walk_time <= MaxWalkDist1]
        time_start = D_TIME 
        stop_times_index = preprocess_stop_times(stoptimes_dict)
        min_time = 600
        max_time = 900
                        
        available_boardings = get_available_boardings(time_start,
                                                          min_time, 
                                                          max_time, 
                                                          trans_info, 
                                                          stop_times_index                                                          
                                                          )
        
        print ("available_boardings")
        processed_boardings = [
            (item[0], item[1], seconds_to_time(item[2]), item[3]) 
            if isinstance(item[2], (int, float)) else item 
            for item in available_boardings
        ]

        for row in processed_boardings:
            print(", ".join(map(str, row)))
        """
        ##########################################


        if verify_break(self):
            return 0, 0

            
        
        nearby_buildings_from_start = footpath_on_projection.get_nearby(str(SOURCE), graph_projection, dict_osm_vertex, dict_vertex_osm, mode="b")

        #print (f'nearby_buildings_from_start {nearby_buildings_from_start}')

        SOURCE = str(SOURCE)
        D_TIME_copy = D_TIME
        if not (timetable_mode):

            if raptor_mode == 1:               
            
                output_duration = raptor(SOURCE,
                            D_TIME,
                            MAX_TRANSFER,
                            MIN_TRANSFER,
                            CHANGE_TIME_SEC,
                            routes_by_stop_dict,
                            stops_dict,
                            stoptimes_dict,
                            footpath_dict,

                            idx_by_route_stop_dict,
                            MaxTimeTravel,
                            MaxWalkDist1,
                            MaxWalkDist2,
                            MaxWalkDist3,
                            MaxWaitTime,
                            MaxWaitTimeTransfer,
                            timetable_mode,
                            MaxExtraTime,
                            steps_to_buildings  =  nearby_buildings_from_start
                            )

            else:
                
                output_duration = rev_raptor(SOURCE,
                                D_TIME,
                                MAX_TRANSFER,
                                MIN_TRANSFER,
                                CHANGE_TIME_SEC,
                                routes_by_stop_dict,
                                stops_dict,
                                stoptimes_dict,
                                footpath_dict,

                                idx_by_route_stop_dict,
                                MaxTimeTravel,
                                MaxWalkDist1,
                                MaxWalkDist2,
                                MaxWalkDist3,
                                MaxWaitTime,
                                MaxWaitTimeTransfer,
                                timetable_mode,
                                MaxExtraTime,
                                steps_to_buildings  =  nearby_buildings_from_start                                                                                                
                                )
            
                    
        if  timetable_mode:
                        
            final_output_duration = {}  
            
            
            time_curr = D_TIME
            time_delta = 5 * 60             
            count_steps = max(1, MaxExtraTime // time_delta)
            step = 0

            MaxWaitTime = 10*60     
                                                            
            while step < count_steps:
                
                step += 1

                if raptor_mode == 1:
                    time_curr = D_TIME + (step-1) * time_delta
                else:
                    time_curr = D_TIME - (step-1) * time_delta

                
                if verify_break(self):
                    return 0, 0
                                    
                
                if hasattr(self, 'setMessage'):
                        
                        if raptor_mode == 1:
                            self.setMessage(f'Calculating №{i} of {count} (checking time {seconds_to_time(time_curr)})')
                        else:
                            self.setMessage(f'Calculating №{i} of {count} (checking time {seconds_to_time(time_curr+MaxExtraTime)})')
                        QApplication.processEvents()

                if raptor_mode == 1:

                                         
                    output_duration = raptor(SOURCE,
                            time_curr,
                            MAX_TRANSFER,
                            MIN_TRANSFER,
                            CHANGE_TIME_SEC,
                            routes_by_stop_dict,
                            stops_dict,
                            stoptimes_dict,
                            footpath_dict,

                            idx_by_route_stop_dict,
                            MaxTimeTravel,
                            MaxWalkDist1,
                            MaxWalkDist2,
                            MaxWalkDist3,
                            MaxWaitTime,
                            MaxWaitTimeTransfer,
                            timetable_mode,
                            MaxExtraTime,
                            steps_to_buildings  =  nearby_buildings_from_start                            
                            )
                    
                    
                else:
                    
                    output_duration = rev_raptor(SOURCE,
                                time_curr,
                                MAX_TRANSFER,
                                MIN_TRANSFER,
                                CHANGE_TIME_SEC,
                                routes_by_stop_dict,
                                stops_dict,
                                stoptimes_dict,
                                footpath_dict,

                                idx_by_route_stop_dict,
                                MaxTimeTravel,
                                MaxWalkDist1,
                                MaxWalkDist2,
                                MaxWalkDist3,
                                MaxWaitTime,
                                MaxWaitTimeTransfer,
                                timetable_mode,
                                MaxExtraTime,
                                D_TIME_copy = D_TIME_copy,
                                steps_to_buildings  =  nearby_buildings_from_start                             
                                )
                
                for p_i in output_duration.keys():
                
                    # Обновляем словарь duration
                    data_duration = output_duration[p_i]
                    duration = data_duration[1]                                
                    #if duration <= MaxTimeTravel_copy:
                    if p_i not in final_output_duration or duration < final_output_duration[p_i][1]:
                            final_output_duration[p_i] = data_duration
                               
            output_duration = final_output_duration

        """
        ######################### exp
        # здания, найденные для текущего source
        current_buildings = set(output_duration.keys())
        buildings_per_source.append(current_buildings)

            # сохраняем line1/2/3_id для каждого здания
        current_lines = {}
        for dest, info in output_duration.items():
                pareto = info[2]
                if pareto:
                    journey = pareto
                    # извлекаем line1_id, line2_id, line3_id
                    line_ids = []
                    for leg in journey:
                        if isinstance(leg[0], int):  # автобусный сегмент
                            line_ids.append(leg[4])
                    # дополняем до 3 элементов
                    while len(line_ids) < 3:
                        line_ids.append("")
                    current_lines[dest] = tuple(line_ids[:3])

        lines_per_source.append(current_lines)
        #########################
        """

        if protocol_type == 1:
            
            if len(fields_ok) > 0:
                for field in fields_ok:
                    for suffix in suffixes:
                        
                        if "_min_duration" in suffix:
                            data_body = make_protocol_summary(SOURCE,
                                                  destinations,
                                          output_duration,                        
                                          grades,
                                          aggregate_dict_all[field],                                          
                                          set_stops,
                                          field,
                                          short_result
                                          )
                            
                            if not roundtrip_mode:                                
                                df_current_min_duration = pd.DataFrame(data_body, columns=header_dict[field])
                                df_min_duration_all_dict[field].append(df_current_min_duration)
                      
                        
        if protocol_type == 2:
                                     
            data_body = make_protocol_detailed(                                   
                                   raptor_mode,
                                   D_TIME_copy,
                                   output_duration,                                   
                                   timetable_mode,                                   
                                   set_stops,
                                   destinations,
                                   SOURCE,
                                   short_result
                                   )
            
            
            #if not roundtrip_mode:
            df_current_min_duration = pd.DataFrame(data_body, columns=header_list)
            df_min_duration_all.append(df_current_min_duration)
                
            """
                if len(sources) == 1:                     
                    table_name = f'{file_name}_fastest_trip'
                    table_name_list.append(table_name)
                    fast_write_gpkg(file_name_gpkg, table_name, df_current_min_duration)
            """
                            
            QApplication.processEvents()

    if protocol_type == 1 and not roundtrip_mode:
    
            for field, list_of_dfs in df_min_duration_all_dict.items():
                if list_of_dfs:  
                    df_final = pd.concat(list_of_dfs, ignore_index=True)
                    table_name = f'{file_name}_stat_{field}_fastest_trip'
                    table_name_list.append(table_name)
                    fast_write_gpkg(file_name_gpkg, table_name, df_final)


    col_star = cols["star"]
    col_hash = cols["hash"]

    # создаем pivot если не roundtrip, данные не свернутые
    if not roundtrip_mode:
       df_pivot = make_pivot_gpkg (short_result, col_star, col_hash)              
       table_name = f'{file_name}_fastest_by_{name}s'
       fast_write_gpkg(file_name_gpkg, table_name, df_pivot)        

    # данные сворачиваем если SA и количество больше 1
    if protocol_type == 2:# and len(sources) > 1:      
        df_min_duration, short_result = make_service_area_report_gpkg(df_min_duration_all,col_star, col_hash)        
        ### experiment ############
        #df_min_duration, _ = make_service_area_report_gpkg(df_min_duration_all,col_star, col_hash) 

    """
    origin_to_check = '1035910'
    # --- Проверка в df_min_duration_all ---
    found_in_frames = False
    for i, df in enumerate(df_min_duration_all):
        if origin_to_check in df[col_hash].values:
            print(f"Origin {origin_to_check} FOUND in df_min_duration_all[{i}]")
            found_in_frames = True

    if not found_in_frames:
        print(f"Origin {origin_to_check} NOT found in ANY df_min_duration_all frame")

    origin_to_check = 1035910

    matches = [
        (src, dest, value)
        for (src, dest), value in short_result.items()
        if dest == origin_to_check
    ]

    if matches:
        print(f"Origin {origin_to_check} FOUND in short_result, count = {len(matches)}")
        for src, dest, value in matches[:10]:   # первые 10 для примера
            print(f"  src={src}, dest={dest}, duration={value}")
    else:
        print(f"Origin {origin_to_check} NOT found in short_result")
    """
    

    # если SA и не roundtrip - сохраняем данные
    if protocol_type == 2 and not roundtrip_mode: 
        table_name_list = []                
        table_name = f'{file_name}_fastest_trip'
        table_name_list.append(table_name)
        fast_write_gpkg(file_name_gpkg, table_name, df_min_duration)       
    
    QApplication.processEvents()
    if not (shift_mode):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Finished: {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
    
        self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

    add_thematic_map = True
    
    write_info(self,
               file_name_gpkg,
               vis,
               fields_ok,
               table_name_list,
               protocol_type,
               shift_mode,
               add_thematic_map                           
               )
    
    if hasattr(self, 'progressBar'):   
        self.setMessage(f'Finished')
        self.progressBar.setValue(self.progressBar.maximum())
    
    """
    pr_child.disable()
    
    with open(output_filename_txt, "w") as f:
        ps = pstats.Stats(pr_child, stream=f).sort_stats('cumulative')
        ps.print_stats()
    pr_child.dump_stats(output_filename_prof)
    """
    
    """
    ######################### exp
    if buildings_per_source:
        common_buildings = set.intersection(*buildings_per_source)
    else:
        common_buildings = set()

    
    common_buildings_int = {
    int(b)
    for b in common_buildings
    if b.isdigit()
    }

    filtered_short_result = {
    (src, dest): value
    for (src, dest), value in short_result.items()
    if (src == dest) or (dest in common_buildings_int)
    }


    output_file = r"c:\doc\Igor\GIS\36_routes_26POI\stat_routes\lines_gtfs2025.txt"

    buffer = []

    for lines_dict in lines_per_source:
        for dest, (l1, l2, l3) in lines_dict.items():
            if dest in common_buildings:
                for lid in (l1, l2, l3):
                    if lid:
                        # обрезаем до первого _
                        buffer.append(lid.split("_")[0] + "\n")

    # записываем в файл
    with open(output_file, "a", encoding="utf-8") as f:
        f.writelines(buffer)

    short_result = filtered_short_result

    #########################
    """

    return short_result

def preprocess_stop_times(stop_times):
   
    stop_index = {}
    for route_id, trips in stop_times.items():
        for trip_id, stops in trips.items():
            for stop_seq, stop_seconds in stops:
                stop_id_str = str(stop_seq)
                if stop_id_str not in stop_index:
                    stop_index[stop_id_str] = []
                stop_index[stop_id_str].append((route_id, trip_id, stop_seconds))
    
    # Сортируем по времени для каждого stop_id для бинарного поиска
    for stop_id in stop_index:
        stop_index[stop_id].sort(key=lambda x: x[2])
    
    return stop_index
"""
def get_available_boardings(start_time_seconds, 
                            max_delta_seconds, 
                            trans_info, 
                            stop_times_index, 
                            mode, 
                            express_mode = True):
    
    available_departures = []
    
    used_routes = set()
    
    for stop_id, walk_time in trans_info:
        
        if mode == 1:
            arrival_time = start_time_seconds + walk_time
            max_time = start_time_seconds + max_delta_seconds + walk_time
        else:
            arrival_time = start_time_seconds - walk_time
            max_time = start_time_seconds + max_delta_seconds - walk_time
        
        if arrival_time > max_time:
            continue
        
        if stop_id in stop_times_index:
            for route_id, trip_id, stop_seconds in stop_times_index[stop_id]:
            
                route_key = (stop_id, route_id)  # Создаем ключ из сочетания
            
                if route_key in used_routes:
                   continue
            
                if arrival_time <= stop_seconds <= max_time:
            
                    available_departures.append((stop_id, route_id, stop_seconds, walk_time))
                    used_routes.add(route_key)
    
    available_departures.append(("xxx", "xxx", "xxx"))
    return sorted(available_departures, key=lambda x: (x[0], x[1]))
"""

# experiment
def get_available_boardings(start_time_seconds, 
                            min_delta_seconds,
                            max_delta_seconds, 
                            trans_info, 
                            stop_times_index):
    
    available_departures = []
    for stop_id, walk_time in trans_info:
    
        min_time = start_time_seconds + min_delta_seconds
        max_time = start_time_seconds + max_delta_seconds 

        if min_time > max_time:
            continue
        
        if stop_id in stop_times_index:
            for route_id, trip_id, stop_seconds in stop_times_index[stop_id]:
                if min_time <= stop_seconds <= max_time:
                    if stop_seconds < start_time_seconds+ walk_time:
                        continue
                    available_departures.append((stop_id, route_id, stop_seconds, walk_time))
        
    
    available_departures.append(("xxx", "xxx", "xxx"))
    return sorted(available_departures, key=lambda x: (x[0], x[1]))

def write_info(self,
               file_name_gpkg,
               vis,
               fields_ok,
               table_name_list,
               protocol_type,
               shift_mode = False,
               add_thematic_map = True,
               ):
    
    

    if shift_mode:
        return 0
    
    #self.textLog.append(f'<a>Output:</a>')

    if protocol_type == 1:
        if len(fields_ok) > 0:
            for item in table_name_list:
                item = os.path.normpath (item)
                #self.textLog.append(f'<a>{item}</a>')
                if not (shift_mode) and add_thematic_map:
                    alias = os.path.splitext(os.path.basename(item))[0]
                    vis.add_thematic_map_gpkg(file_name_gpkg, item, alias )

    if protocol_type == 2:
        for item in table_name_list:
            #self.textLog.append(f'<a>{item}</a>')
            if not (shift_mode) and add_thematic_map:
                alias = os.path.splitext(os.path.basename(item))[0]
                vis.add_thematic_map_gpkg(file_name_gpkg, item, alias )
    
    if not (shift_mode):
        self.lblEstimateTime.setText("")
        self.textLog.append(f'Output in file: <a href="file:///{file_name_gpkg}" target="_blank" > {file_name_gpkg}</a>')
    

def int1(s):
    result = s
    if s == "":
        result = 0
    return result
