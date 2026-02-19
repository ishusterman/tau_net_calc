from RAPTOR.raptor_functions import *
from PyQt5.QtWidgets import QApplication
import numpy as np
from common import seconds_to_time


def raptor(SOURCE,
           D_TIME,
           MAX_TRANSFER,
           MIN_TRANSFER,
           change_time,
           routes_by_stop_dict,
           stops_dict,
           stoptimes_dict,
           footpath_dict,

           idx_by_route_stop_dict,
           Maximal_travel_time,
           MaxWalkDist1,
           MaxWalkDist2,
           MaxWalkDist3,
           MaxWaitTime,
           MaxWaitTimeTransfer,
           timetable_mode,
           MaxExtraTime,
           first_step = None
           ) -> list:
    
    list_stops = set()

    (marked_stop,
     marked_stop_dict,
     label,
     pi_label) = initialize_raptor(routes_by_stop_dict,
                                   SOURCE,
                                   MAX_TRANSFER
                                   )

    change_time_save = change_time

    label[0][SOURCE] = D_TIME
    Q = {}  # Format of Q is {route:stop index}
    roundsCount = MAX_TRANSFER + 1
    trans_info = -1

    MaxWalkDist1_time = np.int64(MaxWalkDist1)
    MaxWalkDist2_time = np.int64(MaxWalkDist2)
    MaxWalkDist3_time = np.int64(MaxWalkDist3)

    max_time = np.int64(D_TIME + Maximal_travel_time)
    TIME_START = D_TIME

    
    if timetable_mode:
        pass
        #MaxWaitTime = MaxExtraTime
        #max_time = np.int64(D_TIME + Maximal_travel_time + MaxExtraTime)

    
            
    if first_step is None:
                if trans_info == -1:
                    trans_info = footpath_dict.get(SOURCE, [])

                for i in trans_info:
                    (p_dash, to_pdash_time) = i
                    if not (label[0].get(p_dash)):
                        continue
                    if to_pdash_time > MaxWalkDist1_time:
                        continue

                    new_p_dash_time = TIME_START + to_pdash_time
                    label[0][p_dash] = new_p_dash_time
                    pi_label[0][p_dash] = ('walking',
                                       SOURCE,
                                       p_dash,
                                       to_pdash_time,
                                       new_p_dash_time 
                                       )
                    
                    list_stops.add(p_dash)
                    if marked_stop_dict[p_dash] == 0:
                        marked_stop.append(p_dash)
                        marked_stop_dict[p_dash] = 1

    if first_step:
                
                (stop_id, time_departure, dist) = first_step
                label[0][stop_id] = time_departure 
                pi_label[0][stop_id] = ('walking',
                                       SOURCE,
                                       stop_id,
                                       dist,
                                       time_departure 
                                       )
                
                
                
                list_stops.add(stop_id)
                if marked_stop_dict[stop_id] == 0:
                        marked_stop.append(stop_id)
                        marked_stop_dict[stop_id] = 1

    
    
    for k in range(1, roundsCount + 1):
        QApplication.processEvents()
        
        if k == 1:
            MaxWaitCurr = MaxWaitTime
            
        else:
            MaxWaitCurr = MaxWaitTimeTransfer
    
        Q.clear()


        while marked_stop:
            p = marked_stop.pop()

        
            marked_stop_dict[p] = 0

            # may by stop exist in layer but not exist in PKL
            try:
                routes_serving_p = routes_by_stop_dict[p]
            except:
                continue
            
            for route in routes_serving_p:
                stp_idx = idx_by_route_stop_dict[(route, p)]
                try:
                    Q[route] = min(stp_idx, Q[route])
                except KeyError as e:
                    Q[route] = stp_idx
        
        # Main code part 2

        boarding_time, boarding_point = -1, -1

        for route, current_stopindex_by_route in Q.items():
            
            QApplication.processEvents()
            boarding_time, boarding_point = -1, -1
            current_trip_t = -1

            if not stops_dict.get(route):
                continue

            for p_i in stops_dict[route][current_stopindex_by_route-1:]:

                
           
                to_process = True

                if current_trip_t != -1:
                 
                    try:
                        arr_by_t_at_pi = current_trip_t[current_stopindex_by_route - 1][1]
                    except:

                        continue
                    
                    if max_time < arr_by_t_at_pi:
                        to_process = False
                                        
                    # no rewrite if exist best solve!!!
                    if not isinstance(pi_label[k][p_i], int):
                        if pi_label[k][p_i][3] < arr_by_t_at_pi:

                            
                            to_process = False

                    if to_process and boarding_point != p_i:

                        label[k][p_i] = arr_by_t_at_pi
                        pi_label[k][p_i] = (boarding_time,
                                            boarding_point,
                                            p_i,
                                            arr_by_t_at_pi,
                                            tid)
                        
                                                                    
                        if marked_stop_dict[p_i] == 0:
                            marked_stop.append(p_i)
                            marked_stop_dict[p_i] = 1
                                                
                        list_stops.add(p_i)

                if (current_trip_t == -1 or (label[k - 1][p_i] + change_time < current_trip_t[current_stopindex_by_route-1][1])):
                    # my comment: this condition means that with current trip one is not on time
                    # to next arriving so on need to get more later trip
                    arrival_time_at_pi = label[k - 1][p_i]
                    
                    tid, current_trip_t = get_latest_trip_new(
                        stoptimes_dict, route, arrival_time_at_pi, current_stopindex_by_route, change_time, MaxWaitCurr)

                    if current_trip_t == -1:
                        boarding_time, boarding_point = -1, -1
                    else:
                        boarding_point = p_i

                        boarding_time = current_trip_t[current_stopindex_by_route-1][1]

                current_stopindex_by_route = current_stopindex_by_route + 1

        # Main code part 3
        
        """
        MaxWalkDist = max (MaxWalkDist2_time, MaxWalkDist3_time)
        save_marked_stop = True
        process_walking_stage(max_time,
                              MaxWalkDist,
                              k,
                              footpath_dict,
                              marked_stop_dict,
                              marked_stop,
                              label,
                              pi_label,
                              save_marked_stop,
                              list_stops
                              )
        """
        
        if k < roundsCount and MaxWalkDist2_time != MaxWalkDist3_time:

            save_marked_stop = True
            
            process_walking_stage(max_time,
                                  MaxWalkDist2_time,
                                  k,
                                  footpath_dict,
                                  marked_stop_dict,
                                  marked_stop,
                                  label,
                                  pi_label,
                                  save_marked_stop,
                                  list_stops,
                                  check_only_buildings = False
                                  )

        save_marked_stop = False

        process_walking_stage(max_time,
                              MaxWalkDist3_time,
                              k,
                              footpath_dict,
                              marked_stop_dict,
                              marked_stop,
                              label,
                              pi_label,
                              save_marked_stop,
                              list_stops,
                              check_only_buildings = True
                              )

        # Main code End
        if marked_stop == deque([]):
            break

    journeys_endtime, journeys_duration = post_processingAll(
        SOURCE,
        D_TIME,
        list_stops,
        pi_label,
        MIN_TRANSFER,
        MaxWalkDist2,
        MaxWalkDist3,
        timetable_mode,
        Maximal_travel_time,
        MaxExtraTime,
        mode = 1       
    )

    

    return journeys_endtime, journeys_duration

