
Contributions
=============

We welcome contributions to the project. To contribute, please follow the steps below:

1. Fork the repository on GitHub.
2. Clone the repository to your local machine.
3. Create a new branch off of the `main` branch.
4. Make your changes.
5. Push your changes to your fork on GitHub.
6. Open a pull request to the `main` branch of the repository.
7. Wait for the pull request to be reviewed and merged.

Please make sure to follow the project's code style and to run the tests before opening a pull request.

If you have any questions or need help with contributing, please feel free to reach out to us via the issues page on GitHub.

Adding a new calculation module
===============================
To add a new calculation module, you need to create a new class that inherits from the `template` class.
This class should implement the required functions and any additional functions that are necessary for the calculation module.
The required functions are:

- `__init__`: This function initializes the calculation module and sets up the necessary variables.
- `create_slurm_scripts`: This function creates the slurm script that will be submitted to the server.
- `prepare_jobs`: This function prepares the jobs that will be submitted to the server.
- `check_job_status`: This function checks the status of the jobs that are currently running on the server.
- `collect_results`: This function collects results from the server and stores them in the correct location.
- `run_job`: This function submits the jobs to the server and monitors their progress.
- `restart_job`: This function restarts a job that has failed or been stopped.

Failure to implement any of these functions will result in an error when trying to use the calculation module.

For more documentation you can refer to the API reference of the :ref:`ORCA <script_maker2000_orca>` and :ref:`template <script_maker2000_template>` classes.

