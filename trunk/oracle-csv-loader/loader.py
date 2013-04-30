# CONFIG
GLOBAL_CONFIG_FILE = 'loader.cfg'

import ConfigParser
import os
import time
import sys
from optparse import OptionParser
from collections import OrderedDict
from subprocess import call

# used to estimate max_length for varchar2 fields
def get_varchar2_size(char_number):
    n = 2
    while n < char_number:
        n = n * 2
    return min (n, 32767 )

# return True if my_date is a valid date, False otherwise
def is_valid_date(my_date):
    # creates the python style string for date formatting
    py_date_format = config.get('CSV', 'date_format').replace("DD", "%d").replace("MM", "%m").replace("YYYY", "%Y");
    try:
        valid_date = time.strptime(my_date, py_date_format)
        return True
    except ValueError:
        return False


# return True if my_date is a valid number, False otherwise
def is_valid_number(my_number):
    try:
        float(my_number.replace(config.get('CSV', 'decimal_separator'), '.'))
        return True
    except ValueError:
        return False


# returns the length of integer and decimal part of a number
def number_info(my_number):
    number_parts = my_number.split(config.get('CSV', 'decimal_separator'))
    integer_part = len(number_parts[0])
    if len (number_parts) > 1:
        decimal_part = len(number_parts[1])
    else:
        decimal_part = 0
    return (integer_part, decimal_part)


# creates config file config file for current csv (with informations about columns type)
def create_csv_config_file(csv_file_name, csv_config_file_name):

    global config

    # read csv file to get info about columns
    csv_file = open(csv_file_name, "r")
    csv_data = []

    # loads file header into csv_header
    if config.getboolean('CSV', 'first_line_is_header'):
        csv_header = csv_file.readline().strip().split(config.get('CSV', 'separator'))
    else:
        csv_header = csv_file.readline().strip().split(config.get('CSV', 'separator'))
        csv_file.seek(0)

    fields_number = len(csv_header)
    csv_fields = []
    for x in range (0, fields_number):
        csv_fields.append([])

    # loops trough the first n lines of current csv to detect data types
    for line_number in range(0, config.getint('CONFIG', 'csv_lines_to_parse')):
        line = csv_file.readline()
        if not line: break

        # this is where the magic happens (csv data types are detected)
        # on each iteration the array csv_fields[] is updated with the
        # informations on data types. if no special type (number, date, etc.) is detected
        # or if special types are mixed the resulting type will default to varchar2.
        # csv_fields[] array looks like this:
        # csv_fields[0] = DATE | NUMBER | VARCHAR2
        # if csv_fields[0] = DATE then csv_fields[1] = length(date_string)
        # if csv_fields[0] = NUMBER then csv_fields[1] = length(number_string), csv_fields[2] = length(integer part), csv_fields[3] = length(decimal part)
        # if csv_fields[0] = VARCHAR2 then csv_fields[1] = length(varchar2_string)
        values = line.strip().split(config.get('CSV', 'separator'))
        for index in range (0, fields_number):
            # if field type is not defined yet (first iteration)
            if not csv_fields[index]:
                # date
                if is_valid_date(values[index]):
                    csv_fields[index] = ['DATE', len(values[index])]
                # number
                elif is_valid_number (values[index]):
                    int_len, dec_len = number_info(values[index])
                    csv_fields[index] = ['NUMBER', len(values[index]), int_len,  dec_len]
                # general string
                else:
                    csv_fields[index] = ['VARCHAR2', len(values[index])]

            # if field type is date (so far)
            elif csv_fields[index][0] == 'DATE':
                # date
                if is_valid_date(values[index]):
                    csv_fields[index] = ['DATE', len(values[index])]
                # general string
                else:
                    csv_fields[index] = ['VARCHAR2', max([csv_fields[index][1], len(values[index])])]

            # if field type is number (so far)
            elif csv_fields[index][0] == 'NUMBER':
                # number
                if is_valid_number (values[index]):
                    int_len, dec_len = number_info(values[index])
                    csv_fields[index] = ['NUMBER', max([csv_fields[index][1], len(values[index])]), max([csv_fields[index][2], int_len]),  max([csv_fields[index][3], dec_len])]
                # general string
                else:
                    csv_fields[index] = ['VARCHAR2', max([csv_fields[index][1], len(values[index])])]

            # if field type is varchar2
            elif csv_fields[index][0] == 'VARCHAR2':
                csv_fields[index] = ['VARCHAR2', max([csv_fields[index][1], len(values[index])])]

    # write config file for current csv
    csv_config = ConfigParser.RawConfigParser(dict_type=OrderedDict) # dict_type=OrderedDict used to keep fields ordered

    # the options in section CSV of global config are copied to the section CONF of the config file for current csv
    csv_config.add_section('CONF')
    for name, value in config.items('CSV'):
        csv_config.set('CONF', name, value)

    # write fields type info to the config file for current csv
    csv_config.add_section('FIELDS')
    if options.manual_config:
        csv_config.set('FIELDS', '# = =-------------------------------------------------------------------- ', '')
        csv_config.set('FIELDS', '# = This section contains fields name and data types that will be used to ', '')
        csv_config.set('FIELDS', '# = create the table on database and the sql loader control file.         ', '')
        csv_config.set('FIELDS', '# = field_name = data_type                                                ', '')    
        csv_config.set('FIELDS', '# = You can change here the field name and data types. Allowed types are: ', '')
        csv_config.set('FIELDS', '# = DATE                                                                  ', '')
        csv_config.set('FIELDS', '# = NUMBER integer_part_length decimal_part_length                        ', '')
        csv_config.set('FIELDS', '# = VARCHAR2 max_length                                                   ', '')
        csv_config.set('FIELDS', '# = --------------------------------------------------------------------- ', '')    
    
    for index in range (0, fields_number):
        if csv_fields[index][0] == 'DATE':
            value = 'DATE'
        elif csv_fields[index][0] == 'NUMBER':
            value = 'NUMBER' + ' ' + str(csv_fields[index][2] + int(config.get('CONFIG', 'add_integer_length'))) + ' ' + str(csv_fields[index][3] + int(config.get('CONFIG', 'add_decimal_length')))
        elif csv_fields[index][0] == 'VARCHAR2':
            value = 'VARCHAR2' + ' ' + str(get_varchar2_size(csv_fields[index][1]))
                
        csv_config.set('FIELDS', csv_header[index].upper().replace(' ', '_'), value)

    csv_conf_file = open(csv_config_file_name, "wb")
    csv_config.write(csv_conf_file)
    csv_conf_file.close()


