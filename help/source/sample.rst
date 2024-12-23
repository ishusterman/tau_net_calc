.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>
.. _sample:  

Assessing the effect of a new Light Rail Transit line on transport accessibility in the Tel-Aviv Metropolitan Area
==================================================================================================================

This section presents the use of the Accessibility Calculator for assessing the effects of the new “Red” LRT line in the Tel Aviv Metropolitan area (TAMA). The line started functioning at the end of 2023 and became fully operational in 2024. 
|br|
The TAMA area is about 1.5K sq. km, and it includes a dozen cities and many minor settlements. The population of TAMA in 2024 is 4,2M and the number of buildings there is 252K. Figure 1 below presents maps of TAMA.

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img1.png" style="width: 32%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img2.png" style="width: 65%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 1. TAMA roads (left); zoom to the area served by the Red LRT line (right)</p>

The example is built with the Lenovo ThinkPad X1 laptop with the Intel i7 2.80GHz processor and 32MB memory, and we accompany each result by the estimates of computing time.

Arrange the data
----------------

To study TAMA transport accessibility, we need the layers of buildings, roads, and GTFS dataset, each for the TAMA or larger area. The layer of roads must be topologically cleaned, that is, all links must be split at the points of intersection, and links’ ends must connect at junctions. We do not include the issue of topological cleaning in this tutorial. Note, however, that in the case of the OSM road for Israel, the use of an uncleaned road layer will not result in qualitatively different results.
|br|
All datasets used in this tutorial are provided as a zip file, together with the plugin.
|br|
Build one more PT dictionary for the 2024 GTFS dataset. Save the results in the TAMA_PT_2024 folder. The general characteristics of the three databases are as follows: [Change dictionary to Database in the titles of the table columns below]
|br|
As we already mentioned, we do not recommend cutting parts of the GTFS. The increase in performance that you will obtain with the smaller databases will not be significant.
|br|
To study the effects of the Red line we used two GTFS datasets, one before, and one after the Red line introduction. We assume that buildings and roads did not change much between 2018 and 2024 and used the 2024 data. All these datasets are provided as a zip file with this tutorial.
|br|
This section is thus based on the minimal possible set of data: 
|br2|

-	The layers of buildings and roads were selected with the TAMA polygon from the OSM layers of buildings and roads in Israel that were downloaded in June 2024. The road layer was topologically cleaned. 
-	To study the Red line effects, we exploit two GTFS datasets, both for the entire Israel. The 2018 GTFS is downloaded from https://openmobilitydata.org/p/ministry-of-transport-and-road-safety/820/20180711 and the one for 2024 from https://s3.gtfs.pro/files/sourcedata/israel-public-transportation.zip.

|br|
The major characteristics of the exploited datasets are presented in the table.

.. list-table:: 
   :header-rows: 1
   :widths: 20 15 20 15

   * - Database
     - Type
     - Number of features
     - Size (MB)
   * - TAMA Buildings
     - Shape
     - 252,364
     - 147
   * - TAMA Roads
     - Shape
     - 301,230
     - 120
   * - Israel GTFS 2018
     - Dataset
     - 
     - 757
   * - Israel GTFS 2024
     - Dataset
     - 
     - 1,150

Note that the latest version of the Israeli GTFS can be downloaded using **PowerShell**:

.. code-block:: powershell

    Invoke-WebRequest -Uri "https://gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip" 
    -OutFile "C:\Path\To\Directory\israel-public-transportation.zip"

.. _sample_data_preprocessing:

Data preprocessing
------------------

To continue with the Accessibility Calculator, we must build three databases. One for the data on the layer of buildings and the road network, and two for the GTFS data, one for the year 2018 and one for 2024. The meaning of the databases and the process of building them is described in the :ref:`Data preprocessing <building_data>` section of this tutorial. Let us reproduce the steps of this process.

-- Click **Car routing** menu and choose the layer of roads and buildings for building dictionary (must be open in the project). Be careful with the choice of fields that represent the link’s speed, type, traffic direction, and building ID. Establish a new folder to store the CAR dictionary before providing its name in the dialog box(Figure 2). 

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/pkl_car1.png" style="width: 90%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 2. Car routing database constriction dialog</p>

