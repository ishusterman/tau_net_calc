import geopandas as gpd
from collections import Counter
import csv

class FreqRoutes:
    def __init__(self, gpkg_path: str, table_name: str, columns: list[str]):
        self.gpkg_path = gpkg_path
        self.table_name = table_name
        self.columns = columns
        

    def _extract_prefix(self, value):
        
        if isinstance(value, str) and "_" in value:
            return value.split("_", 1)[0]
        return None

    def build_frequency_dict(self, csv_path: str):

        self.csv_path = csv_path        
        gdf = gpd.read_file(self.gpkg_path, layer=self.table_name)
        counter = Counter()
        for col in self.columns:
            if col not in gdf.columns:
                raise ValueError(f"'{col}' not found")

            for val in gdf[col].dropna():
                prefix = self._extract_prefix(val)
                if prefix:
                    counter[prefix] += 1
        freq_dict = dict(counter.most_common())
        
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["route", "count"])
            for prefix, count in freq_dict.items():
                writer.writerow([prefix, count])

        return freq_dict

if __name__ == "__main__":
    counter = FreqRoutes(
                gpkg_path=r"C:\doc\Igor\GIS\36_routes\output_cum\260429_143749.gpkg",
                table_name="pFxA_fastest_trip",
                columns=["Line_ID1", "Line_ID2", "Line_ID3"],    
                )
    freq_dict = counter.build_frequency_dict(csv_path=r"C:\doc\Igor\GIS\36_routes\freq_routes.csv")

    print ("finish")


    