# creates the sqlldr control file
def create_ctl_file(fileName):
    ctl_string = ''
    if csv_config.getboolean('CONF', 'first_line_is_header'):
        ctl_string +=  'OPTIONS (skip = 1)\n'
    ctl_string += 'LOAD DATA\n'
    # base_dir = os.path.dirname(os.path.abspath(__file__))
    ctl_string += "INFILE '%s'\n" %(fileName)
    ctl_string += 'BADFILE %s%s\n' %(fileName, '.bad')
    if csv_config.getboolean('CONF', 'append'):
        ctl_string += 'APPEND\n'
    ctl_string += 'INTO TABLE %s\n' %os.path.splitext(fileName)[0]
    ctl_string += 'FIELDS TERMINATED BY "' + csv_config.get('CONF', 'separator') + '"\n'
    ctl_string += 'TRAILING NULLCOLS\n'
    ctl_string += '(\n'

    fields = OrderedDict(csv_config.items('FIELDS'))
    index = 0
    # loop over fields
    for key in fields:
        values = fields[key].split(' ')
        if values[0] == 'DATE':
            field_str = key + ' ' + 'DATE "' + csv_config.get('CONF', 'date_format') + '"'
        elif values[0] == 'NUMBER':
            field_str = key
            if config.get('DATABASE', 'decimal_separator') <> csv_config.get('CONF', 'decimal_separator'):
                field_str += ' "REPLACE(:' + key + ", '" + csv_config.get('CONF', 'decimal_separator') + "', '" + config.get('DATABASE', 'decimal_separator') + "'" + ')"'
        elif values[0] == 'VARCHAR2':
            field_str = key

        if index <> len(fields)-1:
            field_str += ','

        field_str += '\n'
        ctl_string += field_str
        index = index + 1

    ctl_string += ')\n'

    ctl_file = open(config.get('CONFIG', 'output_dir') + os.sep + fileName + '.' + config.get('CONFIG', 'control_file_extension'), "w")
    ctl_file.write(ctl_string)
    ctl_file.close()


