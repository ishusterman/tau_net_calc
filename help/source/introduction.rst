.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>


Introduction
***************
What is it all about?
--------------------------

The goal of the Accessibility Calculator plugin is to assess transport accessibility at the resolution of a single building. The assessment is based on a precise estimation of the travel time between the Origin (O), and the Destination (D) buildings of a trip. The OD travel time depends on the transportation mode which can be a Public Transport (PT) or a Private Car. The results of accessibility computations are stored as a CSV table that presents the details of trips and presented visually as an accessibility map.

Accessibility Calculator accounts for every component of a trip
--------------------------------------------------------------------
The PT or car trip consists of several components: A PT user walks from the O-building to the initial stop, waits for a PT vehicle (bus, tram, metro, other), rides to the transfer stop, waits for the next PT vehicle, and, after, possibly, more transfers, alights at the final stop and walks to the D-building. The car traveler takes a walk from the O-building to the parked car, drives to the destination, finds a parking place nearby, and then walks to the D-building.

The Algorithms of Accessibility Calculator
------------------------------------------

•	To estimate transit accessibility we employ the :term:`RAPTOR algorithm <RAPTOR Algorithm>`.
•	To estimate accessibility with the private car we employ the :term:`Dijkstra algorithm <Dijkstra Algorithm>`.

Both algorithms are modified to deal with real-world data on the transit and road networks and to consider accessibility to city buildings and not only network nodes.
|br|

The data necessary for accessibility computations
------------------------------------------------------
To use the Accessibility Calculator, you need three sets of data, all covering the region of your interest:

•	The layer of roads.
•	The layer of buildings that are represented by polygons or points.
•	The :term:`GTFS <GTFS>` dataset of the PT network and schedule.

Three datasets are checked and translated into three fast-access databases. The first one contains a topologically cleaned road network, the second is constructed for computing transit accessibility and the third is constructed for computing car accessibility. It is often convenient to use datasets that cover an area that is larger than the region of the current interest.  
|br|
In this tutorial, we use GTFS datasets that cover the entire Israel and exploit them for computing accessibility maps for the Tel Aviv Metropolitan Area. The Israeli GTFS datasets are available from https://gtfs.pro/, and in our examples, we use GTFS datasets for June 2018 and June 2024. The OSM layers of roads and buildings for Israel are available from https://www.openstreetmap.org/. In this tutorial, we use the ``gis_osm_buildings_a_free`` layer of buildings (as polygons) and the ``gis_osm_roads_free layer`` layer of roads.

.. note:: The layer of roads that you download from the OSM site often contains significant topological errors and must be topologically cleaned before using for computations. This cleaning is a part of the construction of the road database, see section 4.2. 

The menu of Accessibility  Calculator
-------------------------------------

Figure 1 presents the menu of the Accessibility Calculator.

*The service area is employed for accessing accessibility of the specific set of locations.*
|br|
*The region accessibility is employed for assessing accessibility of all locations in the area.*

In this introductory section, we briefly present the abilities of the Accessibility Calculator. Each of these abilities is then presented in detail in the consequent sections.

.. raw:: html

    <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/mainwindow.png" style="width: 50%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 1. The menu of the Accessibility Calculator</p>

Constructing Databases
----------------------

To accelerate data access for accessibility computations and fix the data inconsistencies, all three datasets necessary for computations are translated into the internal databases. You can build different databases for different versions of the infrastructure or transit network development, assess accessibility for each of them, and compare the results. The databases are usually constructed for large areas, or even the entire country. We recommend working with the datasets that represent areas containing 0.5-1M buildings.

From-accessibility versus To-accessibility
------------------------------------------

From-accessibility is based on the travel time from each of the selected buildings to all other locations in the city (Figure 2 left). The typical application of from-accessibility is the assessment of the residents’ travel time to the locations of their possible employment. 
|br|
To-accessibility is based on the travel time to each of the selected buildings from all other locations in the city (Figure 2 right). The typical application of to-accessibility is the assessment of the residents’ travel time to shops and attractions in the city center.


