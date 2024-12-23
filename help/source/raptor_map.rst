.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>
.. _raptor_map:  

Transit Accessibility of all locations in the     Region 
========================================================

This section explains the *Transit accessibility → Region* part of the Accessibility Calculator menu (Figure 1).

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/mainwindow-region.png" style="width: 50%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 1. <i>Transit accessibility → Region</i> menu</p>

We present in detail the *From every location – Fixed-time departure* option and then, for each of the three other options, present the differences between this option and the chosen one.

The necessary datasets
----------------------

-	Transit routing database, see :ref:`building_data`.
-	The layer of buildings opened in the current QGIS project.

Accessibility from every location in the region, fixed-time departure
---------------------------------------------------------------------

Choose *Transit accessibility → Region → From every location – fixed-time departure*. Enter the parameters (Figure 2).

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/pt-fr-m.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 2: <i>Region → From every location – a fixed-time departure </i> dialog</p>
   
:guilabel:`Transit routing database folder` — the folder of the transit routing database must contain the following files ``stops.pkl``, ``stoptimes.pkl``, ``transfers_dict.pkl``, ``idx_by_route_stop.pkl``, ``routes_by_stop.pkl``
|br2|
:guilabel:`Output folder` — the name of the folder for storing the results of the computation.
|br2|
:guilabel:`Output alias` — the alias name for the files of results and layers of visualization.
|br2|
:guilabel:`Facilities` — the layer of the facility buildings, may be selection set.
|br2|
:guilabel:`id` — the field of the unique identifier of a building, in the layer of buildings.
|br2|
:guilabel:`Visualization layer` — the layer that will be used for visualization of accessibility maps, must be a part of the current QGIS project. 
|br2|
:guilabel:`id` — the field of the unique identifier of the visualization layer feature. The identifiers must be the subset of buildings’ identifiers. More information :doc:`here <visualization>`.
|br2|
:guilabel:`Minimum number of transfers` — the minimum number of transfers of the transit trip, typically 0.
|br2|
:guilabel:`Maximum number of transfers` — the maximum number of transfers of the trip, typically 1 or 2.
|br2|
:guilabel:`Maximum walk distance to the initial PT stop, m` — the maximum acceptable walking distance between the trip origin and the first bus stop. The default value is 400 m.
|br2|
:guilabel:`Maximum walk distance at transfer, m` — the maximum acceptable walking distance between two stops at the transfer. The default value is 150 m.
|br2|
:guilabel:`Maximum walk distance from the last PT stop, m` — the maximum acceptable walking distance between the last stop of a trip to the destination. The default value is 400 m.
|br2|
:guilabel:`Start at (hh:mm:ss)` — trip start time.
|br2|
:guilabel:`Walking speed (km/h)` — walking speed.
|br2|
:guilabel:`Maximum waiting time at the initial stop, min` — the maximum waiting time at the initial stop of the trip.
|br2|
:guilabel:`Maximum waiting time at the transfer stop, min` — the maximum waiting time at the transfer stop.
|br2|
:guilabel:`Boarding time gap` — the minimum time between two sequential activities, like arriving at the stop and boarding the bus. Usually, zero or several seconds.
|br2|
:guilabel:`Maximum travel time, min` — the maximum total travel time.
|br2|
:guilabel:`Number of bins` — the number of bins to split the time interval [0, Maximum travel time]. The aggregate accessibility measures will be stored for every bin, just as the cumulative histogram frequencies. 
|br2|
The bin’s width is equal to the :guilabel:`Maximum travel time` /:guilabel:`Number of bins`, and the :guilabel:`Number of bins` must not exceed the :guilabel:`Maximum travel time`. If the last bin does not match the :guilabel:`Maximum travel time`, the measures for the :guilabel:`Maximum travel time` are also stored. Typically, the :guilabel:`Number of bins` is selected in a way to have the bin’s width of 5 or 10 minutes, while a 2- or even 1-minute bin can be useful for further analysis of accessibility.
|br2|
:guilabel:`Aggregate` — each of the numeric attributes of buildings can be selected for aggregation. For example, if the number of jobs is known for a building, then the total number of jobs that can be reached from a building in a given time can be calculated as a measure of the from-accessibility to jobs. You could choose several fields to aggregate (Figure 3). 

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/map_opt1.png" style="width: 60%; border: 0px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 3. The choice of attributes for aggregation</p>

The sum of the aggregated attribute over buildings achievable in one, two, etc., bins will be stored as a result in the :guilabel:`Output folder`, as a separate file for each of the aggregated fields. Each of the aggregated measures is presented by the thematic map. The structure of the result files is described in the next section.

Click **Run** to start. The **Progress bar** shows the progress of the computations. You can break the process of the computations by pressing **Break**. The **Log** tab contains the metadata about the computations (next section). In case the computations are based on the selection of buildings, the results will include the new layer that represents these buildings.

