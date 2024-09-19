CLI 
===

Scope and use cases:
--------------------    

This project has various command line tools which will be explained here.
These tools are designed to help you create, organzie, submit and return you chemical calculations on any slurm based server or system.

There are two main command groups we need to differentiate:

- Local commands: are designed to be run on your local machine. These include:
    - config-creator: This command opens the GUI and will be discussed in more detail in the GUI section.
    - collect-input: Search the config file for input files and prepare a zipball with all the files.
    - return-batch-config: will return the status file for all batch processes.

- Remote commands: are designed to be run on the server. These include:
    - start-config: Will start a batch calculation based on a given config. Jobs will be submitted through slurm.
    - start-zip: Will start a batch calculation based on a given zipball. Jobs will be submitted through slurm.
    - return-batch-config: will return the status file for all batch processes.
    - collect-resuls: Collect the results from the specified path and create a zip file. 



.. toctree::
    :maxdepth: 1

    config-creator <config_creator>

    collect-input <collect_input>


    collect-results <collect_results>