.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/forward-backward.png" style="width: 70%; border: 3px solid white;margin-bottom: 20px" />
   </div>
   <p>Figure 2. From-accessibility (left) versus To-accessibility (right)</p>

|br|

Service area of several facilities versus accessibility of all buildings in the region
--------------------------------------------------------------------------------------

From- and To-accessibility computations can be performed to assess the service area of several facilities located in the buildings or aggregate measures of accessibility for all buildings in the region of interest – *region accessibility*. In both cases, origins and destinations can be all or just selected buildings. In the latter case, the selected buildings will be stored as a layer as a part of the results. 
|br|
*The service area* consists of buildings that can be served by at least one of the facilities.

•	The “From” service area of the set of facilities includes all buildings that can be reached in maximum travel time or faster, from at least one of the facilities in this set. If the building can be reached from several facilities, then the trip with the minimal travel time is considered.
•	The “To” service area of the set of facilities, includes all buildings from which at least one of the facilities can be reached in maximum travel time or faster. If several facilities can be reached, then the trip with minimal travel time is considered.

The details of each leg of the fastest trips are stored as attributes of the served building and the thematic map presents the total travel time from the facilities to the served building or from the served building to the facility. Importantly, the service area of *every* facility is also stored. The user can exploit this file for computing other measures of accessibility, like the area from where the residents can reach more than half of the facilities in the center of the city in a maximum travel time. 
|br|
*The region accessibility* represents aggregate measures of accessibility for each building in the region.

•	The default aggregate measure of the from-accessibility for the region’s building is the number of other buildings accessible from it. Other measures, like the number of shops, or jobs, accessible from the building can be calculated if the information on jobs or use at a building resolution is available.
•	The default aggregate measure of the to-accessibility for the region’s building is the number of buildings from which it is accessible. Other measures, like the total population that can reach the building, can be calculated if the information on the population at a building resolution is available.

The accessibility of a region is computed at a time resolution that is defined by the user. All aggregate measures are stored as attributes of the region’s buildings, for each time interval.


Adjustment of the trip’s start or arrival time to the transit timetable
-----------------------------------------------------------------------

Modern transit users are aware of the time the bus or train arrives at the stop they plan to start from, or to the final stops of their trip, and plan their trips accordingly. To assess the accessibility for these informed users we modify the :term:`RAPTOR algorithm <RAPTOR Algorithm>` to account for the schedule-based trip’s start or finish. Schedule-defined accessibility can be chosen for each of the From/To and Location/Region regimes.

|br|

.. _car_speed_by_link_type:

Car speed for accessibility computation
--------------------------------------------

To compute car accessibility, one must know traffic speed along the route. In the current version of the plugin, the traffic speed is defined by the type of road - a highway, major city street, neighborhood secondary street, etc., and the hour of the day. The free flow traffic speeds V\ :sub:`p`\, by the road link types p, is given in the ``car_speed_by_link_type.csv`` table (Figure 3, left). 
The effect of the hour of the day is reflected by the Congestion Delay Index (CDI) - a ratio of the average, for the hour of a day, speed to the free flow speed, and stored in the ``cdi_index.csv`` table (Figure 3, right). Both tables are stored in the system folder and can be edited by the user.

The speed V\ :sub:`p`\(t) on the link of a type p at the hour t is calculated as V\ :sub:`p`\(t)  = V\ :sub:`p`\*CDI\ :sub:`t`\.