def process_walking_stage(max_time,
                          WALKING_LIMIT,
                          k,
                          footpath_dict,
                          marked_stop_dict,
                          marked_stop,
                          label,
                          pi_label,
                          save_marked_stop,
                          list_stops,
                          check_only_buildings

                          ):

    marked_stop_copy = marked_stop.copy()
    
    for p in marked_stop_copy:

        if pi_label[k][p][0] == 'walking':
            continue

        trans_info = footpath_dict.get(p, 0)


        if not trans_info:
            continue

        label_k_p = np.int64(label[k][p])

        for p_dash, to_pdash_time in trans_info:

            
            if to_pdash_time > WALKING_LIMIT:
                continue

           

            try:
                pi_label_k_p_dash = pi_label[k][p_dash]
            except:
                pi_label_k_p_dash = -1

            # this line is "don't rewrite founded bus trip to footleg"

           
                        
            if pi_label_k_p_dash != - 1 and pi_label_k_p_dash[0] != 'walking':
                continue

                            
            new_p_dash_time = label_k_p + to_pdash_time

            if max_time < new_p_dash_time:
                continue

            
            # veryfy cause if exist solve for this p_dash (not was better?)
            if pi_label_k_p_dash != -1 and pi_label_k_p_dash[0] == "walking" and new_p_dash_time > pi_label_k_p_dash[4]:
                continue

            
            # если это остановка
            if check_only_buildings:
                if (not(p_dash.isdigit()) or int(p_dash) < 110000):
                    continue

            label[k][p_dash] = new_p_dash_time
            
            pi_label[k][p_dash] = ('walking', p, p_dash,
                                   to_pdash_time, new_p_dash_time)

            list_stops.add(p_dash)

            if save_marked_stop:
                marked_stop.append(p_dash)
                marked_stop_dict[p_dash] = 1
    