import os
import csv
from datetime import datetime
import pandas as pd
from pathlib import Path
from collections import defaultdict

from qgis.analysis import QgsGraphAnalyzer
from qgis.PyQt.QtWidgets import QApplication

from tau_net_calc.cls.visualization import visualization
from tau_net_calc.cls.common import (get_existing_path, 
                    get_name_columns,
                    make_service_area_report_gpkg,
                    fast_write_gpkg,
                    make_pivot_gpkg)


class car_accessibility:
    def __init__(self,
                 parent,
                 layer_dest,
                 layerdest_field,
                 max_time_minutes,
                 time_step_minutes,
                 layer_vis,
                 layer_vis_field,
                 list_fields_aggregate                 
                 ):

        

        self.max_time_minutes = max_time_minutes
        
        #self.number_bins = time_step_minutes
        #self.time_step_minutes = self.max_time_minutes//self.number_bins
        #self.time_step_last = self.max_time_minutes%self.number_bins

        self.time_step_minutes = time_step_minutes  
        self.number_bins = int(max_time_minutes // (self.time_step_minutes ))  
        self.time_step_last = int(max_time_minutes % (self.time_step_minutes) )

        self.layer_dest = layer_dest
        
        self.layer_orig = parent.layer_origin
        self.layerorig_field = parent.layerorig_field
        self.crs = self.layer_dest.crs()
        units = self.crs.mapUnits()
        self.crs_grad = (units == 6)
        
        self.parent = parent
        self.target_ids = set(self.parent.get_feature_from_layer(self.layer_dest))

        self.layer_vis = layer_vis
        self.max_time_sec = self.max_time_minutes * 60

        self.layerdest_field = layerdest_field
        self.layer_vis_field = layer_vis_field

        self.list_fields_aggregate = list_fields_aggregate        

        self.already_display_break = False

        self.read_factor_speed_by_hour()

        cols_dict = get_name_columns()
        self.cols = cols_dict[(self.parent.mode, self.parent.protocol_type)]
        self.short_result = {}

        self.df_all = []
        self.table_name_list = []

        self.header_dict = defaultdict(list)
        self.df_all_dict = defaultdict(list)

        self.fields_ok = []

    def read_factor_speed_by_hour(self):
             
        self.file_path_factor_speed_by_hour = get_existing_path (self.parent.path_to_pkl, "cdi_index.csv")
        self.factor_speed_by_hour = {}

        with open(self.file_path_factor_speed_by_hour, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hour_item = int(row['hour'])
                factor_item = float(row['cdi'])
                self.factor_speed_by_hour[hour_item] = factor_item


    # experimental
    
    def check_speed_fields(self, layer):
        field_names = layer.fields().names()
        for h in range(5, 24):  # от 05 до 23
            fname = f"fspeed_{h:02d}"
            if fname not in field_names:
                return False
        return True
    
    def read_road_speed_default(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, 'config')
        
        self.file_path_road_speed_default = os.path.join(
            config_path, "car_speed_by_link_type.csv")
        
        self.type_road_speed_default = {}

        with open(self.file_path_road_speed_default, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                type_road = row['link_type']
                speed_default = int(row['speed_km_h'])
                self.type_road_speed_default[type_road] = speed_default    
    
    def find_car_accessibility(self):

        self.short_result = {}

        graph = self.graph

        self.f_list = []
        
        count = len(self.parent.points)
        self.parent.progressBar.setMaximum(count)

        self.parent.progressBar.setValue(1)
        i = 0

        time_estimate_start = datetime.now()
        total_tasks = count * self.roundtrip_cycle_all
        
        for source in self.parent.points:
            QApplication.processEvents()
            if self.verify_break():
                return 0
            
            if i > 0:# and i%10 == 0:          
                tasks_done = ((self.roundtrip_cycle_current - 1) * count) + i                    
                # 3. Среднее время на одну задачу
                elapsed = datetime.now() - time_estimate_start
                avg_time_per_task = elapsed / i                
                # 4. Сколько задач осталось
                tasks_remaining = total_tasks - tasks_done                
                # 5. Итоговое время            
                remaining_duration = avg_time_per_task * tasks_remaining                            
                display_time = str(remaining_duration).split('.')[0]                
                self.parent.lblEstimateTime.setText(f'Time remaining: {display_time}')

            i += 1

            self.parent.setMessage(f'Building thematic map for the feature №{i} of {count}')
            QApplication.processEvents()

            self.source = source
            idStart = self.parent.dict_building_vertex.get(self.source, ("xxx"))
            
            if idStart == "xxx":
                self.parent.progressBar.setValue(count+1)
                continue

            (self.tree, self.costs) = QgsGraphAnalyzer.dijkstra(graph,  idStart, 0)
            self.calc_min_cost()
            if self.parent.protocol_type == 2:
                data_body = self.makeProtocolArea()
                if not self.parent.roundtrip:
                    df_current = pd.DataFrame(data_body, columns=self.table_header_list)
                    self.df_all.append(df_current)
            else:
                if len(self.fields_ok) > 0:
                    for field in self.fields_ok:
                        data_body = self.makeProtocolMap(self.aggregate_dict_all[field],field)
                        if not self.parent.roundtrip:
                            df_current = pd.DataFrame(data_body, columns=self.header_dict[field])
                            self.df_all_dict[field].append(df_current)

            self.parent.progressBar.setValue(i + 1)

    def calc_min_cost(self):
        self.min_costs = {}
        if self.source is not None:
            self.min_costs[(self.source, self.source)] = (0, 0,0,0)
        count = 0        
        
        sum_walk = self.parent.walk_on_start_m + self.parent.walk_on_finish_m

        # Итерируемся по вершинам: индекс — это vertex_id, значение — incoming edgeId
        for vertex_id, edgeId in enumerate(self.tree):

            count += 1
            if count % 10000 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()

            if edgeId == -1:
                continue
            
            if vertex_id >= len(self.costs):
                continue
                
            cost_edge = self.costs[vertex_id]  # Стоимость берется по vertex_id
            if cost_edge == float('inf'):
                continue

            # Ищем здание строго по ID вершины (vertex_id)
            building = self.parent.dict_vertex_building.get(vertex_id)

            if building is None or int(building) not in self.target_ids:
                continue

            Dist_between_nodes = cost_edge * 10            
            Dist_OD = Dist_between_nodes
            Dist_to_drive = Dist_OD - sum_walk

            if Dist_to_drive <= 0:
                cost_res = round(Dist_OD / self.parent.walk_speed_m_s)
                veh_legs = 0
            else:
                veh_legs = 1
                if Dist_between_nodes < self.parent.MinimalDistance:
                    Time_to_drive = round(Dist_between_nodes / self.parent.walk_speed_m_s)
                else:
                    Time_to_drive = cost_edge * (Dist_to_drive / Dist_between_nodes) / self.factor_speed

                cost_res = round(sum_walk / self.parent.walk_speed_m_s + Time_to_drive)

            if self.source == building:
                cost_res = 0

            if cost_res > self.max_time_sec:
                continue

            pair = (self.source, building)
            existing = self.min_costs.get(pair)
            if existing is None or cost_res < existing[0]:
                start_time = self.start_time
                end_time = start_time + cost_res
                self.min_costs[pair] = (cost_res, veh_legs, start_time, end_time)

    def makeProtocolArea(self):

        rows = []
        for (source, building), (min_cost, veh_legs, start_time, end_time) in self.min_costs.items():
            if self.parent.mode == 1:
                row = f'{source},{building},{veh_legs},{min_cost}\n'
            else:
                row = f'{building},{source},{veh_legs},{min_cost}\n'
                        
            rows.append (row)
            self.short_result[(source, building)] = (start_time, end_time, min_cost)        

        data_body = [row.split(',') for row in rows]
        return data_body
        
    def makeProtocolMap(self,                       
                        aggregate_dict,
                        field):

        unique_sources = set(src for src, _ in self.min_costs.keys())
        for source in unique_sources:
            counts = {x: 0 for x in range(0, len(self.grades))}
            aggregates = {x: 0 for x in range(0, len(self.grades))}

            # iterate through the minimum cost values for each pair (source, building)
            for (src, building), (cost, veh_legs, start_time, end_time) in self.min_costs.items():
                if src == source and cost <= self.max_time_sec:
                    # find the corresponding gradation
                    self.short_result[(src, building)] = (start_time, end_time, cost)
                    for i in range(0, len(self.grades)):
                        grad = self.grades[i]
                        if cost <= grad[1]:
                            counts[i] += 1

                            if field != "nbldg":
                                aggregates[i] = aggregates[i] + \
                                    aggregate_dict.get(int(building), 0)

            row = source

            if field == "nbldg":
                Total = counts[len(self.grades) - 1]
            if field != "nbldg":
                Total = aggregates[len(self.grades) - 1]
            
            for i in range(0, len(self.grades)):
                row = f'{row},{counts[i]}'
                if field != "nbldg":
                    row = f'{row},{aggregates[i]}'
            
            data_body = [row.split(',') + [str(Total)]]

            return data_body

    def create_head_files(self):

        if self.parent.protocol_type == 1:  # MAP
            
            self.aggregate_dict_all = {}
            self.aggregate_this_fields = {}
            self.f = {}

            intervals_number = self.number_bins
            protocol_header = self.cols["star"]
            time_step_min = self.time_step_minutes
            low_bound_min = 0
            top_bound_min = time_step_min
            self.grades = []

            for i in range(0, intervals_number):
                protocol_header += f',{top_bound_min}m'
                self.grades.append([low_bound_min*60, top_bound_min*60])
                low_bound_min = low_bound_min + time_step_min
                top_bound_min = top_bound_min + time_step_min

            if self.time_step_last != 0:
                intervals_number += 1
                top_bound_add = low_bound_min + self.time_step_last
                self.grades.append([low_bound_min*60, top_bound_add*60])
                protocol_header += f',{top_bound_add}m'

            protocol_header += ',nbldg_total\n'
            field = "nbldg"

            #hex = "_hex_" in self.layer_dest.name().lower()

            if True: #not (hex and self.list_fields_aggregate):                                       
                self.header_dict[field] = protocol_header.strip().split(',')                        
                self.fields_ok.append(field)
                self.aggregate_this_fields[field] = False
                self.aggregate_dict_all[field] = {}
            
            if self.list_fields_aggregate != "":

                field_name_id = self.layerdest_field
                fields_aggregate = [value.strip() for value in self.list_fields_aggregate.split(',')]

                for field in fields_aggregate:

                    attribute_dict = {}
                    self.parent.setMessage(f"Building database for '{field}' ...")
                    QApplication.processEvents()

                    self.aggregate_this_fields[field] = True

                    features_dest = self.layer_dest.getFeatures()

                    for feature in features_dest:
                        attribute_dict[int(feature[field_name_id])] = int(feature[field])

                    self.fields_ok.append(field)
                    self.aggregate_dict_all[field] = attribute_dict

                    """Prepare header and time grades  
                                statistics_by_accessibility_time_header="Stop_ID,10m,20 m,30 m,40 m,50 m,60 m"+"\n"+"\n"
                                """

                    protocol_header = self.cols["star"]
                    time_step_min = self.time_step_minutes
                    top_bound_min = time_step_min

                    intervals_number = self.number_bins

                    for i in range(0, intervals_number):
                        protocol_header += f',{top_bound_min}m'
                        #protocol_header += f',sum({field}[{top_bound_min}m])'
                        protocol_header += f',{top_bound_min}m_{field}'
                        top_bound_min = top_bound_min + time_step_min

                    if self.time_step_last != 0:
                        intervals_number += 1
                        top_bound_add = top_bound_min - time_step_min + self.time_step_last
                        protocol_header += f',{top_bound_add}m'
                        protocol_header += f',{top_bound_add}m_{field}'

                    protocol_header += f',{field}_total\n'

                    self.header_dict[field] = protocol_header.strip().split(',')
                   
    def run(self, 
            begin_computation_time, 
            hour, 
            graph, 
            start_time,
            write_info,            
            roundtrip_cycle_all = 1,
            roundtrip_cycle_current =  1):
        
        self.roundtrip_cycle_all = roundtrip_cycle_all
        self.roundtrip_cycle_current = roundtrip_cycle_current

        self.begin_computation_time = begin_computation_time

        self.factor_speed = self.factor_speed_by_hour[hour]

        self.hour = hour

        self.graph = graph

        self.start_time = start_time

        if True:
            self.create_head_files()

            if self.parent.mode == 1:
                table_header = f'{self.cols["star"]},{self.cols["hash"]},Veh_legs,Duration\n'
            else:
                table_header = f'{self.cols["hash"]},{self.cols["star"]},Veh_legs,Duration\n'
            
            self.table_header_list = table_header.strip().split(',')
        
        self.file_name = Path(self.parent.file_name_gpkg).stem        
        self.find_car_accessibility()

        if self.parent.mode == 1:
            name = 'origin'
        else:
            name = 'destination'
        
        # создаем pivot если не roundtrip, данные не свернутые
        if self.parent.protocol_type == 2 and not self.parent.roundtrip:
            df_pivot = make_pivot_gpkg (self.short_result, self.cols["star"], self.cols["hash"])
            table_name = f'{self.file_name}_triptime_by_{name}s'
            fast_write_gpkg(self.parent.file_name_gpkg, table_name, df_pivot)

        # данные сворачиваем если SA 
        if self.parent.protocol_type == 2 and not self.parent.roundtrip: #and len(self.parent.points) > 1:            
            df_min_duration = make_service_area_report_gpkg(self.df_all, self.cols["star"], self.cols["hash"])    

        # если SA и не roundtrip - сохраняем данные
        if self.parent.protocol_type == 2 and not self.parent.roundtrip:
            table_name = f'{self.file_name}_triptime'
            self.table_name_list.append(table_name)            
            fast_write_gpkg(self.parent.file_name_gpkg, table_name, df_min_duration)
        
        if self.parent.protocol_type == 1 and not self.parent.roundtrip:
    
            for field, list_of_dfs in self.df_all_dict.items():
                if list_of_dfs:  
                    df_final = pd.concat(list_of_dfs, ignore_index=True)
                    table_name = f'{self.file_name}_stat_{field}_triptime'
                    self.table_name_list.append(table_name)
                    fast_write_gpkg(self.parent.file_name_gpkg, table_name, df_final)

        QApplication.processEvents()

        if  write_info:
            self.write_info()
        
        return self.short_result

    def verify_break(self):
        if self.parent.break_on:
            self.parent.setMessage("Car accessibility computations are interrupted by user")
            if not self.already_display_break:
                self.parent.textLog.append(f'<a><b><font color="red">Car accessibility computations are interrupted by user</font> </b></a>')
                #self.write_info()
                self.already_display_break = True
                self.parent.lblEstimateTime.setText("")

            self.parent.progressBar.setValue(0)
            return True
        return False

    def write_info(self):

        vis = visualization(self.parent,
                            self.layer_vis,
                            mode=self.parent.protocol_type,
                            fieldname_layer=self.layer_vis_field,
                            from_to = self.parent.mode,
                            prefix = self.file_name
                            )
        
        #self.parent.textLog.append(f'<a>Output:</a>')
        if self.parent.protocol_type == 1:
            if len(self.fields_ok) > 0:
                for item in  self.table_name_list:
                    vis.add_thematic_map_gpkg(self.parent.file_name_gpkg, item, item )
                    #self.parent.textLog.append(f'<a>{item}</a>')

        if self.parent.protocol_type == 2:
            
            for item in self.table_name_list:
                
                vis.add_thematic_map_gpkg(self.parent.file_name_gpkg, item, item )
            #self.parent.textLog.append(f'<a>{item}</a>')

        after_computation_time = datetime.now()
        after_computation_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')

        duration_computation = after_computation_time - self.begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

        self.parent.textLog.append(f'Output in file: <a href="file:///{self.parent.file_name_gpkg}" target="_blank" > {self.parent.file_name_gpkg}</a>')
        self.parent.setMessage(f'Finished')
        self.parent.lblEstimateTime.setText("")
        self.parent.progressBar.setValue(self.parent.progressBar.maximum())       
