How does this program work?
===========================


Three layers of abstraction
---------------------------


The core of this program is divided into three different layers.

The inner most layer is the **JOB**, the second is the **work_manager** and the outer most layer is the **batch_manager**.


| The **JOB** is the most basic unit of work. It is a single calculation that needs to be done.
 For an orca calculation this would be the desired molecule and the orca input file. 
| Each job can be in different stages depending on its process. 
| These stages go from *initilized* -> *submitted* -> *running* -> *returned* -> *finished*
| Jobs only have information about themselves and their current status.



| The **work_manager** is responsible for managing the jobs. It is the layer that interacts with the calculation module.
 In the beginning each work_manager is given a list of jobs and a single calculation config. (eg. a specific optimization *or* a single point calculation)
 The work manager will create all necessary input files and folders and submit the jobs via *slurm*.
 It then enters a loop to continually check and update the status of the jobs.
| Prepare new jobs -> Submit jobs -> Check submitted jobs -> Manage returned jobs -> Check if all jobs are done -> Wait -> Repeat
| Should new input files appear in its managed directories the new calculation will be initialized and submitted.
 Once all its jobs are finished it will automatically shut off.
| The work_manager only has information about the jobs it is managing and its own calculation config.



The **batch_manager** is the outer most layer and is responsible for managing the *work_managers*.
it is given a list of molecules and a list of calculations as well as the order these calculations are to be performed in.

.. image:: example_config.png
   :alt: Description of the image
   :width: 400px
   :align: center

The example flow chart reads as follows:

First all molecules are optimized according to the config in **Optimization A**.
Next for all molecules both **FREQ** and **Optimization B** are performed.
Finally another *FREQ* is performed only on the results of **Optimization B**.


To do this the batch_manager will create a work_manager for each calculation setup and give it the list of molecules.
It will then enter a loop to continually monitor if all work_managers are finished.
As long as they are not yet finished it will check for finished outputs and either move them to their next work manager or to the *finished_results* folder.
Once all work_managers are finished and all results collected it will automatically shut off. When this happens all tasks are completed and the program is done.


