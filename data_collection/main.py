"""

FILE MUST BE NAMED main.py OR boot.py

"""


from machine import Pin, Timer, ADC, reset
import time
import sys
import network
import urequests
import gc
import onewire
import ds18x20
import os
import json

# sensor setup
adc = ADC(Pin(26))
ds_pin = machine.Pin(4)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
roms = ds_sensor.scan()
led = Pin("LED", machine.Pin.OUT)

# callback information
beat_timer = Timer()
api_timer = Timer()
detect_freq = 100
api_period = 300000

# values used or the logic and math 
MAX_HISTORY = 250
TOTAL_BEATS = 60
tail_length = 5
max_increase = 1.3
max_decrease = 0.75
upper_threshold_modifier = 0.10
lower_threshold_modifier = 0.12
record_threshold = 30
outlier_avoidence = 3
sort_point = 100

# values needed to 
detect_values = {
    "history" : [],
    "beats" : [],
    "beat_counter" : 0,
    "beat" : False,
    "last_beat_time" : 0,
    "detections_since_last_sort" : 0,
    "threshold_on" : 0,
    "threshold_off" : 0
}

#final transmited data structure
beat_storage = {
    "first_record" : 0,
    "most_recent_record" : 0,
    "transmission_time" : 0,
    "beats" : [],
    "temps" : []
}

# configuration values
api_root = ""
logfile = ""
wifi_list = []

# wifi init
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()

gc.enable()

def log(record_string):
    """
    records to the log file
    """
    with open(logfile, "a") as Log_File:
        Log_File.write(record_string)
        

def temp(beat_storage):
    """
    get the temperature data modified from http://www.pibits.net/code/raspberry-pi-pico-and-ds18b20-thermometer-using-micropython.php
    """
    ds_sensor.convert_temp()
    for rom in roms:
        beat_storage["temps"].append({
            "temps" : ds_sensor.read_temp(rom),
            "time" : time.time()
        })


def calculate_bpm(beats, beat_storage):
    """
    Truncate beats queue to max, then calculate bpm.
    Calculate difference in time from the head to the
    tail of the list. Divide the number of beats by
    this duration (in seconds)
    """
    beat_time = beats[-1] - beats[0]
    
    bpm = (len(beats) / (beat_time)) * 60000
    temp(beat_storage)
    cur_time = time.time()
    if beat_storage["first_record"] == 0:
        beat_storage["first_record"] = cur_time
    beat_storage["most_recent_record"] = cur_time
    beat_storage["beats"].append({
        "bpm" : bpm,
        "time" : cur_time
    })
            

def detect(detect_values, beat_storage):
    """
    runs 60 times a second (set by freq) 
    This records a trailing history of the values recorded from the sensor to follow the wave forms
    it looks at the maximum and minumum values applies a percentage of that to determine the bounds that will trigger a beat
    this is then gated by a toggle so a new beat is not able to occure until the value passes a lower threshold.
    """
    # read and append values to a list that stores the analog signal strength
    detect_values["detections_since_last_sort"] += 1
    reading = adc.read_u16()
    
    detect_values["history"].append(reading)
    
    detect_values["history"] = detect_values["history"][-MAX_HISTORY:]
    
    
    # set threshholds on what to count for a new beat logic
    if detect_values["detections_since_last_sort"]  >= sort_point and len(detect_values["history"]) == MAX_HISTORY:
        
        sorted_history = sorted(detect_values["history"])
        minima = sorted_history[outlier_avoidence]
        maxima = sorted_history[-outlier_avoidence]
        detect_values["threshold_on"] = maxima - (maxima - minima) * upper_threshold_modifier
        detect_values["threshold_off"] = minima + (maxima - minima) * lower_threshold_modifier
        
        detect_values["detections_since_last_sort"]  = 0
        
        
    # avoids counting a beat until the history is full
    if detect_values["threshold_on"] == 0:
        return
    
    """
    count a new beat if the value detected is over the beat threshold
    and if the beat toggle is false
    """
    if reading > detect_values["threshold_on"] and reading < detect_values["threshold_on"] + 150 and detect_values["beat"] == False:
        detect_values["beat_counter"] += 1
        detect_values["beat"] = True
        detect_values["last_beat_time"] = time.ticks_ms()
        detect_values["beats"].append(time.ticks_ms())
        detect_values["beats"] = detect_values["beats"][-TOTAL_BEATS:]
        # every set quantity of beats record the bpm
        if detect_values["beat_counter"] % record_threshold == 0:
            calculate_bpm(detect_values["beats"], beat_storage)
            detect_values["beat_counter"] = 0

    """
    If the beat toggle is on, the value is below the beat threshold
    and there is time since the last beat.
    """
    if reading < detect_values["threshold_off"] and reading > detect_values["threshold_off"] - 150 and detect_values["beat"] == True and time.ticks_ms() - detect_values["last_beat_time"] > 275:
        detect_values["beat"] = False

# try to establish a wifi connection to one of 3 known networks
def connect():
    """
    attempts to make a connection to one of the networks listed in the config/wifi.json file 
    """
    log("attempting to connect to a network\n")
    # Try to connect to one of the Wi-Fi networks
    for wifi in wifi_list:
        if wlan.status() == 3:
            break
        log("connecting to: " + wifi["ssid"] + "\n")
        wlan.connect(wifi["ssid"], wifi["password"])
        if(wlan.status() == 3):
            log("bad connection found restarting device\n")
            machine.reset()
        max_wait = 20
        while max_wait > 0:
            log("Connection status: " + str(wlan.status()) + "\n")
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            led.toggle()
            time.sleep(1)
    led.off()
    if wlan.status() != 3:
        log("No connection found attempting again at the next request\n")
        return False
    log("Connected\n")
    return True

