"""
Module contains function related to RAPTOR, rRAPTOR
"""
from collections import deque as deque
from common import seconds_to_time

def initialize_raptor(routes_by_stop_dict,
                      SOURCE,
                      MAX_TRANSFER) -> tuple:

    inf_time = 200000
    roundsCount = MAX_TRANSFER + 1
    
    routes = list(routes_by_stop_dict.keys())
    pi_label = {x: {(stop): -1 for stop in routes}
                for x in range(0, roundsCount + 1)}
    label = {x: {(stop): inf_time for stop in routes}
             for x in range(0, roundsCount + 1)}

    marked_stop = deque()
    marked_stop_dict = {(stop): 0 for stop in routes_by_stop_dict.keys()}
    marked_stop.append(SOURCE)
    marked_stop_dict[SOURCE] = 1

    return marked_stop, marked_stop_dict, label, pi_label


def get_latest_trip_new(stoptimes_dict,
                        route,
                        arrival_time_at_pi,
                        pi_index,
                        change_time,
                        max_waiting_time) -> tuple:

    t2 = arrival_time_at_pi + change_time
    t3 = arrival_time_at_pi + max_waiting_time

    for trip_idx, trip in (stoptimes_dict[route].items()):
            # ! this error occurs due to the removal of stop_times > 23:59 !

        try:
            t1 = trip[pi_index-1][1]
        except IndexError:
            continue
    
        if (t1 >= t2) and (t1 <= t3):

            return f'{route}_{trip_idx}', stoptimes_dict[route][trip_idx]
    return -1, -1  # No trip is found after arrival_time_at_pi


def post_processing(DESTINATION,
                    pi_label,
                    MIN_TRANSFER,
                    MaxWalkDist2,
                    MaxWalkDist3,
                    timetable_mode,
                    Maximal_travel_time,
                    D_Time,
                    mode_raptor,
                    MaxExtraTime
                    ) -> tuple:


    # rounds in which the destination is achieved
    rounds_inwhich_desti_reached = [x for x in pi_label.keys(
    ) if DESTINATION in pi_label[x] and pi_label[x][DESTINATION] != -1]

    pareto_set = []

    if not rounds_inwhich_desti_reached:
        return None

    rounds_inwhich_desti_reached.reverse()

    last_mode = ""

    for k in rounds_inwhich_desti_reached:
        transfer_needed = k - 1

        # null transfers:
        # 1) footpath
        # 2) footpath + route
        # 2) footpath + route + footpath
        if transfer_needed == -1:
            transfer_needed = 0

        journey = []
        
        stop = DESTINATION

        walking_stops = []

        while pi_label[k][stop] != -1:

            journey.append(pi_label[k][stop])

            mode = pi_label[k][stop][0]
            if mode == 'walking':
                if last_mode == "":
                    last_mode = 'walking'

                """
                    These new checkings were added to process a case when 2 adjacent stops
                    are such that walking is from one to the other so we get infinite loop
                """
                if walking_stops != []:  # previous step was also walking

                    if stop in walking_stops:
                        
                        walking_stops = []
                        journey = []
                        break
                        
                    else:
                        
                        walking_stops.append(stop)
                        stop = pi_label[k][stop][1]
                        
                else:
                    walking_stops.append(stop)
                    stop = pi_label[k][stop][1]
            else:
                last_mode = ""
                stop = pi_label[k][stop][1]
                k = k - 1

            if k < 0 or (not pi_label[k].get(stop)):
                break

        if journey != []:
            journey.reverse()
            
            duration, start_time, end_time = get_duration(journey, mode_raptor)
                        
            append = True
            
            """
            if not (check_walking_jorney (DESTINATION, journey, MaxWalkDist2, MaxWalkDist3)):
                append = False
            """
            
                
            if timetable_mode:  # or mode_raptor == 2:

                if len(journey) > 1 and journey[0][0] == "walking" and journey[1][0] != "walking":

                    
                    journey[0] = (journey[0][0],
                              journey[0][1],
                              journey[0][2],
                              journey[0][3],
                              journey[1][0])
                                    
                    duration, start_time, end_time = get_duration(
                        journey, mode_raptor)
               
                if mode_raptor == 1:
                    if (duration > Maximal_travel_time) or start_time > D_Time + MaxExtraTime:
                        append = False
                    
                if mode_raptor == 2:
                    if (duration > Maximal_travel_time) or end_time > D_Time: 
                        append = False
                
            if  not (journey[-1][0] == 'walking'):
                append = False
                
            if  len(journey) == 1 and  journey[-1][0] == 'walking':
                append = False
                
            if len(journey) > 0 and not (journey[-1][0] == 'walking' and journey[-1][3] > MaxWalkDist3) and (transfer_needed >= MIN_TRANSFER):
                if append:
                    pareto_set.append((transfer_needed, duration, end_time, journey))

                    
                
                    
    if len(pareto_set) == 0:
        return None
    
    return pareto_set

