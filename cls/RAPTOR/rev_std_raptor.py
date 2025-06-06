"""
Module contains rRAPTOR implementation.
"""
from PyQt5.QtWidgets import QApplication
from RAPTOR.raptor_functions import *
import numpy as np


def rev_raptor(SOURCE,
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

    (
        marked_stop,
        marked_stop_dict,
        label,
        pi_label,
    ) = initialize_rev_raptor(routes_by_stop_dict, SOURCE, MAX_TRANSFER)

    change_time_save = change_time

    # change for new version timetable mode backward
    
    if timetable_mode:
        D_TIME = D_TIME + MaxExtraTime
     

    label[0][SOURCE] = D_TIME
    Q = {}  # Format of Q is {route:stop index}
    roundsCount = MAX_TRANSFER + 1
    trans_info = -1

    MaxWalkDist1_time = np.int64(MaxWalkDist1)
    MaxWalkDist2_time = np.int64(MaxWalkDist2)
    MaxWalkDist3_time = np.int64(MaxWalkDist3)

    min_time = np.int64(D_TIME - Maximal_travel_time)
    TIME_START = D_TIME
    
    """
    if timetable_mode:
        MaxWaitTime = MaxExtraTime
        min_time = np.int64(D_TIME - Maximal_travel_time - MaxExtraTime)
        
    """
            
    if first_step is None:
                if trans_info == -1:
                    trans_info = footpath_dict.get(SOURCE, [])

                for i in trans_info:
                    (p_dash, to_pdash_time) = i
                    if not (label[0].get(p_dash)):
                        continue
                    if to_pdash_time > MaxWalkDist3_time:
                        continue
                    new_p_dash_time = TIME_START - to_pdash_time
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
            
        

    # Main Code
    # Main code part 1

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

        boarding_time, boarding_point = -1, -1,

        for route, current_stopindex_by_route in Q.items():
            QApplication.processEvents()
            boarding_time, boarding_point = -1, -1
            current_trip_t = -1

            if not stops_dict.get(route):
                continue

            for p_i in stops_dict[route][current_stopindex_by_route - 1:]:

                to_process = True
                
                if current_trip_t != -1:

                    try:
                        arr_by_t_at_pi = current_trip_t[current_stopindex_by_route-1][1]
                    except: 

                        continue

                    if min_time > arr_by_t_at_pi:
                        to_process = False

                    # no rewrite if exist best solve!!!
                    if not isinstance(pi_label[k][p_i], int):
                        if pi_label[k][p_i][3] > arr_by_t_at_pi:
                            to_process = False

                    # and boarding_time >= arr_by_t_at_pi :
                    if to_process and boarding_point != p_i:

                        #if boarding_point == '13472' and p_i == '25107':
                        #    print (f'boarding_point={boarding_point} p_i={p_i} boarding_time {boarding_time} arr_by_t_at_pi= {arr_by_t_at_pi} tid= {tid} k={k}')    
                        
                        


                        label[k][p_i] = arr_by_t_at_pi
                        pi_label[k][p_i] = (boarding_time,
                                            boarding_point,
                                            p_i,
                                            arr_by_t_at_pi,
                                            tid)

                        list_stops.add(p_i)

                        if marked_stop_dict[p_i] == 0:
                            marked_stop.append(p_i)
                            marked_stop_dict[p_i] = 1

                if current_trip_t == -1 or (label[k - 1][p_i] - change_time > current_trip_t[current_stopindex_by_route-1][1]):
                    
                    # what means the last condition: we found new arrive time label[k - 1][p_i] to current stop
                    # and if we subtract from it change_time that still it will be greater than
                    # current_trip_t[current_stopindex_by_route][1] - so we need to find a trip
                    # with more later arrive time but the erliest from them, and it is what
                    # function get_earliest_trip_new returns

                    # his condition means that current trip arrives too early
                    # assuming arrival_time = departure_time

                    arrival_time_at_pi = label[k - 1][p_i]
                                        
                    tid, current_trip_t = get_earliest_trip_new(
                        stoptimes_dict, route, arrival_time_at_pi, current_stopindex_by_route, change_time, MaxWaitCurr)

                    if current_trip_t == -1:
                        boarding_time, boarding_point = -1, -1
                    else:
                        boarding_point = p_i
                        boarding_time = current_trip_t[current_stopindex_by_route-1][1]

                current_stopindex_by_route = current_stopindex_by_route + 1


        # Main code part 3
        """
        save_marked_stop = True
        MaxWalkDist = max (MaxWalkDist1_time, MaxWalkDist2_time)
        process_walking_stage(min_time,
                              MaxWalkDist,
                              k,
                              footpath_dict,
                              marked_stop_dict,
                              marked_stop,
                              label,
                              pi_label,
                              save_marked_stop,
                              list_stops,
                              )
        """
        MaxWalkTransfer = MaxWalkDist2_time
        if k < roundsCount and MaxWalkDist2_time != MaxWalkDist3_time:

            save_marked_stop = True
            process_walking_stage(min_time,
                                  MaxWalkDist2_time,
                                  k,
                                  footpath_dict,
                                  marked_stop_dict,
                                  marked_stop,
                                  label,
                                  pi_label,
                                  save_marked_stop,
                                  list_stops,
                                  MaxWalkTransfer
                                  )

        save_marked_stop = False

        process_walking_stage(min_time,
                              MaxWalkDist1_time,
                              k,
                              footpath_dict,
                              marked_stop_dict,
                              marked_stop,
                              label,
                              pi_label,
                              save_marked_stop,
                              list_stops,
                              MaxWalkTransfer
                              )
        # Main code End
        if marked_stop == deque([]):
            break

    journeys_endtime, journeys_duration = post_processingAll(
        SOURCE,
        D_TIME,
        label,
        list_stops,
        pi_label,
        MIN_TRANSFER,
        MaxWalkDist2,
        MaxWalkDist1,
        timetable_mode,
        Maximal_travel_time,
        MaxExtraTime,
        mode=2
        )

    return journeys_endtime, journeys_duration

def process_walking_stage(min_time,
                          WALKING_LIMIT,
                          k,
                          footpath_dict,
                          marked_stop_dict,
                          marked_stop,
                          label,
                          pi_label,
                          save_marked_stop,
                          list_stops,
                          MaxWalkTransfer):

    marked_stop_copy = marked_stop.copy()
    #save_marked_stop = True

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

            new_p_dash_time = label_k_p - to_pdash_time  # changed + to -

            if min_time > new_p_dash_time:
                continue

            # veryfy cause if exist solve for this p_dash (not was better?)
            if pi_label_k_p_dash != -1 and pi_label_k_p_dash[0] == "walking" and new_p_dash_time < pi_label_k_p_dash[4]:
               continue

            # если это остановка, но идти до нее дольше чем MaxWalkTransfer, то пропускаем
            if (not(p_dash.isdigit()) or int(p_dash) < 100000) and to_pdash_time > MaxWalkTransfer:
                continue

            label[k][p_dash] = new_p_dash_time

            pi_label[k][p_dash] = ('walking', p, p_dash,
                                   to_pdash_time, new_p_dash_time)
            
            list_stops.add(p_dash)

            # experiment !!!!!!!!!
            #save_marked_stop = k != 2 or to_pdash_time <= 200    
            # experiment !!!!!!!!!
            
            if save_marked_stop:
                marked_stop.append(p_dash)
                marked_stop_dict[p_dash] = 1