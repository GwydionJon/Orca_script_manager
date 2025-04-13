return_batch_config
===================

.. py:function:: return_batch_config(as_json=False)

The ``return_batch_config`` function is mostly used internally to collect the batch config file. 
It is part of the ``script_maker_cli`` group of commands.

The batch config file is a json file that stores which calculations have been deployed under which config name and where they are stored.
It exists as a cli interface to allow the remote link to easily fetch this data through the ssh tunnel.



Parameters
----------

- ``as_json`` (bool, optional): If the config should be returned as json. Defaults to False.

Returns
-------

- int: The return value indicating the success of the function (0 for success, 1 for failure).

This function reads the batch config file and returns it either as a JSON string or as a file path, depending on the ``as_json`` parameter. If the config file cannot be read, it prints an error message and returns 1.