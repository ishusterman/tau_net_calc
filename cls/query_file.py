import os
import zipfile
import shutil
import pickle
from datetime import datetime, date
from numbers import Real
import tempfile
import pandas as pd
import glob

from PyQt5.QtWidgets import QApplication, QMessageBox
from qgis.core import (QgsProject,
                       QgsVectorFileWriter,
                       QgsVectorLayer,
                       QgsWkbTypes
                       )

from footpath_on_projection import cls_footpath_on_projection
from RAPTOR.std_raptor import raptor
from RAPTOR.rev_std_raptor import rev_raptor


from footpath_on_air_b_to_b import cls_footpath_on_air_b_b
from visualization import visualization
from common import seconds_to_time

# # Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

def get_route_desc__route_id(path):
    route_desc__route_id = {}
    if os.path.exists(path + '/route_desc__route_id.pkl'):
        with open(path + '/route_desc__route_id.pkl', 'rb') as file:
            route_desc__route_id = pickle.load(file)
    return route_desc__route_id

def myload_all_dict(self,
                    PathToNetwork,
                    mode,
                    RunOnAir,

                    layer_origin,
                    layer_dest,
                    MaxWalkDist1,
                    layer_dest_field,
                    Speed
                    ):

    path = PathToNetwork
    
    if self is not None:
        self.setMessage("Loading walking paths ...")
        QApplication.processEvents()

    if RunOnAir:
        filename_transfer = 'transfers_dict_air.pkl'
    else:
        filename_transfer = 'transfers_dict_projection.pkl'
    filename_transfer = os.path.join(path, filename_transfer)
   
    with open(filename_transfer, 'rb') as file:
            footpath_dict = pickle.load(file)
    
    stop_ids = pd.read_pickle(path + '/stop_ids.pkl')
    stop_ids_set = set(stop_ids)

    if self is not None:
        self.progressBar.setValue(2)
        self.setMessage("Loading transit routes ...")
        QApplication.processEvents()

    with open(path + '/routes_by_stop.pkl', 'rb') as file:
        routes_by_stop_dict = pickle.load(file)

    if self is not None:
        self.progressBar.setValue(3)

    if mode == 1:
        if self is not None:
            self.setMessage("Loading transit stops ...")
            QApplication.processEvents()
        with open(path + '/stops_dict_pkl.pkl', 'rb') as file:
            stops_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(4)
            self.setMessage("Loading transit time schedule ...")
            QApplication.processEvents()

        with open(path + '/stoptimes_dict_pkl.pkl', 'rb') as file:
            stoptimes_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(5)
            self.setMessage("Loading index ...")
            QApplication.processEvents()

        with open(path + '/idx_by_route_stop.pkl', 'rb') as file:
            idx_by_route_stop_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(6)

    else:
        if self is not None:
            self.setMessage("Loading transit stops ...")
            QApplication.processEvents()
        with open(path + '/stops_dict_reversed_pkl.pkl', 'rb') as file:  # reversed
            stops_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(4)
            self.setMessage("Loading transit time schedule ...")
            QApplication.processEvents()
        with open(path + '/stoptimes_dict_reversed_pkl.pkl', 'rb') as file:  # reversed
            stoptimes_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(5)
            self.setMessage("Loading index ...")
            QApplication.processEvents()

        with open(path + '/rev_idx_by_route_stop.pkl', 'rb') as file:
            idx_by_route_stop_dict = pickle.load(file)

        if self is not None:
            self.progressBar.setValue(6)

    footpath_on_air_b_b = None
    footpath_on_projection = None
    graph_projection = None
    dict_osm_vertex = None
    dict_vertex_osm = None

    if RunOnAir:
        footpath_on_air_b_b = cls_footpath_on_air_b_b(layer_origin,
                                                      layer_dest,
                                                      MaxWalkDist1,
                                                      layer_dest_field,
                                                      Speed
                                                      )
    else:
        footpath_on_projection = cls_footpath_on_projection(self, MaxPath = MaxWalkDist1)
        graph_projection = footpath_on_projection.load_graph(PathToNetwork)
        dict_osm_vertex = footpath_on_projection.load_dict_osm_vertex(
            PathToNetwork)
        dict_vertex_osm = footpath_on_projection.load_dict_vertex_osm(
            PathToNetwork)
            
    return (
            stops_dict,
            stoptimes_dict,
            footpath_dict,
            routes_by_stop_dict,
            idx_by_route_stop_dict,
            stop_ids_set
            ),(
            footpath_on_air_b_b,
            footpath_on_projection,
            graph_projection,
            dict_osm_vertex,
            dict_vertex_osm
            )

def verify_break(self,
                 Layer="",
                 LayerDest="",
                 vis="",
                 fields_ok="",
                 f="",
                 protocol_type="",
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

                       )
            self.progressBar.setValue(0)
            self.setMessage("Raptor Algorithm is interrupted by user")
            return True
    return False

