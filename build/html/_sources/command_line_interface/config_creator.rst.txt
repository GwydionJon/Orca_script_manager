config_creator
==============

.. py:function:: config_creator(port, config, hostname, username, password)

The ``config_creator`` function is a command-line interface (CLI) command that creates a new config file for the script_maker2000 tool. This function is part of the ``script_maker_cli`` group of commands.

Parameters
----------

- ``port``: Port to run the dash server on. Default is 8050. This only needs to be changed when you run multiple dash servers on the same machine.

- ``config``: Path to the config file. If the file does not exist a new file will be created and you will still be able to choose one of the already registered ones. Default is None.

- ``hostname``: Hostname of the remote server. Default is "justus2.uni-ulm.de". You could use this to always connect to the same log in node or even an entirly different server, though the last usecase is no tested.

- ``username``: Username of the remote server. This is a required parameter and will be asked if not directly provided.

- ``password``: Password of the remote server. This is a required parameter and will be asked if not directly provided. However it will be shown in clear text when given directly as an argument.


Usage
-----

You can use the ``config_creator`` command from the command line as follows:

If your password includes special characters, you should put it in quotes.

First a full example:
.. code-block:: bash

   script_maker_cli config_creator --port 8050 --config /path/to/config --hostname my-server.com --username my-username --password "my-password"


and here a shortend example:
.. code-block:: bash

   script_maker_cli config_creator --hostname justus2-login01.rz.uni-ulm.de	 --username hd_xyz --password "my-password"



This command will create a new config file for the script_maker2000 tool, establish a connection to the remote server, create the main application, open the browser after 1 second, and run the server.