from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        xlabel="Start time",  # X-axis label
        ylabel="Convenience coefficient",  # Y-axis label
        title="Accessibility Gesher, from (5 min waiting at the initial stops)"  # Plot title
    )
    
    # Add lines from the specified directory with specific transfer counts
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_0_0\\",        
        label="fix-time,t(0-0)) ",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time    
    )
    print ("plot1")

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_1_1\\",        
        label="fix-time,t(1-1)) ",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time    
    )
    print ("plot2")

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_2_2\\",        
        label="fix-time,t(2-2))",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time    
    )
    print ("plot3")

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_5min_wait\\gesher_from_fix-time_0_2\\",        
        label="fix-time,t(0-2))",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time    
    )
    print ("plot4")


    #############################
    #############################
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base_0_0\\",        
        label="(schedule-base,t(0-0)) ",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time     
    )
    print ("plot5")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base_1_1\\",        
        label="schedule-base,t(1-1)) ",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time     
    )
    print ("plot6")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base_2_2\\",        
        label="schedule-base,t(2-2)) ",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time     

    )
    print ("plot7")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_from_shedule-base\\",        
        label="schedule-base,t(0-2))",
        calculation_method = PlotGenerator.calculate_convenience_coefficient,
        average_travel_time=PlotGenerator.average_travel_time, 
        average_wait_time=PlotGenerator.average_wait_time,
        count_transfers=PlotGenerator.count_transfers,
        average_walk_time=PlotGenerator.average_walk_time     
    )
    print ("plot8")
    
    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data8.xlsx")

    # Generate the plot
    plot_generator.generate_plot(show_legend = True)
