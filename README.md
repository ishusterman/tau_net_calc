# What is it all about?

What is it all about?
The goal of the Accessibility Calculator plugin is to assess transport accessibility at the resolution of a single building. The assessment is based on a precise estimation of the travel time between the Origin (O), and the Destination (D) buildings of a trip. The OD travel time depends on the transportation mode which can be a Public Transport (PT) or a Private Car. The results of accessibility computations are stored as a CSV table that presents the details of trips and presented visually as an accessibility map.

# ACCESSIBILITY plugin accounts for every component of a trip

The PT or car trip consists of several components: A PT user walks from the O-building to the initial stop, waits for a PT vehicle (bus, tram, metro, other), rides to the transfer stop, waits for the next PT vehicle, and, after, possibly, more transfers, alights at the final stop and walks to the D-building. The car traveler takes a walk from the O-building to the parked car, drives to the destination, finds a parking place nearby, and then walks to the D-building.

# The algorithms employed in the ACCESSIBILITY plugin

-   We employ the modified RAPTOR algorithm for estimating the PT accessibility based on [https://github.com/transnetlab/transit-routing](https://github.com/transnetlab/transit-routing).
-   To estimate accessibility with the private car we employ
    Dijkstra algorithm, also with modifications.

# The data necessary for ACCESSIBILITY computations

To use the Accessibility Calculator, you need three sets of data, all covering the region of your interest:

- The layer of roads.

- The layer of buildings that are represented by polygons or points.

- The GTFS dataset of the PT network and schedule.

Three datasets are checked and translated into three fast-access databases. The first one contains a topologically cleaned road network, the second is constructed for computing transit accessibility and the third is constructed for computing car accessibility. It is often convenient to use datasets that cover an area that is larger than the region of the current interest.

# From-accessibility versus To-accessibility

From-accessibility is based on the travel time from each of the selected buildings to all other locations in the city. The typical application of from-accessibility is the assessment of the residents’ travel time to the locations of their possible employment.
To-accessibility is based on the travel time to each of the selected buildings from all other locations in the city. The typical application of to-accessibility is the assessment of the residents’ travel time to shops and attractions in the city center.

# Service area of several facilities versus accessibility of all buildings in the region

From- and To-accessibility computations can be performed to assess the service area of several facilities located in the buildings or aggregate measures of accessibility for all buildings in the region of interest – region accessibility. In both cases, origins and destinations can be all or just selected buildings. In the latter case, the selected buildings will be stored as a layer as a part of the results.
The service area consists of buildings that can be served by at least one of the facilities.

The “From” service area of the set of facilities includes all buildings that can be reached in maximum travel time or faster, from at least one of the facilities in this set. If the building can be reached from several facilities, then the trip with the minimal travel time is considered.

The “To” service area of the set of facilities, includes all buildings from which at least one of the facilities can be reached in maximum travel time or faster. If several facilities can be reached, then the trip with minimal travel time is considered.

The details of each leg of the fastest trips are stored as attributes of the served building and the thematic map presents the total travel time from the facilities to the served building or from the served building to the facility. Importantly, the service area of every facility is also stored. The user can exploit this file for computing other measures of accessibility, like the area from where the residents can reach more than half of the facilities in the center of the city in a maximum travel time.
The region accessibility represents aggregate measures of accessibility for each building in the region.

The default aggregate measure of the from-accessibility for the region’s building is the number of other buildings accessible from it. Other measures, like the number of shops, or jobs, accessible from the building can be calculated if the information on jobs or use at a building resolution is available.

The default aggregate measure of the to-accessibility for the region’s building is the number of buildings from which it is accessible. Other measures, like the total population that can reach the building, can be calculated if the information on the population at a building resolution is available.

The accessibility of a region is computed at a time resolution that is defined by the user. All aggregate measures are stored as attributes of the region’s buildings, for each time interval.

# Adjustment of the trip’s start or arrival time to the transit timetable

Modern transit users are aware of the time the bus or train arrives at the stop they plan to start from, or to the final stops of their trip, and plan their trips accordingly. To assess the accessibility for these informed users we modify the RAPTOR algorithm to account for the schedule-based trip’s start or finish. Schedule-defined accessibility can be chosen for each of the From/To and Location/Region regimes.

# Car speed for accessibility computation

The assessment of car accessibility is based on the traffic speed of the
OD route. We assume that the traffic speed is defined by the type of the
road - a highway, major city street, neighborhood secondary street, etc.
The average speed for every road type is provided by a user-defined
table of average speeds by the road type.

# Comparing accessibility scenarios

The study of accessibility does not end with assessment of **Service area** or
**Region** accessibility. Typically, we compare accessibility for
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

-   In the **Service area** regime - the travel time to, or from a certain
    building
-   In the **Region** regime - the number and the aggregate parameters of
    buildings that can be accessed from a certain O-building, or from
    which a certain D-building can be accessed

These results are presented as thematic maps. These maps can be built
based on the buildings themselves, but the gaps between buildings
prevent clear view of the phenomenon. The better view can be constructed
based on the continuous coverages and ACCESSIBILITY plugin employ
covereges of two kinds:

-   Voronoi polygons constructed based on the buildings\' foundations    
-   H3 hexagons, of the h11, h10, h9 and h8 scales.