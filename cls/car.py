import os
import csv
from datetime import datetime
import zipfile
import tempfile
import pandas as pd
import glob

from qgis.analysis import QgsGraphAnalyzer
from PyQt5.QtWidgets import QApplication, QMessageBox
from qgis.core import QgsVectorFileWriter

from pkl_car import pkl_car
from visualization import visualization
from common import get_prefix_alias


class car_accessibility:
    def __init__(self,
                 parent,
                 layer_dest,
                 selected_only2,
                 layerdest_field,
                 max_time_minutes,
                 time_step_minutes,
                 layer_vis,
                 layer_vis_field,
                 list_fields_aggregate
                 ):

        self.max_time_minutes = max_time_minutes
        
        self.number_bins = time_step_minutes
        self.time_step_minutes = round(self.max_time_minutes/self.number_bins)

        self.time_step_last = round((self.max_time_minutes) % self.number_bins)

        self.layer_dest = layer_dest
        self.crs = self.layer_dest.crs()
        self.selected_only2 = selected_only2

        self.parent = parent

        self.layer_vis = layer_vis
        self.max_time_sec = self.max_time_minutes * 60

        self.layerdest_field = layerdest_field
        self.layer_vis_field = layer_vis_field

        self.list_fields_aggregate = list_fields_aggregate

        self.writed_info = False

        self.already_display_break = False

        self.read_factor_speed_by_hour()

        self.factor_speed = self.factor_speed_by_hour[self.parent.hour]

    def read_factor_speed_by_hour(self):

        self.file_path_factor_speed_by_hour = os.path.join(
            self.parent.path_to_pkl, "cdi_index.csv")
        self.factor_speed_by_hour = {}

        with open(self.file_path_factor_speed_by_hour, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hour_item = int(row['hour'])
                factor_item = float(row['cdi'])
                self.factor_speed_by_hour[hour_item] = factor_item

    def find_car_accessibility(self):

        self.f_list = []
        pkl_car_reader = pkl_car()
        count = len(self.parent.points)
        self.parent.progressBar.setMaximum(count + 1)
        self.parent.setMessage("Loading pkl...")
        QApplication.processEvents()

        self.dict_building_vertex, self.dict_vertex_buildings = pkl_car_reader.load_files(
            self.parent.path_to_pkl
        )

        self.graph = pkl_car_reader.load_graph(
            self.parent.mode,
            self.parent.path_to_pkl,
            self.crs
        )

        self.parent.progressBar.setValue(1)
        i = 0

        self.create_head_files()

        if self.parent.mode == 1:
            table_header = "Origin_ID,Destination_ID,Duration\n"
        else:
            table_header = "Destination_ID,Origin_ID,Duration\n"

        prefix_alias = get_prefix_alias(False,
                                        self.parent.protocol_type,
                                        self.parent.mode
                                        )
        if self.parent.protocol_type == 2:
            self.f = f'{self.parent.folder_name}//{self.parent.file_name}_{prefix_alias}.csv'
            # self.f_list.append(self.f)
            with open(self.f, 'w') as self.filetowrite:
                self.filetowrite.write(table_header)

        for source in self.parent.points:

            # if self.parent.protocol_type == 2:
            #    self.f = f'{self.parent.folder_name}//{self.parent.file_name}_{prefix_alias}_id{source}.csv'
            # self.f_list.append(self.f)
            #    with open(self.f, 'w') as self.filetowrite:
            #        self.filetowrite.write(table_header)

            QApplication.processEvents()
            if self.verify_break():
                return 0
            i += 1

            self.parent.setMessage(f'Building thematic map for the feature №{i} of {count}')
            QApplication.processEvents()

            self.source = source

            idStart, _ = self.dict_building_vertex.get(self.source, (0, 0))

            if idStart == 0:
                self.parent.progressBar.setValue(count+1)
                break

            (self.tree, self.costs) = QgsGraphAnalyzer.dijkstra(
                self.graph,  idStart, 0)

            if self.parent.protocol_type == 2:
                self.makeProtocolArea()
            else:

                if len(self.fields_ok) > 0:
                    for field in self.fields_ok:
                        self.makeProtocolMap(
                            self.f[field],
                            self.aggregate_dict_all[field],
                            field
                        )

            self.parent.progressBar.setValue(i + 1)

        if self.parent.protocol_type == 2 and count > 1:
            self.f = self.make_service_area_report(
                self.parent.folder_name, self.parent.file_name, prefix_alias)

    def make_service_area_report(self, folder_name, aliase, prefix_alias):

        all_data = pd.DataFrame()

        # add a mask for searching CSV files
        file_pattern = rf"{folder_name}\*.csv"
        for file in glob.glob(file_pattern):
            df = pd.read_csv(file)
            all_data = pd.concat([all_data, df], ignore_index=True)

        result = all_data.loc[all_data.groupby('Destination_ID')[
            'Duration'].idxmin()]
        filename = f'{folder_name}//{aliase}_{prefix_alias}_service_area.csv'
        result.to_csv(filename, index=False)
        return filename

    def calc_min_cost(self):

        self.min_costs = {}

        count = 0

        _, dist_start = self.dict_building_vertex[self.source]

        sum_walk = self.parent.walk_on_start_m + self.parent.walk_on_finish_m

        # iterate through all edgeId in the tree
        for edgeId in self.tree:

            count += 1
            if count % 10000 == 0:
                if self.verify_break():
                    return 0
                QApplication.processEvents()

            if edgeId == -1:
                continue
            try:
                if edgeId >= len(self.costs):
                    continue
                if self.costs[edgeId] == float('inf'):
                    continue

                buildings, dists_finish = zip(
                    *self.dict_vertex_buildings[edgeId])
            except KeyError:
                continue

            # cost = round(self.costs[edgeId]/self.factor_speed + time_start_avto + self.parent.walk_time_start + self.parent.walk_time_finish)
            # cost = cost + 2 * self.parent.time_gap

            Dist_between_nodes = self.costs[edgeId] * 10
            Dist_OD_0 = dist_start + Dist_between_nodes

            for building, dist_finish in zip(buildings, dists_finish):
                # define the pair {self.source, building}
                pair = (self.source, building)

                Dist_OD = Dist_OD_0 + dist_finish
                Dist_to_drive = Dist_OD - sum_walk
                if Dist_to_drive <= 0:
                    cost_res = round(Dist_OD / self.parent.walk_speed_m_s)
                else:
                    if Dist_between_nodes != 0:
                        Time_to_drive = self.costs[edgeId] * \
                            (Dist_to_drive/Dist_between_nodes)/self.factor_speed
                    else:
                        Time_to_drive = 0
                    cost_res = round(
                        (sum_walk)/self.parent.walk_speed_m_s + Time_to_drive)

                cost_res = cost_res + 2 * self.parent.time_gap

                if int(self.source) == int(building):
                    cost_res = 0

                if cost_res > self.max_time_sec:
                    continue
             
                # if the pair already exists in the dictionary, check the minimum cost.
                if pair in self.min_costs:
                    self.min_costs[pair] = min(self.min_costs[pair], cost_res)
                else:
                    self.min_costs[pair] = cost_res

    def makeProtocolArea(self):

        self.calc_min_cost()
        with open(self.f, 'a') as filetowrite:
            for (source, building), min_cost in self.min_costs.items():
                if self.parent.mode == 1:
                    filetowrite.write(f'{source},{building},{min_cost}\n')
                else:
                    filetowrite.write(f'{building},{source},{min_cost}\n')

    def makeProtocolMap(self,
                        f,
                        aggregate_dict,
                        field):

        self.calc_min_cost()

        # counters for gradations
        counts = {x: 0 for x in range(0, len(self.grades))}
        # Счётчики для агрегатов
        aggregates = {x: 0 for x in range(0, len(self.grades))}

        # iterate through the minimum cost values for each pair (source, building)
        for (source, building), cost in self.min_costs.items():
            if cost <= self.max_time_sec:
                # find the corresponding gradation
                for i in range(0, len(self.grades)):
                    grad = self.grades[i]
                    if cost <= grad[1]:
                        counts[i] += 1

                        if field != "bldg":
                            aggregates[i] = aggregates[i] + \
                                aggregate_dict.get(int(building), 0)

        row = f'{self.source}'

        if field == "bldg":
            Total = counts[len(self.grades) - 1]
        if field != "bldg":
            Total = aggregates[len(self.grades) - 1]

        with open(f, 'a') as filetowrite:
            for i in range(0, len(self.grades)):
                row = f'{row},{counts[i]}'
                if field != "bldg":
                    row = f'{row},{aggregates[i]}'
            filetowrite.write(f'{row},{Total}\n')

    def create_head_files(self):

        if self.parent.protocol_type == 1:  # MAP
            
            self.fields_ok = []
            self.aggregate_dict_all = {}
            self.aggregate_this_fields = {}
            self.f = {}

            intervals_number = self.number_bins
            protocol_header = "Origin_ID"
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

            protocol_header += ',bldg_total\n'
            field = "bldg"

            prefix_alias = get_prefix_alias(False,
                                            self.parent.protocol_type,
                                            self.parent.mode,
                                            field_name="bldg",
                                            layer=self.parent.layer_origins_name
                                            )
            self.f[field] = f'{self.parent.folder_name}//{self.parent.file_name}_{prefix_alias}.csv'
            self.fields_ok.extend([field])
            self.aggregate_this_fields[field] = False
            self.aggregate_dict_all[field] = {}
            with open(self.f[field], 'w') as filetowrite:
                filetowrite.write(protocol_header)

            if self.list_fields_aggregate != "":

                field_name_id = self.layerdest_field
                fields_aggregate = [
                    value.strip() for value in self.list_fields_aggregate.split(',')]

                for field in fields_aggregate:

                    attribute_dict = {}
                    self.parent.setMessage(f"Building database for '{field}' ...")
                    QApplication.processEvents()

                    self.aggregate_this_fields[field] = True

                    features_dest = self.layer_dest.getFeatures()
                    if self.selected_only2:
                        features_dest = self.layer_dest.selectedFeatures()

                    for feature in features_dest:
                        attribute_dict[int(feature[field_name_id])] = int(
                            feature[field])

                    self.fields_ok.extend([field])
                    self.aggregate_dict_all[field] = attribute_dict

                    """Prepare header and time grades  
                                statistics_by_accessibility_time_header="Stop_ID,10m,20 m,30 m,40 m,50 m,60 m"+"\n"+"\n"
                                """

                    protocol_header = "Origin_ID"
                    time_step_min = self.time_step_minutes
                    top_bound_min = time_step_min

                    intervals_number = self.number_bins

                    for i in range(0, intervals_number):
                        protocol_header += f',{top_bound_min}m'
                        protocol_header += f',sum({field}[{top_bound_min}m])'
                        top_bound_min = top_bound_min + time_step_min

                    if self.time_step_last != 0:
                        intervals_number += 1
                        top_bound_add = top_bound_min - time_step_min + self.time_step_last
                        protocol_header += f',{top_bound_add}m'
                        protocol_header += f',sum({field}[{top_bound_add}m])'

                    protocol_header += f',{field}_total\n'

                    prefix_alias = get_prefix_alias(False,
                                                    self.parent.protocol_type,
                                                    self.parent.mode,
                                                    field_name=field,
                                                    layer=self.parent.layer_origins_name
                                                    )
                    self.f[field] = f'{self.parent.folder_name}//{self.parent.file_name}_{prefix_alias}.csv'

                    with open(self.f[field], 'w') as filetowrite:
                        filetowrite.write(protocol_header)

    def run(self, begin_computation_time):

        self.find_car_accessibility()

        QApplication.processEvents()
        after_computation_time = datetime.now()
        after_computation_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.parent.textLog.append(f'<a>Finished: {after_computation_str}</a>')

        duration_computation = after_computation_time - begin_computation_time
        duration_without_microseconds = str(duration_computation).split('.')[0]
        self.parent.textLog.append(f'<a>Processing time: {duration_without_microseconds}</a>')

        if not (self.writed_info):
            self.write_info()

        self.parent.textLog.append(f'<a href="file:///{self.parent.folder_name}" target="_blank" >Output in folder</a>')
        self.parent.setMessage(f'Finished')

        return self.parent.folder_name

    def verify_break(self):
        if self.parent.break_on:
            self.parent.setMessage("Car accessibility computations are interrupted by user")
            if not self.already_display_break:
                self.parent.textLog.append(f'<a><b><font color="red">Car accessibility computations are interrupted by user</font> </b></a>')
                if self.parent.folder_name != "":
                    self.write_info()
                self.already_display_break = True

            self.parent.progressBar.setValue(0)
            return True
        return False

    def write_info(self):

        self.writed_info = True
        vis = visualization(self.parent,
                            self.layer_vis,
                            mode=self.parent.protocol_type,
                            fieldname_layer=self.layer_vis_field,
                            )
        if self.parent.protocol_type == 1:
            
            count_diapazone = self.number_bins
            vis.set_count_diapazone(count_diapazone)

        self.parent.textLog.append(f'<a>Output:</a>')
        if self.parent.protocol_type == 1:
            if len(self.fields_ok) > 0:
                for field in self.fields_ok:
                    alias = os.path.splitext(
                        os.path.basename(self.f[field]))[0]
                    vis.add_thematic_map(self.f[field], alias, set_min_value=0)
                    self.parent.textLog.append(f'<a>{self.f[field]}</a>')

        if self.parent.protocol_type == 2:
            alias = os.path.splitext(os.path.basename(self.f))[0]
            vis.add_thematic_map(self.f, alias, set_min_value=0)
            self.parent.textLog.append(f'<a>{self.f}</a>')

        text = self.parent.textLog.toPlainText()
        filelog_name = f'{self.parent.folder_name}//log_{self.parent.alias}.txt'
        with open(filelog_name, "w") as file:
            file.write(text)

        if self.parent.selected_only1 or self.parent.selected_only2:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setWindowTitle("Confirm")
            msgBox.setText(
                f'Do you want to store selected features as a layer?')
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            result = msgBox.exec_()

            if result == QMessageBox.Yes:
                if self.parent.selected_only1:

                    zip_filename1 = f'{self.parent.folder_name}//origins_{self.parent.alias}.zip'
                    filename1 = f'{self.parent.folder_name}//origins_{self.parent.alias}.geojson'
                    self.save_layer_to_zip(
                        self.parent.layer_origins, zip_filename1, filename1)
                if self.parent.selected_only2:

                    zip_filename2 = f'{self.parent.folder_name}//destinations_{self.parent.alias}.zip'
                    filename2 = f'{self.parent.folder_name}//destinations_{self.parent.alias}.geojson'
                    self.save_layer_to_zip(
                        self.parent.layer_dest, zip_filename2, filename2)

    def save_layer_to_zip(self, layer, zip_filename, filename):

        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp_file:
            temp_file = tmp_file.name

        QApplication.processEvents()

        QgsVectorFileWriter.writeAsVectorFormat(layer,
                                                temp_file,
                                                "utf-8",
                                                layer.crs(),
                                                "GeoJSON",
                                                onlySelected=True)
        QApplication.processEvents()

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(temp_file, os.path.basename(filename))

        QApplication.processEvents()

        if os.path.exists(temp_file):
            os.remove(temp_file)
