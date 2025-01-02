from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        title="Accessibility osm209771454 6.00-24:00 transfers = 0"  # Plot title
    )
    
    # Add lines from the specified directory with specific transfer counts
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\209771454_6_00_22_00\\schedule_from\\",        
        max_transfer = 0,
        label="schedule_from",
        )
    print ("plot1")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\209771454_6_00_22_00\\schedule_to\\",        
        max_transfer = 0,
        label="schedule_to",
        )
    print ("plot2")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\209771454_6_00_22_00\\fixed_from\\",   
        max_transfer = 0,     
        label="fixed_from",
        )
    print ("plot3")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\209771454_6_00_22_00\\fixed_to\\",    
        max_transfer = 0,    
        label="fixed_to",
        )
    print ("plot4")

    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data12.xlsx")

    # Generate the plot
    plot_generator.generate_plot(show_legend = True)