# creates a sql text file containing the "create table" statement
def create_sql_file(fileName):
    sql_string = ''
    if not csv_config.getboolean('CONF', 'append'):
        sql_string += 'DROP TABLE %s;\n\n' %os.path.splitext(fileName)[0].upper()
    sql_string += 'CREATE TABLE %s\n(\n' %os.path.splitext(fileName)[0].upper()
    fields = OrderedDict(csv_config.items('FIELDS'))

    index = 0
    # loop over fields
    for key in fields:
        values = fields[key].split(' ')
        if values[0] == 'DATE':
            field_str = key.upper() + ' ' + 'DATE'
        elif values[0] == 'NUMBER':
            field_str = key.upper() + ' ' + 'NUMBER(' + str(int(values[1])+int(values[2])) + ',' + values[2] + ')'
        elif values[0] == 'VARCHAR2':
            field_str = key.upper() + ' ' + 'VARCHAR2(' + values[1] + ')'

        if index <> len(fields)-1:
            field_str += ','

        field_str += '\n'
        sql_string += field_str
        index = index + 1

    sql_string += ');\n\nquit;\n' 

    sql_file = open(config.get('CONFIG', 'output_dir') + os.sep + fileName + '.' + config.get('CONFIG', 'sql_file_extension'), "w")
    sql_file.write(sql_string)
    sql_file.close()


# creates a batch file for running sqlldr
def create_batch_file(fileName):
    # locates the sqlplus executable
    if config.has_option('CONFIG', 'path_to_sqlplus_executable'):
        sqlplus_executable = config.get('CONFIG', 'path_to_sqlplus_executable') + os.sep + config.get('CONFIG', 'sqlplus_executable')
    else:
        sqlplus_executable = config.get('CONFIG', 'sqlplus_executable')

    batch_string = sqlplus_executable
    batch_string += ' %s/%s' %(config.get('DATABASE', 'user'),config.get('DATABASE', 'password'))
    batch_string += '@'
    batch_string += '%s:%s/%s' %(config.get('DATABASE', 'host'), config.get('DATABASE', 'port'), config.get('DATABASE', 'service_name'))
    batch_string += ' @%s.%s\n' %(fileName, config.get('CONFIG', 'sql_file_extension'))

    # locates the sqlldr executable
    if config.has_option('CONFIG', 'path_to_sqlldr_executable'):
        sqlldr_executable = config.get('CONFIG', 'path_to_sqlldr_executable') + os.sep + config.get('CONFIG', 'sqlldr_executable')
    else:
        sqlldr_executable = config.get('CONFIG', 'sqlldr_executable')

    batch_string += sqlldr_executable
    batch_string += ' %s/%s' %(config.get('DATABASE', 'user'),config.get('DATABASE', 'password'))
    batch_string += '@'
    batch_string += '%s:%s/%s' %(config.get('DATABASE', 'host'), config.get('DATABASE', 'port'), config.get('DATABASE', 'service_name'))
    batch_string += ' control=%s.%s' %(fileName, config.get('CONFIG', 'control_file_extension'))
    batch_string += ' %s' %config.get('CONFIG', 'sqlldr_options')
    if config.has_option('CONFIG', 'run_after_loading'):
        batch_string += '\n%s' %config.get('CONFIG', 'run_after_loading')

    batch_file = open(config.get('CONFIG', 'output_dir') + os.sep + fileName + '.' + config.get('CONFIG', 'batch_file_extension'), "w")
    # batch_file = open(fileName + '.' + config.get('CONFIG', 'batch_file_extension'), "w")
    batch_file.write(batch_string)
    batch_file.close()


