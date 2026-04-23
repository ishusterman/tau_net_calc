import os
import csv
import sys
from collections import defaultdict

try:
    from PyQt5.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
GUI_AVAILABLE = False


class TripAnalyzer:
    def __init__(self, parent, path_from, path_to):
        self.parent = parent
        self.path_from = path_from
        self.path_to = path_to
        
    
    def gather_time_data(self, path_to_files, mode):
        """Collects time data for start or destination times"""
        time_data = defaultdict(int)
        file_count = 0
        
        if mode == "duration":
            name = "min_duration.csv"
        elif mode == "endtime":
            name = "min_endtime.csv"
        else:
            return time_data

        # Determine which field to use based on path
        is_from_path = path_to_files == self.path_from
        time_field = 'Start_time' if is_from_path else 'Destination_time'

        for root_entry in os.scandir(path_to_files):
            if not root_entry.is_dir():
                continue

            root_path = root_entry.path
            for file_entry in os.scandir(root_path):
                file_name = file_entry.name

                if file_name.endswith(name):
                    file_path = file_entry.path
                    file_count += 1
                    
                    row_count = 0

                    with open(file_path, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            row_count += 1
                            if row_count % 1000000 == 0:
                                sys.stdout.write(f'\r file_count {file_count} row_count: {row_count}')
                                sys.stdout.flush()
                            
                            # Save full time value (e.g., 9:20:00)
                            time_value = row.get(time_field, '')
                            if time_value:
                                time_data[time_value] += 1
        
        print(f"\nFiles processed: {file_count}")
        return time_data
    
    def build_time_matrix(self, from_data, to_data):
        """Builds matrix with sum of from_data and to_data values for each time combination"""
        # Get all unique times from both datasets
        all_times_from = sorted(from_data.keys())
        all_times_to = sorted(to_data.keys())
        
        # Create matrix with sum of values for each combination
        matrix = {}
        for time_to in all_times_to:
            matrix[time_to] = {}
            for time_from in all_times_from:
                # Sum values from both dictionaries
                sum_value = from_data.get(time_from, 0) + to_data.get(time_to, 0)
                matrix[time_to][time_from] = sum_value
        
        return matrix, all_times_from, all_times_to
    
    def save_matrix_to_csv(self, matrix, times_from, times_to, output_path):
        """Saves matrix to CSV file"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header - time from (горизонтально)
            header = ['time to \\ time from'] + times_from
            writer.writerow(header)
            
            # Matrix data - time to (вертикально)
            for time_to in times_to:
                row = [time_to]
                for time_from in times_from:
                    row.append(matrix[time_to].get(time_from, 0))
                writer.writerow(row)
    
    def run(self, result_path1, result_path2, mode):
        self.result_path1 = result_path1
        self.result_path2 = result_path2
        self.mode = mode
        
        # Collect data for from (using Start_time)
        print("Collecting data for from (Start_time)...")
        from_data = self.gather_time_data(self.path_from, mode)

        print (from_data)
        
        # Collect data for to (using Destination_time)
        print("Collecting data for to (Destination_time)...")
        to_data = self.gather_time_data(self.path_to, mode)

        print (to_data)
        
        print(f"From data count: {len(from_data)}")
        print(f"To data count: {len(to_data)}")
        
        # Build matrix with sums
        print("Building matrix...")
        matrix, times_from, times_to = self.build_time_matrix(from_data, to_data)
        
        # Save result
        print("Saving results...")
        self.save_matrix_to_csv(matrix, times_from, times_to, self.result_path1)
        
        print("Finish")
        if GUI_AVAILABLE:
            self.parent.setMessage('Finish')
            QApplication.processEvents()
        
        return matrix

if __name__ == "__main__":
    folder_name_from = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Government_Complex-new\Government_Complex-new\2018\250910_104757_PFXA_from'
    folder_name_to = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Government_Complex-new\Government_Complex-new\2018\250910_104757_PFXA_to'
    #folder_name_from = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Government_Complex-new\Government_Complex-new\2025\250910_102538_PFXA_from'
    #folder_name_to = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Government_Complex-new\Government_Complex-new\2025\250910_102538_PFXA_to'
    output_path = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Government_Complex-new\Government_Complex-new\2018\result_matrix.csv'
    

    analyzer = TripAnalyzer(
        None,
        path_from=folder_name_from,
        path_to=folder_name_to,
    )

    result = analyzer.run(output_path, "", mode="duration")
    print("Matrix created successfully!")
    print(f"Result saved to: {output_path}")