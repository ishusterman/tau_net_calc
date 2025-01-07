from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        title="Accessibility Kazrin osm700274831, 6.00-24:00, 1 transfers"  # Plot title
    )
    
    # Add lines from the specified directory with specific transfer counts
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Kazrin\\schedule_from\\",        
        label="schedule_from",
        )
    print ("plot1")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Kazrin\\schedule_to\\",        
        label="schedule_to",
        )
    print ("plot2")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Kazrin\\fixed_from\\",        
        label="fixed_from",
        )
    print ("plot3")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\Kazrin\\fixed_to\\",        
        label="fixed_to",
        )
    print ("plot4")



    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data16.xlsx")

    # Generate the plot
    plot_generator.generate_plot(show_legend = True)
