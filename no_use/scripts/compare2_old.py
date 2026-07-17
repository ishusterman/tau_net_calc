import pandas as pd

def merge_csv_by_origin_destination(file1, file2):
    
    df1 = pd.read_csv(file1, usecols=["Origin_ID", "Destination_ID", "Duration"], 
                     dtype={"Origin_ID": str, "Destination_ID": str})
    df2 = pd.read_csv(file2, usecols=["Origin_ID", "Destination_ID", "Duration"], 
                     dtype={"Origin_ID": str, "Destination_ID": str})
    
    df1.rename(columns={"Duration": "schedule"}, inplace=True)
    df2.rename(columns={"Duration": "fix"}, inplace=True)
    merged_df = pd.merge(df1, df2, on=["Origin_ID", "Destination_ID"], how="inner")
    count_less = (merged_df["fix"] < merged_df["schedule"]).sum()
    print(f"fix < schedule: {count_less}")
    

file_schedule= r"c:\doc\Igor\GIS\temp\1811-211621047\211621047_schedule\211621047_schedule_min_endtime.csv"
file_fix = r"c:\doc\Igor\GIS\temp\1811-211621047\211621047_schedule_fix-2\211621047_schedule_fix-2_min_endtime.csv"


merge_csv_by_origin_destination(file_schedule, file_fix)