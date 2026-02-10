import os
import zipfile
from pathlib import Path

import pickle
from datetime import datetime
from numbers import Real
import tempfile
import pandas as pd
import cProfile
import pstats
#from collections import Counter
from report import (make_protocol_detailed, 
                    make_protocol_summary, 
                    make_service_area_report)

from PyQt5.QtWidgets import QApplication, QMessageBox
from qgis.core import (QgsProject,
                       QgsVectorFileWriter,
                       )

from footpath_on_projection import cls_footpath_on_projection
from RAPTOR.std_raptor import raptor
from RAPTOR.rev_std_raptor import rev_raptor


from footpath_on_air_b_to_b import cls_footpath_on_air_b_b
from visualization import visualization
from common import (seconds_to_time, 
                    get_existing_path, 
                    get_name_columns)

# # Get the current directory
#current_dir = os.path.dirname(os.path.abspath(__file__))

def myload_all_dict(self, PathToNetwork, mode, RunOnAir):
        path = PathToNetwork
        
        if self is not None:
            self.setMessage("Loading walking paths ...")
            QApplication.processEvents()

        
        base_transfer = 'transfers_dict_air.pkl' if RunOnAir else 'transfers_dict_projection.pkl'
        filename_transfer = get_existing_path(path, base_transfer)
       
        with open(filename_transfer, 'rb') as file:
            footpath_dict = pickle.load(file)
                
        stop_ids_path = get_existing_path(path, 'stop_ids.pkl')
        stop_ids = pd.read_pickle(stop_ids_path)
        stop_ids_set = set(stop_ids)

        if self is not None:
            self.progressBar.setValue(2)
            self.setMessage("Loading transit routes ...")
            QApplication.processEvents()

        # 3. Загрузка routes_by_stop_dict
        routes_path = get_existing_path(path, 'routes_by_stop.pkl')
        with open(routes_path, 'rb') as file:
            routes_by_stop_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(3)

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
            self.progressBar.setValue(4)
            self.setMessage("Loading transit time schedule ...")
            QApplication.processEvents()


        with open(get_existing_path(path, stoptimes_file), 'rb') as file:
            stoptimes_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(5)
            self.setMessage("Loading index ...")
            QApplication.processEvents()

        
        with open(get_existing_path(path, idx_file), 'rb') as file:
            idx_by_route_stop_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(6)

        return (
            stops_dict,
            stoptimes_dict,
            footpath_dict,
            routes_by_stop_dict,
            idx_by_route_stop_dict,
            stop_ids_set
        )

def verify_break(self,
                 Layer="",
                 LayerDest="",
                 vis="",
                 fields_ok="",
                 f="",
                 protocol_type="",
                 shift_mode = True
                 ):

    if getattr(self, 'break_on', False):
        if self.break_on:

            self.textLog.append(f'<a><b><font color="red">Raptor Algorithm is interrupted by user</font> </b></a>')
            time_after_computation = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.textLog.append(f'<a>Interrupted at: {time_after_computation}</a>')

            if self.folder_name != "":
                write_info(self,
                       Layer,
                       LayerDest,
                       False,
                       False,
                       vis,
                       fields_ok,
                       f,
                       protocol_type,
                       shift_mode,
                       
                       )
                
            self.progressBar.setValue(0)
            self.setMessage("Raptor Algorithm is interrupted by user")
            return True
    return False

def prepare_protocol_region(field, number_bins, time_step, time_step_last, cols_star, is_aggregate=False):
        
        header_parts = [cols_star]
        grades = []
        
        curr_low = 0
        
        for _ in range(number_bins):
            curr_top = curr_low + time_step
            header_parts.append(f"{curr_top}m")
            if is_aggregate:
                header_parts.append(f"sum({field}[{curr_top}m])")
            grades.append([curr_low, curr_top])
            curr_low = curr_top

        
        if time_step_last != 0:
            curr_top = curr_low + time_step_last
            header_parts.append(f"{curr_top}m")
            if is_aggregate:
                header_parts.append(f"sum({field}[{curr_top}m])")
            grades.append([curr_low, curr_top])

        header_parts.append(f"{field}_total\n")
        return ",".join(header_parts), grades

