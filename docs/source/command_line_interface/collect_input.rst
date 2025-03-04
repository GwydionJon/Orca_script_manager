collect_input_files
===================

.. py:function:: collect_input_files(config_path, preparation_dir, config_name=None, zip_name=None)

The ``collect_input_files`` function collects all input files (xyz, config, csv) and puts them into a single zipball.

Parameters
----------

- ``config_path`` (str): Path to the config file.

- ``preparation_dir`` (str): Path to the directory where the input files will be prepared.

- ``config_name`` (str, optional): Name of the config file. If not provided, the file name will be used. Defaults to None.

- ``zip_name`` (str, optional): Name of the zip archive. If not provided, a default name will be used. Defaults to None.

Return Value
------------

The function returns 0 on success. If the results path does not exist, it returns 1.
This function will also output a logging text while running.


Usage
-----

You can use the ``collect_input_files`` function as follows:

.. code-block:: bash

    script_maker_cli collect_input_files --config_path /path/to/config --preparation_dir /path/to/preparation --config_name my_config --zip_name my_zipball