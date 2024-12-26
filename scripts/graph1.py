import os
import re
import matplotlib.pyplot as plt

def generate_plot(base_dir, xlabel="Start time", ylabel="Number of buildings", title="Accessibility"):
    """
    Generates a plot based on log_*.txt files and the corresponding single *.csv file in the specified directory.

    Parameters:
        base_dir (str): Path to the directory containing the data.
        xlabel (str): Label for the X-axis.
        ylabel (str): Label for the Y-axis.
        title (str): Title of the plot.
    """
    # Pattern to extract time from log files
    time_pattern = re.compile(r"Start at \(hh:mm:ss\):\s+(\d{2}:\d{2}:\d{2})")

    # Data for the plot
    x_values = []
    y_values = []

    # Iterate through the directory
    for root, dirs, files in os.walk(base_dir):
        # Filter log files
        log_files = [f for f in files if f.startswith("log_") and f.endswith(".txt")]
        for log_file in log_files:
            log_path = os.path.join(root, log_file)

            # Read the log file
            with open(log_path, 'r') as log:
                log_content = log.read()
                time_match = time_pattern.search(log_content)
                if time_match:
                    time_str = time_match.group(1)  # Extract time
                    time_without_seconds = time_str[:5]  # Keep only hh:mm part
                    x_values.append(time_without_seconds)  # Add time to X

                    # Find the corresponding CSV file (assuming only one in the directory)
                    base_name = log_file.replace("log_", "").replace(".txt", "")
                    print (base_name)
                    csv_file_path = None
                    for file in files:
                        if file.startswith(base_name) and file.endswith(".csv"):
                            csv_file_path = os.path.join(root, file)
                            break

                    if csv_file_path:
                        # Count the number of rows in the CSV file
                        with open(csv_file_path, 'r') as csv_file:
                            y_values.append(sum(1 for _ in csv_file))  # Add row count to Y
                    else:
                        print(f"CSV file corresponding to {log_file} not found.")

    # Plot the graph
    plt.figure(figsize=(10, 6))
    plt.plot(x_values, y_values, marker='o', linestyle='-', color='b')
    plt.xlabel(xlabel)  # Set the X-axis label
    plt.ylabel(ylabel)  # Set the Y-axis label
    plt.title(title)  # Set the plot title
    plt.xticks(rotation=0)  # Set X-axis labels to be horizontal
    plt.grid(True)  # Enable grid on the plot
    plt.tight_layout()  # Adjust layout to prevent overlap
    plt.show()

# Example usage
if __name__ == "__main__":
    generate_plot(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_fix-time",
        xlabel="Start time",  # Label for the X-axis
        ylabel="Number of buildings",  # Label for the Y-axis
        title="Accessibility"  # Title of the plot
    )
