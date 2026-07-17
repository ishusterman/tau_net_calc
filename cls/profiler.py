import pstats

stats = pstats.Stats(
    r"c:\temp\plugin_profile_process_0.prof")
stats.sort_stats(pstats.SortKey.TIME) 
stats.print_stats(10) 
