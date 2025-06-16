import csv

# Paths to the input files
file1_path = r"C:\Users\geosimlab\Documents\Igor\experiments\gesher_5min_wait\gesher_from_fix-time_0_2\29dec_10h01m06s_PT_PFX-1\29dec_10h01m06s_PT_PFX.csv"  # Replace with the actual path of the first file
file2_path = r"C:\Users\geosimlab\Documents\Igor\experiments\gesher_5min_wait\gesher_from_fix-time_1_1\29dec_09h51m40s_PT_PFX-1\29dec_09h51m40s_PT_PFX.csv"  # Replace with the actual path of the second file

# Dictionary to store Destination_ID and Duration from the second file
destination_duration_map = {}

# Step 1: Read the second file and store Destination_ID and Duration in a dictionary
with open(file2_path, "r") as file2:
    reader = csv.DictReader(file2)
    for row in reader:
        try:
            destination_id = row["Destination_ID"]
            duration = float(row["Duration"]) if row["Duration"] else None
            if destination_id and duration is not None:
                destination_duration_map[destination_id] = duration
        except ValueError:
            # Ignore rows with invalid Duration values
            continue

# Counter for cases where Duration in the first file is greater
count_greater_durations = 0

# Step 2: Read the first file and compare Duration with the second file
with open(file1_path, "r") as file1:
    reader = csv.DictReader(file1)
    for row in reader:
        try:
            destination_id = row["Destination_ID"]
            duration = float(row["Duration"]) if row["Duration"] else None
            if (
                destination_id in destination_duration_map
                and duration is not None
                and duration > destination_duration_map[destination_id]
            ):
                count_greater_durations += 1
        except ValueError:
            # Ignore rows with invalid Duration values
            continue

# Step 3: Print the result
print(f"The number of times Duration in the first file is greater: {count_greater_durations}")
