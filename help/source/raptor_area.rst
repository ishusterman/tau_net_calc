.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>
.. _raptor_area:  

Transit accessibility – Service area
====================================

This section explains the *Transit accessibility → Service Area* part of the Accessibility Calculator menu (Figure 1).

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/mainwindow_single_location.png" style="width: 50%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 1. <i>Transit accessibility → Service Area</i> menu</p>

We present in detail the *From locations → Fixed-time departure* option and then, for each of the three other options, present the differences between this option and the chosen one.  

The necessary datasets
----------------------

- Transit routing — GTFS database, see  :ref:`building_data`
- The layer of buildings opened in the current QGIS project.

From - service area, fixed-time departure
-----------------------------------------

Choose *Transit accessibility map → Service area  → From service locations – fixed-time departure*. Enter the parameters (Figure 2).
   
.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/pt-fr-a.png" style="width: 80%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 2. <i>Service area → From locations – fixed-time departure</i> dialog</p>

:guilabel:`Transit routing database folder` — the folder of the transit routing database must contain the following files ``stops.pkl``, ``stoptimes.pkl``, ``transfers_dict.pkl``, ``idx_by_route_stop.pkl``, ``routes_by_stop.pkl``
|br2|
:guilabel:`Output folder` — the folder for storing the results of the computation.
|br2|
:guilabel:`Output alias` — the alias for the files of results and layers of visualization.
|br2|
:guilabel:`Facilities` — the layer of the facility buildings, may be selection set.
|br2|
:guilabel:`id` — the name of the field with the unique building identifier, in the layer of buildings.
|br2|
:guilabel:`Visualization layer` — the layer that will be used for visualization of accessibility maps, must be a part of the current QGIS project. 
|br2|
:guilabel:`id` — the name of the unique identifier field of the visualization layer unit. The features’ identifiers must be the subset of buildings’ identifiers. More information :doc:`here <visualization>`.
|br2|
:guilabel:`Minimum number of transfers` — minimum number of transfers of the transit trip, typically 0.
|br2|
:guilabel:`Maximum number of transfers` — maximum number of transfers of the trip, typically 1 or 2.
|br2|
:guilabel:`Maximum walk distance to the initial PT stop, m` — maximum acceptable walking distance between the trip origin and the first bus stop. The default value is 400 m.
|br2|
:guilabel:`Maximum walk distance at the transfer, m` — maximum acceptable walking distance between two stops at the transfer.The default value is 150 m.
|br2|
:guilabel:`Maximum walk distance from the last PT stop, m` — maximum acceptable walking distance between the last stop of a trip to the destination. The default value is 400 m.
|br2|
:guilabel:`Start at (hh:mm:ss)` — trip start time.
|br2|
:guilabel:`Walking speed (km/h)` — walking speed.
|br2|
:guilabel:`Maximal waiting time at the initial stop, min` — maximum waiting time at the initial stop of the trip.
|br2|
:guilabel:`Maximal waiting time at the transfer stop, min` — maximum waiting time at the transfer stop.
|br2|
:guilabel:`Boarding time gap` — the minimum time between two sequential activities, like arriving at the stop and boarding the bus. Usually, zero or several seconds.
|br2|
:guilabel:`Maximal time travel, min` — maximum total trip time.
|br2|
   
Click **Run** to start. The **Progressbar** shows the progress of the computations. You can break the process of the computations by pressing **Break**.
|br|
The **Log** tab contains the metadata about the computations (next section).
|br|
The results of the computations are stored as two CSV report files in the :guilabel:`Output folder`. The first depicts the service area and contains all buildings that can be reached from *at least one* of the facilities in :guilabel:`Maximal time travel, min` or faster. Each of these buildings is represented by the record that contains the :guilabel:`id` of the facility that served it in a minimal time, and all details of the trip between the facility and the building. The service area is visualized based on the :guilabel:`Visualization layer`.
|br|
The service area file does not contain information on whether the building can be served by more than one facility. This information can be retrieved from the second output file, where for each facility, all buildings that can be served are listed irrespective of the travel time from the facility. This second file can be used for deeper analysis of the accessibility, for example for recognizing buildings that can be reached from half or more of the facilities. In both output files, the details of every leg for every trip are described in detail, see the next section.

.. _raptor_area_log:  

The structure of the service area log file and reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The log file (Figure 3) in the results folder stores all settings and computation time of the run.

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/log_point.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>
    <p>Figure 3. Log file of the <i>From service locations – fixed-time departure</i> computations</p>

The *From service locations – fixed-time departure* computations report contains all the details of each trip. Its structure is as follows:

+---------------------------+---------------------------------------------------------+
| Attribute                 | Meaning                                                 |
+===========================+=========================================================+
| Origin_ID                 | The ID of the facility building                         |
+---------------------------+---------------------------------------------------------+
| Start_time                | Time of the trip start                                  |
+---------------------------+---------------------------------------------------------+
| Walk_time\ :sub:`1`       | Time of walking to the initial stop                     |
+---------------------------+---------------------------------------------------------+
| BStop_ID\ :sub:`1`        | The ID of the inital stop                               |
+---------------------------+---------------------------------------------------------+
| Wait_time\ :sub:`1`       | Time of waiting for a bus at the initial stop           |
+---------------------------+---------------------------------------------------------+
| Bus_start_time\ :sub:`1`  | Start time of the first ride of a trip                  |
+---------------------------+---------------------------------------------------------+
| Line_ID\ :sub:`1`         | ID of the line used for the first ride of a trip        |
+---------------------------+---------------------------------------------------------+
| Ride_time\ :sub:`1`       | Duration of the first ride of a trip                    |
+---------------------------+---------------------------------------------------------+
| AStop_ID\ :sub:`1`        | Alighting stop of the first ride of a trip              |
+---------------------------+---------------------------------------------------------+
| Bus_finish_time\ :sub:`1` | Finish time of the first ride of a trip                 |
+---------------------------+---------------------------------------------------------+
| Walk_time\ :sub:`2`       | Time of walking time to the first transfer stop         |
+---------------------------+---------------------------------------------------------+
| BStop_ID\ :sub:`2`        | ID of the first transfer stop                           |
+---------------------------+---------------------------------------------------------+
| Wait_time\ :sub:`2`       | Time of waiting for a bus at the first transfer stop    |
+---------------------------+---------------------------------------------------------+
| Next legs and transfers   | If more transfers are possible.                         |
+---------------------------+---------------------------------------------------------+
| DestWalk_time             | Walking time to a destination building                  |
+---------------------------+---------------------------------------------------------+
| Destination_ID            | The ID of the destination building                      |
+---------------------------+---------------------------------------------------------+
| Destination_time          | Time of arrival to destination                          |
+---------------------------+---------------------------------------------------------+
| Duration                  | Total trip duration                                     |
+---------------------------+---------------------------------------------------------+

