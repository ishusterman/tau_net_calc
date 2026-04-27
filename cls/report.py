from common import seconds_to_time

# for type_protokol = 1
def make_protocol_summary(SOURCE,
                          destinations,
                          dictInput,                          
                          grades,
                          attribute_dict,                          
                          set_stops,
                          field,
                          short_result = None
                          ):

    """"
    example
    nearby_buildings_from_start [('1049165', 14),
    list_buildings_from_start {'1049120', '1235069', 
    set_stops {'8362', '14775', '26149', '34636',
    destinations {1048576, 1048577, 1048578, 1048579, 1048580, 1048581, 1048582, 1048583, 1048584, 1048585, 104858
    SOURCE type <'str'>
    dest type <class 'str'>
    """

    SOURCE_int = int(SOURCE)
    time_grad = grades
    # [[-1,0], [0,10],[10,20],[20,30],[30,40],[40,50],[50,61] ]

    counts = {x: 1 for x in range(0, len(time_grad))}  # counters for grades - (1-{source,source})
    agrregates = {x: attribute_dict.get(SOURCE_int, 0) for x in range(0, len(time_grad))}

    if short_result is not None: 
        if field == "nbldg":
            short_result[(SOURCE_int, SOURCE_int)] = 0
        
    for dest, info in dictInput.items():

            if dest in set_stops:
                continue

            dest_int = int (dest)

            if dest_int not in destinations:
                continue

            #if str(SOURCE) == str(dest):
            #    continue
            time_to_dest = int(info[1])
            
            for i in range(0, len(time_grad)):
                grad = time_grad[i]

                if time_to_dest <= grad[1]*60:
                    counts[i] = counts[i] + 1
                    
                    if field != "nbldg":
                        agrregates[i] = agrregates[i] + \
                            attribute_dict.get(dest_int, 0)
            
            if short_result is not None: 
                if field == "nbldg":
                    short_result[(SOURCE_int, dest_int)] = time_to_dest

    
    row = str(SOURCE)
    if field == "nbldg":
            Total = counts[len(time_grad)-1]
    if field != "nbldg":
            Total = agrregates[len(time_grad)-1]

    for i in range(0, len(time_grad)):
            row = f'{row},{counts[i]}'
            if field != "nbldg":
                row = f'{row},{agrregates[i]}'

    data_body = [row.split(',') + [str(Total)]]

    return data_body