.. raw:: html

    <style>
        .custom-table {
            border-collapse: collapse;
            width: 100%;
        }  

        .custom-table th, .custom-table td {
            border: 1px solid #d3d3d3; 
            padding: 8px;
            text-align: center;  
            vertical-align: middle;
        }

        .custom-table th {
            background-color: white;
            font-weight: normal;  
        }

        .custom-table tr:nth-child(even) {
            background-color: #f0f8ff; 
        }

        .custom-table tr:nth-child(odd) {
            background-color: white; 
        }
    </style>

    <div style="display: flex; justify-content: space-between;margin-bottom: 10px">
        
        <div style="margin-right: 10px;">
            
            <table class="custom-table">
                <tr>
                    <th style="width: 150px;">link type</th>
                    <th style="width: 150px;">speed (km/h)</th>
                </tr>
                <tr>
                    <td>busway</td>
                    <td>18</td>
                </tr>
                <tr>
                    <td>cycleway</td>
                    <td>15</td>
                </tr>
                <tr>
                    <td>footway</td>
                    <td>3</td>
                </tr>
                <tr>
                    <td>motorway_link</td>
                    <td>40</td>
                </tr>
                <tr>
                    <td>...</td>
                    <td>...</td>
                </tr>
            </table>
        </div>

        
        <div>
            
            <table class="custom-table">
                <tr>
                    <th style="width: 150px;">hour</th>
                    <th style="width: 100px;">cdi</th>
                </tr>
                <tr>
                    <td>0</td>
                    <td>1.0</td>
                </tr>
                <tr>
                    <td>...</td>
                    <td>...</td>
                </tr>
                <tr>
                    <td>5</td>
                    <td>0.9</td>
                </tr>
                <tr>
                    <td>6</td>
                    <td>0.65</td>
                </tr>
                <tr>
                    <td>...</td>
                    <td>...</td>
                </tr>
            </table>
        </div>
    </div>
    <p>Figure 3. Free flow speeds by the link types (left) and the CDI index, by hours of the day (right)</p> 


Comparison of accessibility computations for different scenarios
----------------------------------------------------------------

Typically, the accessibility is computed for different scenarios of urban transportation development, and then the outputs for these scenarios are compared. 
|br|
Let the scenarios be S\ :sub:`1`\  and S\ :sub:`2`\  and accessibility for each of them is already computed. The Accessibility Calculator includes three options for comparison scenarios’ outputs:

•	Relative accessibility: 
         The ratio R\ :sub:`1,2`\ = S\ :sub:`1`\/S\ :sub:`2`\  of the outputs of S\ :sub:`1`\  and S\ :sub:`2`\, by buildings. 
•	Accessibility difference: 
         The difference D\ :sub:`1,2`\ = S\ :sub:`1`\ – S\ :sub:`2`\  of the outputs of S\ :sub:`1`\  and S\ :sub:`2`\, by buildings.
•	Relative accessibility difference: 
         The relative difference RD\ :sub:`1,2`\ = (S\ :sub:`1`\ – S\ :sub:`2`\)/S\ :sub:`2`\  of the outputs of S\ :sub:`1`\  and S\ :sub:`2`\, by buildings.

Note that scenarios S\ :sub:`1`\  and S\ :sub:`2`\  must be comparable, i.e.,  both must be for the same single location or, in the case of region accessibility, for the overlapping regions. The Accessibility Calculator tests the comparability of the scenarios, and either reports incomparability or performs the comparison.

Visualization of accessibility computations
-------------------------------------------

The Accessibility Calculator results are always presented as thematic maps. These maps are based on one of the coverages that are supplied together with the plugin (Figure 4):

•	:term:`Voronoi polygons <Voronoi diagram>` that are constructed based on the buildings’ foundations,
•	:term:`H3 hexagons <H3>` of the h11, h10, h9, and h8 scales.

.. raw:: html

   <div style="display: flex; justify-content: space-between;">
       <img src="_images/sample/visual1.png" style="width: 32%; border: 0px solid black;margin-bottom: 10px" />
       <img src="_images/sample/visual2.png" style="width: 32%; 
       border: 0px solid black;margin-bottom: 20px" />
       <img src="_images/sample/visual3.png" style="width: 32%; border: 0px solid black;margin-bottom: 10px" />
   </div>
   <p>Figure 4: Left to right – The 45-min transit service maps from the Gesher theater in the center of the Yafo area, Tel Aviv, presented with the Voronoi polygons, h3-10, and h3-9 hexagons</p>

|br|

Accessibility Calculator visualization options are considered in :doc:`section 9 <visualization>`.