The log file preserves all necessary data on the TAMA CAR dictionary construction and is stored in the CAR dictionary library(Figure 3).   

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img4.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 3. Log file of the Car routing database construction</p>

As can be seen, the time of the TAMA CAR dictionary construction was 2 mins 11 sec 

-- Click **Transit routing - GTFS** menu item. Choose the layer of roads and buildings (must be open in the project). Establish a new folder to store the 2018 GTFS database before providing its name in a dialog box. Note that this database is constructed for the GTFS of the entire Israel (Figure 4).

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/pkl1.png" style="width: 90%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 4. GTFS database constriction dialog</p>

The log file preserves all necessary data on the GTFS database construction for Israeli 2018 GTFS and is stored in the database folder. The time necessary for building the database for the entire Israel is much longer than it took to construct the Car database, 16 min 43 sec (Figure 5). 

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img6.png" style="width: 60%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 5. Log file of the Transit routing – GTFS database construction</p>

Build one more PT dictionary for the 2024 GTFS dataset. Save the results in the TAMA_PT_2024 folder. The general characteristics of the three libraries are as follows:

.. list-table:: 
   :header-rows: 1
   :widths: 20 25 25 20

   * - Dataset
     - Construction time (mins)
     - Source files total size (MB)
     - Dataset size (MB)
   * - CAR
     - 2:11
     - 267
     - 194
   * - PT2018
     - 16:43
     - 1,125
     - 430
   * - PT2024
     - 26:21
     - 1,417
     - 595

The number of PT lines in TAMA is about 10% of the country’s PT lines, but they are, on average, more frequent than the lines outside TAMA. Overall, the side of the TAMA GTFS, if constructed, will be about 25% of the Israeli GTFS. 
|br|
As we already mentioned, we do not recommend cutting parts of the GTFS. The increase in performance that you will obtain with the smaller dictionaries will not be significant until this part is less than 5-10% of the country’s GTFS.

Accessibility of a single location  
----------------------------------

The example we have chosen for illustrating single location accessibility computation is the accessibility of the Gesher (Bridge) theater in the Yafo region of Tel Aviv.  

.. _sample_from-accessibility_fixed-time:
.. _sample_to-accessibility_fixed-time:

From-accessibility, fixed-time arrival/departure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let us estimate Gesher's accessibility at 20:00 when the performance starts, and at 22:30, when it ends. The accessibility computations, in all possible regimes, demand the definition of parameters that define travelers' behavior (Figure 6 left). Below, for the PT trips, we assume that:

-	Minimum number of transfers = 0
-	Maximum number of transfers = 1
-	Maximum walking distance from the origin building to the first PT stop = 400 m
-	Maximum distance between stops when changing lines = 200 m
-	Maximum walk distance from the last PT stop to the destination building = 400 m
-	Walking speed = 3.0 km/h
-	Maximum waiting time at the first PT stop = 10 min
-	Maximum waiting time at the transfer stop = 5 min
-	Minimal gap between activities = 15 sec
-	Boarding time gap = 15 sec

Importantly, the network and not aerial distance is used for all our computations below (The air distance checkbox is disabled) and maximal trip duration is set to 45 minutes.
|br|
Additional parameters for the single location accessibility computations are the arrival and departure times, 20:00 for the backward, and 22:30 for the forward accessibility, respectively, and the folder for storing the results (TAMA_results). All these parameters are part of the UI dialog, and the figure below presents this dialog and the Log files in full for the Backward accessibility computations for the 2018 state of the PT network.
|br|
On **Run** the folder with the Alias name (BPTGesher) will be created in the result folder and, after the computations finish in 9 seconds (Log file, Figure 6 right) this folder will contain two files: The log file log_BPTGesher.txt, and BPTGesher_45m_tot_265984731.csv file of results. The 265984731 in the name of the result file is an OSM_ID of the Gesher Theater building. 
|br|
The CSV file of results is joined to the visualization layer and presented as a map.
|br|
Single-location computations can be done for more than one origin/destination. Each result is stored as a separate file, with the origins/destinations OSM_ID as a part of the name.

