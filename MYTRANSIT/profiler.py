import pstats

stats = pstats.Stats(
    r"plugin_profile.txt")
stats.sort_stats(pstats.SortKey.TIME) 
stats.print_stats(10) 
