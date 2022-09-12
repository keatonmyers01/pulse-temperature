import time

from numpy import record
# Import SPI library (for hardware SPI) and MCP3008 library.
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
import datetime
import json


# maintains one json file per day to avoid data bloating
# if unable to sync to database
def update_file_name(file_data):
    global date
    date = datetime.datetime.utcnow().strptime("%d:%m:%Y")
    global Log_File_name
    Log_File_name = f".data_logs/temperature_data.json" + date
    file_data.clear()
    file_data = {
        "readings" : []
    }

# Truncate beats queue to max, then calculate bpm.
# Calculate difference in time from the head to the
# tail of the list. Divide the number of beats by
# this duration (in seconds)
def calculate_bpm(beats, file_data):
    # if it moves to the next day while the script is running
    record_time = datetime.datetime.utcnow()
    if record_time.strptime("%d:%m:%Y") != date:
        update_file_name()
    beats = beats[-TOTAL_BEATS:]
    beat_time = beats[-1] - beats[0]
    
    bpm = (len(beats) / (beat_time)) * 60
    file_data["readings"].append(
        {
            "UTCDatetime": record_time,
            "bmp": bpm
        }
    )
    with open(Log_File_name, 'w')as file:
        json.dump(file_data, file, indent=4)

def detect(file_data):
    # Maintain a log of previous values to
    # determine min, max and threshold.
    history = []
    beats = []
    beat = False
    beat_counter = 0
    threshold_modifier = 0.05
    record_threshold = 30
    while True:
        # read and append values to a list that stores the analog signal strength
        v = mcp.read_adc(0)
        history.append(v)
        history = history[-MAX_HISTORY:]

        # set threshholds on what to count for a new beat logic
        minima, maxima = min(history), max(history)
        threshold_on = maxima - (maxima - minima) * threshold_modifier
        threshold_off = minima + (maxima - minima) * threshold_modifier

        # count a new beat if the value detected is over the beat threshold
        # and if the beat toggle is false
        if v > threshold_on and beat == False:
            beat_counter +=  1
            beat = True
            beat_time = time.time()
            beats.append(beat_time)
            beats = beats[-TOTAL_BEATS:]
            # every set quantity of beats record to the json
            if beat_counter % record_threshold == 0:
                calculate_bpm(beats, file_data)
                beat_counter = 0

        # If the beat toggle is on, the value is bellow the beat threshold
        # and there is time since the last beat.
        if v < threshold_off and beat == True and time.time() - beat_time  > 0.01:
            beat = False


SPI_PORT = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

MAX_HISTORY = 1000
TOTAL_BEATS = 30

# set up logging file
date = datetime.datetime.utcnow().strptime("%d:%m:%Y")
Log_File_name = f".data_logs/temperature_data.json" + date
with open(Log_File_name, 'r+')as file:
    file_data = json.load(file)
    if "readings" not in file_data:
        file_data = {
            "readings" : []
        }
        json.dump(file_data, file, indent=4)

detect(file_data)