# for type_protokol =2
def make_protocol_detailed(raptor_mode,
                           D_TIME,
                           dictInput,                           
                           timetable_mode,                           
                           set_stops,
                           SOURCE,                           
                           short_result = None
                           ):
    
    """"
    example
    nearby_buildings_from_start [('1049165', 14),
    list_buildings_from_start {'1049120', '1235069', 
    set_stops {'8362', '14775', '26149', '34636',
    destinations {1048576, 1048577, 1048578, 1048579, 1048580, 1048581, 1048582, 1048583, 1048584, 1048585, 104858
    SOURCE type <'str'>
    orig_dest type <class 'str'>
    """
    
    sep = ","
    stop_symbol = "s:"
    rows_to_write = []
    
    if True:

        SOURCE_int = int(SOURCE)

        start_time = seconds_to_time(D_TIME)
        
        if True: #SOURCE_int in destinations:
            if raptor_mode == 1:
                row = f'{SOURCE}{sep}{start_time}{sep}0{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}0{sep}{SOURCE}{sep}{start_time}{sep}0{sep}0'
            else:
                row = f'{SOURCE}{sep}{start_time}{sep}0{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}\
{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}{sep}0{sep}{SOURCE}{sep}{start_time}{sep}{start_time}{sep}0{sep}0'

            rows_to_write.append(row)
            if short_result is not None:
                short_result[(SOURCE_int, SOURCE_int)] = 0        
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
                wait1_time = ""
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

                    legs_counter = legs_counter + 1
                    last_leg = leg                    
                    if leg[0] == 'walking':
                        walking_time_sec = leg[3]
                        if ride_counter == 0:
                            SOURCE_REV = leg[1]  # for backward algo                            
                            walk1_time = walking_time_sec
                            walk1_arriving_time = leg[4] + leg[3]
                        elif ride_counter == 1:                            
                            walk2_time = walking_time_sec                            
                        elif ride_counter == 2:
                            walk3_time = walking_time_sec                            
                        elif ride_counter == 3:
                            walk4_time = walking_time_sec
                        if start_time is None:
                            start_time = leg[4]

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

                            ride1_time = first_bus_arrival_time - first_boarding_time

                            if last_leg_type == "walking":
                                wait1_time = first_boarding_time - walk1_arriving_time
                            else:
                                if raptor_mode == 1:
                                    wait1_time = first_boarding_time - D_TIME
                                else:
                                    wait1_time = first_boarding_time - start_time

                            line1_id = leg[4]

                        elif not second_bus_leg_found:
                            # in this leg - second leg is bus, saving params for report
                            if start_time is None:
                                start_time = leg[0]
                            second_bus_leg_found = True
                            ride_counter = 2
                            second_boarding_time = leg[0]
                            ssecond_boarding_time = seconds_to_time(second_boarding_time)
                            second_boarding_stop = leg[1]

                            second_bus_arrive_stop = leg[2]
                            second_bus_arrival_time = leg[3]
                            ssecond_bus_arrival_time = seconds_to_time(second_bus_arrival_time)

                            if last_leg_type == "walking":
                                wait2_time = second_boarding_time - first_bus_arrival_time - walk2_time
                            else:
                                wait2_time = second_boarding_time - first_bus_arrival_time

                            line2_id = leg[4]

                            ride2_time = second_bus_arrival_time - second_boarding_time

                        else:  # 3-rd bus found
                            third_bus_leg_found = True
                            # in this leg - third leg is bus, saving params for report
                            if start_time is None:
                                start_time = leg[0]
                            ride_counter = 3
                            third_boarding_time = leg[0]
                            sthird_boarding_time = seconds_to_time(third_boarding_time)
                            third_boarding_stop = leg[1]
                            third_bus_arrive_stop = leg[2]
                            third_bus_arrival_time = leg[3]
                            sthird_bus_arrival_time = seconds_to_time(third_bus_arrival_time)

                            if last_leg_type == "walking":
                                wait3_time = third_boarding_time - second_bus_arrival_time - walk3_time
                            else:
                                wait3_time = third_boarding_time - second_bus_arrival_time

                            line3_id = leg[4]

                            ride3_time = third_bus_arrival_time - third_boarding_time

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
                if not last_bus_leg is None:                    
                    sfirst_boarding_stop = f'{stop_symbol}{first_boarding_stop}'
                    sfirst_arrive_stop = f'{stop_symbol}{first_bus_arrive_stop}'

                    sfirst_boarding_time = seconds_to_time(first_boarding_time)
                    sfirst_arrive_time = seconds_to_time(first_bus_arrival_time)

                    if second_bus_leg_found:                        
                        ssecond_boarding_stop = f'{stop_symbol}{second_boarding_stop}'
                        ssecond_arrive_stop = f'{stop_symbol}{second_bus_arrive_stop}'

                    if third_bus_leg_found:                        
                        sthird_boarding_stop = f'{stop_symbol}{third_boarding_stop}'
                        sthird_arrive_stop = f'{stop_symbol}{third_bus_arrive_stop}'

                # Define what was mode of the last leg:
                # here leg is the last leg that was in previous cycle
                Destination = leg[2]

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

                if raptor_mode == 1:                    
                    arrival_time = last_leg[4] + last_leg[3]
                    sarrival_time = seconds_to_time(arrival_time)

                if raptor_mode == 2:
                    if not timetable_mode:
                        if len(journey) > 1:
                            sarrival_time = seconds_to_time(journey[-2][3]+journey[-1][3])
                        else:
                            sarrival_time = seconds_to_time(D_TIME)
                    else:
                        if len(journey) > 1:
                            sarrival_time = seconds_to_time(journey[-1][3] + journey[-1][4])
                        else:
                            sarrival_time = seconds_to_time(D_TIME)
                      
                if raptor_mode == 1:
      
                    if (orig_dest) in set_stops:
                        continue

                    orig_dest_int = int(orig_dest)

                    row = f'{SOURCE}{sep}{seconds_to_time(D_TIME)}{sep}{walk1_time}{sep}{sfirst_boarding_stop}\
{sep}{wait1_time}{sep}{sfirst_boarding_time}{sep}{line1_id}{sep}{ride1_time}{sep}{sfirst_arrive_stop}{sep}{sfirst_arrive_time}\
{sep}{walk2_time}{sep}{ssecond_boarding_stop}{sep}{wait2_time}{sep}{ssecond_boarding_time}{sep}{line2_id}{sep}{ride2_time}{sep}{ssecond_arrive_stop}{sep}{ssecond_bus_arrival_time}\
{sep}{walk3_time}{sep}{sthird_boarding_stop}{sep}{wait3_time}{sep}{sthird_boarding_time}{sep}{line3_id}{sep}{ride3_time}{sep}{sthird_arrive_stop}{sep}{sthird_bus_arrival_time}\
{sep}{dest_walk_time}{sep}{orig_dest}{sep}{sarrival_time}{sep}{legs}{sep}{duration}'
                                        
                    if short_result is not None:
                        short_result[(SOURCE_int, orig_dest_int)] = int(duration)

                else:

                    if (SOURCE_REV) in set_stops:
                        continue

                    SOURCE_REV_int = int(SOURCE_REV)

                    row = f'{SOURCE_REV}{sep}{seconds_to_time(start_time)}{sep}{walk1_time}{sep}{sfirst_boarding_stop}\
{sep}{wait1_time}{sep}{sfirst_boarding_time}{sep}{line1_id}{sep}{ride1_time}{sep}{sfirst_arrive_stop}{sep}{sfirst_arrive_time}\
{sep}{walk2_time}{sep}{ssecond_boarding_stop}{sep}{wait2_time}{sep}{ssecond_boarding_time}{sep}{line2_id}{sep}{ride2_time}{sep}{ssecond_arrive_stop}{sep}{ssecond_bus_arrival_time}\
{sep}{walk3_time}{sep}{sthird_boarding_stop}{sep}{wait3_time}{sep}{sthird_boarding_time}{sep}{line3_id}{sep}{ride3_time}{sep}{sthird_arrive_stop}{sep}{sthird_bus_arrival_time}\
{sep}{dest_walk_time}{sep}{SOURCE}{sep}{sarrival_time}{sep}{seconds_to_time(D_TIME)}{sep}{legs}{sep}{duration}'
                    
                    if short_result is not None:
                        short_result[(SOURCE_int, SOURCE_REV_int)] = int(duration)
                rows_to_write.append(row)
    
    data_body = [row.split(',') for row in rows_to_write]
  
    return  data_body
