# !/usr/bin/env python3

# Changelog

# v1.0
# Single sensor input, single schedule, simple logging, no web interface

# v1.1
# Read any temp sensors that are availible

# v1.2
# interface with django db
# auto add any new sensors to location table
# inetgrate with web interface

# v3
# only record every 10 minutes


# v4.0
# changed record keeping to only record on temp or control output change
# keep the last 5 readings in memory

# Changelog end

import time, os, signal, sys, sqlite3, datetime
import RPi.GPIO as GPIO
from dbshrink import archive_db, shrink_db

# Global settings
DATABASE = "/home/pi/thermostat/thermostat.sqlite3"
sensorPath = "/sys/bus/w1/devices"


# RPi settings
# set the General Purpose Input/Output pins to the correct mode
GPIO.setmode(GPIO.BCM)

# disable warnings - background process so they aren't visible - add to logging later?
GPIO.setwarnings(False)

# select the pin to control
relay = 17

# set the relay pin as an output pin
GPIO.setup(relay, GPIO.OUT)


# exit code
def sigterm_handler(_signo, _stack_frame):
    # switch off and free up pins
    GPIO.cleanup()

    # close db connection
    conn.close()

    print("Safe exit")

    # exit program - I think??
    sys.exit(0)

# I have very little idea what this section is doing...


# signal handler to catch the TERM signal
signal.signal(signal.SIGTERM, sigterm_handler)

signal.signal(signal.SIGINT, sigterm_handler)


# I have more of an idea about this...
# connect to db for logging/interaction details
conn = sqlite3.connect(DATABASE)
c = conn.cursor()

# create the recent temperature matrix placeholder
last5 = [[], []]

