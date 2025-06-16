import os
import re
import pandas as pd


""""

Создаем статистику вида

Time,Origin_ID,Num_Buildings
08:00:00,149281177,23541
08:00:00,149281178,23541
08:00:00,230605310,23527
08:15:00,149281177,23915
08:15:00,149281178,23915
08:15:00,230605310,22541
08:30:00,149281177,23501
08:30:00,149281178,23501
08:30:00,230605310,22871
08:45:00,149281177,23565
08:45:00,149281178,23565
08:45:00,230605310,23424
09:00:00,149281177,23591
09:00:00,149281178,23776
09:00:00,230605310,23365

"""

class DayStat_DestinationID:
    

    def __init__(self, base_path, output_path):
        """
        Initialize the processor with the base path (directory containing folders with CSV files)
        and an output path.

        :param base_path: Path to the directory containing subfolders with CSV files.
        :param output_path: Path to save the resulting file.
        """
        self.base_path = base_path
        self.output_path = output_path
        self.result = None
        self.files = []  # List to hold paths to all CSV files

    def gather_files(self):
        """
        Gathers all CSV files ending with 'min_duration.csv' from subdirectories nested
        within the immediate subdirectories of the base path.
        """
    

        # Обходим все директории в self.base_path
        for root_dir_entry in os.scandir(self.base_path):
            if root_dir_entry.is_dir():
                root_dir = root_dir_entry.path

                # В каждом таком каталоге ищем вложенные каталоги
                for nested_dir_entry in os.scandir(root_dir):
                    if nested_dir_entry.is_dir():
                        nested_dir = nested_dir_entry.path

                        # В каждом вложенном каталоге ищем нужные CSV-файлы
                        for file in os.listdir(nested_dir):
                            if file.endswith("min_duration.csv"):
                                full_path = os.path.join(nested_dir, file)
                                self.files.append(full_path)
                
        if not self.files:
            raise ValueError(
                f"No 'min_duration.csv' files found in nested subdirectories of: {self.base_path}"
            )




    def extract_time_pattern_from_txt(self, txt_path):
        """
        Extracts the last matched time pattern from the provided .txt file.

        :param txt_path: Path to the .txt file.
        :return: Last matched time string or None if no match found.
        """
        # Define the regex pattern
        time_pattern = re.compile(
            r"Start at \(hh:mm:ss\):\s+(\d{1,2}:\d{2}:\d{2})|"
            r"Earliest start time:\s+(\d{1,2}:\d{2}:\d{2})|"
            r"Arrive before \(hh:mm:ss\):\s+(\d{1,2}:\d{2}:\d{2})|"
            r"Earliest arrival time:\s+(\d{1,2}:\d{2}:\d{2})"
        )

        # Read the .txt file
        
        with open(txt_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Find all matches
        matches = time_pattern.findall(content)

        # If there are matches, return the last non-empty match
        if matches:
            for match in reversed(matches):
                for time in match:
                    if time:
                        return time
        return None


    def process_files(self):
        """
        Process the provided CSV files to merge data based on common Destination_ID
        and compute additional statistics for each column.
        """
        # Gather all CSV files
        self.gather_files()

        # Loop through all files
        
        rows = []

        for idx, file in enumerate(self.files):
            # Read the current CSV file
            df = pd.read_csv(file, low_memory=False)
            
            if idx % 100 == 0:
                print(f'Num {idx}', end='\r', flush=True)
            if df.shape[0] == 0:
                continue
            # Get the folder where the current file is located
            file_folder = os.path.dirname(file)
            # Find the corresponding .txt file in the same folder
            txt_file = next((f for f in os.listdir(file_folder) if f.endswith(".txt")), None)
            
            # Extract time pattern from the .txt file
            time_value = self.extract_time_pattern_from_txt(os.path.join(file_folder, txt_file))
            

            origin_id = df["Origin_ID"].iloc[0]    
            num_buildings = df.shape[0]

             # Добавляем строку в итог
            rows.append({"Time": time_value, "Origin_ID": origin_id, "Num_Buildings": num_buildings})
           

        self.result = pd.DataFrame(rows)

        if self.result is not None:
            self.result.sort_values(by="Time", inplace=True)
            self.result.to_csv(self.output_path, index=False)
        else:
            print("No valid CSV files processed.")


if __name__ == "__main__":
    base_path = r'F:/Igor/output/to_update_start_buildings_tama'
    output_path = os.path.join(base_path, f"stat.csv")
    processor = DayStat_DestinationID(base_path, output_path)
    processor.process_files()
    print ("ok")