def runRaptorWithProtocol(self,
                          sources,
                          raptor_mode,
                          protocol_type,
                          timetable_mode,
                          D_TIME,
                          selected_only1,
                          selected_only2,
                          dictionary,
                          dictionary2,
                          shift_mode = False) -> tuple:

    
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
    MaxWaitTime_copy = MaxWaitTime
    MaxWaitTimeTransfer = float(self.config['Settings']['MaxWaitTimeTransfer'].replace(',', '.'))*60

    
    CHANGE_TIME_SEC = 1
    # time_step = int (self.config['Settings']['TimeInterval'])

    number_bins = int(self.config['Settings']['TimeInterval'])
    time_step = round(MaxTimeTravel/(number_bins*60))  # to min
    time_step_last = round((MaxTimeTravel/60) % number_bins)

    Layer = self.config['Settings']['Layer']
    
    LayerDest = self.config['Settings']['LayerDest']
    layer_dest_field = self.config['Settings']['LayerDest_field']

    LayerViz = self.config['Settings']['LayerViz']
    layer_vis_field = self.config['Settings']['LayerViz_field']
    layer_dest = QgsProject.instance().mapLayersByName(LayerDest)[0]

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

    (
        footpath_on_air_b_b,
        footpath_on_projection,
        graph_projection,
        dict_osm_vertex,
        dict_vertex_osm

    ) = dictionary2

    
    
    if verify_break(self):
        return 0, 0
   

    reachedLabels = dict()

    features_dest = layer_dest.getFeatures()

    if selected_only2:
        features_dest = layer_dest.selectedFeatures()

    fields_ok = []
    f_list = []
    f = ""
    if protocol_type == 2:

        ss = "Origin_ID,Start_time"
        ss += ",Walk_time1,BStop_ID1,Wait_time1,Bus_start_time1,Line_ID1,Ride_time1,AStop_ID1,Bus_finish_time1"
        ss += ",Walk_time2,BStop_ID2,Wait_time2,Bus_start_time2,Line_ID2,Ride_time2,AStop_ID2,Bus_finish_time2"
        ss += ",Walk_time3,BStop_ID3,Wait_time3,Bus_start_time3,Line_ID3,Ride_time3,AStop_ID3,Bus_finish_time3"
        ss += ",DestWalk_time,Destination_ID,Destination_time"
        if raptor_mode == 2:
            ss = ss.replace("Origin_ID", "TEMP_ORIGIN_ID")
            ss = ss.replace("Destination_ID", "Origin_ID")
            ss = ss.replace("TEMP_ORIGIN_ID", "Destination_ID")
            if timetable_mode:
                ss += ",Earlest_arrival_time"
            if not(timetable_mode):
                ss += ",Arrive_before"
        ss += ",Legs,Duration"
        protocol_header = ss + "\n"

    if protocol_type == 1:
        #     with open(f, 'w') as filetowrite:
        #           filetowrite.write(protocol_header)

        ###

        aggregate_dict_all = {}
        # aggregate_this_fields = {}
        f = {}

        intervals_number = number_bins

        if True:  # list_fields_aggregate == "":

            protocol_header = "Origin_ID"
            time_step_min = time_step
            low_bound_min = 0
            top_bound_min = time_step_min
            grades = []

            for i in range(0, intervals_number):
                protocol_header += f',{top_bound_min}m'
                grades.append([low_bound_min, top_bound_min])
                low_bound_min = low_bound_min + time_step_min
                top_bound_min = top_bound_min + time_step_min

            if time_step_last != 0:
                intervals_number += 1
                top_bound_add = low_bound_min + time_step_last
                grades.append([low_bound_min, top_bound_add])
                protocol_header += f',{top_bound_add}m'

            protocol_header += ',bldg_total\n'
            field = "bldg"
            
            f[field] = f'{self.folder_name}//{self.alias}_bldg.csv'
            fields_ok.extend([field])
            # aggregate_this_fields[field] = False
            aggregate_dict_all[field] = {}

            f_curr = f["bldg"].replace(".csv", "_min_duration.csv")
            with open(f_curr, 'w') as filetowrite:
                filetowrite.write(protocol_header)
            f_curr = f["bldg"].replace(".csv", "_min_endtime.csv")
            with open(f_curr, 'w') as filetowrite:
                filetowrite.write(protocol_header)

        if list_fields_aggregate != "":

            field_name_id = layer_dest_field
            fields_aggregate = [value.strip()
                                for value in list_fields_aggregate.split(',')]

            for field in fields_aggregate:

                attribute_dict = {}
                if hasattr(self, 'setMessage'):
                    self.setMessage(f"Building dictionary for '{field}' ...")
                    QApplication.processEvents()

                # aggregate_this_fields[field] = True

                features_dest = layer_dest.getFeatures()
                #if selected_only2:
                #    features_dest = layer_dest.selectedFeatures()

                for feature in features_dest:
                    if isinstance(feature[field], Real) or str(feature[field]).isdigit():
                        attribute_dict[int(feature[field_name_id])] = int(
                            feature[field])
                    else:
                        self.textLog.append(f'<a><b><font color="red"> WARNING: The field "{field}" is not numeric, excluded from aggregation</font> </b></a>')
                        # aggregate_this_fields[field] = False

                        break

                # if aggregate_this_fields[field]:

                fields_ok.extend([field])
                aggregate_dict_all[field] = attribute_dict

                """Prepare header and time grades  
                    statistics_by_accessibility_time_header="Stop_ID,10m,20 m,30 m,40 m,50 m,60 m"+"\n"+"\n"
                    """
                # if aggregate_this_fields[field]:

                protocol_header = "Origin_ID"
                time_step_min = time_step
                low_bound_min = 0
                top_bound_min = time_step_min
                grades = []
                intervals_number = number_bins

                for i in range(0, intervals_number):
                    protocol_header += f',{top_bound_min}m'
                    protocol_header += f',sum({field}[{top_bound_min}m])'
                    grades.append([low_bound_min, top_bound_min])
                    low_bound_min = low_bound_min + time_step_min
                    top_bound_min = top_bound_min + time_step_min

                if time_step_last != 0:
                    intervals_number += 1
                    top_bound_add = low_bound_min + time_step_last
                    grades.append([low_bound_min, top_bound_add])
                    protocol_header += f',{top_bound_add}m'
                    protocol_header += f',sum({field}[{top_bound_add}m])'

                protocol_header += f',{field}_total\n'
                
                f[field] = f'{self.folder_name}//{self.alias}_{field}.csv'

                f_curr = f[field].replace(".csv", "_min_duration.csv")
                with open(f_curr, 'w') as filetowrite:
                    filetowrite.write(protocol_header)

                f_curr = f[field].replace(".csv", "_min_endtime.csv")
                with open(f_curr, 'w') as filetowrite:
                    filetowrite.write(protocol_header)
        f_copy = f

    if not (shift_mode):
        vis = visualization(self, LayerViz, mode=protocol_type,
                        fieldname_layer=layer_vis_field, schedule_mode = timetable_mode)
    else:
        vis = None 
    
    

    for i in range(0, count):

        #if i == 3:
        #   break
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
                        f,
                        protocol_type                        
                        ):
            return 0, 0

        if RunOnAir:
            nearby_buildings_from_start = footpath_on_air_b_b.get_nearby_buildings(SOURCE)
            #list_buildings_from_start = [
            #    str(osm_id) for osm_id, _ in nearby_buildings_from_start]
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
            MaxWaitTime_copy = MaxWaitTime
            
            trans_info = footpath_dict.get(SOURCE, [])
            if raptor_mode == 2: 
                time_start = D_TIME - MaxExtraTime
            else: 
                time_start = D_TIME
            available_boardings = get_available_boardings(time_start, 
                                                          MaxExtraTime, 
                                                          trans_info, 
                                                          stoptimes_dict,
                                                          raptor_mode)
            
            #for step in available_boardings:
            #    (stop_id, time_departure, dist) = step
            #    print (stop_id, seconds_to_time(time_departure), dist)
            #continue
                        
                        
            for step in available_boardings:
                (stop_id, time_departure, dist) = step

                if verify_break(self,
                        Layer,
                        LayerDest,
                        vis,
                        fields_ok,
                        f,
                        protocol_type                        
                        ):
                    return 0, 0
                                    
                #if not (stop_id == '13472' and seconds_to_time(time_departure) == '07:56:20'):
                #    continue
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
                                first_step= firts_step #None#(stop_id, time_departure, dist) 
                                )
                
                for p_i, data in output_endtime.items():
                                       
                    end_time = data[4]  # end_time
                    # Если p_i нет в final_output или найден меньший end_time, обновляем
                    if p_i not in final_output_endtime or end_time < final_output_endtime[p_i][4]:
                        final_output_endtime[p_i] = data
                                        
                for p_i, data in output_duration.items():
                    
                    duration = data[1]  # duration
                                        
                    # Если p_i нет в final_output или найден меньший end_time, обновляем
                    if p_i not in final_output_duration or duration < final_output_duration[p_i][1]:
                        final_output_duration[p_i] = data
                    
            output_endtime = final_output_endtime
            output_duration = final_output_duration

        
        """
        if  timetable_mode:
            MaxExtraTime_copy = MaxExtraTime
            final_output_endtime = {}  
            final_output_duration = {}  
            cycle = 1
            while cycle <=2:
                QApplication.processEvents()
                if cycle == 1:
                    MaxExtraTime = MaxWaitTime
                    timetable_mode = True
                    timetable_mode_sim = True
                    
                else: 
                    MaxExtraTime = MaxExtraTime_copy
                    timetable_mode = True
                    timetable_mode_sim = False
                
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
                            MaxExtraTime,
                            timetable_mode_sim                            
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
                            MaxExtraTime,
                            timetable_mode_sim
                            )

                #keys_to_remove = [key for key, value in output.items() if value[-1] == (None, None, None, None)]

                #for key in keys_to_remove:
                #    del output[key]

                for p_i, data in output_endtime.items():

                                        
                    end_time = data[4]  # end_time
                    
                    # Если p_i нет в final_output или найден меньший end_time, обновляем
                    if p_i not in final_output_endtime or end_time < final_output_endtime[p_i][4]:
                        final_output_endtime[p_i] = data
                                        
                for p_i, data in output_duration.items():
                    
                    duration = data[1]  # duartion
                                        
                    # Если p_i нет в final_output или найден меньший end_time, обновляем
                    if p_i not in final_output_duration or duration < final_output_duration[p_i][1]:
                        final_output_duration[p_i] = data
                    
                output_endtime = final_output_endtime
                output_duration = final_output_duration
                cycle += 1
        """
        if protocol_type == 1:
            f_new = []
            if len(fields_ok) > 0:
                for field in fields_ok:
                    
                    path_file = f_copy[field]
                    f_curr = path_file.replace(".csv", "_min_duration.csv")
                    f_new.append(f_curr) 
                                        
                    make_protocol_summary(SOURCE,
                                          output_duration,
                                          f_curr,
                                          grades,
                                          aggregate_dict_all[field],
                                          nearby_buildings_from_start,
                                          list_buildings_from_start,
                                          set_stops,
                                          field
                                          )
                    
                    
                    f_curr = path_file.replace(".csv", "_min_endtime.csv")
                    f_new.append(f_curr)
                    QApplication.processEvents()
                    make_protocol_summary(SOURCE,
                                          output_endtime,
                                          f_curr,
                                          grades,
                                          aggregate_dict_all[field],
                                          nearby_buildings_from_start,
                                          list_buildings_from_start,
                                          set_stops,
                                          field)
            
            f = f_new
            
            
             


        if protocol_type == 2:
            
            f_curr = f'{self.folder_name}//{self.alias}.csv'
            f_min_duration = f_curr.replace(".csv", "_min_duration.csv")
            f_min_endtime = f_curr.replace(".csv", "_min_endtime.csv")
            f = (f_min_endtime, f_min_duration) 

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
                                   SOURCE
                                   )

    if protocol_type == 2 and len(sources) > 1 and not (timetable_mode):
        f_min_endtime = make_service_area_report(f_min_endtime, f'{self.alias}_min_endtime')
        f_min_duration = make_service_area_report(f_min_duration, f'{self.alias}_min_duration')
        
        f = (f_min_endtime, f_min_duration) 
    
    if protocol_type == 1:
        f = f_new

    QApplication.processEvents()
    if not (shift_mode):
        after_computation_time = datetime.now()
        after_computation_str = after_computation_time.strftime(
        '%Y-%m-%d %H:%M:%S')
        self.textLog.append(f'<a>Finished {after_computation_str}</a>')
        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
    
        self.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

    
    write_info(self,
               Layer,
               LayerDest,
               selected_only1,
               selected_only2,
               vis,
               fields_ok,
               f,
               protocol_type,
               shift_mode,               
               )
    
    if hasattr(self, 'progressBar'):   
        self.setMessage(f'Finished')
        self.progressBar.setValue(self.progressBar.maximum())
    return 1, self.folder_name


