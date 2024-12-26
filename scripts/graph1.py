import os
import re
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd

class PlotGenerator:
    def __init__(self, xlabel="Start time", ylabel="Number of buildings", title="Accessibility"):
        """
        Initializes the PlotGenerator with the given parameters.
        
        Parameters:
            xlabel (str): Label for the X-axis.
            ylabel (str): Label for the Y-axis.
            title (str): Title of the plot.
        """
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.lines = []  # List to store line data
        self.colors = list(mcolors.TABLEAU_COLORS.values())  # Using Tableau color palette

    def count_transfers(self, row):
    
        transfers = -1
    
        if pd.notna(row['Bus_start_time1']) and pd.notna(row['Bus_finish_time1']):
            transfers += 1
        if pd.notna(row['Bus_start_time2']) and pd.notna(row['Bus_finish_time2']):
            transfers += 1
        if pd.notna(row['Bus_start_time3']) and pd.notna(row['Bus_finish_time3']):
            transfers += 1
        return transfers

    def add_line(self, base_dir, 
                    min_transfer = 0, 
                    max_transfer = 2, 
                    color=None, 
                    label=None
                    ):
        """
        Adds a line to the plot using the log file and the corresponding CSV file in the specified directory.

        Parameters:
            base_dir (str): Path to the directory containing the data for this line.
            transfer_list (list): List of transfer scenarios (optional).
            color (str): Color of the line (optional, defaults to a color from the palette).
            label (str): Label for the line (optional, defaults to "Line X").
        """
        # Use a color from the palette if none is provided
        color = color or self.colors[len(self.lines) % len(self.colors)]
        
        # If no label is provided, use a default label
        label = label or f'Line {len(self.lines) + 1}'

        # Pattern to extract time from log files
        time_pattern = re.compile(
            r"Start at \(hh:mm:ss\):\s+(\d{2}:\d{2}:\d{2})|The earliest start time:\s+(\d{2}:\d{2}:\d{2})")

        # Prepare to collect the lines of data
        x_values = []
        y_values = []

        # Searching the directory for log files
        for root, dirs, files in os.walk(base_dir):
            log_files = [f for f in files if f.startswith("log_") and f.endswith(".txt")]
            if log_files:
                log_file = log_files[0]  # Take the first log file found
                log_path = os.path.join(root, log_file)

                # Read the log file
                with open(log_path, 'r') as log:
                    log_content = log.read()
                    time_match = time_pattern.search(log_content)
                    if time_match:
                        if time_match.group(1):
                            time_str = time_match.group(1)
                        elif time_match.group(2):
                            time_str = time_match.group(2)
        
                        time_without_seconds = time_str[:5]  # Keep only hh:mm part
                        x_values.append(time_without_seconds)  # Add time to X

                        # Find the corresponding CSV file (assuming only one in the directory)
                        base_name = log_file.replace("log_", "").replace(".txt", "")
                        csv_file_path = None
                        for file in files:
                            if file.startswith(base_name) and file.endswith(".csv"):
                                csv_file_path = os.path.join(root, file)
                                break

                        if csv_file_path:
                            # Read the CSV file using pandas
                            df = pd.read_csv(csv_file_path)
                         
                            # Apply the transfer conditions or use all rows if no list is provided
                            if min_transfer == 0 and max_transfer == 2:
                                # Use all rows (no filtering by transfer count)
                                row_count = df.shape[0]
                                y_values.append(row_count)
                                
                            else:
                                # Filter rows by the number of transfers
                                df['Transfers'] = df.apply(self.count_transfers, axis=1)
                                filtered_df = df[(df['Transfers'] >= min_transfer) & (df['Transfers'] <= max_transfer)]
                                row_count = filtered_df.shape[0]
                                y_values.append(row_count)
                                #self.lines.append((x_values, y_values, color, f'{label}_{transfer_count}'))

                        else:
                            print(f"CSV file corresponding to {log_file} not found.")

        if not(min_transfer == 0 and max_transfer == 2):
            label = f'{label} (transfers {min_transfer}-{max_transfer})'

        if x_values and y_values:
            self.lines.append((x_values, y_values, color, label))
        else:
            print(f"No data found for directory: {base_dir}.")

    def generate_plot(self):
        """
        Generates the plot with the added lines.
        """
        plt.figure(figsize=(10, 6))

        # Plot each line
        for idx, (x_values, y_values, color, label) in enumerate(self.lines):
            plt.plot(x_values, y_values, marker='o', linestyle='-', color=color)  # Plot the line

            # Position the label at the first point of the line
            x_start = x_values[0]  # First X value (start of the line)
            y_start = y_values[0]  # First Y value (start of the line)

            # Add the label to the plot at the start of the line with a small offset down
            plt.text(x_start, y_start - 0.05, label, color=color, fontsize=10,
                 verticalalignment='bottom', horizontalalignment='left')

        if not self.lines:
            print("No lines to plot. Ensure that data is added correctly.")
            return

        plt.xlabel(self.xlabel)  # X-axis label
        plt.ylabel(self.ylabel)  # Y-axis label
        plt.title(self.title)  # Plot title
        plt.xticks(rotation=0)  # Set X-axis labels to be horizontal
        plt.grid(True)  # Enable grid on the plot

        plt.tight_layout()  # Adjust layout to prevent overlap
        plt.show()

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        xlabel="Start time",  # X-axis label
        ylabel="Number of buildings",  # Y-axis label
        title="Accessibility"  # Plot title
    )

    # Add lines from the specified directory with specific transfer counts
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_fix-time\\",        
        min_transfer = 0, max_transfer = 0,
        label="Gesher (from, fix-time)"  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_fix-time\\",        
        min_transfer = 1, max_transfer = 1,
        label="Gesher (from, fix-time)"  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_fix-time\\",        
        min_transfer = 2, max_transfer = 2,
        label="Gesher (from, fix-time)"  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_fix-time\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, fix-time)"  # Set line label
    )
    ##################################

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base\\",        
        min_transfer = 0, max_transfer = 0,
        label="Gesher (from, shedule-based)"  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base\\",        
        min_transfer = 1, max_transfer = 1,
        label="Gesher (from, shedule-based)"  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base\\",        
        min_transfer = 2, max_transfer = 2,
        label="Gesher (from, shedule-based)"  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, shedule-based)"  # Set line label
    )

    # Generate the plot
    plot_generator.generate_plot()
