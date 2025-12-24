import pandas as pd

df1 = pd.read_csv(r'c:\doc\Igor\GIS\test\result_round_trip_2025.csv')
df2 = pd.read_csv(r'c:\doc\Igor\GIS\test\result_round_trip_2025+3lines.csv')
set1 = set(df1['Round_Trip_Start'].unique())
set2 = set(df2['Round_Trip_Start'].unique())
   
result_set = set1 - set2
print(list(result_set))