def runRaptorWithProtocol(self,
                          sources,
                          raptor_mode,
                          protocol_type,
                          timetable_mode,
                          D_TIME,
                          selected_only1,
                          selected_only2,
                          dictionary,
                          shift_mode,
                          layer_dest_obj,
                          layer_origin_obj,
                          path_to_pkl) -> tuple:

    short_result = {}
    
    count = len(sources)
    if hasattr(self, 'progressBar'):
        self.progressBar.setMaximum(count + 5)
        self.progressBar.setValue(0)

    MAX_TRANSFER = int(self.config['Settings']['Max_transfer'])
    MIN_TRANSFER = int(self.config['Settings']['Min_transfer'])

    MaxExtraTime = int(self.config['Settings']['MaxExtraTime'])*60
    
    Speed = float(self.config['Settings']['Speed'].replace(
        ',', '.')) * 1000 / 3600                    # from km/h to m/sec

    # dist to time
    MaxWalkDist1 = int(self.config['Settings']['MaxWalkDist1'])/Speed
    # dist to time
    MaxWalkDist2 = int(self.config['Settings']['MaxWalkDist2'])/Speed
    # dist to time
    MaxWalkDist3 = int(self.config['Settings']['MaxWalkDist3'])/Speed

    MaxTimeTravel = float(self.config['Settings']['MaxTimeTravel'].replace(',', '.'))*60           # to sec
    
    MaxWaitTime = float(self.config['Settings']['MaxWaitTime'].replace(',', '.'))*60               # to sec
    #MaxWaitTime_copy = MaxWaitTime
    MaxWaitTimeTransfer = float(self.config['Settings']['MaxWaitTimeTransfer'].replace(',', '.'))*60

    
    CHANGE_TIME_SEC = 1
    # time_step = int (self.config['Settings']['TimeInterval'])

    number_bins = int(self.config['Settings']['TimeInterval'])
    time_step = MaxTimeTravel//(number_bins*60)  # to min
    time_step_last = (MaxTimeTravel/60) % number_bins

    Layer = self.config['Settings']['Layer']
    
    LayerDest = self.config['Settings']['LayerDest']
    layer_dest_field = self.config['Settings']['LayerDest_field']

    LayerViz = self.config['Settings']['LayerViz']
    layer_vis_field = self.config['Settings']['LayerViz_field']
    #layer_dest = QgsProject.instance().mapLayersByName(LayerDest)[0]
    layer_dest = layer_dest_obj
    layer_origin = layer_origin_obj

    if 'Field_ch' in self.config['Settings']:
        list_fields_aggregate = self.config['Settings']['Field_ch']
    else:
        list_fields_aggregate = ""

    RunOnAir = self.config['Settings']['RunOnAir'] == 'True'
    
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

    footpath_on_air_b_b = None
    footpath_on_projection = None
    graph_projection = None
    dict_osm_vertex = None
    dict_vertex_osm = None

    
    Dist1 = int(self.config['Settings']['MaxWalkDist1'])
    if RunOnAir:
        footpath_on_air_b_b = cls_footpath_on_air_b_b(layer_origin,
                                                      layer_dest,
                                                      Dist1,
                                                      layer_dest_field,
                                                      Speed
                                                      )
    else:
        footpath_on_projection = cls_footpath_on_projection(None, MaxPath = Dist1)
        graph_projection = footpath_on_projection.load_graph(path_to_pkl)
        dict_osm_vertex = footpath_on_projection.load_dict_osm_vertex(
            path_to_pkl)
        dict_vertex_osm = footpath_on_projection.load_dict_vertex_osm(
            path_to_pkl)
        

    
    if verify_break(self):
        return 0, 0
   
    fields_ok = []
    
    f = ""
    cols_dict = get_name_columns()
    cols = cols_dict[(raptor_mode, protocol_type)]
    if protocol_type == 2:

        ss = f"{cols[1]},Start_time"
        ss += ",Walk_time1,BStop_ID1,Wait_time1,Bus_start_time1,Line_ID1,Ride_time1,AStop_ID1,Bus_finish_time1"
        ss += ",Walk_time2,BStop_ID2,Wait_time2,Bus_start_time2,Line_ID2,Ride_time2,AStop_ID2,Bus_finish_time2"
        ss += ",Walk_time3,BStop_ID3,Wait_time3,Bus_start_time3,Line_ID3,Ride_time3,AStop_ID3,Bus_finish_time3"
        ss += f",DestWalk_time,{cols[2]},Destination_time"
        if raptor_mode == 2:
            #ss = ss.replace("Origin_ID", "TEMP_ORIGIN_ID")
            #ss = ss.replace("Destination_ID", "Origin_ID")
            #ss = ss.replace("TEMP_ORIGIN_ID", "Destination_ID")
            if timetable_mode:
                ss += ",Earlest_arrival_time"
            if not(timetable_mode):
                ss += ",Arrive_before"
        ss += ",Legs,Duration"
        protocol_header = ss + "\n"
    
    files_path = {}
    suffixes = ["_min_duration.csv", "_min_endtime.csv"]
    if protocol_type == 1:
        aggregate_dict_all = {}
        
        base_path = Path(self.folder_name)

        # 1. Обработка базового поля "bldg"
        field_bldg = "bldg"
        
        header, grades = prepare_protocol_region(field_bldg, number_bins, time_step, time_step_last, cols ["star"])
        
        fields_ok.append(field_bldg)
        aggregate_dict_all[field_bldg] = {}
        
        # Записываем файлы для bldg
        for suffix in suffixes:
            file_path = str(base_path / f"{self.alias}_{field_bldg}{suffix}")
            files_path[field_bldg, suffix] = file_path
            with open(file_path, 'w') as f_out:
                f_out.write(header)

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
                
                # Записываем файлы
                for suffix in suffixes:
                    file_path = str(base_path / f"{self.alias}_{field}{suffix}") 
                    files_path[field, suffix] = file_path
                    with open(file_path, 'w') as f_out:
                        f_out.write(header)
    
    
    
    if not (shift_mode):
        vis = visualization(self, 
                            LayerViz, 
                            mode=protocol_type,
                            fieldname_layer=layer_vis_field, 
                            schedule_mode = timetable_mode, 
                            from_to = raptor_mode
                            )
    else:
        vis = None 
    
    
    #pr_child = cProfile.Profile()
    #pr_child.enable()
    
    if timetable_mode:
        stop_times_index = preprocess_stop_times(stoptimes_dict)

    for i in range(0, count):

        #if i == 100:
        #    break
        if hasattr(self, 'progressBar'):
            self.progressBar.setValue(i + 6)
            self.setMessage(f'Calculating №{i+1} of {count}')
            QApplication.processEvents()
        SOURCE = sources[i]

        if verify_break(self,
                        Layer,
                        LayerDest,
                        vis,
                        fields_ok,
                        files_path,
                        protocol_type,
                        shift_mode                        
                        ):
            return 0, 0

        if RunOnAir:
            nearby_buildings_from_start = footpath_on_air_b_b.get_nearby_buildings(SOURCE)
            
            list_buildings_from_start = [
                str(osm_id) for osm_id, _ in nearby_buildings_from_start]
            
        else:
            nearby_buildings_from_start = footpath_on_projection.get_nearby_buildings(str(
                SOURCE), graph_projection, dict_osm_vertex, dict_vertex_osm, mode="find_b")
            list_buildings_from_start = [
                str(osm_id) for osm_id, _ in nearby_buildings_from_start]

        SOURCE = str(SOURCE)
        D_TIME_copy = D_TIME
        if not (timetable_mode):

            if raptor_mode == 1:
            
                output_endtime, output_duration = raptor(SOURCE,
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
                            MaxExtraTime                            
                            )

            else:
                
                output_endtime, output_duration = rev_raptor(SOURCE,
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
                                MaxExtraTime                                                                
                                )
            
            

            
            #keys_to_remove = [key for key, value in output.items() if value[-1] == (None, None, None, None)]
            #for key in keys_to_remove:
            #    del output[key]

        
        if  timetable_mode:
            
            final_output_endtime = {}  
            final_output_duration = {}  
            
            
            time_curr = D_TIME
            time_delta = 5 * 60 
            #MaxExtraTime = time_delta # !!!!!!!!!!!!!!!!!!! test
            count_steps =  MaxExtraTime // time_delta
            step = 0

            MaxWaitTime = 10*60
            MaxTimeTravel_copy = MaxTimeTravel
            MaxTimeTravel = MaxTimeTravel + MaxExtraTime 
                                                            
            while step < count_steps:
                
                step += 1

                

                if raptor_mode == 1:
                    time_curr = D_TIME + (step-1) * time_delta
                else:
                    time_curr = D_TIME - (step-1) * time_delta

                
                if verify_break(self,
                        Layer,
                        LayerDest,
                        vis,
                        fields_ok,
                        f,
                        protocol_type,
                        shift_mode                        
                        ):
                    return 0, 0
                                    
                
                if hasattr(self, 'setMessage'):
                        if raptor_mode == 1:
                            self.setMessage(f'Calculating №{i+1} of {count} (checking time {seconds_to_time(time_curr)})')
                        else:
                            self.setMessage(f'Calculating №{i+1} of {count} (checking time {seconds_to_time(time_curr+MaxExtraTime)})')
                        QApplication.processEvents()

                if raptor_mode == 1:
                                            
                    output_endtime, output_duration = raptor(SOURCE,
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
                            MaxExtraTime                            
                            )
                    
                else:
                    
                    output_endtime, output_duration = rev_raptor(SOURCE,
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
                                MaxExtraTime                                
                                )
                
                for p_i in output_endtime.keys():
                   
                    # Обновляем словарь endtime
                    data_endtime = output_endtime[p_i]
                    end_time = data_endtime[4]
                    duration = data_endtime[1]
                    if duration < MaxTimeTravel_copy:
                        if p_i not in final_output_endtime or end_time < final_output_endtime[p_i][4] :
                            final_output_endtime[p_i] = data_endtime
    
                    # Обновляем словарь duration
                    data_duration = output_duration[p_i]
                    duration = data_duration[1]
                    end_time = data_duration[4]
                    
                    if duration < MaxTimeTravel_copy:
                        if p_i not in final_output_duration or duration < final_output_duration[p_i][1]:
                            final_output_duration[p_i] = data_duration
                                    
                    
            output_endtime = final_output_endtime
            output_duration = final_output_duration
        """
        
        if  timetable_mode:
            
            final_output_endtime = {}  
            final_output_duration = {}  
            
            MaxWaitTime_copy = MaxWaitTime
            
            trans_info = footpath_dict.get(SOURCE, [])
            trans_info = [(stop_id, walk_time) for stop_id, walk_time in trans_info if walk_time <= MaxWalkDist1]
            if raptor_mode == 2: 
                time_start = D_TIME #- MaxExtraTime
            else: 
                time_start = D_TIME
            
            available_boardings = get_available_boardings(time_start, 
                                                          MaxExtraTime, 
                                                          trans_info, 
                                                          stop_times_index,
                                                          raptor_mode,
                                                          express_mode=True 
                                                          )

            #print (available_boardings)

            for step in available_boardings:
                (stop_id, time_departure, dist) = step

                if verify_break(self,
                        Layer,
                        LayerDest,
                        vis,
                        fields_ok,
                        f,
                        protocol_type,
                        shift_mode                        
                        ):
                    return 0, 0
                                    
                
                if hasattr(self, 'setMessage'):
                    if stop_id == "xxx":
                        self.setMessage(f'Calculating №{i+1} of {count}')
                    else:
                        self.setMessage(f'Calculating №{i+1} of {count} (checking stop {stop_id} time {seconds_to_time(time_departure)})')
                    QApplication.processEvents()

                if stop_id == "xxx":
                    D_TIME = D_TIME_copy
                    firts_step = None
                    MaxWaitTime = MaxWaitTime_copy
                else:
                    MaxWaitTime = 1


                if raptor_mode == 1:
                    if stop_id != "xxx":
                        time_departure -= 1
                        D_TIME = time_departure - dist
                        firts_step = (stop_id, time_departure, dist)
                                            
                    output_endtime, output_duration = raptor(SOURCE,
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
                            first_step = firts_step
                            )
                    
                else:
                    
                    if stop_id != "xxx":
                        time_departure += 1
                        D_TIME = time_departure + dist
                        firts_step = (stop_id, time_departure, dist)
                    
                    output_endtime, output_duration = rev_raptor(SOURCE,
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
                                first_step= firts_step
                                )
                
                for p_i in output_endtime.keys():
                   
                    # Обновляем словарь endtime
                    data_endtime = output_endtime[p_i]
                    end_time = data_endtime[4]
                    if p_i not in final_output_endtime or end_time < final_output_endtime[p_i][4]:
                        final_output_endtime[p_i] = data_endtime
    
                    # Обновляем словарь duration
                    data_duration = output_duration[p_i]
                    duration = data_duration[1]
                    if p_i not in final_output_duration or duration < final_output_duration[p_i][1]:
                        final_output_duration[p_i] = data_duration

                    
                    
            output_endtime = final_output_endtime
            output_duration = final_output_duration
        """
        if protocol_type == 1:
            
            if len(fields_ok) > 0:
                for field in fields_ok:
                    for suffix in suffixes:
                        path_file = files_path[field, suffix]
                        if "_min_duration" in suffix:
                            make_protocol_summary(SOURCE,
                                          output_duration,
                                          path_file,
                                          grades,
                                          aggregate_dict_all[field],
                                          nearby_buildings_from_start,
                                          list_buildings_from_start,
                                          set_stops,
                                          field,
                                          short_result
                                          )
                        else: 
                            make_protocol_summary(SOURCE,
                                          output_endtime,
                                          path_file,
                                          grades,
                                          aggregate_dict_all[field],
                                          nearby_buildings_from_start,
                                          list_buildings_from_start,
                                          set_stops,
                                          field
                                          )
                        
        if protocol_type == 2:
            
            f_curr = f'{self.folder_name}//{self.alias}.csv'
            f_min_duration = f_curr.replace(".csv", "_min_duration.csv")
            f_min_endtime = f_curr.replace(".csv", "_min_endtime.csv")

            files_path = (f_min_endtime, f_min_duration)
            

            if i == 0:
                with open(f_min_duration, 'w') as filetowrite:
                    filetowrite.write(protocol_header)

                with open(f_min_endtime, 'w') as filetowrite:
                    filetowrite.write(protocol_header)

                
                
            make_protocol_detailed(raptor_mode,
                                   D_TIME_copy,
                                   output_endtime,
                                   f_min_endtime,
                                   timetable_mode,
                                   nearby_buildings_from_start,
                                   list_buildings_from_start,
                                   set_stops,
                                   SOURCE
                                   )
            QApplication.processEvents()
                        
            make_protocol_detailed(raptor_mode,
                                   D_TIME_copy,
                                   output_duration,
                                   f_min_duration,
                                   timetable_mode,
                                   nearby_buildings_from_start,
                                   list_buildings_from_start,
                                   set_stops,
                                   SOURCE,
                                   short_result
                                   )
            
            
            QApplication.processEvents()
            
            

    if protocol_type == 2 and len(sources) > 1 and not (timetable_mode):
        col_star = cols["star"]
        col_hash = cols["hash"]
        f_min_endtime, _ = make_service_area_report(f_min_endtime, f'{self.alias}_min_endtime', col_star, col_hash)
        f_min_duration, short_result = make_service_area_report(f_min_duration, f'{self.alias}_min_duration', col_star, col_hash)
        
        files_path = [f_min_endtime,f_min_duration]
        
    #if protocol_type == 1:
    #    f = f_new

    QApplication.processEvents()
    if not (shift_mode):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime('%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Finished {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
    
        self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

    add_thematic_map = True
    if timetable_mode and len(sources) > 1 and  protocol_type == 2 :
        add_thematic_map = False

    write_info(self,
               Layer,
               LayerDest,
               selected_only1,
               selected_only2,
               vis,
               fields_ok,
               files_path,
               protocol_type,
               shift_mode,
               add_thematic_map,
               field_star = cols["star"],              
               field_hash = cols["hash"],              
               )
    
    if hasattr(self, 'progressBar'):   
        self.setMessage(f'Finished')
        self.progressBar.setValue(self.progressBar.maximum())
    
    
    #pr_child.disable()
    
    #output_filename_txt = r"c:\temp\profile_raptor.txt"
    #output_filename_prof = r"c:\temp\profile_raptor.prof"
    
    #with open(output_filename_txt, "w") as f:
    #    ps = pstats.Stats(pr_child, stream=f).sort_stats('cumulative')
    #    ps.print_stats()
    #pr_child.dump_stats(output_filename_prof)
    

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
            
                    available_departures.append((stop_id, stop_seconds, walk_time))
                    used_routes.add(route_key)
    
    available_departures.append(("xxx", "xxx", "xxx"))
    return sorted(available_departures, key=lambda x: (x[0], x[1]))


def write_info(self,
               Layer,
               LayerDest,
               selected_only1,
               selected_only2,
               vis,
               fields_ok,
               f,
               protocol_type,
               shift_mode = False,
               add_thematic_map = True,
               field_star = "",
               field_hash = ""
               ):

    if hasattr(self, 'textLog'):        
        text = self.textLog.toPlainText()
        filelog_name = f'{self.folder_name}//log_{self.alias}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)
    
    if shift_mode:
        return 0
    
    self.textLog.append(f'<a>Output:</a>')

    if protocol_type == 1:
        if len(fields_ok) > 0:
            for _, file_path in f.items():
                item = os.path.normpath (file_path)
                self.textLog.append(f'<a>{item}</a>')
                if not (shift_mode):
                    alias = os.path.splitext(os.path.basename(item))[0]
                    vis.add_thematic_map(item, alias, set_min_value=0)

    

    if protocol_type == 2:
        for item in f:
            item = os.path.normpath (item)
            self.textLog.append(f'<a>{item}</a>')
            if not (shift_mode) and add_thematic_map:
                alias = os.path.splitext(os.path.basename(item))[0]
                vis.add_thematic_map(item, alias, set_min_value=0)

    if (selected_only1 or selected_only2) and not shift_mode:
        if field_star and field_hash:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f'Do you want to store selected features as a layer?'
            )
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            result = msgBox.exec_()
            if result == QMessageBox.Yes:
                if selected_only1:

                    zip_filename1 = f'{self.folder_name}//{field_star}_{self.alias}.zip'
                    filename1 = f'{self.folder_name}//{field_star}_{self.alias}.geojson'

                    self.setMessage(f'Zipping the layer of {field_star} ...')
                    QApplication.processEvents()

                    save_layer_to_zip(Layer, zip_filename1, filename1)

                if selected_only2:

                    zip_filename2 = f'{self.folder_name}//{field_hash}_{self.alias}.zip'
                    filename2 = f'{self.folder_name}//{field_hash}_{self.alias}.geojson'

                    self.setMessage(f'Zipping the layer of {field_hash} ...')
                    QApplication.processEvents()

                    save_layer_to_zip(LayerDest, zip_filename2, filename2)

    self.textLog.append(f'<a href="file:///{self.folder_name}" target="_blank" >Output in folder</a>')



def int1(s):
    result = s
    if s == "":
        result = 0
    return result


def save_layer_to_zip(layer_name, zip_filename, filename):

    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp_file:
        temp_file = tmp_file.name

    QApplication.processEvents()

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GeoJSON"
    options.fileEncoding = "UTF-8"
    options.onlySelectedFeatures = True

    QgsVectorFileWriter.writeAsVectorFormatV3(
                layer, 
                temp_file, 
                QgsProject.instance().transformContext(), 
                options)

    """
    QgsVectorFileWriter.writeAsVectorFormat(layer,
                                            temp_file,
                                            "utf-8",
                                            layer.crs(),
                                            "GeoJSON",
                                            onlySelected=True)
    """
    QApplication.processEvents()

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(temp_file, os.path.basename(filename))

    QApplication.processEvents()

    if os.path.exists(temp_file):
        os.remove(temp_file)