.. raw:: html

   <div style="display: flex; justify-content: center;">
       <img src="_images/sample/img7.png" style="width: 37%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img8.png" style="width: 37%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 6. The dialog of the <i>Transit accessibility map → Single location → To location – fixed time arrival</i> (left) and the Log file of the computations (right)</p>

The maps of accessibility to/from the Gesher theater, two before and two after the Red LRT line was introduced are presented in Figure 7. It took 9-10 seconds per scenario to compute each. We will compare the left and right maps and assess the Red line effects in this way, in the :ref:`Compare Accessibility <sample_compare_accessibility>` section below.  

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img9.png" style="width: 49%; border: 3px solid white;margin-bottom: 0px" />
       <img src="_images/sample/img10.png" style="width: 49%; border: 3px solid white;margin-bottom: 0px" />
   </div>

|br|

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img11.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img12.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 7. The results of the <i>Transit accessibility map → Single location, fixed-time</i> computations of the Gesher Theater in Yafo. To-accessibility at 20:00, in 2018 (top left) and 2024 (top right). From-accessibility at 22:30, in 2018 (bottom left) and 2024 (bottom right)</p>

.. _sample_schedule-based:

Single location accessibility, schedule-based arrival/departure time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Schedule-dependent accessibility considers the traveler who does not have to start or finish the trip at a certain exact time. Rather it’s a traveler who may stay at home until the convenient bus arrives at the departure or arrival stop. Like a traveler who plans to go shopping between 10-10:30 in the morning or wants to get to a fish market that works from 8:00 during the first half an hour of the market work. 
|br|
Formally, the schedule-based travel behavior nullifies the waiting time at the first PT stop, the arrival is never early, and the travel period can be shifted within the interval of the traveler’s flexibility. The flexibility is defined by the time between the earliest and the latest moment of the trip start for from-accessibility or by the time between the earliest and latest arrival in case of to-accessibility. 
|br|
The schedule-based accessibility calculation dialogs are almost the same as they are for the fixed-time accessibility. The only difference is an additional parameter that defines the flexibility of the start or arrival time. In the case of forward accessibility, “The start time” is substituted by “The earliest start time,” while the maximum delay (in minutes) is a parameter that defines the start time flexibility.  
  
.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img13.png" style="width: 70%; border: 3px solid white;margin-bottom: 5px" />
   </div>

In the case of to-accessibility, “The arrival time” is substituted by “The earliest arrival time” while the maximum lateness (in minutes) is a parameter that defines the arrival time flexibility.

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img14.png" style="width: 70%; border: 3px solid white;margin-bottom: 5px" />
   </div>

The travel time in case of schedule-based accessibility does not include waiting at the first stop, and the arrival is always on time. That is why the schedule-based accessibility is always higher than the fixed-time one. In addition, schedule-based accessibility is essentially less sensitive to the start or arrival time – these moments can freely slide within the intervals of flexibility. 
|br|
Four maps of the schedule-based accessibility to/from the Gesher Theater in the years 2018 and 2024 are presented in Figure 8. There was a photo exhibition in the theater foyer, and many visitors were ready to arrive at the theater any moment between 19:30 and 20:00 and spend time there before the performance. They also kept in mind that the theater café serves drinks and snacks long after the performance is over and it’s worth waiting for some time for the empty buses. 

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img15.png" style="width: 49%; border: 3px solid white;margin-bottom: 0px" />
       <img src="_images/sample/img16.png" style="width: 49%; border: 3px solid white;margin-bottom: 0px" />
   </div>
   

|br|   

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img17.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img18.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 8. The results of the <i>Transit accessibility map → Single location, schedule-based time </i>accessibility of the Gesher Theater. To-accessibility, in 2018 (top left) and 2024 (top right) between 19:30 and 20:00, and From-accessibility of the Gesher Theater between 22:30 and 23:00, in 2018 (bottom left) and 2024 (bottom right)</p>

