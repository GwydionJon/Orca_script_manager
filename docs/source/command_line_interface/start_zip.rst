start_zip
=========

.. py:function:: start_zip(zip, extract_path, remove_extracted, profile: bool, hide_job_status: bool = False)

The ``start_zip`` function starts the batch processing with the given zip file.

Parameters
----------

- ``zip`` (str): The path to the zip file containing the input files.

- ``extract_path`` (str): The path to extract the contents of the zip file.

- ``remove_extracted`` (bool): Flag indicating whether to remove the extracted files after processing.

- ``profile`` (bool): If the code should be profiled. Mainly useful for performance analysis when coding. Will create a '.prof' file.

- ``hide_job_status`` (bool, optional): Flag indicating whether to hide the job status. Defaults to False.

Returns
-------

- int: The exit code of the batch processing.

Raises
------

- Exception: If there is an error reading the molecule json file or creating the batch manager.

This function extracts the input files from the given zip file, loads and updates the config, reads the molecule json file, creates the batch manager, and starts the batch processing. If the ``remove_extracted`` flag is set, it removes the extracted files after processing. If the ``profile`` flag is set, it enables profiling. The function returns the exit code of the batch processing.

Usage
-----

You can use the ``start_zip`` command from the command line as follows:

.. code-block:: bash

   script_maker_cli start_zip --zip /path/to/zip --extract_path /path/to/extract --remove_extracted --profile --hide_job_status
   