#creates the table and loads the csv data into database
def load_data(fileName):
    os.chdir(config.get('CONFIG', 'output_dir'))
    call([fileName + '.' + config.get('CONFIG', 'batch_file_extension'), ''])
    
    
def process_file(fileName):

    global csv_config

    print ('Processing file: ' + fileName)

    # config file for current csv
    csv_config = ConfigParser.ConfigParser()

    # full path of the temporary and saved config file for current csv (if they exists)
    tmp_csv_config_file = config.get('CONFIG', 'output_dir') + os.sep + os.path.basename(fileName) + '.' + config.get('CONFIG', 'config_file_extension')
    saved_csv_config_file = config.get('CONFIG', 'saved_dir') + os.sep + os.path.basename(fileName) + '.' + config.get('CONFIG', 'config_file_extension')    

    if options.manual_config:
        # creates the manual config file for current csv, if it doesn't exists
        create_csv_config_file(fileName, saved_csv_config_file)
        csv_config_file = saved_csv_config_file
        print ('  Manual csv configuration file created: ' + saved_csv_config_file + '.')
        print ('  You can edit the file to customize configuration')
        print ('  (field types and column names) and run this program')
        print ('  without -m option to load csv data with custom  configuration')

    else:    
        # find the config file for current csv, or create it if it doesn't exists
        if (os.path.exists(saved_csv_config_file)):
            csv_config_file = saved_csv_config_file
            print ('  Manual csv configuration file loaded: ' + saved_csv_config_file)

        else:
            # creates the config file for current csv, if it doesn't exists
            create_csv_config_file(fileName, tmp_csv_config_file)
            csv_config_file = tmp_csv_config_file
            print ('  Automatic csv configuration file created: ' + tmp_csv_config_file)

    # reads the config file for current csv
    csv_config.read(csv_config_file)
    
    if not options.manual_config:
        # creates the sqlldr control file
        create_ctl_file(os.path.basename(fileName))
        print ('  Control file created')

        # creates a sql text file containing the "create table" statement
        create_sql_file(os.path.basename(fileName))
        print ('  Sql file created')

        # creates a batch file for running sqlldr
        create_batch_file(os.path.basename(fileName))
        print ('  Batch file created')

        if not options.no_load:
            #creates the table and loads the csv data into database
            load_data(os.path.basename(fileName))
            print ('  CSV Data loaded')
        else:
            print ('  Run the batch file to load CSV data to database')


def main(argv):

    global args, config, options

    # parse command line arguments
    parser = OptionParser()
    parser.add_option("-f", "--file", type="string", dest="fileName", default=False, help="loads only the given file, default is all files", metavar="FILE")
    parser.add_option("-m", "--manual-config", action="store_true", dest="manual_config", default=False, help="creates a csv configuration file that can be manually edited before loading data")
    parser.add_option("-n", "--no-load", action="store_true", dest="no_load", default=False, help="creates the batch file to load the data but doesn't load the data automatically")
    (options, args) = parser.parse_args()

    # reads the global configuration file
    config = ConfigParser.ConfigParser()
    config.read(GLOBAL_CONFIG_FILE)

    # baseDir = os.getcwd()
    # print (baseDir)

    if  options.fileName:
        #processes only the given file
        process_file(options.fileName)
    else:
        #processes all files in csv_files_dir with extension included in csv_extentions parameters
        for csv_file_name in os.listdir(config.get('CONFIG', 'csv_files_dir')):
            for extension in config.get('CONFIG', 'csv_extentions').split(' '):
                if csv_file_name[-len(extension):].upper() == extension.upper():
                    process_file(config.get('CONFIG', 'csv_files_dir') + os.sep + csv_file_name)


# global variables
args = None
config = None
csv_config = None
options = None

if __name__ == "__main__":
    main(sys.argv)
