start_config
============

.. py:function:: start_config(config, continue_run, profile: bool)

The ``start_config`` function starts the batch manager with the given config file.

Parameters
----------

- ``config`` (str): Path to the config file.

- ``continue_run`` (bool): If the batch processing should continue from the last calculation.

- ``profile`` (bool): If the code should be profiled. Mainly useful for performance analysis when coding. Will create a '.prof' file.

Returns
-------

- int: The return value indicating the success of the function (0 for success, 1 for failure).

This function checks if the provided config file exists, enables profiling if the ``profile`` flag is set, checks the config file, and starts the batch processing. If the ``continue_run`` flag is set, it continues from the last calculation.

Usage
-----

You can use the ``start_config`` command from the command line as follows:

.. code-block:: bash

   script_maker_cli start_config --config /path/to/config --continue_run --profile