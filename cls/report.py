import os
import pandas as pd
from common import seconds_to_time

# for type_protokol = 1
def make_protocol_summary(SOURCE,
                          dictInput,
                          f,
                          grades,
                          attribute_dict,
                          nearby_buildings_from_start,
                          list_buildings_from_start,
                          set_stops,
                          field
                          ):

    
    time_grad = grades
    # [[-1,0], [0,10],[10,20],[20,30],[30,40],[40,50],[50,61] ]
    counts = {x: 0 for x in range(0, len(time_grad))}  # counters for grades
    # counters for agrregates
    agrregates = {x: 0 for x in range(0, len(time_grad))}

    
    with open(f, 'a') as filetowrite:
        for dest, info in dictInput.items():

            if str(dest) in set_stops:
                continue

            if str(dest) in list_buildings_from_start:
                continue

            time_to_dest = round(int(info[1]))
            
            for i in range(0, len(time_grad)):
                grad = time_grad[i]

                if time_to_dest <= grad[1]*60:
                    counts[i] = counts[i] + 1
                    # file2.write(f'{str(dest)}\n')

                    if field != "bldg":
                        agrregates[i] = agrregates[i] + \
                            attribute_dict.get(int(dest), 0)

                        

        # counts[0] = counts[0] + 1 # for case time_item = 0 (from source to source)

        # add build to build to var counts
        for build_item, time_item in nearby_buildings_from_start:
            for i in range(0, len(time_grad)):
                grad = time_grad[i]

                if time_item <= grad[1]*60:
                    counts[i] = counts[i] + 1
                    
                    if field != "bldg":
                        agrregates[i] = agrregates[i] + \
                            attribute_dict.get(int(build_item), 0)

        row = str(SOURCE)
        if field == "bldg":
            Total = counts[len(time_grad)-1]
        if field != "bldg":
            Total = agrregates[len(time_grad)-1]

        for i in range(0, len(time_grad)):
            row = f'{row},{counts[i]}'
            if field != "bldg":
                row = f'{row},{agrregates[i]}'

        filetowrite.write(f'{row},{Total}\n')