The example of the *Transit accessibility → Service area → From service locations – fixed-time departure* computations see :ref:`here<sample_from-accessibility_fixed-time>`.

“To” service area, fixed-time arrival
-------------------------------------

Run *Transit accessibility → To service locations – fixed-time arrival* option. Most of the parameters of the to-accessibility computations are the same as for the from-accessibility. This regards walking distance, walking speed, waiting time at stops, number of transfers, and the gap between sequential activities. The major difference is in establishing facilities and buildings to serve: For the to-accessibility, facilities are the destinations and not the origins as it was in the case of the from-accessibility (Figure 4).

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/area_opt.png" style="width: 80%; border: 3px solid white;margin-bottom: 10px" />
      </div>
    <p>Figure 4. The Facilities/Origins part of the <i>Service area → To locations</i> dialog</p>

In addition, the trip’s start time is substituted by the arrival time (Figure 5). 

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/area_opt2.png" style="width: 80%; border: 3px solid white;margin-bottom: 10px" />
      </div>
    <p>Figure 5. The Start/Arrive time part of the <i>Service area → To locations</i> dialog</p>

The Log and Result files for the to-accessibility are the same as for the from-accessibility, with minor differences that reflect the *from-accessibility* to the *to-accessibility* changes. The output table includes one additional attribute:

+---------------------------+
|Latest time at destination |
+---------------------------+

That contains the value of the :guilabel:`Arrives before`.
|br|
The example of the *Transit accessibility → Service area  → To service locations  – fixed-time departure* computations see :ref:`here<sample_from-accessibility_fixed-time>` section.

Service area for schedule-based departure or arrival
----------------------------------------------------

The modern users of public transport are aware of the time the bus arrives at the stop they plan to start from or at the final stop of the trip. These travelers start their trip and walk to the initial stop to be there just before the bus arrival or take the bus that arrives at the destination just before the time a traveler must be at their destination. We have modified the :term:`RAPTOR algorithm <RAPTOR Algorithm>` to compute accessibility for these schedule-informed travelers. 
|br|
As an example of the “from” schedule-dependent accessibility computation, let us consider travelers who reside in the same building, are willing to start their PT trip to work between 8:00 and 8:30, and travel up to 45 minutes. Let us also assume that there is one stop reachable by foot near their home in a 3-minute walk, and 3 buses are arriving at this stop at 8:10, 8:25, and 8:32. In case of a fixed time start, all travelers will start at 8:00, wait for each of 3 buses and get with the PT whenever possible, probably making transfers, in 45 minutes. All trips will finish at 8:45 or earlier. In the case of the schedule-dependent start, travelers will start their trips at 8:07, 8:22, and 8:29 (but not later than 8:30) and will still have 45 minutes of travel time ahead. The trips that start with the first bus must end at 8:07 + 0:45 = 8:52, with the second at 9:07, and with the third at 9:14. Since the time before the start of the trip is not included in the total travel time, the schedule-dependent accessibility will be always the same or higher than the accessibility computed for the fixed start time. 
|br|
Note that, instead of one “start time” parameter, 8:00 in this example, the forward schedule-dependent accessibility demands two – the “earliest start time” that remains 8:00, and the “maximum delay at start” that is 30 minutes and the time between the earliest start time and the actual start of the trip is not included in the travel time.
|br| 
In the case of the to-accessibility computations, the latest arrival time is also substituted by the arrival interval. A traveler is allowed to arrive at the destination between the “earliest arrival time” and this time plus the “Maximum lateness”. As above, the time between the actual arrival and the latest possible arrival is not included in the travel time. The difference between the accessibility computations for travelers behaving according to the fixed time start or finish of the trip, and for the travelers whose behavior is schedule-defines is conceptual. We will be happy to know your experience in employing these two approaches and comparing the results.
|br|
The parameters of the *From locations – schedule-based departure* computations are almost the same as for the fixed-time option. The difference is in the description of the start of the trip which is defined by two parameters

:guilabel:`The earliest start time` — the earliest start time of a trip,

and the length of the period during which the trip can start:

:guilabel:`Maximum delay at start, min` — the maximum delay of the start of a trip.

For the *To locations – schedule-based arrival accessibility*, the arrival is defined by:

:guilabel:`The earliest arrival time` — the time of the earliest arrival to a destination,

and the length of the arrival period:

:guilabel:`Maximum lateness at arrival, min` — the maximum lateness in arriving at a destination.

The examples of schedule-based accessibility are :ref:`here<sample_schedule-based>`. 

The :ref:`example section<sample_comparison_time-fixed_schedule-dependent>` contains the comparison between the time-fixed and schedule-dependent accessibility estimates.