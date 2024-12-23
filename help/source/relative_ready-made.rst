.. |br| raw:: html

  <span style="display: block; margin-top: 5px;"></span>

.. |br2| raw:: html

   <br/>

.. _relative_ready-made:  

Compare accessibility maps
==========================

Accessibility is a relative characteristic. Typically, every accessibility study demands a comparison of the results of accessibility computations for two or more scenarios that consider different travel modes or different sets of parameters. This section explains the *Compare accessibility* maps part of the Accessibility Calculator menu (Figure 1) that is developed for this purpose.
 
.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <img src="_images/mainwindow-compare.png" style="width: 35%; border: 3px solid white;margin-bottom: 10px" />
   </div>
    <p>Figure 1. <i>Compare accessibility menu</i></p>

The Accessibility Calculator verifies that the comparison can be performed based on the Log files of the scenarios. These log files must be in the folder of each scenario’s output, otherwise the comparison will be quit. The compatibility tests verify that:

-	The scenarios are both for the service area or for the regions.
-	The overlap between the regions is not empty. 
-	In the REGION regime, the time bins of both outputs are the same.

|br|
Note that the comparison of the from-accessibility maps to the to-accessibility maps is allowed.
|br|
If the tests are all passed successfully, the comparison made for the spatially overlapping parts of the output. The non-overlapping parts are presented as additional layers, together with the results of the comparison. 
|br|
The dialog and parameters  of the *Compare accessibility maps → Service areas or Region* computations same. We illustrate them with the *Compare accessibility maps → Service areas* comparison.
|br|
Enter the parameters:

   .. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/compare.png" style="width: 70%; border: 3px solid white;margin-bottom: 10px" />
      </div>   

:guilabel:`Result1 folder` — the folder that contains the results of the first scenario.
|br|
:guilabel:`Name of file1`— the CSV file of the Scenario_1 results in the
:guilabel:`Result1 folder` is found automatically.
|br|
:guilabel:`Result2 folder` — the folder that contains the results of the second scenario.
|br|
:guilabel:`Name of file2` — the CSV file of the Scenario_2 results in the :guilabel:`Result2 folder` is found automatically.
|br|
:guilabel:`Output folder` — the folder to store the results of the comparison.
|br|
:guilabel:`Output alias` — the alias for the files of results and layers of visualization.
|br|
:guilabel:`Basic visualization layer` — the name of the layer that will be used for visualization of accessibility maps, must be a part of the current QGIS project. 
|br|
:guilabel:`id`- the name of the unique identifier field of the visualization layer unit. The identifiers must be the subset of buildings’ identifiers. More information :doc:`here <visualization>`.
|br|
The measures of comparison:
|br2|   
:guilabel:`Ratio: Result_1/Result_2` — the ratio of the result of the first scenario to the results of the second scenario, for the overlapping part of the outputs.
|br|
:guilabel:`Difference: Result_1 - Result_2` — the difference between the result of the first scenario and the results of the second scenario, for the overlapping part of the outputs.
|br|
:guilabel:`Relative difference: [Result_1 - Result_2]/Result 2` — the difference between the result of the first scenario and the results of the second scenario divided by the result of the second scenario, for the overlapping part of the outputs. The result is presented in percents.
|br|
For each of the three cases, in addition to the map of the selected measure of difference, two more maps are presented. The first one presents the buildings that were not accessible in Scenario 1 (Result_1 is NULL) but are accessible in Scenario 2 (Result_2 is not NULL). The second map presents the buildings that were not accessible in Scenario 2 (Result_2 is NULL) but are accessible in Scenario 1 (Result_1 is not NULL). 
|br|
Click **Run** to start. The **Progress bar** shows the progress of the computations. You can break the process of the computations by pressing **Break**.
|br|
The **Log** tab repeats the **Log** information of each of the compared scenarios and contains the metadata about the chosen measures and the overlapping parts of the outputs. If the comparison has failed the Log file contains the reason for the failure (Figure 2). 


.. raw:: html

      <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <img src="_images/compare_log.png" style="width: 60%; border: 3px solid white;margin-bottom: 10px" />
      </div>
      <p>Figure 2. The log file of the Compare accessibility maps output</p>

The example of the *Compare accessibility map → Service areas*, see :ref:`here<sample_compare_single>`.
|br2|
The example of the *Compare accessibility map → Region*, see :ref:`here<sample_compare_region>`.