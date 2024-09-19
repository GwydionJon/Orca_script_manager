
collect-results
===============

.. py:function:: collect_results

The ``collect_results`` function is a command-line interface (CLI) command that collects the results from a specified path and creates a zip file. This function is part of the ``script_maker_cli`` group of commands.

Parameters
----------


- ``results_path``: The path to the results folder. This path is resolved to an absolute path before being used. If the path does not exist, the function will print an error message and return 1.

- ``exclude_patterns``: A comma-separated list of patterns to exclude from the zip file. If this parameter is not provided or is an empty string, it is set to an empty list. If it is a string, it is split on commas to create a list of patterns. Any leading or trailing whitespace is removed from each pattern.

Return Value
------------

The function returns 0 on success. If the results path does not exist, it returns 1.

Usage
-----

You can use the ``collect_results`` command from the command line as follows:

.. code-block:: bash

   script_maker_cli collect_results --results_path /path/to/results --exclude_patterns pattern1,pattern2

This command will collect the results from the directory at ``/path/to/results`` and create a zip file. It will exclude any files that match the patterns ``pattern1`` or ``pattern2``.