We will assess the difference between the schedule-based and fixed-time accessibility maps in the :ref:`Compare Accessibility <sample_compare_accessibility>` subsection below.

.. _sample_car_from-accessibility_fixed-time:

Single location CAR accessibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CAR accessibility computations demand very few parameters related to travelers’ behavior. There is no schedule-dependent accessibility either. However, assessment of the car travel time demands knowledge of the traffic speed along the route and this information is hardly available. The only source of systematic knowledge of the traffic speed we are aware of is `Google API <https://developers.google.com/maps/documentation/distance-matrix/distance-matrix#distance-matrix-advanced>`_
and we plan to relate car accessibility calculations to the Google data on traffic speed in the next version of the Accessibility Calculator. 
|br|
For now, to calculate CAR accessibility, we assume that the speed on the road link is defined by the link’s type. The table of the characteristic speeds for the OSM classification of links is supplied with the plugin and is in the folder of each CAR dictionary that the user constructs. The name of the table is Car_speed_by_link_type.csv and, different from the dictionary, the table of speeds can be edited by the user. See more details on this table in the :ref:`this <car_speed_by_link_type>` section.
|br|
As a Single-location accessibility example, we calculate the Car accessibility of the Gesher Theater in Yaffo. The to-accessibility, as above for 20:00 when the performance starts, and from-accessibility at 22:30, when it ends (Figure 9).

.. raw:: html

   <div style="display: flex; justify-content: center; ">
       <img src="_images/sample/img19.png" style="width: 39%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img20.png" style="width: 39%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 9. <i>Car accessibility map → Single location</i> computations. In the to-accessibility dialog (left), Gesher is a destination origin and TAMA buildings are origins; in the from-accessibility dialog (right), it's vice versa</p>

The maps of the to- and from-accessibility (Figure 10) look much simpler than those of the PT accessibility. It’s worth noting that the car accessibility from the theater at 22:30, when the congestion is over, is essentially higher than the to-accessibility at 20:00 when the congestion is still there. It is worth noting that CAR accessibility at 20:00 and 22:30 is essentially higher than PT accessibility for the same conditions. 

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img21.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img22.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 10. Car accessibility to the Gesher Theater at 20:00 (left), when the congestion is still there, and from the Theater at 22:30, without congestion (right)</p>

Accessibility of every location in a region 
-------------------------------------------

Single-location accessibility regards one or several locations only. The infrastructure changes affect many locations at once. This is the goal of the Region part of the Accessibility Calculator. 
|br|
A single building remains the basic unit of the Region calculations and accessibility is calculated for every building in the region. The difference is in the measures of accessibility. The travel time between the selected building and a distant location cannot be useful when all buildings in the region are considered, the buildings are just too many and we do not need a detailed description of each trip from every building in the region to every destination. Instead, in the Region regime, each building is characterized by the aggregate measures of accessibility. The default measure is the number of buildings that may be accessed in a given time for from-accessibility or from which the building can be accessed in case of to-accessibility. This measure is stored at a user-defined time resolution, typically of 5 minutes. The user-defined measures can be the number of buildings of a certain type, the number of residents in these buildings, the number of jobs, and any other aggregate characteristic that can be calculated based on the buildings’ attributes and presented as a thematic map at resolution of the region’s buildings.
|br|
Let us continue with the example of the Red LRT line and investigate the line’s effect on accessibility in the city of Tel Aviv. The number of buildings in Tel Aviv is 40K and, different from the single location accessibility, the time necessary for each of the accessibility calculations below is several hours. We will limit ourselves to the default measure – the number of accessible buildings. 

.. _sample_region_from-accessibility_fixed-time:

Region PT accessibility, fixed-time arrival/departure time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Figure 11 presents two parts of the UI dialogs for the from-/to fixed-time accessibility calculations that are different from the corresponding dialogs for the single location forward/backward accessibility.
|br|
The first part is a layer of the origins in the case of the form- and of the destinations in the case of to-accessibility.  The difference is conceptual - one can call one building a region and perform computations for it. The result, however, will contain one record only – the number of buildings that can be achieved from this building in 5, 10, etc. minutes.
 
