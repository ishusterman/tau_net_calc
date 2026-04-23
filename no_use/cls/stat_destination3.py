import os
import pandas as pd

class DayStat_DestinationID:
    def __init__(self, base_path, output_path):
        self.base_path = base_path
        self.output_path = output_path
        self.result = None
        self.files = []

    def gather_files(self):
        """Gathers all CSV files from the immediate subdirectories"""
        self.files = []
        subdirs = [os.path.normpath(f.path) for f in os.scandir(self.base_path) if f.is_dir()]
        
        for subdir in subdirs:
            for file in os.listdir(subdir):
                if file.endswith("min_duration.csv"):
                    self.files.append(os.path.join(subdir, file))

        if not self.files:
            raise ValueError(f"No CSV files found in: {self.base_path}")

    def process_files(self):
        """Process CSV files and calculate statistics, keeping only Destination_ID present in all files"""
        self.gather_files()
        
        all_dfs = []
        destination_ids_sets = []
        
        # Read all files and collect Destination_ID sets
        for file in self.files:
            df = pd.read_csv(file)
            if "Destination_ID" not in df.columns or "Duration" not in df.columns:
                print(f"Skipping file {file} due to missing required columns.")
                continue
            
            # Keep only necessary columns
            df = df[["Destination_ID", "Duration"]]
            all_dfs.append(df)
            destination_ids_sets.append(set(df['Destination_ID']))

        if not all_dfs:
            print("No valid CSV files processed.")
            return

        # Find common Destination_ID across all files
        common_destination_ids = set.intersection(*destination_ids_sets)
        
        if not common_destination_ids:
            print("No common Destination_ID found across all files.")
            return
        
        print(f"Found {len(common_destination_ids)} common Destination_ID across {len(all_dfs)} files")
        
        # Filter each DataFrame to keep only common Destination_ID
        filtered_dfs = []
        for df in all_dfs:
            filtered_df = df[df['Destination_ID'].isin(common_destination_ids)].copy()
            filtered_dfs.append(filtered_df)

        # Combine all filtered data
        combined_df = pd.concat(filtered_dfs, ignore_index=True)
        
        # Calculate statistics grouped by Destination_ID
        self.result = combined_df.groupby('Destination_ID')['Duration'].agg([
            ('count_duration', 'count'),
            ('mean_duration', 'mean'),
            ('min_duration', 'min'),
            ('max_duration', 'max'),
            ('std_duration', 'std')
        ]).reset_index()

        # Round numeric columns
        numeric_cols = ['mean_duration', 'std_duration']
        self.result[numeric_cols] = self.result[numeric_cols].round(2)
        
        # Save result
        self.result.to_csv(self.output_path, index=False)
        print(f"Results saved to: {self.output_path}")
        print(f"Total records: {len(self.result)}")

if __name__ == "__main__":
    #base_path = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Beilinson-112025\251127_124751_PFXA\from'
    #output_path = os.path.join(base_path, f"stat_from.csv")
    base_path = r'c:\doc\Igor\GIS\prj\exp_08_2025\exp_08_2025_output\Beilinson-112025\251127_124751_PFXA\to'
    output_path = os.path.join(base_path, f"stat_to.csv")
    processor = DayStat_DestinationID(base_path, output_path)
    processor.process_files()
    print ("ok")