def get_available_boardings(start_time_seconds, max_delta_seconds, trans_info, stop_times, mode):
    available_departures = []
    
    for stop_id, walk_time in trans_info:
        if mode == 1:
            arrival_time_seconds = start_time_seconds + walk_time
            max_time_seconds = start_time_seconds + max_delta_seconds + walk_time
        else:
            arrival_time_seconds = start_time_seconds - walk_time
            max_time_seconds = start_time_seconds + max_delta_seconds - walk_time
        
        if arrival_time_seconds > max_time_seconds:
            continue
        
        for route_id, trips in stop_times.items():
            for trip_id, stops in trips.items():
                for stop_seq, stop_seconds in stops:
                    if str(stop_seq) == stop_id:
                        if arrival_time_seconds <= stop_seconds <= max_time_seconds:
                            available_departures.append((stop_id, stop_seconds, walk_time))
        
        available_departures.append(("xxx", "xxx", "xxx"))
        
    return sorted(available_departures, key=lambda x: (x[0], x[1]))

def make_service_area_report(file_path, alias):
    df = pd.read_csv(file_path)

    result = df.loc[df.groupby('Destination_ID')['Duration'].idxmin()]
    folder_name = os.path.dirname(file_path)
    filename = os.path.join(folder_name, f"{alias}_service_area.csv")

    result.to_csv(filename, index=False)
    return filename


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
            for item in f:
                item = os.path.normpath (item)
                self.textLog.append(f'<a>{item}</a>')
                
                alias = os.path.splitext(os.path.basename(item))[0]
                if not (shift_mode):
                    vis.add_thematic_map(item, alias, set_min_value=0)
                

    if protocol_type == 2:
        for item in f:
            item = os.path.normpath (item)
            self.textLog.append(f'<a>{item}</a>')
        if not (shift_mode):
            for item in f:
                alias = os.path.splitext(os.path.basename(item))[0]
                vis.add_thematic_map(item, alias, set_min_value=0)

    if (selected_only1 or selected_only2) and not shift_mode:
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

                zip_filename1 = f'{self.folder_name}//origins_{self.alias}.zip'
                filename1 = f'{self.folder_name}//origins_{self.alias}.geojson'

                self.setMessage(f'Zipping the layer of origins ...')
                QApplication.processEvents()

                save_layer_to_zip(Layer, zip_filename1, filename1)

            if selected_only2:

                zip_filename2 = f'{self.folder_name}//destinations_{self.alias}.zip'
                filename2 = f'{self.folder_name}//destinations_{self.alias}.geojson'

                self.setMessage(f'Zipping the layer of destinations ...')
                QApplication.processEvents()

                save_layer_to_zip(LayerDest, zip_filename2, filename2)

    self.textLog.append(f'<a href="file:///{self.folder_name}" target="_blank" >Output in folder</a>')