# main section
if __name__ == "__main__":

    # loop forever
    while True:
        # if the db is too big, archive and shrink
        if os.path.getsize(DATABASE) > 10000000:
            # copy the database to an date-tagged version
            archive_db(DATABASE)

            # remove all but the specified most recent entries from the current db
            shrink_db(DATABASE, "control_log")
            shrink_db(DATABASE, "temp_log")

        # get all the sensors
        tempSensors = os.listdir(sensorPath)

        # get data from all attached temperature sensors
        # initialise array
        sensorData = [[0 for j in range(3)] for i in range(len(tempSensors) - 1)]

        # reset counter
        i = 0
        for sensor in tempSensors:

            # ignore the sensor master
            if sensor != "w1_bus_master1":

                sensorData[i][0] = sensor

                #  Open the sensor file
                sensorFile = open(sensorPath + "/" + sensor + "/w1_slave")

                #  Read all of the text in the file.
                text = sensorFile.read()

                #  Close the file now that the text has been read.
                sensorFile.close()

                # chop out the CRC section
                sensorData[i][1] = text.split("\n")[0].split(" ")[11]

                # grab the temperature value
                sensorData[i][2] = float(text.split("\n")[1].split(" ")[9][2:]) / 1000

                i += 1

        # update the time as sqLite understands it
        c.execute("SELECT datetime('now')")
        timeStamp = c.fetchone()[0]

        # update the current sensor inputs
        for row in sensorData:

            # check the CRC comes back ok
            if row[1] == "YES":

                # check if the sensor exists in the location table
                c.execute("SELECT id from location WHERE sensor = ?", (row[0],))

                if c.fetchone() is None:
                    # print("new location added")
                    # add the location into the location table, if missing
                    newLoc = "New location added " + str(datetime.datetime.now())
                    c.execute("INSERT INTO location (location_name, sensor, latest_temp, latest_time) VALUES(?,?,?,?)", (newLoc, row[0], row[2], timeStamp,))
                    conn.commit()

                    # add a temp long entry
                    c.execute("INSERT INTO temp_log (timestamp, sensor_id, temp) VALUES(?,?,?)", (timeStamp, row[0], row[2],))
                    # commit the record to the db
                    conn.commit()

                else:
                    # update the current temp record
                    c.execute("UPDATE location SET latest_time = ?, latest_temp = ? WHERE sensor = ?", (timeStamp, row[2], row[0],))
                    # commit the record to the db
                    conn.commit()

                    # add an entry to the temperature log, if the temperature has changed
                    c.execute("SELECT temp from temp_log WHERE sensor_id = ? ORDER BY timestamp DESC LIMIT 1", (row[0],))

                    lastTemp = c.fetchone()
                    # check if there are any temp readings
                    if lastTemp:
                        # if there are readings, compare the last one
                        if lastTemp[0] != row[2]:
                            c.execute("INSERT INTO temp_log (timestamp, sensor_id, temp) VALUES(?,?,?)", (timeStamp, row[0], row[2],))
                            conn.commit()

                    # if there are no logs at all
                    else:
                        # add a temp long entry
                        c.execute("INSERT INTO temp_log (timestamp, sensor_id, temp) VALUES(?,?,?)", (timeStamp, row[0], row[2],))
                        conn.commit()

        # print("Target temp : %f" %target)

        # update the current sensor/reading matrix with current values
        # 0 = sensor id
        # 1 = CRC value
        # 2 = temperature reading

        # if we have no recent data, refill
        if len(last5[0]) == 0:
            for sensor in sensorData:
                last5[0].append(sensor[0])
                last5[1].append([sensor[2]])

        # if we have some previous data
        else:
            for sensor in sensorData:
                # check if the sensor is in the current list
                if sensor[0] in last5[0]:
                    # add the new reading to the start of the list
                    si = last5[0].index(sensor[0])
                    last5[1][si].insert(0, sensor[2])

                    # keep only the most recent 5 readings
                    last5[1][si] = last5[1][si][:5]

                # add the sensor if it is not in the list already
                else:
                    last5[0].append(sensor[0])
                    last5[1].append([sensor[2]])

        # remove sensors that have broken/been removed from the system
        for sensor in last5[0]:
            if not any(sensor in i for i in sensorData):
                last5[1].pop(last5[0].index(sensor))
                last5[0].pop(last5[0].index(sensor))

        # get the average for the last 5 mins, over all live sensors
        i = 0
        t = 0
        for row in last5[1]:
            for reading in row:
                i += 1
                t = t + reading

        aveTemp = t / i
        # print("Average temp = %f" % aveTemp)
        # print(last5)

        # check if we've changed state in the last 10 minutes
        c.execute("SELECT output FROM control_log WHERE timestamp >= (SELECT datetime('now', '-10 minutes')) ORDER BY timestamp DESC LIMIT 1")
        lastOutput = c.fetchone()

        # if there was a change inside 10 mins
        if lastOutput:
            # print("inside lockout period")
            output = lastOutput[0]

        # if there was not, we can decide what to do
        else:
            # get the override details if present and not expired
            c.execute("SELECT temp FROM override WHERE expires >= (SELECT datetime('now')) ORDER BY expires DESC LIMIT 1")
            override = c.fetchone()

            if override:
                target = override[0]

            else:
                # get the normal scheduled temp
                c.execute("SELECT min_temp FROM schedule WHERE start_time <= (SELECT time('now', 'localtime')) ORDER BY start_time DESC LIMIT 1")
                target = c.fetchone()[0]

            # print("outside lockout")
            if aveTemp < target:
                output = 1

            else:
                output = 0

        #
        # ---IMPORTANT---
        # frost protection override - this trumps all other temperature calculations
        for row in sensorData:
            if row[2] <= 7:
                output = 1
        # ---END IMPORTANT---
        #

        # write the record of the control output back to the db, if different to the existing
        c.execute("SELECT output, timestamp FROM control_log ORDER BY timestamp DESC LIMIT 1")
        lastOutput = c.fetchone()

        # prevents a crash if there is no log yet - shouldn't be an issue after initial config
        if lastOutput:
            # compare to last if there is a last
            if output != lastOutput[0]:
                # print("state change: {} -> {}" .format(lastOutput[0], output))
                c.execute("INSERT INTO control_log (timestamp, output) VALUES(?, ?)", (timeStamp, output))
                conn.commit()

            # else:
                # print("no state change")

        # if there is no last output - create one
        else:
            c.execute("INSERT INTO control_log (timestamp, output) VALUES(?, ?)", (timeStamp, output))
            conn.commit()

        # print("Calculated state: %s" %output)

        # turn the boiler on or off, depending on the decision
        if output == 0:
            GPIO.output(relay, True)

        else:
            GPIO.output(relay, False)

        # sleep for 60 seconds
        time.sleep(60)
