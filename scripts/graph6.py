from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        xlabel="Start time",  # X-axis label
        ylabel="Average Wait Time",  # Y-axis label
        title="Accessibility Gesher (5 min waiting at the initial stops)"  # Plot title
    )

    # Add lines from the specified directory with specific transfer counts
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_0_0\\",        
        label="Gesher (from, fix-time, transfers (0-0)) ",
        calculation_method = PlotGenerator.average_wait_time    
    )

    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data3.xlsx")

    # Generate the plot
    plot_generator.generate_plot(show_legend = True)
