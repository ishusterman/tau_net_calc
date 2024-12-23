.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>
.. _visualization:  

Visualization of accessibility map
==================================

Accessibility Calculator always presents the thematic map of the results. In the case of the *Service area* regime, these are maps of the travel time. In the case of the *Region regime*, these are the thematic maps of the aggregate measures.

The style of presentation
-------------------------

The default map style is **Graduated**. The [Minimum accessibility, Maximal accessibility] interval is split into bins as follows: 

- *Service area* accessibility - a constant 5-minute bin.
- *Region* accessibility – the interval is split into the  :guilabel:`Number of bins`.
- *Compare accessibility* – the [MIN, MAX] interval of the result is divided into deciles.

The palettes for the visualization are supplied with the Accessibility Calculator and presented in the examples of this and other sections. 

The layers for visualization
----------------------------

The results can be visualized based on:

- The layer of buildings (not recommended)
- The layer of the :term:`Voronoi polygons <Voronoi diagram>` that are constructed based on the buildings’ foundations.
- The layers of :term:`hexagonal cells h3 <h3>` at resolutions of h8, h9, h10, h11.

The layers of the Voronoi polygons and four h3 hexagon layers at resolutions of h8, h9, h10, and h11 for Israel are supplied with the Accessibility Calculator.
|br|
The IDs of the visualization polygons must repeat the IDs of some of the buildings, and each polygon will present the results for the building with this ID. The maps below (Figure 1) present the results of the same computations based on the Voronoi polygons of buildings, h3-11, h3-10, and h3-9 hexagons.

.. raw:: html

   <div style="display: flex; justify-content: space-between;">
       <img src="_images/sample/vis1.png" style="width: 48%; border: 0px solid black;margin-bottom: 10px" />
       <img src="_images/sample/vis2.png" style="width: 48%; border: 0px solid black;margin-bottom: 10px" />
   </div>

.. raw:: html

      <div style="display: flex; justify-content: space-between;">
       <img src="_images/sample/vis3.png" style="width: 48%; border: 0px solid black;margin-bottom: 10px" />
       <img src="_images/sample/vis4.png" style="width: 48%; border: 0px solid black;margin-bottom: 10px" />
   </div>
   <p>Figure 1. Gesher Theater in Yafo from accessibility at 22:30, after the performance is finished. Calculated with the <i>Transit accessibility maps → Service area → From location Fixed-time departure</i> option. Visualized with the Voronoi polygons of buildings (top-left), h3-11 hexagons (top-right), h3-10 hexagons (bottom left), and h3-9 hexagons (bottom right)</p>

Visualization of accessibility maps comparison
----------------------------------------------

The map in Figure 2 presents the region accessibility map. 

.. raw:: html

  <div style="display: flex; justify-content: center">
       <img src="_images/sample/vis5.png" style="width: 50%; border: 0px solid black;margin-bottom: 10px" />
  </div>
  <p>Figure 2. <i>Transit accessibility map → Region → From every location – fixed time departure</i> accessibility map. Visualization of the number of buildings accessible in 45 minutes from each of the region’s buildings</p>

Figure 3 presents the comparison between two to-accessibility scenarios of the Yafo Gesher Theater at the beginning of the performance, 20:00. One of them is computed before and the other after the Red LRT line was established in the Tel Aviv Metropolitan Area in 2024.

.. raw:: html

      <div style="display: flex; justify-content: space-between;">
       <img src="_images/sample/vis6.png" style="width: 48%; border: 0px solid black;margin-bottom: 10px" />
       <img src="_images/sample/vis7.png" style="width: 48%; border: 0px solid black;margin-bottom: 10px" />
   </div>
   <p>Figure 3. The map output of the <i>Compare accessibility maps → Service Area</i> option.</p> 
   
In 2024, after the Red LRT line was established, accessibility to the distant buildings in the North-East along the LRT line increased (greenish), while accessibility to the buildings to the south and west of the LRT line decreased (brownish) due to cancellation of several bus lines (left map). Note, that many additional buildings became accessible after the Red LRT line was established (right map)

For more examples of visualization see :ref:`here<sample_compare_single>`.
