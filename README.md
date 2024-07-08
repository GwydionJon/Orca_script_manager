# AC-Forschi

To use this program you need to provide a config.json and an molecules.csv

the config contains all the calculation setups while the csv file contains the file location of the molecules, their multiplicity and charge. 



# Quickstart

## Installation: 
`pip install git+pip install git+https://github.com/GwydionJon/Orca_script_manager`



## Prepare your files

For this program to work you need to include the charge and multiplicity information in your xyz filename.
To do this add "__cXmX.xyz" at the end of your file name, where the 'X' needs to replaced by the actual number. 



## Create config

First open a terminal where you want to create your new config file.

`script_maker_cli config-creator` 

You may need to ctrl+click or copy the short link showing up in your terminal to open the web based config creator.

Simply set the config however you want and follow the hints you are provided with when entering a wrong parameter.
Choose a unique name and output directory for your config as the filename will be used to track the calculation

## Collect input files
Afterwards you have exported your config you can use to collect all relevant files for you, so you only have to copy one archive to the server. (May change in the future)
This archive will be placed under OUTPUT_PATH.

`script_maker_cli collect-input -c CONFIG_PATH -o OUTPUT_PATH` 

The creater tar.gz file must be transfered to your cluster or compute server of choice. 
It must run SLURM for this programm to function.


## Start calculations
After you have succesfully transfered your file simply run either of these lines:
`script_maker_cli start-zip --zip ZIP_PATH --extract_path EXTRACT_PATH`
`script_maker_cli start-zip --zip ZIP_PATH --extract_path EXTRACT_PATH --remove_extracted`

The EXTRACT_PATH is the location where you want to start your calculation and where your logs and results are shown.

The `--remove_extracted` flag at the end means that the extracted data will be deleted after starting the workflow, this will reduce unused file overhead. More useful for large datasets.

Now just wait for the program to finish. 





# Notes on the gui


## Results:
if you enter a custom path in the "Custom Output Directoy" input your chosen dropdown value will be ignored. 
leave empty to enable dropdown again.