# for type_protokol = 1
def make_protocol_summary(SOURCE,
                          dictInput,
                          f,
                          grades,
                          attribute_dict,
                          nearby_buildings_from_start,
                          list_buildings_from_start,
                          set_stops,
                          field
                          ):

    
    time_grad = grades
    # [[-1,0], [0,10],[10,20],[20,30],[30,40],[40,50],[50,61] ]
    counts = {x: 0 for x in range(0, len(time_grad))}  # counters for grades
    # counters for agrregates
    agrregates = {x: 0 for x in range(0, len(time_grad))}

    # f2 = r"c:\temp\rep2.csv"
    with open(f, 'a') as filetowrite:
        # with open(f2, 'w') as file2:

        for dest, info in dictInput.items():

            if str(dest) in set_stops:
                continue

            if str(dest) in list_buildings_from_start:
                continue

            time_to_dest = round(int(info[1]))
            
            for i in range(0, len(time_grad)):
                grad = time_grad[i]

                if time_to_dest <= grad[1]*60:
                    counts[i] = counts[i] + 1
                    # file2.write(f'{str(dest)}\n')

                    if field != "bldg":
                        agrregates[i] = agrregates[i] + \
                            attribute_dict.get(int(dest), 0)

                        

        # counts[0] = counts[0] + 1 # for case time_item = 0 (from source to source)

        # add build to build to var counts
        for build_item, time_item in nearby_buildings_from_start:
            for i in range(0, len(time_grad)):
                grad = time_grad[i]

                if time_item <= grad[1]*60:
                    counts[i] = counts[i] + 1
                    # file2.write(f'{str(build_item)}\n')
                    if field != "bldg":
                        agrregates[i] = agrregates[i] + \
                            attribute_dict.get(int(build_item), 0)

        row = str(SOURCE)
        if field == "bldg":
            Total = counts[len(time_grad)-1]
        if field != "bldg":
            Total = agrregates[len(time_grad)-1]

        for i in range(0, len(time_grad)):
            row = f'{row},{counts[i]}'
            if field != "bldg":
                row = f'{row},{agrregates[i]}'

        filetowrite.write(f'{row},{Total}\n')


