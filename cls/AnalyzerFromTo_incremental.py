import os
import csv
import math
import time
from collections import defaultdict

try:
    from PyQt5.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class roundtrip_analyzer:
    def __init__(self, 
                 path_from: str = None, 
                 path_to: str = None, 
                 report_path: str = None, 
                 duration_max: int = 3600, 
                 alias = "" ):
        
        self.path_from = path_from
        self.path_to = path_to
        self.duration_max = duration_max  # maximum duration for binning
        
        self.common_keys = None
        self.results = {}
        self.report_path = report_path
        self.limit = (2 / 3) * self.duration_max
        self.alias = alias

        self.path_stats = os.path.normpath(os.path.join(self.report_path, f"{self.alias}_round_trip_stats.csv"))
        self.path_bins = os.path.normpath(os.path.join(self.report_path, f"{self.alias}_round_trip_bins.csv"))

        

    # -------------------------------------------------------------------------
    # File-based processing (original functionality)
    # -------------------------------------------------------------------------
    def get_file_paths(self, folder):
        file_paths = []
        for root in os.scandir(folder):
            if not root.is_dir():
                continue
            for f in os.scandir(root.path):
                if f.name.endswith("min_duration.csv"):
                    file_paths.append(f.path)
        return sorted(file_paths)

    
    def read_file(self, path):
        result = {}
        
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    o, d = row['Origin_ID'], row['Destination_ID']
                    duration = int(row['Duration'])
                    if duration <= self.limit:
                        result[(o, d)] = duration
                except Exception:
                    continue
        return result

    # -------------------------------------------------------------------------
    # Data structure processing 
    # -------------------------------------------------------------------------
    
    def get_data_for_analyzer_from_to(self, dict_data):
        """
        Convert data with filtering: Dict[(source, dest), duration]
        """
        return {k: v for k, v in dict_data.items() if v <= self.limit}

    # -------------------------------------------------------------------------
    # Incremental processing with direct data structures
    # -------------------------------------------------------------------------
    def init_from_data(self, to_data,  from_data):
        """
        Initialize with first pair of data structures
        """
        #print("Initializing with first data structures...")
              
        to_intersection = set(to_data.keys())
        from_intersection = set(from_data.keys())
        self.common_keys = to_intersection & from_intersection

        #print(f"Initialized with {len(self.common_keys)} common OD-pairs")
        
        # Initialize results with statistics
        self.results = {}
        for i, pair in enumerate(self.common_keys):
            to_value = to_data[pair]
            from_value = from_data[pair]
            
            state = self.init_round(to_value, from_value)
            self.results[pair] = {'state': state}

            if i % 1000 == 0 and GUI_AVAILABLE:
                QApplication.processEvents()

    def add_to_data(self, to_data):
        """Add new TO data and update statistics"""
        new_keys_set = set(to_data.keys())
        self.common_keys &= new_keys_set
        self.results = {k: v for k, v in self.results.items() if k in self.common_keys}
        for i, pair in enumerate(self.common_keys):
            value = to_data[pair]
            state = self.results[pair]['state']
            self.results[pair]['state'] = self.add_new_to(state, value)
            if i % 1000 == 0 and GUI_AVAILABLE:
                QApplication.processEvents()
        #print(f"Added TO data. Now have {len(self.common_keys)} datasets")
        

    def add_from_data(self, from_data):
        """Add new FROM data and update statistics"""
        new_keys_set = set(from_data.keys())
        self.common_keys &= new_keys_set
        self.results = {k: v for k, v in self.results.items() if k in self.common_keys}
        for i, pair in enumerate(self.common_keys):
            value = from_data[pair]
            state = self.results[pair]['state']
            self.results[pair]['state'] = self.add_new_from(state, value)
            if i % 1000 == 0 and GUI_AVAILABLE:
                QApplication.processEvents()
        
        #print(f"Added FROM data. Now have {len(self.common_keys)} datasets")
     
    def run_finalize_all(self):
        """Run final processing and generate reports for incremental mode"""
       
        # Calculate final statistics and apply filter
        final_results = {}
        for i, (pair, data) in enumerate(self.results.items()):
            state = data['state']
            
            # Calculate means for filtering
            mean_to = state['to']['sum'] / state['to']['count']
            mean_from = state['from']['sum'] / state['from']['count']
            
            # Apply filter condition
            if mean_from + mean_to > self.duration_max:
                continue
            
            mean, std, count = self.finalize(state)
            final_results[pair] = {
                    'count': count,
                    'duration_mean': round(mean, 2),
                    'duration_std': round(std, 2)
                }
            
            if i % 1000 == 0 and GUI_AVAILABLE:
                QApplication.processEvents()

        # --- save statistics file ---
        
        
        with open(self.path_stats, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Origin_ID", "Destination_ID", "Count", "Mean", "Std"])
            for (o, d), vals in final_results.items():
                writer.writerow([o, d, vals['count'], vals['duration_mean'], vals['duration_std']])

        # --- compute and save bins ---
        bin_counts = self.group_durations_by_time_bins(final_results)
        self.save_bins_to_file(bin_counts)

        #print(f"=== Incremental processing finished. {len(final_results)} pairs processed ===")

    # -------------------------------------------------------------------------
    # Statistical functions (unchanged)
    # -------------------------------------------------------------------------
    @staticmethod
    def init_round(to0, from0): 
        return {
            'to': {'count': 1, 'sum': to0, 'sum_sq': to0 ** 2},
            'from': {'count': 1, 'sum': from0, 'sum_sq': from0 ** 2},
            'round': {'count': 1, 'sum': to0 + from0, 'sum_sq': (to0 + from0) ** 2}
        }

    @staticmethod
    def add_new_to(state, new_to): 
        c_f, s_f, sq_f = state['from']['count'], state['from']['sum'], state['from']['sum_sq']
        state['round']['sum'] += new_to * c_f + s_f
        state['round']['sum_sq'] += c_f * new_to ** 2 + 2 * new_to * s_f + sq_f
        state['to']['count'] += 1
        state['to']['sum'] += new_to
        state['to']['sum_sq'] += new_to ** 2
        state['round']['count'] = state['to']['count'] * c_f
        return state

    @staticmethod
    def add_new_from(state, new_from):
        c_t, s_t, sq_t = state['to']['count'], state['to']['sum'], state['to']['sum_sq']
        state['round']['sum'] += new_from * c_t + s_t
        state['round']['sum_sq'] += c_t * new_from ** 2 + 2 * new_from * s_t + sq_t
        state['from']['count'] += 1
        state['from']['sum'] += new_from
        state['from']['sum_sq'] += new_from ** 2
        state['round']['count'] = c_t * state['from']['count']
        return state

    @staticmethod
    def finalize(state):
        n = state['round']['count']
        s, sq = state['round']['sum'], state['round']['sum_sq']
        mean = s / n
        var = (sq / n) - mean ** 2
        if var < 0 and var > -1e-9:
            var = 0.0
        std = math.sqrt(var)
        return mean, std, n

    # -------------------------------------------------------------------------
    # Binning and output (unchanged)
    # -------------------------------------------------------------------------
    def group_durations_by_time_bins(self, results):
        """Group duration_mean of pairs by Origin_ID and 10-minute bins."""
        bin_counts = defaultdict(lambda: defaultdict(int))
        max_bin_code = self.duration_max // 600

        #print("Grouping results by 10-minute bins...")

        for (origin_id, dest_id), data in results.items():
            duration = data['duration_mean']
            bin_code = int(duration // 600)
            if bin_code >= max_bin_code:
                bin_code = max_bin_code - 1
            bin_counts[origin_id][bin_code] += 1

        return bin_counts

    def save_bins_to_file(self, bin_counts):
        #print(f"Saving bin report to: {path}")
        all_bin_codes = sorted(list(set(bin_code for bins in bin_counts.values() for bin_code in bins.keys())))

        with open(self.path_bins, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ["Origin_ID"] + [f"bin_{b}" for b in all_bin_codes]
            writer.writerow(header)
            for origin_id, bins in bin_counts.items():
                row = [origin_id]
                cumulative_count = 0
                for bin_code in all_bin_codes:
                    cumulative_count += bins.get(bin_code, 0)
                    row.append(cumulative_count)
                writer.writerow(row)
        
    def run_on_files(self):
        """File-based processing using incremental methods"""
        #print("=== TripAnalyzer started (file-based) ===")
        print(f"Input folders:\n  FROM {self.path_from}\n  TO {self.path_to}")

        files_from = self.get_file_paths(self.path_from)
        files_to = self.get_file_paths(self.path_to)
        print(f"Found {len(files_from)} FROM-files and {len(files_to)} TO-files.")
       
        # --- read files sequentially ---
        to_data_list = []
        for file_path in files_to:
            data = self.read_file(file_path)
            to_data_list.append(data)
            print(f"Loaded TO data from {file_path}: {len(data)} pairs")
        
        
        from_data_list = []
        for file_path in files_from:
            data = self.read_file(file_path)
            from_data_list.append(data)
            print(f"Loaded FROM data from {file_path}: {len(data)} pairs")
        
        
        #print("Initializing with first TO and FROM datasets...")
        self.init_from_data(to_data_list[0], from_data_list[0])

        for from_data in from_data_list[1:]:
            self.add_from_data(from_data)


        for to_data in (to_data_list[1:]):
            self.add_to_data(to_data)

        self.run_finalize_all()
        #print("=== TripAnalyzer finished successfully ===")
   

# Example usage for both modes
if __name__ == "__main__":
    # Mode 1: Original file-based processing
    
    folder_from = r'c:\doc\Igor\GIS\temp\251110_142920_PFXA\from' 
    folder_to = r'c:\doc\Igor\GIS\temp\251110_142920_PFXA\to'
    report_path = r'c:\doc\Igor\GIS\temp\251110_142920_PFXA\from'

    analyzer1 = roundtrip_analyzer(path_from = folder_from, path_to = folder_to, report_path = report_path, duration_max = 3600)
    analyzer1.run_on_files()
    print ("ok")

    """
    # Mode 2: Incremental processing with direct data structures
    # Your original data format
    dict_from1 = {'4': ('10', 360), '5': ('10', 360)}
    dict_from2 = {'4': ('10', 420), '5': ('10', 360)}
    dict_from3 = {'4': ('10', 300), '5': ('10', 360)}
    dict_from4 = {'4': ('10', 180), '5': ('10', 360)}

    dict_to1 = {'4': ('10', 300), '5': ('10', 360)}
    dict_to2 = {'4': ('10', 420), '5': ('10', 360)}
    dict_to3 = {'4': ('10', 600)}
    
    
    analyzer2 = roundtrip_analyzer(report_path = r"c:\temp", duration_max=3600)
    
    # Convert once using the helper method
    to_data1 = analyzer2.get_data_for_analyzer_from_to(dict_to1)
    to_data2 = analyzer2.get_data_for_analyzer_from_to(dict_to2)
    to_data3 = analyzer2.get_data_for_analyzer_from_to(dict_to3)

    from_data1 = analyzer2.get_data_for_analyzer_from_to(dict_from1)
    from_data2 = analyzer2.get_data_for_analyzer_from_to(dict_from2)
    from_data3 = analyzer2.get_data_for_analyzer_from_to(dict_from3)
    from_data4 = analyzer2.get_data_for_analyzer_from_to(dict_from4)
    
    
    # Initialize with first pair - DIRECT usage, no conversions!
    analyzer2.init_from_data(to_data1, from_data1)

    
    
    # Add more data incrementally - DIRECT usage!
    analyzer2.add_to_data(to_data2)
    analyzer2.add_from_data(from_data2)
    analyzer2.add_to_data(to_data3)
    analyzer2.add_from_data(from_data3)
    analyzer2.add_from_data(from_data4)
    
    
    # Generate final reports
    analyzer2.run_finalize.all()
    """
    