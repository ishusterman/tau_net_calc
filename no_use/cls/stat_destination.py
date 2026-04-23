import os
import re
import pandas as pd

#rom qgis.core import QgsProject, QgsVectorLayer

class DayStat_DestinationID:
    TIME_DELTA = 420

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
        Gathers all CSV files from the immediate subdirectories of the base path.
        """
        # List directories in the base path (ignoring files)
        #subdirs = [f.path for f in os.scandir(self.base_path) if f.is_dir()]

        self.files = []  # Clear previous contents

        subdirs = [os.path.normpath(f.path) for f in os.scandir(self.base_path) if f.is_dir()]

        
        # Iterate through each subdirectory and add CSV files to self.files
        for subdir in subdirs:
            
            for file in os.listdir(subdir):
                if file.endswith("min_duration.csv"):
                    self.files.append(os.path.join(subdir, file))

        

        if not self.files:
            raise ValueError(f"No CSV files found in the immediate subdirectories of the directory: {self.base_path}")



    def extract_time_pattern_from_txt(self, txt_path):
        """
        Extracts the last matched time pattern from the provided .txt file.

        :param txt_path: Path to the .txt file.
        :return: Last matched time string or None if no match found.
        """
        # Define the regex pattern
        time_pattern = re.compile(
            r"Start at \(hh:mm:ss\):\s+(\d{2}:\d{2}:\d{2})|"
            r"Earliest start time:\s+(\d{2}:\d{2}:\d{2})|"
            r"Arrive before \(hh:mm:ss\):\s+(\d{2}:\d{2}:\d{2})|"
            r"Earliest arrival time:\s+(\d{2}:\d{2}:\d{2})"
        )

        # Read the .txt file
        with open(txt_path, "r") as file:
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
        for idx, file in enumerate(self.files):
            # Read the current CSV file
            df = pd.read_csv(file)
            if "Destination_ID" not in df.columns or "Duration" not in df.columns:
                print(f"Skipping file {file} due to missing required columns.")
                continue

            # Get the folder where the current file is located
            file_folder = os.path.dirname(file)

            # Find the corresponding .txt file in the same folder
            txt_file = next((f for f in os.listdir(file_folder) if f.endswith(".txt")), None)
            if not txt_file:
                print(f"No .txt file found in the folder: {file_folder}")
                continue

            # Extract time pattern from the .txt file
            time_value = self.extract_time_pattern_from_txt(os.path.join(file_folder, txt_file))
            if not time_value:
                print(f"No time pattern found in the .txt file: {txt_file}")
                continue

            # Filter and rename columns
            df = df[["Destination_ID", "Duration"]]
            df = df.rename(columns={"Duration": time_value})

            # Merge the data into the result DataFrame
            if idx == 0:
                # Initialize the result DataFrame with the first file
                self.result = df
            else:
                # Merge with the existing result DataFrame
                self.result = pd.merge(self.result, df, on="Destination_ID", how="outer")

        # Replace NaN values with zeros
        # ?????????????????????????????
        if self.result is not None:
            #self.result.fillna(0, inplace=True)

            # Sort columns by name, keeping Destination_ID first
            duration_columns = [col for col in self.result.columns if col != "Destination_ID"]
            self.result[duration_columns] = self.result[duration_columns].astype('Int64')
            #self.result[duration_columns] = self.result[duration_columns].astype(int)
            sorted_columns = sorted(duration_columns)
            self.result = self.result[["Destination_ID"] + sorted_columns]

            # Add statistical calculations
            self.add_statistics()

            # Save the final result to a CSV file
            numeric_cols = ['mean', 'std_dev', 'cv', 'percentage_lt_min_plus_delta']
            self.result[numeric_cols] = self.result[numeric_cols].apply(pd.to_numeric, errors='coerce')
            self.result[numeric_cols] = self.result[numeric_cols].round(3)
            self.result.to_csv(self.output_path, index=False)

            """
            path_protokol = os.path.normpath(self.output_path)
            path_protokol = path_protokol.replace("\\", "/")
            alias = os.path.splitext(os.path.basename(path_protokol))[0]
            uri = f"file:///{path_protokol}?type=csv&maxFields=10000&detectTypes=yes&geomType=none&subsetIndex=no&watchFile=no"
            print (uri)
            self.protocol_layer = QgsVectorLayer(uri, alias, "delimitedtext")
            QgsProject.instance().addMapLayer(self.protocol_layer)
            """

        else:
            print("No valid CSV files processed.")


    def add_statistics(self):
        """
        Add min, max, variance, standard deviation, and coefficient of variation columns for each row 
        based on duration columns in the result DataFrame.
        """
        # Select only the duration columns
        duration_columns = [col for col in self.result.columns if col != 'Destination_ID']
        
        # Convert all duration columns to numeric, replacing errors with NaN
        self.result[duration_columns] = self.result[duration_columns].apply(pd.to_numeric, errors='coerce')

        # Calculate min and max for the duration columns
        self.result["count"] = self.result[duration_columns].count(axis=1)
        self.result["min"] = self.result[duration_columns].min(axis=1, skipna=True)
        self.result["min_in_time"] = self.result[duration_columns].idxmin(axis=1, skipna=True)
        self.result["max"] = self.result[duration_columns].max(axis=1, skipna=True)
        self.result["max_in_time"] = self.result[duration_columns].idxmax(axis=1, skipna=True)
        self.result["mean"] = self.result[duration_columns].mean(axis=1, skipna=True)

        # Calculate standard deviation directly
        self.result["std_dev"] = self.result[duration_columns].std(axis=1, skipna=True, ddof=1)

        # Calculate coefficient of variation
        self.result["cv"] = self.result.apply(
            lambda row: row["std_dev"] / row["mean"] if row["mean"] > 0 else 0, axis=1
            )
        
        self.result["percentage_lt_min_plus_delta"] = self.result.apply(
            lambda row: sum(row[duration_columns] < (row["min"] + DayStat_DestinationID.TIME_DELTA)) / row["count"] * 100
            if row["count"] > 0 else 0, axis=1
            )

if __name__ == "__main__":
    base_path = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Government_Complex-112025\251124_150637_PFXA\from'
    output_path = os.path.join(base_path, f"stat_from.csv")
    processor = DayStat_DestinationID(base_path, output_path)
    processor.process_files()
    print ("ok")