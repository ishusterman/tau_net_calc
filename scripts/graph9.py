from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        title="Accessibility Gesher 6.00-24:00, max_transfer = 0"  # Plot title
    )
    
    # Add lines from the specified directory with specific transfer counts
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00\\schedule_from\\",
        max_transfer = 0,        
        label="schedule_from",
        )
    print ("plot1")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00\\schedule_to\\",        
        max_transfer = 0,        
        label="schedule_to",
        )
    print ("plot2")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00\\fixed_from\\",        
        max_transfer = 0,        
        label="fixed_from",
        )
    print ("plot3")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00\\fixed_to\\",        
        max_transfer = 0,        
        label="fixed_to",
        )
    print ("plot4")


    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_50_proc\\schedule_from\\",        
        max_transfer = 0,        
        label="schedule_from_50proc",
        )
    print ("plot5")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_50_proc\\schedule_to\\",        
        max_transfer = 0,        
        label="schedule_to_50proc",
        )
    print ("plot6")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_50_proc\\fixed_from\\",        
        max_transfer = 0,        
        label="fixed_from_50proc",
        )
    print ("plot7")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_50_proc\\fixed_to\\",        
        max_transfer = 0,        
        label="fixed_to_50proc",
        )
    print ("plot8")

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_30_proc\\schedule_from\\",        
        max_transfer = 0,        
        label="schedule_from_30proc",
        )
    print ("plot9")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_30_proc\\schedule_to\\",        
        max_transfer = 0,        
        label="schedule_to_30proc",
        )
    print ("plot10")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_30_proc\\fixed_from\\",        
        max_transfer = 0,        
        label="fixed_from_30proc",
        )
    print ("plot11")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\gesher_6_00_22_00_30_proc\\fixed_to\\",        
        max_transfer = 0,        
        label="fixed_to_30proc",
        )
    print ("plot12")

    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data9-1.xlsx")

    # Generate the plot
    plot_generator.generate_plot(show_legend = True)