# for type_protokol =2
def make_protocol_detailed(raptor_mode,
                           D_TIME,
                           dictInput,
                           protocol_full_path,
                           timetable_mode,
                           nearby_buildings_from_start,
                           list_buildings_from_start,
                           set_stops,
                           SOURCE,
                           short_result = None
                           ):

    sep = ","
    stop_symbol = "s:"
    rows_to_write = []
    #f = protocol_full_path
        
    #with open(f, 'a') as filetowrite:
    if True:

        start_time = seconds_to_time(D_TIME)

        if raptor_mode == 1:
                    row = f'{SOURCE}{sep}{start_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}0{sep}{SOURCE}{sep}{start_time}{sep}0{sep}0'
        else:
                    row = f'{SOURCE}{sep}{start_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}0{sep}{SOURCE}{sep}{start_time}{sep}{start_time}{sep}0{sep}0'

        
        #filetowrite.write(row + "\n")
        rows_to_write.append(row)
        if short_result is not None:
            short_result[(SOURCE, SOURCE)] = 0

        for build, dist in nearby_buildings_from_start:

            if raptor_mode == 1:
                        finish_time = seconds_to_time(D_TIME+dist)
                        row = f'{SOURCE}{sep}{start_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{dist}{sep}{build}{sep}{finish_time}{sep}0{sep}{dist}'
            else:
                        finish_time = seconds_to_time(D_TIME-dist)
                        row = f'{build}{sep}{finish_time}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{dist}{sep}{SOURCE}{sep}{start_time}{sep}{start_time}{sep}0{sep}{dist}'

            if str(build) != str(SOURCE):
                #filetowrite.write(row + "\n")
                rows_to_write.append(row)
                if short_result is not None:
                    short_result[(SOURCE, build)] = int(dist)

        # dictInput - dict from testRaptor
        # every item dictInput : dest - key, info - value

        for dest, info in dictInput.items():

            SOURCE = info[0]
            duration = info[1]
            pareto_set = info[2]
            transfers = info[3]
            legs = transfers + 1


            '''
    Examle pareto_set =
    [(0, [('walking', 2003, 24206.0, Timedelta('0 days 00:02:47'),Timestamp('2023-06-30 08:37:13')), 
    (Timestamp('2023-06-30 08:36:59'), 24206, 14603, Timestamp('2023-06-30 08:33:36'), '3150_67'), 
    ('walking', 14603, 1976.0, Timedelta('0 days 00:02:03.300000'), Timestamp('2023-06-30 08:31:32.700000'))])]    
    '''     

            if pareto_set is None or dest is None:
                continue

            '''
    Examle jorney
    [('walking', 2003, 24206.0, Timedelta('0 days 00:02:47'), Timestamp('2023-06-30 08:37:13')), 
    (Timestamp('2023-06-30 08:36:59'), 24206, 14603, Timestamp('2023-06-30 08:33:36'), '3150_67'), 
    ('walking', 14603, 1976.0, Timedelta('0 days 00:02:03.300000'), Timestamp('2023-06-30 08:31:32.700000'))]
    '''

            # for journey in pareto_set: #each journey is array, legs are its elements
            if True:

                journey = pareto_set

                # run inversion jorney also raptor_mode = 1
                
                if raptor_mode == 2:
                    # inversion row
                    journey = journey[::-1]
                    # inversion inside every row

                    journey = [(tup[0], tup[2], tup[1], tup[3], tup[4]) if not isinstance(tup[0], int) else
                               tup[:4][::-1] +
                               (tup[4],) if isinstance(tup[0], int) else tup
                               for tup in journey
                               ]

                if raptor_mode == 1:

                    journey = [(tup[0], tup[1], tup[2], tup[3], tup[4] - tup[3])
                               if tup[0] == 'walking' else tup for tup in journey]

                last_bus_leg = None
                last_leg = None
                first_boarding_stop = ""  # BStop1_ID
                first_boarding_time = ""
                first_bus_arrive_stop = ""  # AStop1_ID
                first_bus_arrival_time = ""

                second_boarding_stop = ""  # BStop2_ID
                second_boarding_time = ""
                second_bus_arrive_stop = ""  # AStop2_ID
                second_bus_arrival_time = ""

                third_boarding_stop = ""  # BStop3_ID
                third_boarding_time = ""
                third_bus_arrive_stop = ""  # AStop3_ID
                third_bus_arrival_time = ""

                sfirst_boarding_time = " "
                sfirst_arrive_time = " "
                ssecond_boarding_time = ""
                ssecond_bus_arrival_time = ""
                sthird_boarding_time = ""
                sthird_bus_arrival_time = ""

                first_bus_leg_found = False
                second_bus_leg_found = False
                third_bus_leg_found = False

                walk1_time = ""  # walk time from orgin to first bus stop or to destination if no buses
                walk1_arriving_time = ""  # I need it to compute wait1_time
                wait1_time = 0
                line1_id = ""  # number of first route (or trip)
                ride1_time = ""

                walk2_time = ""  # from 1 bus alightning to second bus boarding

                wait2_time = ""  # time between arriving to second bus stop and boarding to the bus
                line2_id = ""  # number of second route (or trip)
                ride2_time = ""

                walk3_time = ""  # from 2 bus alightning to 3 bus boarding

                wait3_time = ""  # time between arriving to 3 bus stop and boarding to the bus
                line3_id = ""  # number of 3 route (or trip)
                ride3_time = ""

                walk4_time = ""
                dest_walk_time = ""  # walking time  to destination

                legs_counter = 0
                last_leg_type = ""
                ride_counter = 0
                walking_time_sec = 0

                '''
         Examlpe leg
          ('walking', 2003, 24206.0, Timedelta('0 days 00:02:47'), Timestamp('2023-06-30 08:37:13'))
          or
          (Timestamp('2023-06-30 08:36:59'), 24206, 14603, Timestamp('2023-06-30 08:33:36'), '3150_67')


         '''
                start_time = None

                for leg in journey:

                    legs_counter = legs_counter+1
                    last_leg = leg
                    #  here counting walk(n)_time if leg[0] == 'walking
                    #  !!!!! why can walk1_time != "" !!!!!!!!!!!! why verify?
                    if leg[0] == 'walking':

                        walking_time_sec = round(leg[3], 1)
                        if ride_counter == 0:
                            SOURCE_REV = leg[1]  # for backward algo
                            if walk1_time == "":
                                walk1_time = walking_time_sec
                            else:
                                walk1_time = walk1_time + walking_time_sec

                            walk1_arriving_time = leg[4] + leg[3]
                        elif ride_counter == 1:
                            if walk2_time == "":
                                walk2_time = walking_time_sec
                            else:
                                walk2_time = walk2_time + walking_time_sec

                        elif ride_counter == 2:
                            if walk3_time == "":
                                walk3_time = walking_time_sec
                            else:
                                walk3_time = walk3_time + walking_time_sec

                            

                        elif ride_counter == 3:
                            if walk4_time == "":
                                walk4_time = walking_time_sec
                            else:
                                walk4_time = walk4_time + walking_time_sec
                           

                        if start_time is None:
                            start_time = leg[4]

                        # here finish counting walk1_time if leg[0] == 'walking
                    else:
                        if not first_bus_leg_found:
                            # in this leg - first leg is bus, saving params for report

                            if start_time is None:
                                start_time = leg[0]
                                SOURCE_REV = leg[1]  # for backward algo

                            first_bus_leg_found = True
                            ride_counter = 1
                            
                            first_boarding_time = leg[0]
                            first_boarding_stop = leg[1]
                            first_bus_arrive_stop = leg[2]
                            first_bus_arrival_time = leg[3]

                            ride1_time = round(
                                (first_bus_arrival_time - first_boarding_time), 1)

                            if last_leg_type == "walking":

                                wait1_time = round((first_boarding_time - walk1_arriving_time), 1)
                            else:

                                if raptor_mode == 1:

                                    wait1_time = round((first_boarding_time - D_TIME), 1)
                                else:

                                    wait1_time = round((first_boarding_time - start_time), 1)

                            line1_id = leg[4]

                        elif not second_bus_leg_found:
                            # in this leg - second leg is bus, saving params for report
                            if start_time is None:
                                start_time = leg[0]
                            second_bus_leg_found = True
                            ride_counter = 2
                            second_boarding_time = leg[0]
                            ssecond_boarding_time = seconds_to_time(
                                second_boarding_time)
                            second_boarding_stop = leg[1]

                            second_bus_arrive_stop = leg[2]
                            second_bus_arrival_time = leg[3]
                            ssecond_bus_arrival_time = seconds_to_time(
                                second_bus_arrival_time)

                            if last_leg_type == "walking":

                                wait2_time = round(
                                    (second_boarding_time - first_bus_arrival_time - walk2_time), 1)
                            else:

                                wait2_time = round(
                                    (second_boarding_time - first_bus_arrival_time), 1)

                            line2_id = leg[4]

                            ride2_time = round(
                                (second_bus_arrival_time - second_boarding_time), 1)

                        else:  # 3-rd bus found
                            third_bus_leg_found = True
                            # in this leg - third leg is bus, saving params for report
                            if start_time is None:
                                start_time = leg[0]
                            ride_counter = 3
                            third_boarding_time = leg[0]
                            sthird_boarding_time = seconds_to_time(
                                third_boarding_time)
                            third_boarding_stop = leg[1]
                            third_bus_arrive_stop = leg[2]
                            third_bus_arrival_time = leg[3]
                            sthird_bus_arrival_time = seconds_to_time(
                                third_bus_arrival_time)

                            if last_leg_type == "walking":

                                wait3_time = round((third_boarding_time - second_bus_arrival_time - walk3_time), 1)
                            else:

                                wait3_time = round((third_boarding_time - second_bus_arrival_time), 1)

                            line3_id = leg[4]

                            ride3_time = round((third_bus_arrival_time - third_boarding_time), 1)

                        last_bus_leg = leg

                    last_leg_type = leg[0]  # in current journey

                    # this legs finish, postprocessing this journey
                if last_leg_type == "walking":
                    if walk4_time != "":
                        dest_walk_time = walk4_time
                        walk4_time = ""
                    elif walk3_time != "":
                        dest_walk_time = walk3_time
                        walk3_time = ""
                    elif walk2_time != "":
                        dest_walk_time = walk2_time
                        walk2_time = ""
                    elif walk1_time != "":
                        dest_walk_time = walk1_time
                        walk1_time = ""

                    # end of cycle by legs
                    # Calculate waiting time before boarding

                    # If first_bus_leg and last_bus_leg are found
                    # they may be the same leg
                    # get boarding_time from first_bus_leg
                sfirst_boarding_stop = ""
                sfirst_arrive_stop = ""
                
                ssecond_boarding_stop = ""
                ssecond_arrive_stop = ""
                
                sthird_boarding_stop = ""
                sthird_arrive_stop = ""
                
                # last_bus_leg - last leg of current jorney
                if not last_bus_leg is None:  # work forever?
                    first_boarding_stop_orig = first_boarding_stop
                    first_bus_arrive_stop_orig = first_bus_arrive_stop
                    sfirst_boarding_stop = f'{stop_symbol}{first_boarding_stop_orig}'
                    sfirst_arrive_stop = f'{stop_symbol}{first_bus_arrive_stop_orig}'

                    sfirst_boarding_time = seconds_to_time(first_boarding_time)
                    sfirst_arrive_time = seconds_to_time(
                        first_bus_arrival_time)

                    if second_bus_leg_found:
                        second_boarding_stop_orig = second_boarding_stop
                        second_bus_arrive_stop_orig = second_bus_arrive_stop
                        ssecond_boarding_stop = f'{stop_symbol}{second_boarding_stop_orig}'
                        ssecond_arrive_stop = f'{stop_symbol}{second_bus_arrive_stop_orig}'

                    if third_bus_leg_found:
                        third_boarding_stop_orig = third_boarding_stop
                        third_bus_arrive_stop_orig = third_bus_arrive_stop
                        sthird_boarding_stop = f'{stop_symbol}{third_boarding_stop_orig}'
                        sthird_arrive_stop = f'{stop_symbol}{third_bus_arrive_stop_orig}'

                # Define what was mode of the last leg:
                # here leg is the last leg that was in previous cycle
                Destination = leg[2]

                if last_leg[0] == 'walking':

                    arrival_time = last_leg[4] + last_leg[3]
                else:

                    arrival_time = last_leg[3]

                sarrival_time = seconds_to_time(arrival_time)

                orig_dest = Destination

                if walk1_time == "":
                    walk1_time = 0

                if walk2_time == "" and ssecond_boarding_stop != "":
                    walk2_time = 0

                if walk3_time == "" and sthird_boarding_stop != "":
                    walk3_time = 0

                if dest_walk_time == "":
                    dest_walk_time = 0

                
                if timetable_mode and raptor_mode == 1:
                    D_TIME = journey[0][4]

                if raptor_mode == 2:
                    if len(journey) > 1:
                        sarrival_time = seconds_to_time(
                            journey[-1][3] + journey[-1][4])
                    else:

                        if journey[0][0] == "walking":
                            sarrival_time = seconds_to_time(
                                journey[0][3] + journey[0][4])
                        else:
                            sarrival_time = seconds_to_time(journey[0][3])
                
                if raptor_mode == 1:
                    if orig_dest in list_buildings_from_start:
                        continue
                    if str(orig_dest) in set_stops:
                        continue

                    row = f'{SOURCE}{sep}{seconds_to_time(D_TIME)}{sep}{walk1_time}{sep}{sfirst_boarding_stop}\
{sep}{wait1_time}{sep}{sfirst_boarding_time}{sep}{line1_id}{sep}{ride1_time}{sep}{sfirst_arrive_stop}{sep}{sfirst_arrive_time}\
{sep}{walk2_time}{sep}{ssecond_boarding_stop}{sep}{wait2_time}{sep}{ssecond_boarding_time}{sep}{line2_id}{sep}{ride2_time}{sep}{ssecond_arrive_stop}{sep}{ssecond_bus_arrival_time}\
{sep}{walk3_time}{sep}{sthird_boarding_stop}{sep}{wait3_time}{sep}{sthird_boarding_time}{sep}{line3_id}{sep}{ride3_time}{sep}{sthird_arrive_stop}{sep}{sthird_bus_arrival_time}\
{sep}{dest_walk_time}{sep}{orig_dest}{sep}{sarrival_time}{sep}{legs}{sep}{duration}'
                                        
                    if short_result is not None:
                        short_result[(SOURCE, orig_dest)] = int(duration)

                else:

                    if SOURCE_REV in list_buildings_from_start:
                        continue
                    if str(SOURCE_REV) in set_stops:
                        continue
                    row = f'{SOURCE_REV}{sep}{seconds_to_time(start_time)}{sep}{walk1_time}{sep}{sfirst_boarding_stop}\
{sep}{wait1_time}{sep}{sfirst_boarding_time}{sep}{line1_id}{sep}{ride1_time}{sep}{sfirst_arrive_stop}{sep}{sfirst_arrive_time}\
{sep}{walk2_time}{sep}{ssecond_boarding_stop}{sep}{wait2_time}{sep}{ssecond_boarding_time}{sep}{line2_id}{sep}{ride2_time}{sep}{ssecond_arrive_stop}{sep}{ssecond_bus_arrival_time}\
{sep}{walk3_time}{sep}{sthird_boarding_stop}{sep}{wait3_time}{sep}{sthird_boarding_time}{sep}{line3_id}{sep}{ride3_time}{sep}{sthird_arrive_stop}{sep}{sthird_bus_arrival_time}\
{sep}{dest_walk_time}{sep}{SOURCE}{sep}{sarrival_time}{sep}{seconds_to_time(D_TIME)}{sep}{legs}{sep}{duration}'
                    
                    if short_result is not None:
                        short_result[(SOURCE, SOURCE_REV)] = int(duration)

                #filetowrite.write(row + "\n")
                rows_to_write.append(row)
    
    with open(protocol_full_path, 'a') as f:
        f.write('\n'.join(rows_to_write) + '\n')
   
    return 1

def make_service_area_report(file_path, alias):

    dtype_dict = {
        'Destination_ID': 'int',
        'Duration': 'int'      
    }

    df = pd.read_csv(file_path, dtype=dtype_dict)

    result = df.loc[df.groupby('Destination_ID')['Duration'].idxmin()]
    folder_name = os.path.dirname(file_path)
    filename = os.path.join(folder_name, f"{alias}_service_area.csv")

    result.to_csv(filename, index=False)
    return filename

