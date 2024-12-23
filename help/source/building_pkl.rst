.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>

.. _building_data:  

Data preprocessing for fast routing
-----------------------------------

Accessibility computations are based on repeating routing over the road, which must be topologically correct, and transit networks. To save computation time, the layers of buildings and roads and the GTFS datasets are stored in a special format, as two databases, one for transit and one for the car network routing. These databases must be constructed at the beginning of the accessibility study, based on the topologically correct road network. It is worth constructing these databases for a large area (of up to a million buildings) that covers all potentially interesting locations and regions. Each version of the transit or road network demands its database that is stored in a dedicated folder and the path to it is a parameter of the accessibility algorithms. If you use the externally built database, create the folder and copy the database to this folder. 
|br|
The menu for building databases consists of three items (Figure 1)

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/menu_data_proccessing.png" style="width: 40%; border: 3px solid white; margin-bottom: 10px" />
   </div>
   <p>Figure 1. Data processing section of the Accessibility Calculator menu</p>
   
In this tutorial, we construct a topologically correct version of the road network and then exploit it to construct three databases – the one for car accessibility is limited to the Tel Aviv Metropolitan Area (TAMA), with its 250K buildings; two for transit accessibility, cover the entire Israel. We will use them for accessing TAMA accessibility in different scenarios. Specifically, we use

•	:guilabel:`GTFS folder` is the path to the folder that contains all necessary GTFS files: ``stops.txt``, ``stop_times.txt``, ``routes.txt``, ``trips.txt`` and ``calendar.txt``.
•	The ``gis_osm_roads_free`` OSM TAMA road layer, August 2024.
•	The ``gis_osm_buildings_a_free`` OSM buildings layers for TAMA, August 2024.

The layers of buildings and roads must be a part of the opened QGIS project. The path to the GTFS dataset must be provided as a parameter of the preprocessing procedure. 

Topological cleaning of the road layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The road network can be topologically inconsistent. There are many types of topological errors and the most frequent is the lack of a junction at an intersection of two visually overlapping links. Topologically inconsistent road layers cannot be used for accessibility computations. That is why, the Accessibility Calculator performs the basic topological cleaning of the road network that consists of breaking overlapping links at the intersection and deleting duplicated links. The user can apply more cleaning operations applying the v.clean operation of QGIS, see https://grass.osgeo.org/grass85/manuals/v.clean.html.
|br|
Run the Accessibility Calculator and choose the *Data preprocessing → Build road database option*. In the dialog (Figure 2), enter the parameters:

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/pkl_v_cleen.png" style="width: 60%; border: 3px solid white;margin-bottom: 10px;" />
   </div>
   <p>Figure 2. Build road database dialog</p>

- :guilabel:`Initial road network` -  the initial layer of roads. Must be opened in the current QGIS project.
- :guilabel:`Folder for the cleaned road network` - the folder that contains the constructed layer. This layer will be added to the current GIS project.

Click **Run** to start. The **Progress bar** will show the progress of the computations. If something went wrong, you could break the process of dictionary construction by pressing **Break**. 
|br|
The **Log** tab contains information about the parameters, information on the edits, and the process of construction. For a detailed example of building a road database for TAMA see section 10.2.

Building database for transit accessibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the Accessibility Calculator and choose the *Data preprocessing → Transit routing database* option. In the dictionary construction dialog (Figure 3), enter the parameters:

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/pkl1.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px;" />
   </div>
   <p>Figure 3. The Transit routing database construction dialog</p>

- :guilabel:`Roads database folder` - the folder of the roads database.
- :guilabel:`Layer of buildings` - the layer of buildings. Must be open in a current GIS project. 
- :guilabel:`id` - the unique identifier of a building.
- :guilabel:`GTFS folder` - the path to the folder that must contain all necessary GTFS files: ``stops.txt``, ``stop_times.txt``, ``routes.txt``, ``trips.txt``, ``calendar.txt`` files.
- :guilabel:`Folder to store transit database`- the folder to store the transit routing database.
      
Click **Run** to start. The **Progressbar** will show the progress of the computations. If something went wrong, you could break the process of dictionary construction by pressing **Break**.
|br|
The **Log** tab contains information about the process of construction and a dictionary.
|br|
For a detailed example of building a transit routing database see :ref:`section 10.2<sample_data_preprocessing>`.

.. _building_data_car:  

Building database for car routing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the Accessibility Calculator and choose the *Data preprocessing → Car routing*. Note that the database construction demands two tables (the right part of the dialog). Their meaning is explained in the next section 4.4. 
|br|
In the dictionary construction dialog (Figure 4), enter the parameters:

.. raw:: html

   <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/pkl_car1.png" style="width: 100%; border: 3px solid white;margin-bottom: 10px" />
   </div>
   <p>Figure 4: Car routing database construction dialog</p>

- :guilabel:`Roads database folder` — the folder of the roads database. 
- :guilabel:`link type` — the field of the link’s type in the layer of roads.
- :guilabel:`speed` — the field of the link’s speed in the layer of roads.
- :guilabel:`direction` — the field of traffic direction in the layer of roads.

Currently, we presume that the :guilabel:`direction` field contains the OSM traffic direction codes:
|br2|
B: Two-way link, 
|br2|
F: One-way link, the driving is allowed along the direction the link is drawn, 
|br2|
T: One-way link, driving is allowed against the direction the link is drawn.
|br2|

- :guilabel:`Layer of buildings` - the layer of buildings, must be opened in a current GIS project. 
- :guilabel:`id` - the unique identifier of a building.
- :guilabel:`Default speed (km/h)`- the link’s speed in case the link’s type is missing in the table of links’ speeds.
- :guilabel:`Folder to store car database` - the folder to store the database for car routing.

Click **Run** to start. The **Progress bar** will show the progress of the computations. If something went wrong, you could break the process of dictionary construction by pressing Break.
|br|
The **Log** tab contains information about the constructed dictionary.
For a detailed example of building a database for car routing in TAMA see section 10.2.

Car Speed and Congestion Delay Index 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To compute car accessibility, 
one must know traffic speed along the route.
In the current version of the plugin, the traffic speed is defined by the type of road - a highway, major city street, neighborhood secondary street, etc., and the hour of the day. 
The necessary parameters are stored in two tables that are located in the plugin folder and can be edited. 
|br|
The free-flow traffic speed V\ :sub:`p`\, by the road link types p, is given in the ``car_speed_by_link_type.csv`` table (Figure 3, left). This table contains three fields.
|br2|
``seq`` — the sequential number of the row, 
|br2|
``link_type`` — the OSM type of a link, and 
|br2|
``speed`` — the car speed on the link of this type. 
|br|
The OSM road layer may contain links whose type is missing in the ``car_speed_by_link_type.csv`` table. For these links, the :guilabel:`Default speed (km/h)` will be used.
The hour of the day is reflected by the Congestion Delay Index (CDI) - a ratio of the average, for the hour of a day, speed, to the free flow speed. The CDI values, by hours, are given in the ``cdi_index.csv`` table (Figure 5, right). 
|br|  
The speed V\ :sub:`p`\(t)  on the link of a type p at the hour t is calculated as V\ :sub:`p`\(t)  = V\ :sub:`p`\ *CDI\ :sub:`t`\

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

    <div style="display: flex; justify-content: space-between; ;margin-bottom: 0px">
        
        <div style="margin-right: 0px;">
            
            <table class="custom-table" style="margin-right: 10px;"> 
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
                    <td>track</td>
                    <td>40</td>
                </tr>
                <tr>
                    <td>residential</td>
                    <td>30</td>
                </tr>
                <tr>
                    <td>service</td>
                    <td>40</td>
                </tr>
                <tr>
                    <td>secondary</td>
                    <td>50</td>
                </tr>
                <tr>
                    <td>living_street</td>
                    <td>30</td>
                </tr>
                <tr>
                    <td>tertiary_link</td>
                    <td>50</td>
                </tr>
            </table>
        </div>

        <div>
            
            <table class="custom-table" style="margin-right: 10px;">
                <tr>
                    <th style="width: 150px;">hour</th>
                    <th style="width: 100px;">CDI</th>
                </tr>
                <tr>
                    <td>0</td>
                    <td>1.0</td>
                </tr>
                <tr>
                    <td>1</td>
                    <td>1.0</td>
                </tr>
                <tr>
                    <td>2</td>
                    <td>1.0</td>
                </tr>
                <tr>
                    <td>3</td>
                    <td>1.0</td>
                </tr>
                <tr>
                    <td>4</td>
                    <td>1.0</td>
                </tr>
                <tr>
                    <td>5</td>
                    <td>0.9</td>
                </tr>
                <tr>
                    <td>6</td>
                    <td>0.75</td>
                </tr>
                <tr>
                    <td>7</td>
                    <td>0.6</td>
                </tr>
                <tr>
                    <td>8</td>
                    <td>0.6</td>
                </tr>
                <tr>
                    <td>9</td>
                    <td>0.65</td>
                </tr>
            </table>
        </div>
    </div>
   <p>Figure 5. Several first rows of the free flow speeds table (left) and the CDI table (right). The values of the free flow speed and CDI can be changed by the user.</p>



 