.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img23.png" style="width: 70%; border: 3px solid white;margin-bottom: 0px" />
   </div>

|br|   

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img24.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 11. The origin and destinate choice for the <i>Transit accessibility map → Region fixed-time accessibility</i> option in the case of the from- (top) and to- (bottom) accessibility</p>

The second part is a choice of the attributes for aggregation (Figure 12). It looks the same for all options – the user can choose any of the building’s attributes and the sum of this attribute over buildings achievable in 5, 10, … minutes will be stored as a result.

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img25.png" style="width: 70%; border: 3px solid white;margin-bottom: 0px" />
   </div>

|br|   

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img26.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
   </div>         
   <p>Figure 12. The aggregate (top) part of the dialog and the number of bins box (bottom) for the <i>Transit accessibility map → Region fixed-time accessibility</i> option<p>

If the maximum travel time does not contain an integer number of bins, the results are also stored for the maximum travel time.
|br|
If you are interested in computing the weighted sum of some attribute, calculate the new weighted attribute and sum it up with the Accessibility Calculator.
|br|
Figure 13 presents the maps of region accessibility for 2018 before the red LTR line was established in 2024 when the line was in full operation. We will compare them numerically in the next section.

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img27.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img28.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 13. The maps of region accessibility for 2018 before the red LTR line was established (left) and in 2024 when the line was in full operation (right)</p>

Region PT accessibility, schedule-dependent fixed-time arrival/departure time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The schedule-dependent Region accessibility exploits schedule schedule-dependent view when computing the accessibility of each of the region’s buildings. In all other respects, it repeats the fixed-time approach. 

.. _sample_car_to-accessibility_fixed-time:

CAR accessibility
~~~~~~~~~~~~~~~~~

The Region accessibility with a car employs car-based accessibility computations when computing the accessibility of each of the region’s buildings. In all other respects, it repeats the PT approach. 

.. _sample_compare_accessibility:

Compare the results of accessibility computations
-------------------------------------------------

The goal of our exemplary study is to assess the effects of the Red LRT line. In the previous sections, we have built the accessibility maps, at point and region levels, for the comparison that we will perform in this section. To remind, the Accessibility Calculator provides three measures of difference:

-	:guilabel:`Ratio: Result_1/Result_2`: The ratio of the result of the first scenario to the results of the second scenario, for the overlapping part of the outputs.
-	:guilabel:`Difference: Result_1 - Result_2`: The difference between the result of the first scenario and the results of the second scenario, for the overlapping part of the outputs.
-	:guilabel:`Relative difference: [Result_1 - Result_2]/Result 2`: The difference between the result of the first scenario and the results of the second scenario, for the overlapping part of the outputs. The result is presented in percents.

For each of the three cases, in addition to the map of the selected measure, two more maps are presented. The first one presents the buildings that were not accessible in Scenario 1 (Result_1 is NULL) but are accessible in Scenario 2 (Result_2 is not NULL). The second map presents the buildings that were not accessible in Scenario 2 (Result_2 is NULL) but are accessible in Scenario 1 (Result_1 is not NULL). 
|br|
In this section, we will illustrate the comparison between the accessibility computations with the relative difference between the accessibility in 2024, when the Red LRT line is functioning, and in 2018, before the Red line was established.
.

.. _sample_compare_single:

Compare single-location fixed-time accessibility maps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Our first question is “Whether the Red Line increased the accessibility for those Gesher visitors who want to get to the 20:00 performance with the public transport?” To reply to this question, we compare maps of backward fixed-time accessibility for the years 2024 and 2018, calculating (Result_2024 – Result_2018)/Result_2018 (Figure 14).
|br|
The left map below presents the relative difference for the buildings from which the visitors could reach the theater in less than 45 minutes in 2018 and 2024. The map on the right presents the “only” parts of the map on the left.

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img29.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img30.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 14. The comparison of the to-accessibility maps: Relative difference for the buildings from which the visitors could reach the theater in less than 45 minutes in 2018 and 2024 (left) and the map of the areas that are accessible in 2024 only (right)</p>