The log file and REGION accessibility report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The log file (Figure 4) is in the folder of the results. It stores all the settings of the run and the computation time.

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/log_area.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>
    <p>Figure 4. Log file of the <i>Region → From every location – fixed-time departure</i> computations</p>

In the case of the from-accessibility, the basic file of results presents the total number of buildings that can be reached from each of the region’s buildings after every time bin: 

.. raw:: html

    <style>
        .custom-table {
            border-collapse: collapse;
            width: 100%;
        }

        .custom-table th {
            border: 1px solid #d3d3d3;
            padding: 8px;
            text-align: center;
            vertical-align: middle;
            font-weight: bold;
            background-color: white;
        }

        .custom-table td {
            border: 1px solid #d3d3d3;
            padding: 8px;
            text-align: left;  
            vertical-align: middle;
        }

        .custom-table tr:nth-child(even) {
            background-color: #f0f8ff;
        }

        .custom-table tr:nth-child(odd) {
            background-color: white;
        }
    </style>

    <table class="custom-table" style="margin-bottom: 10px">
        <tr>
            <th>Attribute</th>
            <th>Meaning</th>
        </tr>
        <tr>
            <td>Origin_ID</td>
            <td>The ID of the building of origin</td>
        </tr>
        <tr>
            <td>One bin time</td>
            <td>Total number of buildings accessible in 1 time-bin</td>
        </tr>
        <tr>
            <td>Two bins time</td>
            <td>Total number of buildings accessible in 2 time bins</td>
        </tr>
        <tr>
            <td>… N bins time</td>
            <td>Total number of buildings accessible in N time bins</td>
        </tr>
        <tr>
            <td>Maximum travel time</td>
            <td>Total number of buildings accessible in maximum travel time (if the latter is not an integer number of bins)</td>
        </tr>
    </table>

The thematic map presents the number of buildings reachable in maximum travel time. Additional result files present the totals of other attributes chosen for aggregation and for each of these attributes the thematic map of the result for the maximum travel time is constructed. 
|br|
The example of the *Transit accessibility → Region → From every location – fixed-time* departure computations :ref:`here<sample_region_from-accessibility_fixed-time>`.

Accessibility to every location in the region, fixed-time arrival
-----------------------------------------------------------------

To compute the to-accessibility of every location in the region run the *Transit accessibility → Region → To all locations – fixed-time arrival* option. Most of the parameters of the region’s to-accessibility computations are the same as for the from-accessibility. This regards walking distance, walking speed, waiting time at stops, number of transfers, and the gap between sequential activities. The major difference is in establishing origins and destinations – for to-accessibility, one must establish the layer of the region’s destination buildings, and provide the layer of buildings from which these destinations may be accessed (Figure 5).

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/map_opt2.png" style="width: 80%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 5. The part of the region to-accessibility dialog that is different from the corresponding part in the region from-accessibility dialog</p>

The Log and Result files are the same as for the from-accessibility, with minor differences that reflect the *from-accessibility* changes. 
|br|
The example of the *Transit accessibility → Region → From all locations – fixed-time departure* computations see :ref:`here<sample_region_from-accessibility_fixed-time>` section.

Region accessibility for the schedule-based departure or arrival
----------------------------------------------------------------

The modern users of public transport are aware of the time the bus arrives at the stop they plan to start from, or to the final stops of the trip. These travelers start their trip and walk to the initial stop to be there just before the bus arrival or take the bus that arrives at the destination just before the time a traveler must be at their destination. We have modified the :term:`RAPTOR algorithm <RAPTOR Algorithm>` to compute accessibility for these schedule-informed travelers. The explanation of the schedule-based view of accessibility is presented in the section devoted to the single location accessibility computations :ref:`here<sample_schedule-based>`. 
|br|
Just as for the single location accessibility, instead of one “start time” parameter, schedule-dependent accessibility from every building in the region demands two parameters – the “earliest start time”, and the “maximum delay at start”. In the computation dialog, these are
:guilabel:`The earliest start time` - the earliest start time of a trip, :guilabel:`Maximum delay at start, min` - the maximum delay of a trip start.The time between the earliest start time and the actual start of the trip is not included in the total travel time. In the case of schedule-based accessibility to every location in the region, the latest arrival time is also substituted by the arrival interval. A traveler is allowed to arrive at the destination between the “earliest arrival time” and this time plus “Maximum lateness.” In the computation dialog, these are :guilabel:`The earliest arrival time` - the time of the earliest arrival to a destination, :guilabel:`Maximum lateness at arrival, min` - the maximum lateness in arriving at a destination. The time between the arrival and the latest possible arrival is not included in the total travel time. 
|br|
The examples of schedule-based accessibility are :ref:`here<sample_schedule-based>`. The :ref:`example section<sample_comparison_time-fixed_schedule-dependent>` contains the comparison between the time-fixed and schedule-dependent accessibility estimates.