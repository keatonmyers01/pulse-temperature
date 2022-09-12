# Import Libraries
import os
import glob
import time
import datetime
import json
 
# Initialize the GPIO Pins
os.system('modprobe w1-gpio')  # Turns on the GPIO module
os.system('modprobe w1-therm') # Turns on the Temperature module
 
# Finds the correct device file that holds the temperature data
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# maintains one json file per day to avoid data bloating
# if unable to sync to database
def update_file_name():
    global date
    date = datetime.datetime.utcnow().strptime("%d:%m:%Y")
    global Log_File_name
    Log_File_name = ".data_logs/heart_rate_data.json" + date
    global file_data
    file_data.clear()
    file_data = {
      "readings" : []
    }
 
# A function that reads the sensors data
def read_temp_raw():
    f = open(device_file, 'r') # Opens the temperature device file
    lines = f.readlines() # Returns the text
    f.close()
    return lines
 
# Convert the value of the sensor into a temperature
def read_temp():
    lines = read_temp_raw() # Read the temperature 'device file'
    
    # While the first line does not contain 'YES', wait for 0.2s
    # and then read the device file again.
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
 
    # Look for the position of the '=' in the second line of the
    # device file.
    equals_pos = lines[1].find('t=')
 
    # If the '=' is found, convert the rest of the line after the
    # '=' into degrees Celsius, then degrees Fahrenheit
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

def detect():
    global file_data
    while True:
        cel, far = read_temp()
        record_time = datetime.datetime.utcnow()
        if record_time.strptime("%d:%m:%Y") != date:
            update_file_name()
        file_data["readings"].append(
            {
                "UTCDatetime": record_time,
                "fahrenheit": far,
                "celsius": cel
            }
        )
        with open(Log_File_name, 'w')as file:
            json.dump(file_data, file, indent=4)
        time.sleep(30)

# set file to save values to
date = datetime.datetime.utcnow().strptime("%d:%m:%Y")
Log_File_name = f".data_logs/heart_rate_data.json" + date
# set up logging file
with open(Log_File_name, 'r+')as file:
    file_data = json.load(file)
    if "readings" not in file_data:
        file_data = {
            "readings" : []
        }
        json.dump(file_data, file, indent=4)

detect()