As can be seen, the result is not that simple. Overall, the Red Line essentially improved the PT accessibility for the Gesher visitors. In 2024, Gesher can be achieved in less than 45 minutes from 44646 buildings versus 34437 buildings in 2018 (you should check the output CSV files to know these numbers), and the green shades that denote buildings from which the PT travel time in 2024 is less than travel time in 2018 cover 60% of overlapping areas. Yet there are areas from which one could reach Gesher in less than 45 minutes in 2018 and cannot do that in 2024. 
|br|
More comparison studies will help us to understand the reasons for the differences. To confirm the result, one can compare the to-accessibility maps for the longer maximum travel time or go deeper and, based on the full output of the single-location accessibility that contains the full description of the trip (section :ref:`raptor_area_log`), investigate how the travelers get to the Gesher Theater from each of the “only” parts in 2018 and 2024. 
|br|
To conclude this section, let us compare fixed-time accessibility from the Gesher Theater at 22:30, in 2024 and 2018 (Figure 15). Qualitatively, the differences revealed in Figure 14 are repeated. Yet the maps do not repeat the maps in Figure 14 exactly. 

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img31.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img32.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 15. Comparison of the from-accessibility maps: Relative difference for the buildings that can be reached by the theater visitors in less than 45 minutes in 2018 and 2024 (left) and the map of the areas that are accessible in 2024 only (right)</p>

.. _sample_comparison_time-fixed_schedule-dependent:

Compare single-location fixed-time and schedule-based accessibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To assess the effect of the schedule-based approach to the accessibility computations let us compare the schedule-based and fixed-time accessibility maps for the to- and from accessibility computations of 2024 (Figure 16). The map at the left presents the  
|br|

.. raw:: html

   <div style="text-align: center;">
       (<b>Schedule_based</b>_TO_Result_24 – 
       <b>Fixed_time</b>_TO_Result_24)/ 
       <b>Fixed_time</b>_TO_Result_24,
   </div>

|br|
while the map on the right
|br|

.. raw:: html

   <div style="text-align: center;">
       (<b>Schedule_based</b>_FROM_Result_24 – 
       <b>Fixed_time</b>_FROM_Result_24)/
       <b>Fixed_time</b>_FROM_Result_24,
   </div>

|br|
As can be seen, the schedule-based accessibility is always higher than the fixed-time based. You can continue and check that schedule-based accessibility is essentially less dependent on time than the fixed-based one. For example, build maps for the fixed time of arrival to the Gesher theater at 19:50, 19:40, and 19:30, for people who don’t want to take their seats at the last moment before the performance starts, or want to sit at the theater buffet before the performance, and compare these maps between themselves and to the Schedule-based map we have already constructed for the arrival between 19:30 and 20:00.

.. raw:: html

   <div style="display: flex;">
       <img src="_images/sample/img33.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
       <img src="_images/sample/img34.png" style="width: 49%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 16. Comparison of the schedule-based and fixed-time accessibility maps for the to- (left) and from- (right) accessibility of the Gesher Theater in Yafo, in 2024</p>

.. _sample_compare_region:

Compare Region accessibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comparison of the Region accessibility works in the same way as the Single-location accessibility comparison. In Figure 17, we present this comparison for the from-accessibility in 2024 and 2018 for the fixed time trip starting at 08:00 in the morning. As can be expected, the Red LRT line essentially increased accessibility for most of the locations in the area. However, there are some locations, far from the Red LRT line, whose accessibility has decreased due to the changes in the bus lines network between 2018 and 2024.
|br|
It is worth noting that in the case of single accessibility when the travel times are compared, the range of the differences is limited by the maximum travel time in each of the accessibility scenarios compared. In the case of Region accessibility, the differences can be much higher. This happens when the accessibility of a building is very low for one of the scenarios since there is no PT line at a walkable distance from this building and other buildings can be reached by foot only, while the PT network of the second scenario reaches the building, and the number of accessible buildings becomes tens or even hundreds of thousands. 

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/sample/img35.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 17. The difference in the from-accessibility for the Region in 2024 and 2018, for the fixed time trip starting at 08:00 in the morning</p>