def get_duration(journey, mode_raptor):
    duration = 0
    start_time = 0
    end_time = 0

    if mode_raptor == 1:

        if len(journey) == 1 and journey[0][0] == "walking":
            duration = journey[0][3]
            start_time = journey[0][4]-journey[0][3]
            end_time = journey[0][4]
            return duration, start_time, end_time

        if len(journey) > 1:
            if journey[0][0] == "walking":
                start_time = journey[0][4] - journey[0][3]
            else:
                start_time = journey[0][0]

            if journey[-1][0] == "walking":
                end_time = journey[-1][4]
            else:
                end_time = journey[-1][3]

            duration = end_time - start_time

            return duration, start_time, end_time

    if mode_raptor == 2:

        if len(journey) == 1 and journey[0][0] == "walking":
            duration = journey[0][3]
            start_time = journey[0][4] + journey[0][3]
            end_time = journey[0][4]
            return duration, start_time, end_time

        if len(journey) > 1:
            if journey[0][0] == "walking":
                end_time = journey[0][4] + journey[0][3]
            else:
                end_time = journey[0][3]

            if journey[-1][0] == "walking":
                start_time = journey[-1][4] 
            else:
                start_time = journey[-1][3]
    
    duration = end_time - start_time


    return duration, start_time, end_time


def post_processingAll(
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
        mode
        ):
    
    Dict_endtime, Dict_duration  = {}, {}
    
    for p_i in list_stops:

        if SOURCE == p_i:
            continue
        pareto_set = post_processing(p_i,
                                     pi_label,
                                     MIN_TRANSFER,
                                     MaxWalkDist2,
                                     MaxWalkDist3,
                                     timetable_mode,
                                     Maximal_travel_time,
                                     D_TIME,
                                     mode,
                                     MaxExtraTime,                                     
                                     )
        

        

        if pareto_set == None:
            continue
        
        if pareto_set != None and len(pareto_set) > 0:
            # Just one journey with minimal end time will be in pareto set

            optimal_endtime, optimal_duration = get_optimal_journeys(pareto_set)

            # Заполнение словарей на основе полученных данных
            
            duration, transfers, end_time, journey = optimal_endtime
            Dict_endtime[p_i] = [SOURCE, duration, journey, transfers, end_time ]

            duration, transfers, end_time, journey = optimal_duration
            Dict_duration[p_i] = [SOURCE, duration, journey, transfers, end_time]
                    
    return Dict_endtime, Dict_duration, 

def get_optimal_journeys(pareto_set):
    """
    Находит оптимальные маршруты по разным критериям за один проход.

    :param pareto_set: Набор Парето, содержащий кортежи с данными о поездке.
    :return: Кортеж из четырех кортежей с оптимальными данными для каждого критерия.
    """
    
    first_journey_data = pareto_set[0]
    
    count_leg_0, duration_0, end_time_0, journey_0 = first_journey_data
    
    
    # Инициализация оптимальных значений
    optimal_duration_journey = (duration_0, count_leg_0, end_time_0, journey_0)
    optimal_end_time_journey = (duration_0, count_leg_0, end_time_0, journey_0)
    


    # Единый проход по набору Парето, начиная со второго элемента
    for journey_data in pareto_set[1:]:
        
        count_leg, duration, end_time, journey = journey_data
        
        # Обновляем оптимальный маршрут по длительности
        if duration < optimal_duration_journey[0] or (duration == optimal_duration_journey[0] and count_leg < optimal_duration_journey[1]):
            optimal_duration_journey = (duration, count_leg, end_time, journey)
        
        if end_time < optimal_end_time_journey[2] or (end_time == optimal_end_time_journey[2] and count_leg < optimal_end_time_journey[1]):
            optimal_end_time_journey = (duration, count_leg, end_time, journey)
        
    return optimal_end_time_journey, optimal_duration_journey


def initialize_rev_raptor(routes_by_stop_dict,
                          SOURCE,
                          MAX_TRANSFER) -> tuple:

    inf_time = -1
    roundsCount = MAX_TRANSFER + 1
    routes = list(routes_by_stop_dict.keys())
    
    pi_label = {x: {stop: -1 for stop in routes}
                for x in range(0, roundsCount + 1)}
    label = {x: {stop: inf_time for stop in routes}
             for x in range(0, roundsCount + 1)}
    
    marked_stop = deque()
    marked_stop_dict = {stop: 0 for stop in routes}
    marked_stop.append(SOURCE)
    marked_stop_dict[SOURCE] = 1
    return marked_stop, marked_stop_dict, label, pi_label


def get_earliest_trip_new(stoptimes_dict,
                          route,
                          arrival_time_at_pi,
                          pi_index,
                          change_time,
                          max_waiting_time) -> tuple:

    t2 = arrival_time_at_pi - change_time
    t3 = arrival_time_at_pi - max_waiting_time
    for trip_idx, trip in (stoptimes_dict[route].items()):
        
        # ! this error occurs due to the removal of stop_times > 23:59 !
        try:
            t1 = trip[pi_index-1][1]
        except IndexError:
            continue

        if (t1 <= t2) and (t1 >= t3):
            return f'{route}_{trip_idx}', stoptimes_dict[route][trip_idx]

    return -1, -1  # No trip is found after arrival_time_at_pi


