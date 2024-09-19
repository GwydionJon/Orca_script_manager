return_batch_config
===================

.. py:function:: return_batch_config(as_json=False)

The ``return_batch_config`` function returns the batch config file.

Parameters
----------

- ``as_json`` (bool, optional): If the config should be returned as json. Defaults to False.

Returns
-------

- int: The return value indicating the success of the function (0 for success, 1 for failure).

This function reads the batch config file and returns it either as a JSON string or as a file path, depending on the ``as_json`` parameter. If the config file cannot be read, it prints an error message and returns 1.