# for type_protokol =2
def make_protocol_detailed(raptor_mode,
                           D_TIME,
                           dictInput,
                           protocol_full_path,
                           timetable_mode,
                           nearby_buildings_from_start,
                           list_buildings_from_start,
                           set_stops,
                           SOURCE
                           ):

    sep = ","
    stop_symbol = "s:"
    f = protocol_full_path

    
    
    
    with open(f, 'a') as filetowrite:


        start_time = seconds_to_time(D_TIME)
                

        if raptor_mode == 1:
                    row = f'{SOURCE}{sep}{start_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}0{sep}{SOURCE}{sep}{start_time}{sep}0{sep}0'
        else:
                    row = f'{SOURCE}{sep}{start_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}0{sep}{SOURCE}{sep}{start_time}{sep}{start_time}{sep}0{sep}0'

        filetowrite.write(row + "\n")

        for build, dist in nearby_buildings_from_start:

            if raptor_mode == 1:
                        finish_time = seconds_to_time(D_TIME+dist)
                        row = f'{SOURCE}{sep}{start_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{dist}{sep}{build}{sep}{finish_time}{sep}0{sep}{dist}'
            else:
                        finish_time = seconds_to_time(D_TIME-dist)
                        row = f'{build}{sep}{finish_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{dist}{sep}{SOURCE}{sep}{start_time}{sep}{start_time}{sep}0{sep}{dist}'

            if str(build) != str(SOURCE):
                filetowrite.write(row + "\n")

        # dictInput - dict from testRaptor
        # every item dictInput : dest - key, info - value

        for dest, info in dictInput.items():

            SOURCE = info[0]
            duration = info[1]
            pareto_set = info[2]
            transfers = info[3]
            legs = transfers + 1


            '''
    Examle pareto_set =
    [(0, [('walking', 2003, 24206.0, Timedelta('0 days 00:02:47'),Timestamp('2023-06-30 08:37:13')), 
    (Timestamp('2023-06-30 08:36:59'), 24206, 14603, Timestamp('2023-06-30 08:33:36'), '3150_67'), 
    ('walking', 14603, 1976.0, Timedelta('0 days 00:02:03.300000'), Timestamp('2023-06-30 08:31:32.700000'))])]    
    '''     

            if pareto_set is None or dest is None:
                continue

            '''
    Examle jorney
    [('walking', 2003, 24206.0, Timedelta('0 days 00:02:47'), Timestamp('2023-06-30 08:37:13')), 
    (Timestamp('2023-06-30 08:36:59'), 24206, 14603, Timestamp('2023-06-30 08:33:36'), '3150_67'), 
    ('walking', 14603, 1976.0, Timedelta('0 days 00:02:03.300000'), Timestamp('2023-06-30 08:31:32.700000'))]
    '''

            # for journey in pareto_set: #each journey is array, legs are its elements
            if True:

                journey = pareto_set

                # run inversion jorney also raptor_mode = 1

                if raptor_mode == 2:
                    # inversion row
                    journey = journey[::-1]
                    # inversion inside every row

                    journey = [(tup[0], tup[2], tup[1], tup[3], tup[4]) if not isinstance(tup[0], int) else
                               tup[:4][::-1] +
                               (tup[4],) if isinstance(tup[0], int) else tup
                               for tup in journey
                               ]

                if raptor_mode == 1:

                    journey = [(tup[0], tup[1], tup[2], tup[3], tup[4] - tup[3])
                               if tup[0] == 'walking' else tup for tup in journey]

                last_bus_leg = None
                last_leg = None
                first_boarding_stop = ""  # BStop1_ID
                first_boarding_time = ""
                first_bus_arrive_stop = ""  # AStop1_ID
                first_bus_arrival_time = ""

                second_boarding_stop = ""  # BStop2_ID
                second_boarding_time = ""
                second_bus_arrive_stop = ""  # AStop2_ID
                second_bus_arrival_time = ""

                third_boarding_stop = ""  # BStop3_ID
                third_boarding_time = ""
                third_bus_arrive_stop = ""  # AStop3_ID
                third_bus_arrival_time = ""

                sfirst_boarding_time = " "
                sfirst_arrive_time = " "
                ssecond_boarding_time = ""
                ssecond_bus_arrival_time = ""
                sthird_boarding_time = ""
                sthird_bus_arrival_time = ""

                first_bus_leg_found = False
                second_bus_leg_found = False
                third_bus_leg_found = False

                walk1_time = ""  # walk time from orgin to first bus stop or to destination if no buses
                walk1_arriving_time = ""  # I need it to compute wait1_time
                wait1_time = 0
                line1_id = ""  # number of first route (or trip)
                ride1_time = ""

                walk2_time = ""  # from 1 bus alightning to second bus boarding

                wait2_time = ""  # time between arriving to second bus stop and boarding to the bus
                line2_id = ""  # number of second route (or trip)
                ride2_time = ""

                walk3_time = ""  # from 2 bus alightning to 3 bus boarding

                wait3_time = ""  # time between arriving to 3 bus stop and boarding to the bus
                line3_id = ""  # number of 3 route (or trip)
                ride3_time = ""

                walk4_time = ""
                dest_walk_time = ""  # walking time  to destination

                legs_counter = 0
                last_leg_type = ""
                ride_counter = 0
                walking_time_sec = 0

                '''
         Examlpe leg
          ('walking', 2003, 24206.0, Timedelta('0 days 00:02:47'), Timestamp('2023-06-30 08:37:13'))
          or
          (Timestamp('2023-06-30 08:36:59'), 24206, 14603, Timestamp('2023-06-30 08:33:36'), '3150_67')


         '''
                start_time = None

                for leg in journey:

                    legs_counter = legs_counter+1
                    last_leg = leg
                    #  here counting walk(n)_time if leg[0] == 'walking
                    #  !!!!! why can walk1_time != "" !!!!!!!!!!!! why verify?
                    if leg[0] == 'walking':

                        walking_time_sec = round(leg[3], 1)
                        if ride_counter == 0:
                            SOURCE_REV = leg[1]  # for backward algo
                            if walk1_time == "":
                                walk1_time = walking_time_sec
                            else:
                                walk1_time = walk1_time + walking_time_sec

                            walk1_arriving_time = leg[4] + leg[3]
                        elif ride_counter == 1:
                            if walk2_time == "":
                                walk2_time = walking_time_sec
                            else:
                                walk2_time = walk2_time + walking_time_sec

                            walk2_arriving_time = leg[4]

                        elif ride_counter == 2:
                            if walk3_time == "":
                                walk3_time = walking_time_sec
                            else:
                                walk3_time = walk3_time + walking_time_sec

                            walk3_arriving_time = leg[4] - leg[3]

                        elif ride_counter == 3:
                            if walk4_time == "":
                                walk4_time = walking_time_sec
                            else:
                                walk4_time = walk4_time + walking_time_sec

                            walk4_arriving_time = leg[4] + leg[3]

                        if start_time is None:
                            start_time = leg[4]

                        # here finish counting walk1_time if leg[0] == 'walking
                    else:
                        if not first_bus_leg_found:
                            # in this leg - first leg is bus, saving params for report

                            if start_time is None:
                                start_time = leg[0]
                                SOURCE_REV = leg[1]  # for backward algo

                            first_bus_leg_found = True
                            ride_counter = 1
                            first_bus_leg = leg

                            first_boarding_time = leg[0]
                            first_boarding_stop = leg[1]
                            first_bus_arrive_stop = leg[2]
                            first_bus_arrival_time = leg[3]

                            ride1_time = round(
                                (first_bus_arrival_time - first_boarding_time), 1)

                            if last_leg_type == "walking":

                                wait1_time = round(
                                    (first_boarding_time - walk1_arriving_time), 1)
                            else:

                                if raptor_mode == 1:

                                    wait1_time = round(
                                        (first_boarding_time - D_TIME), 1)
                                else:

                                    wait1_time = round(
                                        (first_boarding_time - start_time), 1)

                            line1_id = leg[4]

                        elif not second_bus_leg_found:
                            # in this leg - second leg is bus, saving params for report
                            if start_time is None:
                                start_time = leg[0]
                            second_bus_leg_found = True
                            ride_counter = 2
                            second_boarding_time = leg[0]
                            ssecond_boarding_time = seconds_to_time(
                                second_boarding_time)
                            second_boarding_stop = leg[1]

                            second_bus_arrive_stop = leg[2]
                            second_bus_arrival_time = leg[3]
                            ssecond_bus_arrival_time = seconds_to_time(
                                second_bus_arrival_time)

                            if last_leg_type == "walking":

                                wait2_time = round(
                                    (second_boarding_time - first_bus_arrival_time - walk2_time), 1)
                            else:

                                wait2_time = round(
                                    (second_boarding_time - first_bus_arrival_time), 1)

                            line2_id = leg[4]

                            ride2_time = round(
                                (second_bus_arrival_time - second_boarding_time), 1)

                        else:  # 3-rd bus found
                            third_bus_leg_found = True
                            # in this leg - third leg is bus, saving params for report
                            if start_time is None:
                                start_time = leg[0]
                            ride_counter = 3
                            third_boarding_time = leg[0]
                            sthird_boarding_time = seconds_to_time(
                                third_boarding_time)
                            third_boarding_stop = leg[1]
                            third_bus_arrive_stop = leg[2]
                            third_bus_arrival_time = leg[3]
                            sthird_bus_arrival_time = seconds_to_time(
                                third_bus_arrival_time)

                            if last_leg_type == "walking":

                                wait3_time = round(
                                    (third_boarding_time - second_bus_arrival_time - walk3_time), 1)
                            else:

                                wait3_time = round(
                                    (third_boarding_time - second_bus_arrival_time), 1)

                            line3_id = leg[4]

                            ride3_time = round(
                                (third_bus_arrival_time - third_boarding_time), 1)

                        last_bus_leg = leg

                    last_leg_type = leg[0]  # in current journey

                    # this legs finish, postprocessing this journey
                if last_leg_type == "walking":
                    if walk4_time != "":
                        dest_walk_time = walk4_time
                        walk4_time = ""
                    elif walk3_time != "":
                        dest_walk_time = walk3_time
                        walk3_time = ""
                    elif walk2_time != "":
                        dest_walk_time = walk2_time
                        walk2_time = ""
                    elif walk1_time != "":
                        dest_walk_time = walk1_time
                        walk1_time = ""

                    # end of cycle by legs
                    # Calculate waiting time before boarding

                    # If first_bus_leg and last_bus_leg are found
                    # they may be the same leg
                    # get boarding_time from first_bus_leg
                sfirst_boarding_stop = ""
                sfirst_arrive_stop = ""
                sline1_id = ""
                sride1_time = ""

                ssecond_boarding_stop = ""
                ssecond_arrive_stop = ""
                sline2_id = ""
                sride2_time = ""

                sthird_boarding_stop = ""
                sthird_arrive_stop = ""
                sline3_id = ""
                sride3_time = ""

                # last_bus_leg - last leg of current jorney
                if not last_bus_leg is None:  # work forever?
                    first_boarding_stop_orig = first_boarding_stop
                    first_bus_arrive_stop_orig = first_bus_arrive_stop
                    sfirst_boarding_stop = f'{stop_symbol}{first_boarding_stop_orig}'
                    sfirst_arrive_stop = f'{stop_symbol}{first_bus_arrive_stop_orig}'

                    sfirst_boarding_time = seconds_to_time(first_boarding_time)
                    sfirst_arrive_time = seconds_to_time(
                        first_bus_arrival_time)

                    if second_bus_leg_found:
                        second_boarding_stop_orig = second_boarding_stop
                        second_bus_arrive_stop_orig = second_bus_arrive_stop
                        ssecond_boarding_stop = f'{stop_symbol}{second_boarding_stop_orig}'
                        ssecond_arrive_stop = f'{stop_symbol}{second_bus_arrive_stop_orig}'

                    if third_bus_leg_found:
                        third_boarding_stop_orig = third_boarding_stop
                        third_bus_arrive_stop_orig = third_bus_arrive_stop
                        sthird_boarding_stop = f'{stop_symbol}{third_boarding_stop_orig}'
                        sthird_arrive_stop = f'{stop_symbol}{third_bus_arrive_stop_orig}'

                # Define what was mode of the last leg:
                # here leg is the last leg that was in previous cycle
                Destination = leg[2]

                if last_leg[0] == 'walking':

                    arrival_time = last_leg[4] + last_leg[3]
                else:

                    arrival_time = last_leg[3]

                sarrival_time = seconds_to_time(arrival_time)

                orig_dest = Destination

                if walk1_time == "":
                    walk1_time = 0

                if walk2_time == "" and ssecond_boarding_stop != "":
                    walk2_time = 0

                if walk3_time == "" and sthird_boarding_stop != "":
                    walk3_time = 0

                if dest_walk_time == "":
                    dest_walk_time = 0

                # if timetable_mode and len(journey) > 1:
                #  D_TIME = journey[0][4]
                if timetable_mode and raptor_mode == 1:
                    D_TIME = journey[0][4]

                # if timetable_mode and raptor_mode == 2:
                
                if raptor_mode == 2:
                    if len(journey) > 1:
                        sarrival_time = seconds_to_time(
                            journey[-2][3] + journey[-1][3])
                    else:

                        if journey[0][0] == "walking":
                            sarrival_time = seconds_to_time(
                                journey[0][3] + journey[0][4])
                        else:
                            sarrival_time = seconds_to_time(journey[0][3])
                
                if raptor_mode == 1:
                    # if orig_dest in list_stops or orig_dest in list_buildings_from_start:
                    #    continue
                    if orig_dest in list_buildings_from_start:
                        continue
                    if str(orig_dest) in set_stops:
                        continue

                    row = f'{SOURCE}{sep}{seconds_to_time(D_TIME)}{sep}{walk1_time}{sep}{sfirst_boarding_stop}\
{sep}{wait1_time}{sep}{sfirst_boarding_time}{sep}{line1_id}{sep}{ride1_time}{sep}{sfirst_arrive_stop}{sep}{sfirst_arrive_time}\
{sep}{walk2_time}{sep}{ssecond_boarding_stop}{sep}{wait2_time}{sep}{ssecond_boarding_time}{sep}{line2_id}{sep}{ride2_time}{sep}{ssecond_arrive_stop}{sep}{ssecond_bus_arrival_time}\
{sep}{walk3_time}{sep}{sthird_boarding_stop}{sep}{wait3_time}{sep}{sthird_boarding_time}{sep}{line3_id}{sep}{ride3_time}{sep}{sthird_arrive_stop}{sep}{sthird_bus_arrival_time}\
{sep}{dest_walk_time}{sep}{orig_dest}{sep}{sarrival_time}{sep}{legs}{sep}{duration}'

                else:
                    # if SOURCE_REV in list_stops or  SOURCE_REV in list_buildings_from_start:
                    #  continue
                    if SOURCE_REV in list_buildings_from_start:
                        continue
                    if str(SOURCE_REV) in set_stops:
                        continue
                    row = f'{SOURCE_REV}{sep}{seconds_to_time(start_time)}{sep}{walk1_time}{sep}{sfirst_boarding_stop}\
{sep}{wait1_time}{sep}{sfirst_boarding_time}{sep}{line1_id}{sep}{ride1_time}{sep}{sfirst_arrive_stop}{sep}{sfirst_arrive_time}\
{sep}{walk2_time}{sep}{ssecond_boarding_stop}{sep}{wait2_time}{sep}{ssecond_boarding_time}{sep}{line2_id}{sep}{ride2_time}{sep}{ssecond_arrive_stop}{sep}{ssecond_bus_arrival_time}\
{sep}{walk3_time}{sep}{sthird_boarding_stop}{sep}{wait3_time}{sep}{sthird_boarding_time}{sep}{line3_id}{sep}{ride3_time}{sep}{sthird_arrive_stop}{sep}{sthird_bus_arrival_time}\
{sep}{dest_walk_time}{sep}{SOURCE}{sep}{sarrival_time}{sep}{seconds_to_time(D_TIME)}{sep}{legs}{sep}{duration}'

                filetowrite.write(row + "\n")


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
