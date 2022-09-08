import time
# Import SPI library (for hardware SPI) and MCP3008 library.
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
from threading import Timer
import meerschaum as mrsm
import datetime

def calculate_bpm(beats, trigger, pipe):
    # Truncate beats queue to max, then calculate bpm.
    # Calculate difference in time from the head to the
    # tail of the list. Divide the number of beats by
    # this duration (in seconds)
    beats = beats[-TOTAL_BEATS:]
    beat_time = beats[-1] - beats[0]
    if beat_time and trigger:
        bpm = (len(beats) / (beat_time)) * 60
    #    print(f"bpm: {bpm}")
        pipe.sync({"UTCDateTime":[datetime.datetime.utcnow()],"bpm":[bpm]})

def detect():
    # Maintain a log of previous values to
    # determine min, max and threshold.
    history = []
    beats = []
    beat = False
    pipe = mrsm.Pipe("plugin:bio_metric", "bpm", "raw", instance="sql:local", columns={"datetime":"UTCDateTime"})
    counter = 0
    while True:
        v = mcp.read_adc(0)

        history.append(v)

        # Get the tail, up to MAX_HISTORY length
        history = history[-MAX_HISTORY:]

        minima, maxima = min(history), max(history)
        threshold_on = maxima - (maxima - minima) * 0.05    # 3/4
        threshold_off = minima + (maxima - minima) * 0.05      # 1/2

#        print(f"\nminima: {minima} maxima: {maxima} on: {threshold_on} off: {threshold_off}")

        if v > threshold_on and beat == False:
            beat = True
            beat_time = time.time()
            beats.append(beat_time)
            last_beat = beat_time
            beats = beats[-TOTAL_BEATS:]
            trigger_print = counter % 30 == 0
            calculate_bpm(beats, trigger_print, pipe)
            counter +=  1

#            print(f"\nminima: {minima} maxima: {maxima} on: {threshold_on} off: {threshold_off}")
 #           print(v)


  #          print(f"beat: {counter}")


        if v < threshold_off and beat == True and time.time() - beat_time  > 0.01:

#            print(f"\nminima: {minima} maxima: {maxima} on: {threshold_on} off: {threshold_off}")
   #         print(v)

            beat = False


SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

MAX_HISTORY = 1000

# Maintain a log of previous values to
# determine min, max and threshold.
history = []
beat = False
beats = 0

TOTAL_BEATS = 30
detect()