def restore(upload_dict, beat_storage):
    """
    if the api request fails, restore the data points to the tracking dictionary
    """
    beat_storage["first_record"] = upload_dict["first_record"]
    if beat_storage["most_recent_record"] == 0:
        beat_storage["most_recent_record"] = upload_dict["most_recent_record"]
    beat_storage["beats"] += upload_dict["beats"]
    beat_storage["temps"] += upload_dict["temps"]
    
    
def reset(detect_values):
    """
    since I can't thread the api call I need to reset the colletion historic values
    Otherwise the heat rates detected following the api call would be considerably incorrect
    """
    detect_values = {
        "history" : [],
        "beats" : [],
        "beat_counter" : 0,
        "beat" : False,
        "last_beat_time" : 0,
        "detections_since_last_sort" : 0,
        "threshold_on" : 0,
        "threshold_off" : 0
    }

def upload_logs(file_path, file_name):
    """
    performs the api call that uploads previous log files to the server using the api
    """
    with open(file_path, 'r') as f:
        log = f.read()
    data = {
        "name" : file_name,
        "content" : log
    }
    response = urequests.post(api_root + '/new_log', json = data,)
    if response.status_code == 200:
        return True
    return False

def log_upload():
    """
    will attemt to upload all logs except in use logfile to the api, deletes them on a sucessfull upload
    """
    log("Attempting to upload logs")
    for file_name in os.listdir('/logs'):
        file_path = '/logs/' + file_name
        if file_path == ( "/" + logfile):
            continue
        
        # Upload the contents of the file to the API
        if upload_logs(file_path, file_name):
            # If upload succeeds, delete the file
            os.remove(file_path)
        time.sleep(1)

def api(detect_values, beat_storage):
    """
    uploads the stored data to the api every 5 minutes
    This stalls the tracking of the heart rate so it must be reset.
    I tried incorporating threading as a solution but the urequests
    library does not seem to support sending an api request in a thread
    """
    log("starting api call\n")
    reset(detect_values)
    
    try:
        log_upload()
    except:
        log("Failed to upload logs\n")
         
    led.on()
    upload_dict = beat_storage
    
    beat_storage = {
        "first_record" : 0,
        "most_recent_record" : 0,
        "transmission_time" : 0,
        "beats" : [],
        "temps" : []
    }
    
    if not wlan.isconnected():
        if not connect():
            restore(upload_dict, beat_storage)
            log("Failed to connect cannot reach API\n")
            led.off()
            return
        
    try:
        gc.collect()
        upload_dict["transmission_time"] = time.time()
        response = urequests.post(api_root + "/new_data", json = upload_dict)
        log("Http request status code: " + str(response.status_code) + "\n")
        response.close()
        led.off()
        if response.status_code == 200:
            return
        restore(upload_dict, beat_storage)
            
    except Exception as e:
        log("data upload failed\n")
        led.off()
        restore(upload_dict, beat_storage)
    
def test_dirs():
    """
    If the needed files and dirrectories do not exist create them for the user wifi still need to be loaded by the user
    """
    if not 'logs' in os.listdir():
        os.mkdir('logs')
    if not 'config' in os.listdir():
        os.mkdir('config')
    if not 'Log_count.txt' in os.listdir('config'):
        with open('config/Log_count.txt', 'w') as f:
            f.write("1")
    if not 'wifi.json' in os.listdir('config'):
        with open('config/wifi.json', 'w') as f:
            f.write("[]")
    if not 'api.txt' in os.listdir('config'):
        with open('config/api.txt', 'w') as f:
            f.write("")
    
def system_init():
    """
    loads configuration information 
    """
    global wifi_list
    global api_root
    global logfile
    led.on()
    # checks dirrectory setup
    test_dirs()
    # gets the version of the log the system is on so that the files are not overwritten evertime the system starts
    with open("config/Log_count.txt", "r") as Log_count_File:
        file_count = int(Log_count_File.readline())
    with open("config/Log_count.txt", "w") as Log_count_File:
        Log_count_File.write(str(file_count + 1))
    logfile = "logs/Log_" + str(file_count) + ".txt"
    
    # load the known wifi connections
    with open('config/wifi.json', 'r') as f:
        wifi_list = json.load(f)
    #check for initially created wifi file
    if wifi_list == []:
        log('Wifi configuration file empty please fill the list in json format: {"ssid" : "<network name>", "password": "<network password>"}\n')
            
    #saves base api url
    with open("config/api.txt", "r") as api_file:
        api_root = api_file.readline()
    if(api_root == ""):
        log('api file is empty please inculde the root url for the api endpoint')
        
    # wifi connection test
    log("Initial connection status: " + str(wlan.isconnected()) + "\n")
    if not wlan.isconnected():
        log("Connection not found attempting to connect\n")
        connect()
    else:
        log("False connection found on init restarting device\n")
        machine.reset()
    led.off()
    
system_init()

# callbacks setup
beat_timer.init(freq=detect_freq, mode=Timer.PERIODIC, callback = lambda t: detect(detect_values, beat_storage))
api_timer.init(mode=Timer.PERIODIC, period = api_period, callback = lambda t: api(detect_values, beat_storage))