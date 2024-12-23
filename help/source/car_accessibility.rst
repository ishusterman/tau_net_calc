.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>

Сar accessibility 
=================

This section explains the *Car accessibility* branch of the Accessibility Calculator menu (Figure 1).

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/mainwindow-car.png" style="width: 50%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 1. <i>Car accessibility</i> menu<p>

Below, we present in detail the *From location – Fixed-time departure* option and then, for each of the three other options, present the differences between this option and the chosen one. Note that the car trip description is simpler than the transit trip and includes three components only – walk from the facility building to the parking car, drive, and walk from the parking spot to the destination. Also, in the case of car accessibility, a fixed start/arrival time only makes sense. 


The necessary datasets
----------------------

- Car routing database, see :ref:`building_data`
- The layer of buildings opened in the current QGIS project.

.. _car_options:

From - service area, fixed-time departure
-------------------------------------------------

Choose a *Car accessibility → Service Area → Fixed-time departure*. Enter the parameters.

.. raw:: html

  <div style="display: flex; justify-content: center;">
       <img src="_images/car_area.png" style="width: 60%; border: 0px solid black;margin-bottom: 10px" />
  </div>
  <p>Figure 2. <i>From locations – fixed-time departure</i> dialog for car accessibility</p>

:guilabel:`Car routing database folder` — the folder of the car routing database. Must contain the following files: ``graph.pkl``, ``graph_rev.pkl``, ``dict_vertex_buildings.pkl``, ``dict_building_vertex.pkl``.
|br2|
:guilabel:`Output folder` — the folder for storing the results of the computation.
|br2|
:guilabel:`Output alias` — the alias name for the files of results and layers of visualization.
|br2|
:guilabel:`Facilities` — the layer of the facility buildings, may be selection set.
|br2|
:guilabel:`id` — the field with the unique identifier of a facility, in the layer of buildings.
|br2|
:guilabel:`Visualization layer` — the layer that will be used for visualization of accessibility maps, must be a part of the current QGIS project. 
|br2|
:guilabel:`id` — the field of the unique identifier of the visualization layer's features. The identifiers must be the subset of buildings’ identifiers. More information :doc:`here <visualization>`.
|br2|
:guilabel:`Walking distance from origin to car parking, m` — a typical walking distance from the building to the parking car.
|br2|
:guilabel:`Walking distance from car parking to destination, m` — a typical walking distance from the parking car to the destination.
|br2|
:guilabel:`Driving start/finish gap` — the minimum time between two sequential activities, like arriving at the parking car and starting driving. Usually, zero or several seconds.
|br2|
:guilabel:`Maximum travel time` — the maximum total trip time.
|br2|
:guilabel:`Walking speed (km/h)` — a walking speed.
|br2|
:guilabel:`Start at (hh:mm:ss)` — trip start time.
|br2|
   
Click **Run** to start. The **Progress bar** shows the progress of the computations. You can break the process of the computations by pressing **Break**.
|br2|
The **Log** tab contains the metadata about the computations (next section). The structure of the report contains details of every leg for every trip and is described in detail in the next section.

The results of the computations are stored as two CSV report files in the :guilabel:`Output folder`. The first depicts the service area and contains all buildings that can be reached from *at least one* of the facilities in :guilabel:`Maximum travel time` or faster. Each of these buildings is represented by the record that contains the :guilabel:`id` of the facility that served it in a minimal time, and all details of the trip between the origin and the reached building. The service area is visualized based on the :guilabel:`Visualization layer`.
|br|
The service area file does not contain information on whether the building can be served by more than one facility. This information can be retrieved from the second output file, where for each origin, all served buildings that can be served are listed irrespective of the travel time from the facility. This second file can be used for deeper analysis of the accessibility, for example for recognizing buildings that can be reached from half or more of the facilities. In both output files, the details of every leg for every trip are described in detail, see the next section.



From - service area log file and accessibility report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The log file (Figure 3) is in the folder of the results. It stores all the settings of the run and the time the computations took.

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/log_car.png" style="width: 60%; border: 3px solid white;margin-bottom: 10px" />
      </div>
    <p>Figure 3. Log file of the <i>From locations – fixed-time departure</i> computations</p>

The output contains all the details of a trip to each of the buildings reachable in less than the maximum travel time from the clisest facility. The map of the output presents the total travel time for each of the accessible buildings (Figure 4).  

