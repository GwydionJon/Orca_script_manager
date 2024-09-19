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

    conda env create -f https://raw.githubusercontent.com/GwydionJon/Orca_script_manager/environment.yml

When this command is finished it will tell you to activate this conda environment, do so by running:

.. code-block:: bash

    conda activate script_maker

Finally, install the package by running:

.. code-block:: bash

    pip install git+https://github.com/GwydionJon/Orca_script_manager
