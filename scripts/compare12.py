import pickle
import sys

FILE1 = r"c:\doc\Igor\GIS\temp\from_data_plugin.pkl"
FILE2 = r"c:\doc\Igor\GIS\temp\from_data_slice.pkl"

with open(FILE1, 'rb') as f1, open(FILE2, 'rb') as f2:
    dict1 = pickle.load(f1)
    dict2 = pickle.load(f2)

print(f"Elements: {len(dict1)} vs {len(dict2)}")
print(f"Memory: {sys.getsizeof(dict1)} vs {sys.getsizeof(dict2)} bytes")
print(f"Keys order same: {list(dict1.keys()) == list(dict2.keys())}")
print(f"Dicts equal (==): {dict1 == dict2}")
print(f"Dicts identical (is): {dict1 is dict2}")

# Check if it's just memory allocation difference
if dict1 == dict2:
    print(" Dictionaries are logically identical - size difference is just internal memory allocation")