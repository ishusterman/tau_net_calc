import pandas as pd

def merge_csv_by_destination(file1, file2, output_file):
    # Загрузка данных из файлов
    df1 = pd.read_csv(file1, usecols=["Destination_ID", "Duration"], dtype={"Destination_ID": str})
    df2 = pd.read_csv(file2, usecols=["Destination_ID", "Duration"], dtype={"Destination_ID": str})
    
    # Переименование столбцов для различия
    df1.rename(columns={"Duration": "schedule"}, inplace=True)
    df2.rename(columns={"Duration": "fix"}, inplace=True)
    
    # Объединение данных по destination_id
    merged_df = pd.merge(df1, df2, on="Destination_ID", how="inner")

    # Подсчет случаев, когда duration2 > duration1
    count_greater = (merged_df["fix"] > merged_df["schedule"]).sum()
    count_greater2 = (merged_df["fix"] < merged_df["schedule"]).sum()
    #percent_greater = (count_greater / len(merged_df)) * 100 if len(merged_df) > 0 else 0
    
    
    print(f"fix < schedule {count_greater2}")
    print("Cases where fix < schedule:")
    greater_cases = merged_df[merged_df["fix"] < merged_df["schedule"]]
    print(greater_cases.to_string(index=False))
    print(f"fix < schedule {count_greater2}")
    print(f"ok")


#file1 = r"c:\temp\1\compare\250310_091700_PFSA.csv"
#file2 = r"c:\temp\1\compare\250310_091511_PFXA.csv"

file1 = r"c:\temp\1\250501_095439_PTSA\250501_095439_PTSA_min_duration.csv"
file2 = r"c:\temp\1\250501_095536_PTXA\250501_095536_PTXA_min_duration.csv"

#file1 = r"c:\temp\1\250404_130231_PFSA\250404_130231_PFSA_min_endtime.csv"
#file2 = r"c:\temp\1\250404_130210_PFXA\250404_130210_PFXA_min_endtime.csv"

res = r"c:\temp\1\compare.csv"
merge_csv_by_destination(file1, file2, res)
