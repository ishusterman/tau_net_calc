import pandas as pd
file_5 = r"C:\Users\geosimlab\Documents\Igor\experiments\Gesher-3\stat_3.csv"
file_8 = r"C:\Users\geosimlab\Documents\Igor\experiments\Gesher-4\stat_4.csv"
df_5 = pd.read_csv(file_5)
df_8 = pd.read_csv(file_8)
filtered_df_8 = df_8[df_8['Destination_ID'].isin(df_5['Destination_ID'])]
output_file = r"C:\Users\geosimlab\Documents\Igor\experiments\Gesher-4\filtered_stat_4.csv"
filtered_df_8.to_csv(output_file, index=False)
print(f"ok")