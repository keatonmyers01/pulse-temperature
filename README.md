# Wearable Biometrics Detection and Upload Project

A Biometric sensor for pulse and temperature designed in MicroPython on the Raspberry Pi Pico W. Data is read using a ds18b20 temperature sensor and a World Famous Electronics pulse sensor. Data is synced to the cloud every five minutes if an internet connection is found. 

I built a prototype for this as a hackathon project. The rest of the team decided to stop working on the project I wanted to continue development so I overhauled the code, added the pulse sensor, API connection, and converted it to work on a Pico W. The orrigional idea came about because of heat sensitivity issues I have that made monitoring temperature intresting to me. While this idea could easily be applied to existing smart watches, most do not track skin temperature or if they do only infrequently at night.

## Known Problems

- Data is lost if power is lost, no way around this as the pi uses the offset of the time that the data is collected from the time it is sent to determine the time of day the data was collected. Since the board doesn't have a cmos this value is reset every time it is restarted causing timing to be off.
- Internet connection can be an issue as the Pico occasionally gets stuck thinking it has a connection when it doesn't. The code is set to restart the machine which fixes the problem, however in the state that it is downloaded in for it to automatically run after this main.py needs to be renamed to boot.py. Ideally this could be set to use bluetooth to transmit data to a phone where a corresponding app could trasmit the data to an api but I have an Iphone with no mac to program it with or a developer key to use in development.
- HTTP requests take time and intrupt the beats from counting. This causes an very short inturupt in the data collection as I need to regather historical data. Ideally the HTTP request would be sent in a seperate thread but the urequests library does not apear thread safe.
- Pulse data has accuracy problems, either the sensor (I ran the data and ground backwards and might have damaged it) or my algorithmn could be the source of the problem. Likely the algorithmn could be improved with some more extensive analysis of the output.

## SetUp

### Pico

Load main.py from the data_collection dirrectory onto the Microcontroller using a editor like Thorny. Run the main.py program which will generate the configuration files. Populate the wifi.json and api.txt to inform the system the networks to connect to and the api endpoint you wish to use.

#### Soldering

1. Solder a Power wire to the 3.3v connection point
2. Solder a ground wire to a gnd connection point
3. Solder the data wire from the pulse sensor to Pin 16
4. Solder the data wire for the ds18b20 to Pin 4
5. Connect the power and ground wires from the boards to the sensors
6. Solder in a 4.7 Ohm resister between the power and data wires on the ds18b20

### API

Use NPM install to install the required packages. Add database access information and the location to store log files to the configuration file. Run the enclosed index.js using Node.js. Port forwarding may be desired I used NGINX.

### Database

Create two tables in the database that the API is writting to with the following definitions:

CREATE TABLE `heart_rate` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `bpm` float NOT NULL,
  `time` timestamp NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) AUTO_INCREMENT=1

CREATE TABLE `temperature` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `temperature` float NOT NULL,
  `time` timestamp NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) AUTO_INCREMENT=1

### Displaying Data

Feel free to use whatever methods to display the data, I personally used Graphana to graph the data over time.
