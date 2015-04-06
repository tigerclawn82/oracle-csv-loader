## Overview ##

When loader is called with no options at all, the following actions are performed for all the .csv and .txt files in "csv" folder
  1. loader reads the first lines of csv file and detect data types, then write these informations in a configuration (.conf) file. If the configuration file already exists in the custom\_config directory, it is used instead of creating a new one.
  1. loader creates the sql loader control file and the sql "create table" file using the information loaded from the configuration (.conf) file
  1. loader creates a batch file that perform the table creation and the data loading on database
  1. loader runs the batch file

### Data Type Detection ###
Oracle CSV Loader detects data types reading the first lines of CSV file

Supported data types so far are:
  * number (integer or float)
  * date
  * varchar2

If no particular type is detected for a column or types are mixed, it defaults to varchar2.

More data types will be added soon.

## Basic Usage ##

### Requirements ###
Before starting, open loader.cfg and edit:
  * The "DATABASE" section with your custom database values
  * The "CSV" section with the custom informations about your csv file

### Automatic Mode ###
With automatic mode data types in CSV file are detected automatically by reading the first lines of CSV. The table is automatically created using the first line of CSV (header) to name columns and the CSV is automatically loaded.
  1. Put the CSV file you want to load in the "csv" folder
  1. Run load.bat


### Manual Mode ###
With manual mode data types are in CSV file are detected automatically, but you can check and customize them before actually loading the data into database.
  1. Put the CSV file you want to load in the "csv" folder
  1. Run manual\_config.bat
  1. Check and customize the CSV configuration file created in custom\_config folder
  1. Run load.bat to load the CSV using your custom configuration



## Advanced Usage ##

### Command line Options ###
  * **-f file** loads only the specified file, default is all .txt and .csv files
  * **-m** creates a csv configuration file that can be manually edited before loading data
  * **-n** creates the batch file to load the data but doesn't load the data automatically

### Configuration ###
For advanced configuration check and customize loader.cfg and use the manual mode (-m)