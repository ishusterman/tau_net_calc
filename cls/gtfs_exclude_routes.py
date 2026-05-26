import pandas as pd
import os
import shutil

try:
    from PyQt5.QtWidgets import QApplication
    IN_QGIS = True
except ImportError:
    IN_QGIS = False

class GTFSExcludeRoutes:
    def __init__(self, parent, gtfs_path, output_path=None,
                 excluded_data_path=None, exclude_ids_list=None):
        """
        Arguments:
            gtfs_path (str): Path to original GTFS.
            exclude_file_path (str): Path to CSV/TXT with route_id to exclude.
            output_path (str): Path for cleaned GTFS.
            excluded_data_path (str): Path for GTFS containing only excluded records.
            exclude_ids_list (list[str]): Direct list of route_id to exclude.
        """
        self.parent = parent
        self.gtfs_path = gtfs_path
        self.output_path = output_path
        self.excluded_data_path = excluded_data_path
        self.exclude_ids_list = exclude_ids_list
        self.exclude_ids = []
        self.already_display_break = False

        self.IN_QGIS = True
        if self.parent == None:
            self.IN_QGIS = False

    
    def _load_exclude_ids(self):
    
        if self.exclude_ids_list is not None:
            self.exclude_ids = [str(x) for x in self.exclude_ids_list]
            return
        self.exclude_ids = []

    def _prepare_dirs(self):
        for path in [self.output_path, self.excluded_data_path]:
            if path is None:
                continue
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)

    def verify_break(self):
        if self.IN_QGIS:
            if self.parent is not None:
                if self.parent.break_on:
                    self.parent.setMessage("Deleting lines from GTFS is interrupted by user")
                    if not self.already_display_break:
                        self.parent.textLog.append(f'<a><b><font color="red">Deleting lines from GTFS is interrupted by user</font> </b></a>')
                        self.already_display_break = True
                    self.parent.progressBar.setValue(0)
                    return True
            return False
    
    def run(self):
        self._load_exclude_ids()
        self._prepare_dirs()

        try:
            # --- ROUTES ---
            if self.verify_break():
                return 0
            routes_df = pd.read_csv(os.path.join(self.gtfs_path, 'routes.txt'),
                                    dtype={'route_id': str})

            mask_excluded = routes_df['route_id'].isin(self.exclude_ids)

            filtered_routes = routes_df[~mask_excluded]
            removed_routes = routes_df[mask_excluded]

            filtered_routes.to_csv(os.path.join(self.output_path, 'routes.txt'), index=False)
            removed_routes.to_csv(os.path.join(self.excluded_data_path, 'routes.txt'), index=False)

            agency_path = os.path.join(self.gtfs_path, 'agency.txt')            
            if os.path.exists(agency_path):
                shutil.copy(agency_path, os.path.join(self.output_path, 'agency.txt'))
                shutil.copy(agency_path, os.path.join(self.excluded_data_path, 'agency.txt'))

            # --- TRIPS ---
            if self.verify_break():
                return 0
            if self.IN_QGIS:
                self.parent.progressBar.setValue(1)
                self.parent.setMessage("Deleting lines from GTFS ('trips.txt') ...")
                QApplication.processEvents()
            trips_df = pd.read_csv(os.path.join(self.gtfs_path, 'trips.txt'),
                                   dtype={'route_id': str, 'trip_id': str, 'service_id': str, 'shape_id': str})

            mask_trips_excluded = trips_df['route_id'].isin(self.exclude_ids)

            filtered_trips = trips_df[~mask_trips_excluded]
            removed_trips = trips_df[mask_trips_excluded]

            filtered_trips.to_csv(os.path.join(self.output_path, 'trips.txt'), index=False)
            removed_trips.to_csv(os.path.join(self.excluded_data_path, 'trips.txt'), index=False)


            # --- SHAPES ---
            if self.verify_break():
                return 0
            if self.IN_QGIS:
                self.parent.progressBar.setValue(1)
                self.parent.setMessage("Deleting lines from GTFS ('shapes.txt') ...")
                QApplication.processEvents()

            shapes_path = os.path.join(self.gtfs_path, 'shapes.txt')
            if os.path.exists(shapes_path):

                shapes_df = pd.read_csv(
                    shapes_path,
                    dtype={'shape_id': str, 'shape_pt_sequence': str}
                )

                
                keep_shape_ids = set(filtered_trips['shape_id'].dropna().unique())
                remove_shape_ids = set(removed_trips['shape_id'].dropna().unique())

                filtered_shapes = shapes_df[shapes_df['shape_id'].isin(keep_shape_ids)]
                removed_shapes = shapes_df[shapes_df['shape_id'].isin(remove_shape_ids)]

                # Удаляем дубли (shape_id + shape_pt_sequence)
                if not filtered_shapes.empty:
                    filtered_shapes = filtered_shapes.drop_duplicates(
                        subset=['shape_id', 'shape_pt_sequence']
                    )

                if not removed_shapes.empty:
                    removed_shapes = removed_shapes.drop_duplicates(
                        subset=['shape_id', 'shape_pt_sequence']
                    )

                filtered_shapes.to_csv(
                    os.path.join(self.output_path, 'shapes.txt'),
                    index=False
                )
                removed_shapes.to_csv(
                    os.path.join(self.excluded_data_path, 'shapes.txt'),
                    index=False
                )


            
            # --- STOP TIMES ---
            if self.verify_break():
                return 0
            if self.IN_QGIS:
                self.parent.progressBar.setValue(2)
                self.parent.setMessage("Deleting lines from GTFS ('stop_times.txt') ...")
                QApplication.processEvents()

            st_path = os.path.join(self.gtfs_path, 'stop_times.txt')
            st_iter = pd.read_csv(st_path, dtype={'trip_id': str, 'stop_id': str}, chunksize=200000)

            keep_trip_ids = set(filtered_trips['trip_id'])

            out_f_path = os.path.join(self.output_path, 'stop_times.txt')
            out_e_path = os.path.join(self.excluded_data_path, 'stop_times.txt')

            first = True

            with open(out_f_path, 'w', newline='') as out_f, \
                open(out_e_path, 'w', newline='') as out_e:

                for chunk in st_iter:
                    if self.verify_break():
                        return 0  # файлы всё равно закроются автоматически

                    mask = chunk['trip_id'].isin(keep_trip_ids)

                    f_chunk = chunk[mask]
                    e_chunk = chunk[~mask]

                    f_chunk.to_csv(out_f, index=False, header=first)
                    e_chunk.to_csv(out_e, index=False, header=first)

                    first = False
                    if self.IN_QGIS:
                        QApplication.processEvents()

    

            # --- STOPS ---
            if self.verify_break():
                return 0
            if self.IN_QGIS:
                self.parent.progressBar.setValue(3)
                self.parent.setMessage("Deleting lines from GTFS ('stops.txt') ...")
                QApplication.processEvents()
            stops_df = pd.read_csv(os.path.join(self.gtfs_path, 'stops.txt'),
                                   dtype={'stop_id': str})

            f_stop_ids = pd.read_csv(os.path.join(self.output_path, 'stop_times.txt'),
                                     usecols=['stop_id'], dtype={'stop_id': str})['stop_id'].unique()

            e_stop_ids = pd.read_csv(os.path.join(self.excluded_data_path, 'stop_times.txt'),
                                     usecols=['stop_id'], dtype={'stop_id': str})['stop_id'].unique()

            stops_df[stops_df['stop_id'].isin(f_stop_ids)].to_csv(
                os.path.join(self.output_path, 'stops.txt'), index=False)

            stops_df[stops_df['stop_id'].isin(e_stop_ids)].to_csv(
                os.path.join(self.excluded_data_path, 'stops.txt'), index=False)
            
            
            # --- CALENDAR ---
            if self.verify_break():
                return 0
            if self.IN_QGIS:
                self.parent.progressBar.setValue(4)
                self.parent.setMessage("Deleting lines from GTFS ('calendar.txt') ...")
                QApplication.processEvents()
            active_f_services = filtered_trips['service_id'].unique()
            active_e_services = removed_trips['service_id'].unique()

            for file in ['calendar.txt', 'calendar_dates.txt']:
                p = os.path.join(self.gtfs_path, file)
                if os.path.exists(p):
                    c_df = pd.read_csv(p, dtype={'service_id': str})
                    c_df[c_df['service_id'].isin(active_f_services)].to_csv(
                        os.path.join(self.output_path, file), index=False)
                    c_df[c_df['service_id'].isin(active_e_services)].to_csv(
                        os.path.join(self.excluded_data_path, file), index=False)
            
            if self.IN_QGIS:  
                QApplication.processEvents()
                self.parent.progressBar.setValue(5)      

        except Exception as e:
            print(f"Error: {e}")
            return 0

        return 1

    
