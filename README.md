# What is it all about?

The goal of the Accessibility Calculator plugin is to assess transport accessibility at the resolution of a single building or at a lower resolutions represented by several layers of hexagons, constructed within the plugin. Each hexagon is considered as a larger building that aggregates the information of all buildings whose centroids are inside it.

The assessment is based on a precise estimation of the travel time between the Origin (O) and the Destination (D) buildings of a trip. The OD travel time depends on the transportation mode, which can be Public Transport (PT) or a Private Car. The results of each accessibility computation scenario are stored as a set of tables in the GeoPackage format and presented visually as accessibility maps.


# The ACCESSIBILITY plugin accounts for every component of a trip

A PT or car trip consists of several legs: A PT user walks from the O-building to the initial stop, waits for a PT vehicle (bus, tram, metro, or other), rides to the transfer stop, waits for the next PT vehicle, and, after possibly more transfers, alights at the final stop and walks to the D-building. A car traveler walks from the O-building to the parked car, drives to the destination, finds a parking place nearby, and then walks to the D-building.

# The algorithms employed in the ACCESSIBILITY plugin

-   We employ a modified RAPTOR algorithm for estimating PT accessibility based on [https://github.com/transnetlab/transit-routing](https://github.com/transnetlab/transit-routing).
-  To estimate accessibility with a private car, we employ the Dijkstra algorithm, also with modifications.

# The data necessary for ACCESSIBILITY computations

To use the Accessibility Calculator, you need three sets of data, all covering your region of interest:
- A layer of roads represented by polylines.
- A layer of buildings represented by polygons.
- A GTFS dataset that represents the PT lines, stops, and schedules.

These three datasets are translated into: a topologically cleaned layers of the road network and buildings, and fast-access databases for computing transit accessibility, and car accessibility.


# FROM-accessibility versus TO-accessibility versus ROUNDTRIP-accessibility

- **FROM-accessibility** assesses the travel time from each origin building to all other buildings, given the start time of a trip. FROM-accessibility answers the question: *“Where can you get from here in half an hour or less, starting at 10:00 in the morning?”*
- **TO-accessibility** is based on the travel time to all destination buildings from all other buildings, given the arrival time. TO-accessibility answers the question: *“From where can you get here at 10:00 in the morning in half an hour or less?”*
- **ROUNDTRIP-accessibility** is based on the travel time between the origin and destination and back, given the time of arrival at the destination and the time of starting the trip back from there. ROUNDTRIP-accessibility answers the question: *“From where can you get here at 10:00 and then return to your origin at 16:00, if you want to limit your total travel time to no more than an hour?”*


# Service area

- The **FROM-service area** of a set of facilities includes all buildings that can be reached within a maximum travel time or faster, starting the trip in a certain hour, from at least one of the facilities in this set. If a building can be reached from several facilities, the trip with the minimal travel time is accounted for. In addition, the travel time from each of the facilities is stored.
- The **TO-service area** of a set of facilities includes all buildings from which at least one of the facilities can be reached within a maximum travel time or faster, arriving at the facility at a certain time. If several facilities can be reached, the trip with the minimal travel time is accounted for. In addition, the travel time to each of the facilities is stored.
- The **ROUNDTRIP-service area** of a set of facilities includes all buildings from which a roundtrip to the facility and back will take no more than a certain total travel time. If several facilities satisfy this condition, the travel time to the closest one is accounted for. In addition, the roundtrip travel time to each of the facilities is stored.

# Cumulative Number of Opportunities (CNO)

The CNO is an aggregate measure of accessibility computed for each building B in the area.
- The default CNO measure of a building's **FROM-accessibility** is the total number of buildings in the area accessible from **B** within a given travel time, starting at a certain hour of the day. Other measures, like the total number of shops or jobs accessible from **B**, can be calculated if information on jobs or building use is available.
- The default CNO measure of a building's **TO-accessibility** is the total number of buildings from which it is possible to arrive at **B** at a certain hour of the day and within a given travel time. Other measures, like the total population that can reach **B**, can be calculated if information on the buildings’ population is available.
- The default CNO measure of a building's **ROUNDTRIP-accessibility** is the total number of buildings from which it is possible to arrive at **B**, arriving at a certain hour of the day, and then get back, starting at another hour of a day, within a given total travel time. Other measures, like the total population that can reach the building and get back, can be calculated if information on the buildings’ population is available.

# Adjustment of the trip’s start or arrival time to the transit timetable

Modern transit users are aware of the time a bus or train arrives at the stop they plan to start from, or at the final stop of their trip, and plan their trips accordingly. To assess accessibility for these informed users, we modify the RAPTOR algorithm to account for schedule-based trip start or finish. Schedule-based accessibility can be chosen for each of the FROM/TO/ROUNDTRIP and Service Area/Cumulative Number of Opportunities regimes.

# Car speed for accessibility computation

The assessment of car accessibility is based on traffic speed, and we assume that it is defined by the type of the road (e.g., a highway, major city street, neighborhood secondary street, etc.) and the hour of the day.

# Comparing accessibility scenarios

The ACCESSIBILITY plugin includes three options for comparing accessibility across different urban transportation development scenarios:
- **The difference in accessibility**, calculated as a difference in travel times or a cumulative numbers of opportunities in two scenarios.
- **Relative accessibility**, calculated as a ratio of travel times or a cumulative numbers of opportunities in two scenarios.
- **Relative difference**, calculated as a ratio of the difference in travel times or cumulative numbers of opportunities divided by the values of the measure for the second scenario.


# Visualization of accessibility computations

The results of the accessibility computations are stored as attributes of buildings or aggregating hexagons and presented as thematic maps.