.. raw:: html

    <style>
        .custom-table {
            border-collapse: collapse;
            width: 100%;
        }

        .custom-table th, .custom-table td {
            border: 1px solid #d3d3d3; 
            padding: 8px;
        }

        .custom-table th {
            background-color: white;
            font-weight: bold;
            text-align: center; 
            vertical-align: middle; 
        }

        .custom-table td {
            text-align: left; 
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
            <th style="width: 150px;">Attribute</th>
            <th style="width: 200px;">Meaning</th>
        </tr>
        <tr>
            <td>Origin_ID</td>
            <td>The ID of the facility building</td>
        </tr>
        <tr>
            <td>Destination_ID</td>
            <td>The ID of the destination building</td>
        </tr>
        <tr>
            <td>Duration</td>
            <td>Total travel time</td>
        </tr>
    </table>
    <p>Figure 4. The structure of the <i>Car accessibility → Service area → From locations – fixed-time departure</i> output file.</p> 

The example of the *Car accessibility → Service area → From locations – fixed-time departure* computations see :ref:`here<sample_car_from-accessibility_fixed-time>`.

“To“ service area, fixed-time arrival
-------------------------------------

Run the *Car accessibility → Service area → To locations – fixed-time arrival* option. As you can see, most of the parameters of the to-accessibility computations are the same as for the from-accessibility. This regards walking distances, walking speed, and the gap between sequential activities. The major difference is in establishing facilities and served buildings – for the to-accessibility, facilities are destinations, and not the origins (Figure 5). 

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/area_opt.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 5. The Destinations/Origins part of the service area, to-accessibility dialog dialog</p> 

In addition, the trip’s start time is substituted by the arrival time (Figure 6). 

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/area_opt2.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 6. The Start/Arrive time part of the region to-accessibility dialog is different from the corresponding part in the region from-accessibility dialog</p>

The Log and Result files are the same as for the from-accessibility, with minor differences that reflect the *from-accessibility* to the *to-accessibility* changes. 
|br|
The example of the *Car accessibility → Service Area → From locations – fixed-time arrival* computations see :ref:`here<sample_car_from-accessibility_fixed-time>` .

Car Accessibility of all locations in the Region
------------------------------------------------

The parameters of accessibility computation for all locations in the Region are the same as they are for computing single-location accessibility, plus the list of attributes for aggregation. The default aggregation parameter is, just as it was for transit accessibility, the number of accessible buildings. In addition, each numeric parameter of the buildings can be selected for aggregation via the dialog option of :guilabel:`Aggregate` (Figure 7). The result of the computations is the sum of this attribute over buildings achievable in one, two, etc., time bins. The results for each of the aggregated fields are stored as a separate file in the :guilabel:`Output folder`.

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/map_opt1.png" style="width: 60%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 7. The choice of attributes for aggregation</p>

The number of bins to split the time interval [0, Maximum travel time] must be chosen via the :guilabel:`Number of bins` box. The aggregate accessibility measures will be stored for every bin, just as the cumulative histogram frequencies. The bin width is equal to the :guilabel:`Maximum travel time`/:guilabel:`Number of bins` and the number of bins must not exceed the :guilabel:`Maximum travel time`. Typically, the :guilabel:`Number of bins` is selected in a way to have the bin’s width of 5 or 10 minutes, while a 2- or even 1-minute bin can be useful for further analysis of accessibility. If the last bin does not match the :guilabel:`Maximum travel time`, the results for the :guilabel:`Maximum travel time` are also stored. The basic file of results presents the total number of buildings that can be reached from each of the region’s buildings after every time bin:

.. raw:: html

    <style>
        .custom-table {
            border-collapse: collapse;
            width: 100%;
        }

        .custom-table th, .custom-table td {
            border: 1px solid #d3d3d3;
            padding: 8px;
        }

        .custom-table th {
            background-color: white;
            font-weight: bold;
            text-align: center;
            vertical-align: middle;
        }

        .custom-table td {
            text-align: left;
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
            <th style="width: 150px;">Attribute</th>
            <th style="width: 400px;">Meaning</th>
        </tr>
        <tr>
            <td>Origin_ID</td>
            <td>ID of the building of origin or destination</td>
        </tr>
        <tr>
            <td>One bin time</td>
            <td>Total number of buildings that are accessible in 1 time-bin</td>
        </tr>
        <tr>
            <td>Two bins time</td>
            <td>Total number of buildings that are accessible in 2 time-bins</td>
        </tr>
        <tr>
            <td>… N bins time</td>
            <td>Total number of buildings that are accessible in N time-bins</td>
        </tr>
        <tr>
            <td>Maximum travel time</td>
            <td>Total number of buildings that are accessible in maximum travel time (if the latter is not an integer number of bins)</td>
        </tr>
    </table>

The thematic map presents the number of buildings reachable in :guilabel:`Maximum travel time`. Additional result files contain accessibility measures for each of the attributes chosen for aggregation. Each of these results is also presented by the thematic map.
|br|
The example of the *Car accessibility → Region → From every location – fixed-time departure* computations see :ref:`here<sample_car_to-accessibility_fixed-time>`.

Car accessibility to every location in the region
-------------------------------------------------

Run the *Car accessibility → Region → To every location – fixed-time arrival* option. As you can see, most of the parameters of the region’s to-accessibility computations are the same as for the from-accessibility. This regards walking distances, walking speed, and the gap between sequential activities. The major difference is in establishing origins and destinations – for to-accessibility, the buildings of the region are destinations (Figure 8). 

.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/sample/area_opt.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 8. The Origins/Destinations part of the region to-accessibility dialog</p>

The Log and Result files are the same as for the from-accessibility, with minor differences that reflect the from-accessibility to the to-accessibility changes. 
|br|
The example of the *Car accessibility → Region → To every location – fixed-time departure* computations see :ref:`here<sample_car_to-accessibility_fixed-time>`.
