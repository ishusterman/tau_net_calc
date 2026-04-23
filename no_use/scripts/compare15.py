import pandas as pd
from collections import Counter

# Read CSV file
df = pd.read_csv(r'c:\doc\Igor\GIS\prg\211621047-112025\exp2\all_from_2025.csv')

# Function to extract numeric part from Line_ID
def extract_line_id(line_id):
    if pd.isna(line_id):
        return None
    return str(line_id).split('_')[0]

# Extract and clean Line_ID1 values
line_ids = df['Line_ID1'].apply(extract_line_id).dropna()

# Calculate statistics sorted by frequency (descending)
line_stats = Counter(line_ids)
top_10_lines = line_stats.most_common(50)

# Display results
print("Top 10 most frequent Line_ID1 routes:")
print("-------------------------------------")
for rank, (line_id, count) in enumerate(top_10_lines, 1):
    print(f"{rank}. Route {line_id}: {count} trips")

# Additional statistics
print(f"\nTotal unique routes: {len(line_stats)}")
print(f"Total records with Line_ID1: {len(line_ids)}")
print(f"Most frequent route: {top_10_lines[0][0]} ({top_10_lines[0][1]} trips)")

# Optional: Save full statistics to file
full_stats = pd.DataFrame(line_stats.most_common(), columns=['Line_ID', 'Trip_Count'])
full_stats.to_csv('line_id1_statistics.csv', index=False)
print("\nFull statistics saved to 'line_id1_statistics.csv'")