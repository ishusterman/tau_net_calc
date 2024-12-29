from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        xlabel="Start time",  # X-axis label
        ylabel="Number of buildings",  # Y-axis label
        title="Accessibility Gesher (5 min waiting at the initial stops)"  # Plot title
    )

    # Add lines from the specified directory with specific transfer counts
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_0_0\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, fix-time, transfers (0-0)) "  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_1_1\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, fix-time, transfers (1-1)) "  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_2_2\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, fix-time, transfers (2-2)) "  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_0_2\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, fix-time, transfers (0-2))"  # Set line label
    )


    #############################
    #############################

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base_0_0\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, schedule-base, transfers (0-0)) "  # Set line label
    )

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base_1_1\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, schedule-base, transfers (1-1)) "  # Set line label
    )
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base_2_2\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, schedule-base, transfers (2-2)) "  # Set line label
    )
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base\\",        
        min_transfer = 0, max_transfer = 2,
        label="Gesher (from, schedule-base, transfers (0-2))"  # Set line label
    )
    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data3.xlsx")

    # Generate the plot
    plot_generator.generate_plot()