if __name__ == "__main__":
   
    #parent, gtfs_path, output_path=None, excluded_data_path=None, exclude_ids_list=None
    src = r'c:\doc\Igor\GIS\36_routes_26POI\GTFS_2025+36r'
    out = r'c:\doc\Igor\GIS\36_routes_26POI\GTFS_2025+36r-208r'
    excluded_data_path = r'c:\doc\Igor\GIS\36_routes_26POI\GTFS_2025+36r-208r\exclude'
    #list = [10276, 10374, 10375, 10965, 13428, 13429, 13760, 13761, 13762, 13763, 14025, 16077, 16304, 16305, 16352, 16353, 16910, 18605, 18632, 18770, 19090, 19091, 19594, 19687, 21188, 21189, 22196, 2240, 2242, 2246, 2248, 2255, 2256, 2259, 2261, 2262, 2263, 2265, 2267, 2268, 2270, 2272, 2273, 2275, 2276, 2277, 2278, 2280, 2287, 2294, 2296, 2299, 2312, 2319, 2320, 2323, 2324, 2326, 2327, 2328, 2332, 23397, 23398, 23399, 23400, 2358, 23595, 23596, 23597, 23598, 23604, 2362, 2369, 2379, 23911, 23916, 23917, 23918, 23919, 23926, 23927, 23991, 23992, 24047, 2415, 2417, 2419, 24224, 2428, 2429, 2444, 2449, 2450, 2454, 2457, 2458, 2460, 2466, 2467, 24798, 24799, 2494, 2495, 2502, 2504, 2508, 2509, 2512, 2513, 2517, 2519, 2524, 2528, 2530, 2535, 2538, 25407, 25408, 2542, 2544, 25628, 25955, 25956, 25957, 25958, 26005, 26007, 26008, 26010, 26615, 26616, 26617, 26618, 26983, 26984, 27069, 27081, 27082, 27083, 27084, 2711, 2712, 27462, 27463, 27901, 27902, 28099, 28100, 2813, 2815, 2816, 2817, 2818, 2819, 2820, 2821, 2822, 2825, 2829, 2830, 2831, 2836, 2837, 28384, 28385, 28386, 28387, 28388, 2840, 2841, 2842, 2843, 2844, 2845, 2846, 2847, 2848, 2849, 2850, 2851, 2853, 2854, 2855, 2856, 2859, 2861, 2862, 2871, 28854, 28855, 28856, 2887, 28877, 2888, 2889, 2890, 2891, 2892, 2893, 2894, 2895, 2896, 2897, 2898, 2899, 2900, 2901, 2902, 2904, 2905, 2906, 2907, 2908, 2909, 2910, 2911, 2912, 2913, 2914, 2915, 29161, 29162, 2917, 2919, 2920, 2921, 2922, 2923, 2926, 2934, 2948, 2949, 2950, 2951, 2959, 2960, 2961, 2963, 30810, 31299, 3147, 3266, 3277, 3397, 35324, 35325, 35326, 36421, 36422, 36425, 36426, 36477, 36478, 36503, 36504, 36593, 36594, 37741, 37742, 39162, 39163, 39164, 39166, 39167, 39168, 39169, 39170, 39171, 39172, 39173, 39174, 39175, 39176, 39177, 39178, 39179, 39180, 39181, 39182, 39183, 39187, 39188, 39189, 39190, 39191, 39193, 39194, 39195, 39196, 39280, 39281, 39282, 39283, 39312, 39313, 39629, 39630, 5230, 975, 9775, 9779, 9780, 9781, 9783, 9785, 9788, 9791, 9792, 9793, 9794, 9802, 9803, 9804, 9805, 9806, 9808, 9809, 9811, 9813, 9821, 9822, 9823, 9824, 9833, 9834, 9835, 9836, 9838, 9842, 9844, 9845, 9847, 9853, 9854, 9855, 9857, 9859, 9860, 9861, 9863, 9864, 9866, 9867, 9872, 9873, 9877, 9880, 991, 993]
    #list = [36504,2444,2519,2934,35325,2261,9824,23598,30810,2270,2888,2842,35326,9880,2816,2851,2844,2840,2898,2913,2836,2905,2923,36477,23919,2906,10276,2711,9806,2272,2273,9803,2963,9794,9809,2415,2379,2530,2419,14025,2323,2256,2327,29246,26010,26008,26005,9861,9863,9864,2960,3277,3397,2853,2830,2829,2897,2854,2922,21188,2919,2892,2294,9859,2908,2889,26615,26616,2467,2902,2847,2846,24047,25408,2495,16077,28384,2912,9823,9811,2460,2901,23918,23400,3147,2267,2920,2917,2328,2512,2240,2263,2891,36503,25955,2504,2494,9775,9854,2508,2959,28855,28854,2275,2843,27463,27462,9873,9838,9835,2712,9783,9781,2815,2825,9866,9867,28386,28385,36426,2848,9822,27082,25957,27084,27083,9780,2899,2517,2287,2262,2817,2259,2450,2862,2850,2820,2819,2926,23597,2871,2299,23911,23926,2813,2818,9802,26618,26617,2538,2841,2502,2910,2915,2914,2845,2822,2896,2894,2911,2837,2369,2319,2296,24224,19091,2320,10965,2855,37657,2524,9821,2509,25958,9779,2821,2528,9793,9834,9833,9877,9872,9860,36425,2324,35324,2893,2849,2544,2542,9808,36478,28856,28100,28099,2535,9843,2276,26007,9836,2293,2856,16076,9776,2458,2457,27081,2332,2859,2466,23927,9853,2277,21189,2265,23399,9857,9855,2358,9792,9791,2255,2326,2909,26984,26983,2511,2510,9807,2454,9785,9788,23603,25956,2242,2861,25407,9813,23398,23397,28387,2248,27069,2246,9842,2312,2961,28388]
    #list = [10276,10965,14025,16076,16077,19091,2240,2242,2246,2248,2255,2256,2259,2261,2262,2263,2265,2267,2287,2293,2294,2312,2323,2324,23397,23398,23399,23400,2358,23597,23598,23603,23911,23918,23919,24047,2415,2419,24224,2466,2467,2494,2495,2502,2504,2508,2509,2510,2511,2512,2517,2519,2524,2528,2530,2535,2538,25407,25408,2542,2544,25957,25958,26005,26007,26008,26010,26615,26616,26617,26618,27069,27081,27082,27083,27084,28099,28100,2813,2815,2816,2817,2818,2819,2820,2821,2822,2825,2829,2830,2836,2837,28384,28385,28386,28387,28388,2840,2841,2842,2843,2844,2845,2846,2847,2848,2849,2850,2851,2853,2854,2855,2856,2859,2861,2862,2871,28854,28855,28856,2888,2889,2891,2892,2893,2894,2896,2897,2898,2899,2901,2902,2905,2906,2908,2909,2910,2911,2912,2913,2914,2915,2917,2919,2920,2922,2923,2926,2934,2959,2960,30810,3147,3277,35324,37657,9775,9776,9779,9780,9791,9792,9793,9794,9806,9807,9859,9860]
    #list = [10276,10965,14025,16076,16077,19091,2240,2242,2246,2248,2255,2256,2259,2261,2262,2263,2265,2267,2270,2272,2273,2287,2293,2294,2312,2323,2324,2326,2327,23397,23398,23399,23400,2358,23597,23598,23603,23911,23918,23919,23926,23927,24047,2415,2419,24224,2466,2467,2494,2495,2502,2504,2508,2509,2510,2511,2512,2517,2519,2524,2528,2530,2535,2538,25407,25408,2542,2544,25957,25958,26005,26007,26008,26010,26615,26616,26617,26618,26983,26984,27069,27081,27082,27083,27084,28099,28100,2813,2815,2816,2817,2818,2819,2820,2821,2822,2825,2829,2830,2836,2837,28384,28385,28386,28387,28388,2840,2841,2842,2843,2844,2845,2846,2847,2848,2849,2850,2851,2853,2854,2855,2856,2859,2861,2862,2871,28854,28855,28856,2888,2889,2891,2892,2893,2894,2896,2897,2898,2899,2901,2902,2905,2906,2908,2909,2910,2911,2912,2913,2914,2915,2917,2919,2920,2922,2923,2926,2934,2959,2960,30810,3147,3277,3397,35324,36503,36504,37657,9775,9776,9779,9780,9791,9792,9793,9794,9806,9807,9833,9834,9835,9836,9838,9853,9854,9855,9857,9859,9860]
    list = [10276,10965,14025,16076,16077,19091,21188,21189,2240,2242,2246,2248,2255,2256,2259,2261,2262,2263,2265,2267,2270,2272,2273,2287,2293,2294,2312,2323,2324,2326,2327,23397,23398,23399,23400,2358,23597,23598,23603,2369,2379,23911,23918,23919,23926,23927,24047,2415,2419,24224,2466,2467,2494,2495,2502,2504,2508,2509,2510,2511,2512,2517,2519,2524,2528,2530,2535,2538,25407,25408,2542,2544,25957,25958,26005,26007,26008,26010,26615,26616,26617,26618,26983,26984,27069,27081,27082,27083,27084,2711,2712,28099,28100,2813,2815,2816,2817,2818,2819,2820,2821,2822,2825,2829,2830,2836,2837,28384,28385,28386,28387,28388,2840,2841,2842,2843,2844,2845,2846,2847,2848,2849,2850,2851,2853,2854,2855,2856,2859,2861,2862,2871,28854,28855,28856,2888,2889,2891,2892,2893,2894,2896,2897,2898,2899,2901,2902,2905,2906,2908,2909,2910,2911,2912,2913,2914,2915,2917,2919,2920,2922,2923,2926,2934,2959,2960,2961,2963,30810,3147,3277,3397,35324,36477,36478,36503,36504,37657,9775,9776,9779,9780,9791,9792,9793,9794,9806,9807,9823,9824,9833,9834,9835,9836,9838,9842,9843,9853,9854,9855,9857,9859,9860,9861,9863,9864,9866,9867]
    
    cleaner = GTFSExcludeRoutes(
        parent = None,
        gtfs_path = src, 
        output_path = out,
        excluded_data_path = excluded_data_path,
        exclude_ids_list = list
    )
    run_ok = cleaner.run()

