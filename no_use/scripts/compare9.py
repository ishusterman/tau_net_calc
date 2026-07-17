import pandas as pd

def merge_files_with_avg_duration(file_paths, output_file):
    """
    Merges files and keeps the average Duration for each Destination_ID
    
    Parameters:
    file_paths (list): List of paths to 7 input files
    output_file (str): Path to output file
    """
    
    if len(file_paths) != 7:
        print(f"Error: Expected 7 files, but received {len(file_paths)}")
        return None
    
    print(f"Processing {len(file_paths)} files...")
    
    # Read and combine all files
    all_data = []
    for i, file_path in enumerate(file_paths, 1):
        print(f"Reading file {i}: {file_path}")
        try:
            df = pd.read_csv(file_path)
            all_data.append(df)
            print(f"  - Rows: {len(df)}")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Total rows after merging: {len(combined_df)}")
    print(f"Unique Destination_ID count: {combined_df['Destination_ID'].nunique()}")
    
    # Group by Destination_ID and calculate average Duration for each group
    # Also aggregate other columns - you can choose how to handle them
    result_df = combined_df.groupby('Destination_ID').agg({
        'Duration': 'mean',
        # For other columns, you might want to keep the first value, or handle differently
        # Add other columns as needed, for example:
        # 'Other_Column': 'first'
    }).reset_index()
    
    # Sort by Destination_ID for better readability
    result_df = result_df.sort_values('Destination_ID').reset_index(drop=True)
    
    # Save result
    result_df.to_csv(output_file, index=False)
    print(f"Result saved to: {output_file}")
    print(f"Final unique Destination_ID count: {len(result_df)}")
    print(f"Duration range: {result_df['Duration'].min()} - {result_df['Duration'].max()}")
    print(f"Average Duration: {result_df['Duration'].mean():.2f}")
    
    return result_df

def merge_files_with_min_duration(file_paths, output_file):
    """
    Merges files and keeps only the row with minimum Duration for each Destination_ID
    
    Parameters:
    file_paths (list): List of paths to 7 input files
    output_file (str): Path to output file
    """
    
    if len(file_paths) != 7:
        print(f"Error: Expected 7 files, but received {len(file_paths)}")
        return None
    
    print(f"Processing {len(file_paths)} files...")
    
    # Read and combine all files
    all_data = []
    for i, file_path in enumerate(file_paths, 1):
        print(f"Reading file {i}: {file_path}")
        try:
            df = pd.read_csv(file_path)
            all_data.append(df)
            print(f"  - Rows: {len(df)}")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Total rows after merging: {len(combined_df)}")
    print(f"Unique Destination_ID count: {combined_df['Destination_ID'].nunique()}")
    
    # Group by Destination_ID and find row with minimum Duration for each group
    min_duration_indices = combined_df.groupby('Destination_ID')['Duration'].idxmin()
    result_df = combined_df.loc[min_duration_indices]
    
    # Sort by Destination_ID for better readability
    result_df = result_df.sort_values('Destination_ID').reset_index(drop=True)
    
    # Save result
    result_df.to_csv(output_file, index=False)
    print(f"Result saved to: {output_file}")
    print(f"Final unique Destination_ID count: {len(result_df)}")
    print(f"Duration range: {result_df['Duration'].min()} - {result_df['Duration'].max()}")
    
    return result_df

def filter_destinations_efficient(file1_path, file2_path, output_path):
    """
    More efficient version using dictionary for lookups
    """
    
    print("Reading input files...")
    
    # Read both files
    df1 = pd.read_csv(file1_path)
    df2 = pd.read_csv(file2_path)
    
    print(f"File 1 rows: {len(df1)}")
    print(f"File 2 rows: {len(df2)}")
    
    # Create dictionary of min durations from second file
    min_duration_2 = df2.groupby('Destination_ID')['Duration'].min().to_dict()
    
    # Filter rows from first file
    result_rows = []
    
    for _, row in df1.iterrows():
        dest_id = row['Destination_ID']
        duration_1 = row['Duration']
        
        # If Destination_ID not in second file, keep row
        if dest_id not in min_duration_2:
            result_rows.append(row)
        # If Duration in first file is lower than min in second file, keep row
        elif duration_1 < min_duration_2[dest_id]:
            result_rows.append(row)
    
    # Create result DataFrame
    result_df = pd.DataFrame(result_rows)
    
    print(f"Result rows: {len(result_df)}")
    
    # Save result
    result_df.to_csv(output_path, index=False)
    print(f"Result saved to: {output_path}")
    
    return result_df

# Example usage
if __name__ == "__main__":
    
    # Define paths to your 7 files
    
    input_files = [
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\1\251015_095057_PFXA_min_duration.csv",
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\2\251015_095057_PFXA_min_duration.csv",
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\3\251015_095057_PFXA_min_duration.csv",
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\4\251015_095057_PFXA_min_duration.csv",
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\5\251015_095057_PFXA_min_duration.csv",
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\6\251015_095057_PFXA_min_duration.csv",
        r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\251015_095057_PFXA_to\7\251015_095057_PFXA_min_duration.csv",
    ]
    
    output_path = r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\211621047_all_to_avg.csv"
    
    # Merge files
    #result = merge_files_with_min_duration(input_files, output_path)
    result = merge_files_with_avg_duration(input_files, output_path)
    
    if result is not None:
        print("Merge completed successfully!")
    else:
        print("Merge failed!")
    


    #file1 = r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\211621047\2018\251010_121903_PFXA_from\1\251010_121903_PFXA_min_duration.csv"
    file1 = r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\211621047\2018\251010_121804_PFXA_to\1\251010_121804_PFXA_min_duration.csv"
    file2 = r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\211621047_all_to_avg.csv"
    output = r"c:\doc\Igor\GIS\prg\exp_08_2025\2zone\test-1210\211621047\2025-50min\211621047_2018faster_to_avg.csv"
    
    # Use the efficient version (recommended)
    result = filter_destinations_efficient(file1, file2, output)
    
    print("Filtering completed successfully!")

    