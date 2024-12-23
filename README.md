# What is it all about?

The goal of the ACCESSIBILITY plugin is to assess transport
accessibility at the resolution of a single building. The assessment is
based on a precise estimation of the travel time between the building of
the trip Origin (O), and the Destination (D) building.
The OD travel time depends on the transportation mode that can be
Public Transport (PT) or Private Car.

# ACCESSIBILITY plugin accounts for every component of a trip

The PT trip consists of many elementary components: A traveler walks
from the O-building to the PT stop, waits for a bus, rides to the
transfer stop, waits for the next bus, and, after, possibly, additional
transfers, alights at the final stop and walks to the D-building.

The car traveler takes a walk from the O-building to the parked car,
drives to the parking place near the destination, and then walks to
the D-building.

# The algorithms employed in the ACCESSIBILITY plugin

-   We employ the modified RAPTOR algorithm for estimating the PT accessibility based on [https://github.com/transnetlab/transit-routing](https://github.com/transnetlab/transit-routing).
-   To estimate accessibility with the private car we employ
    Dijkstra algorithm, also with modifications.

# The data necessary for ACCESSIBILITY computations

To use the ACCESSIBILITY plugin you need three sets of data, all
covering the same region:

-   The standard GTFS dataset that represents the PT network and schedule.
-   The topologically correct layer of roads.
-   The layer of buildings represented by polygons (better) or points.

In this tutorial we use: Israel GTFS dataset available from the
<https://gtfs.pro/>, and
the OSM layers of roads and buildings for Israel - gis_osm_roads_free
and gis_osm_buildings_a_free.
These three datasets are translated into the fast-access dictionary
that serves as an input for all ACCESSIBILITY algorithms.

# Forward versus Backward accessibility

Forward accessibility is based on the travel time FROM each of the
selected buildings TO all other locations in the city.

The typical application of forward accessibility is the assessment of
the residents\' travel time to the locations of their possible
employment.

Backward accessibility is based on the travel time TO each of the
selected buildings FROM all other locations in the city.

The typical application of backward accessibility is the assessment of
the travel time that will take urban residents to reach each of the
attractions in the city center.

# AREA and MAP regimes of accessibility computation

-   The Forward **AREA** regime assesses travel time for the travelers
    who start their trip from one or a few selected building(s).
-   The Backward **AREA** regime assesses travel time for the travelers
    who finish their trip at one or a few selected building(s).

The AREA-based assessment included detailed description of each OD trip.

-   The Forward **MAP** regime assesses what can be accessed, in a given
    time, from each of the buildings in the city region - the number of
    accessible buildings and their total capacity for work, commerce, or
    leisure.
-   The Backward **MAP** regime assesses from where each building in the
    city region can be accessed in a given time - the number of
    buildings from which it can be accessed and the aggregate parameters
    of these buildings, like total population numbers.

The MAP-based assessment is performed at a predefined time resolution
of, typically, 5 minutes.

# Adjustment of the start or arrival time to the transit timetable

The modern PT users are aware of the time the bus ariives to the stop
they plan to start from, or to the final stops of their trip, and plan
their trips accordingly.

To assess the accessibility for these informed users we modify the
RAPTOR algorithm to account for their schedule-based start or finish of the trip.

# Car speed for accessibility computation

The assessment of car accessibility is based on the traffic speed of the
OD route. We assume that the traffic speed is defined by the type of the
road - a highway, major city street, neighborhood secondary street, etc.
The average speed for every road type is provided by a user-defined
table of average speeds by the road type.

# Comparing accessibility scenarios

The study of accessibility does not end with assessment of **AREA** or
**MAP** accessibility. Typically, we compare accessibility for
different scenarios of urban transportation development.

The ACCESSIBILITY plugin includes three options for this comparison:

-   Relative accessibility, is typically used for assessing the ratio
    of the PT and Car travel times.
-   Accessibility difference, is typically used for comparing
    scenarios of the PT scheduling or road network development.
-   Relative accessibility difference, combines two above measure,
    estimating the difference between accessibility in two scenarios
    divided the accessibility in the first of them.

To compare two scenarios, accessibility for each of them must be ready.

# Visualization of accessibility computations

The results of the accessibility computations are stored as buildings\'
attributes. It can be

-   In the **AREA** regime - the travel time to, or from a certain
    building
-   In the **MAP** regime - the number and the aggregate parameters of
    buildings that can be accessed from a certain O-building, or from
    which a certain D-building can be accessed

These results are presented as thematic maps. These maps can be built
based on the buildings themselves, but the gaps between buildings
prevent clear view of the phenomenon. The better view can be constructed
based on the continuous coverages and ACCESSIBILITY plugin employ
covereges of two kinds:

-   Voronoi polygons constructed based on the buildings\' foundations    
-   H3 hexagons, of the h11, h10, h9 and h8 scales.

