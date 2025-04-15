==================
Installation Guide
==================

Using pip
=========

To install the latest version of the package, you can use pip, 
though as of now the package is not hosted on PyPi, 
so you will need to install it directly from the GitHub repository. 
To do this, run the following command in your terminal or command prompt:

.. code-block:: bash

    pip install git+https://github.com/GwydionJon/Orca_script_manager

Troubles on windows
-------------------

A dependency of this package is the `dash-bio` package, which on windows requires additional software to be installed.
For this reason we would recommend installing the dependencies through conda fist.

Using conda
============

Anaconda can be found `here <https://www.anaconda.com/products/individual>`_.
Note that you can skip the registration.

This package is not directly hosted on conda, but conda can still be used to create a complete working environment, 
thus simplifying the installation process on most machines.

.. code-block:: bash

    conda env create -f https://raw.githubusercontent.com/GwydionJon/Orca_script_manager/refs/heads/main/environment.yml

When this command is finished it will tell you to activate this conda environment, do so by running:

.. code-block:: bash

    conda activate script_maker

On some systems you may be required to install git first, you can do this by running:

.. code-block:: bash

    conda install git


Finally, install the package by running:

.. code-block:: bash

    pip install git+https://github.com/GwydionJon/Orca_script_manager


Installation on remote system
=================================================
The remote installation of this software will be done automatically after you first submit a job to a remote server via the gui.

This will install all dependencies and the package itself on the remote server.

For a more detailed explanation of how to do this please look at the GUI section of this documentation.


Quick-launch guide
===================

Opening the GUI through a command line can be a bit bothersome, 
so here is some quick code to create a bash or batch file to open the GUI.

For Linux/MacOS, create a bash script (e.g., `open_gui.sh`) with the following content:

.. code-block:: bash

    #!/bin/bash
    conda activate script_maker
    script_maker_cli config-creator --username UserName --password "PASSWORD" --hostname "justus2.uni-ulm.de"

Make the script executable by running:

.. code-block:: bash

    chmod +x open_gui.sh

For Windows, create a batch file (e.g., `open_gui.bat`) with the following content:

.. code-block:: bat

    call conda activate script_maker
    script_maker_cli config-creator --username UserName --password "PASSWORD" --hostname "justus2.uni-ulm.de"


Double-click the respective file to launch the GUI.
Please note that the default working directory of the GUI is the folder from which you run the script.
This means that the GUI will create all files in the current working directory.