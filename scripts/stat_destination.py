import os
import re
import pandas as pd

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
        Gathers all CSV files from the immediate subdirectories of the base path.
        """
        # List directories in the base path (ignoring files)
        subdirs = [f.path for f in os.scandir(self.base_path) if f.is_dir()]
        
        # Iterate through each subdirectory and add CSV files to self.files
        for subdir in subdirs:
            for file in os.listdir(subdir):
                if file.endswith(".csv"):
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
            r"The earliest start time:\s+(\d{2}:\d{2}:\d{2})|"
            r"Arrive before \(hh:mm:ss\):\s+(\d{2}:\d{2}:\d{2})|"
            r"The earliest arrival time:\s+(\d{2}:\d{2}:\d{2})"
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
            numeric_cols = ['variance', 'std_dev', 'cv']
            self.result[numeric_cols] = self.result[numeric_cols].apply(pd.to_numeric, errors='coerce')
            self.result[numeric_cols] = self.result[numeric_cols].round(3)
            self.result.to_csv(self.output_path, index=False)

            print("Processing completed.")
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
        self.result["min"] = self.result[duration_columns].min(axis=1, skipna=True)
        self.result["min_in_time"] = self.result[duration_columns].idxmin(axis=1, skipna=True)
        self.result["max"] = self.result[duration_columns].max(axis=1, skipna=True)
        self.result["max_in_time"] = self.result[duration_columns].idxmax(axis=1, skipna=True)

        # Calculate variance with Bessel's correction (N-1)
        self.result["variance"] = self.result[duration_columns].apply(lambda row: row.var(ddof=1), axis=1)
    
        # Calculate standard deviation based on variance
        self.result["std_dev"] = self.result["variance"].apply(lambda x: x ** 0.5)
    
        # Calculate coefficient of variation
        self.result["cv"] = self.result.apply(
            lambda row: row["std_dev"] / row[duration_columns].mean() if row[duration_columns].mean() > 0 else 0, axis=1
        )


# Example usage
#base_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo Bek"
base_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo_Bek_7_00_20_00"
output_path = r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Leo_Bek_7_00_20_00\\StatDestination2.csv"

processor = DayStat_DestinationID(base_path, output_path)
processor.process_files()
