# flask-thermostat

This is an updated version of the original Django based home thermostat.
It has been rewritten in Flask as the Django was much larger/more capable than required.
Added simple pages for altering the schedule and viewing statistics.
Stats page doesn't want to be displayed by default as this is supposed to work on a Raspberry Pi Zero.  If the database is a decent size, you'll be running at 100% cpu usage permanently.
This version also includes an additional function to archive the database when 10Mb is reached, so that the system doesnt become unresponsive.

The config files are set up with the expectation that the project is installed into "/home/pi/flask_thermostat".

Requirements:
-Updated version of Raspbian/Raspberry Pi OS (this has been tested up to "buster")
-Functioning nginx server
-Python 3 venv has been created @ "/home/pi/flask_venv" with the required modules from the requirements.txt
-1 or more DS18B20 temp sensors wired into the Pi
-The temp sensors are enabled in the Pi
-git is installed to be able to clone the files OR download directly from the site to skip this step


After a fresh pull/checkout/download the following steps are required to integrate the thermostat and make it run from startup:
1 - Add the modules for the temp sensors to the startup environment with the following by running "sudo nano /etc/modules" and adding the following lines
	-"w1_gpio"
	-"w1_therm"
*the above section is a little suspect as it seems to run without it???*

2 - Rename "thermostat.sqlite3.default" to "thermostat.sqlite" so that it is now used as the live database

3 - Install/enable the uwsgi service with "sudo systemctl enable /home/pi/flask_thermostat/flask_thermostat.service"
-start the service with "sudo systemctl start flask_thermostat.service"

4 - Install/enable the thermostat service with "sudo systemctl enable /home/pi/flask_thermostat/thermostat.service"
-Start the service with "sudo systemctl start thermostat.service"

5 - Enable the website by creating a symlink to the nginx config file with "sudo ln -s /home/pi/flask_thermostat/thermostat.nginx.conf /etc/nginx/sites-enabled/thermostat.nginx.conf"
-Restart the webserver with "sudo service nginx reload"

That should be it, but I'm sure there are more problems that will crop up!  A future action is to roll all that into an install script.