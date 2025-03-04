CLI 
===

Scope and use cases:
--------------------    

This project has various command line tools which will be explained here.
These tools are designed to help you create, organize, submit and return you chemical calculations on any slurm based server or system.

There are two main command groups we need to differentiate:

- Local commands: are designed to be run on your local machine. These include:
    - config-creator: This command opens the GUI and will be discussed in more detail in the GUI section.
    - collect-input: Search the config file for input files and prepare a zipball with all the files.
    - return-batch-config: will return the status file for all batch processes.

- Remote commands: are designed to be run on the server. These include:
    - start-config: Will start a batch calculation based on a given config. Jobs will be submitted through slurm.
    - start-zip: Will start a batch calculation based on a given zipball. Jobs will be submitted through slurm.
    - return-batch-config: will return the status file for all batch processes.
    - collect-results: Collect the results from the specified path and create a zip file. 


| To run any of these commands, you can use the following syntax:
| ``script_maker_cli <command> <arguments>``

| For example:
| ``script_maker_cli start-config --config /path/to/config --continue_run --profile``

This would continue or restart a previously started calculation based on the config file at /path/to/config and profile the code for performance analysis.
For more details about the commands and their arguments, please refer to the individual pages or use the  ``--help`` flag.

When using the GUI most of these commands will be run automatically. However, you can also run them manually from the command line.


.. toctree::
    :maxdepth: 1

    config-creator <config_creator>

    collect-input <collect_input>

    return-batch-config <return_batch_config>

    start-config <start_config>

    start-zip <start_zip>

    collect-results <collect_results>
