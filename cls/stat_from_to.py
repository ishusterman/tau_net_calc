import os
import pandas as pd
from collections import defaultdict
from itertools import product
try:
    from PyQt5.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class StatFromTo:
    
    def __init__(self, 
                 parent, 
                 folder_name_from, 
                 folder_name_to, 
                 PathToProtocols, 
                 alias, 
                 timetable_mode
                 ):
        
        self.parent = parent
        self.folder_name_from = folder_name_from
        self.folder_name_to = folder_name_to
        self.file_from_to = os.path.join(PathToProtocols, f"{alias}_stat_from_to.csv")
        self.file_from = os.path.join(PathToProtocols, f"{alias}_stat_from.csv")
        self.file_to = os.path.join(PathToProtocols, f"{alias}_stat_to.csv")
        self.timetable_mode = timetable_mode
                        
    def gather_files(self, path):
        """
        Gathers all CSV files from the immediate subdirectories of the base path.
        """
        # List directories in the base path (ignoring files)
        list_files = []
        subdirs = [f.path for f in os.scandir(path) if f.is_dir()]

        # Iterate through each subdirectory and add CSV files to self.files
        for subdir in subdirs:
            for file in os.listdir(subdir):
                if file.endswith(".csv"):
                    list_files.append(os.path.join(subdir, file))

        if not list_files:
            raise ValueError(f"No CSV files found in the immediate subdirectories of the directory: {path}")
        
        return list_files
    
    def build_filtered_dict(self, files, common_ids, source_type="from"):
        """
        Reads CSV files and constructs a dictionary with only common Destination_IDs.
        If source_type is 'to', uses 'Latest_time_at_destination' instead of 'Destination_time'.
        """
        data_dict = defaultdict(list)
        
        """
        if self.timetable_mode:
            time_column = "Earlest_arrival_time" if source_type == "to" else "Destination_time"
        else:
            time_column = "Arrive_before" if source_type == "to" else "Destination_time"
        """
        
        time_column = "Destination_time"

        for file in files:
            
            df = pd.read_csv(file, usecols=["Destination_ID", "Start_time", time_column, "Duration", "Legs"], dtype={"Destination_ID": str})
            df = df[df["Destination_ID"].isin(common_ids)] 

            for row in df.itertuples(index=False):
                start_time = row.Start_time #if pd.notna(row.Start_time) else "00:00:00"
                dest_time = getattr(row, time_column) #if pd.notna(getattr(row, time_column)) else "00:00:00"
                transfers = (int(row.Legs))
                data_dict[row.Destination_ID].append((start_time, dest_time, row.Duration, transfers))

        
        for key in data_dict:
            data_dict[key].sort(key=lambda x: (x[0], x[2], key))  

        return data_dict
    
    def save_dict_to_csv(self, data_dict, file_path, order_from=None):
        
        with open(file_path, 'w', newline='') as f:
            if order_from is None :
                f.write("Destination_ID,Start_time,Destination_time,Duration,Legs\n")
            else:
                f.write("Origin_ID,Start_time,Destination_time,Duration,Legs\n")

            if order_from is None:
                grouped_entries = {key: sorted(values, key=lambda x: (x[0], x[2])) for key, values in data_dict.items()}

                group_A = {} 

                for key, values in grouped_entries.items():
                    min_entry_time = min(entry[0] for entry in values) 
                    durations_at_min_time = [entry[2] for entry in values if entry[0] == min_entry_time]
                    group_A[key] = min(durations_at_min_time)
                    
                
                sorted_destination_ids = sorted(group_A.keys(), key=lambda key: group_A[key]) 
                seen = set()  

                for key in sorted_destination_ids:
                    for start_time, dest_time, duration,tranfers in grouped_entries[key]:
                        row = f"{key},{start_time},{dest_time},{duration},{tranfers}\n"
                        if row not in seen:
                            f.write(row)
                            seen.add(row)
                order_from = sorted_destination_ids.copy()
                            
            else:
                seen = set() 
                for key in order_from:
                    if key in data_dict:
                        for start_time, dest_time, duration, tranfers in sorted(data_dict[key], key=lambda x: (x[0])):
                            row = f"{key},{start_time},{dest_time},{duration},{tranfers}\n"
                            if row not in seen:
                                f.write(row)
                                seen.add(row)
                order_from = None

        return order_from
    


    """
    def save_to_csv(self, combined_dict):
        ###
        # Saves the combined dictionary to a CSV file.
        ###
        with open(self.file_from_to, 'w', newline='') as f:
            f.write("Destination_ID,Start_time_from,Destination_time_from,Duration_from,Start_time_to,Destination_time_to,Duration_to\n")
            for key, value in combined_dict.items():
                first_entry = True
                for (start_from, dest_from, duration_from), (start_to, dest_to, duration_to) in value:
                    if pd.isna(start_from) or pd.isna(dest_from) or pd.isna(start_to) or pd.isna(dest_to):
                        if first_entry:
                            f.write(f"{key},{start_from},{dest_from},{duration_from},{start_to},{dest_to},{duration_to}\n")
                            first_entry = False
                    else:
                        f.write(f"{key},{start_from},{dest_from},{duration_from},{start_to},{dest_to},{duration_to}\n")
    """
    def get_common_destination_ids(self, files):
        """
        Returns the set of Destination_IDs that are present in all given files.
        """
        common_ids = None  

        for file in files:
            df = pd.read_csv(file, usecols=["Destination_ID"], dtype={"Destination_ID": str})
            current_ids = set(df["Destination_ID"].dropna())

            if common_ids is None:
                common_ids = current_ids  
            else:
                common_ids &= current_ids  
        
        return common_ids if common_ids else set() 
    
    def process_files(self):
        
        if GUI_AVAILABLE:
            self.parent.setMessage('Calculating statistics ...')
            QApplication.processEvents()
        files_from = self.gather_files(self.folder_name_from)
        files_to = self.gather_files(self.folder_name_to)

        common_ids_from = self.get_common_destination_ids(files_from)
        common_ids_to = self.get_common_destination_ids(files_to)

        common_ids = common_ids_from & common_ids_to

        dict_from = self.build_filtered_dict(files_from, common_ids, source_type="from")
        dict_to = self.build_filtered_dict(files_to, common_ids, source_type="to")
        
        if GUI_AVAILABLE:
            self.parent.setMessage('Saving statistics ...')
            QApplication.processEvents()

        order_from = self.save_dict_to_csv(dict_from, self.file_from)
        self.save_dict_to_csv(dict_to, self.file_to, order_from=order_from)

        """
        combined_dict = defaultdict(list)
        for key in dict_from:
            if key in dict_to:
                combined_dict[key] = [(from_tuple, to_tuple) for from_tuple, to_tuple in product(dict_from[key], dict_to[key]) if pd.isna(to_tuple[0]) or pd.isna(from_tuple[1]) or to_tuple[0] > from_tuple[1]]
        

        self.save_to_csv(combined_dict) "
        """
        if GUI_AVAILABLE:
            self.parent.setMessage('Finished')
            QApplication.processEvents()       

    

if __name__ == "__main__":
    folder_name_from = r'c:\temp\1\11\250310_153721_PFXA_from'
    folder_name_to = r'c:\temp\1\11\250310_153721_PFXA_to'
    output_path = r'c:\temp\1\11'
    parent = None
    alias = "result"
    start_time = "08:00:00"
    processor = StatFromTo(parent, folder_name_from, folder_name_to, output_path, alias, start_time)
    processor.process_files()
    print ("ok")