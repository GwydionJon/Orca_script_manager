=====================================================
Cloning the Repository and setting up the environment
=====================================================


Setting up the repository
-------------------------

To start developing on this project, you will need to clone the repository and set up the environment.

First, clone the repository by running the following command in your terminal or command prompt:

.. code-block:: bash

    git clone https://github.com/GwydionJon/Orca_script_manager.git

Next, navigate to the repository directory:

.. code-block:: bash

    cd Orca_script_manager

Then, install the conda environment by running:

.. code-block:: bash

    conda env create -f environment.yml

When this command is finished, it will tell you to activate this conda environment. Do so by running:

.. code-block:: bash

    conda activate script_maker

Finally, install the package by running:

.. code-block:: bash

    pip install -e .


You now have a working development environment for the project.


Additional development requirements
-----------------------------------

To run the tests and build the documentation, you will need to install additional requirements.
These will also help you adhere to the project's code style.

To install these requirements, run the following command:

.. code-block:: bash

    pip install -r requirements-dev.txt
    pre-commit install

You can now run the tests via pytest as you normally would, and build the documentation using Sphinx.

Note that tests will always be run when creating a pull request, 
so it is important to ensure that they pass before opening a pull request.

