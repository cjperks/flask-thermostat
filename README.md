# flask-thermostat

Updated version of the original Django based home thermostat.
Rewritten in Flask as the Django was much larger than required.
Added simple pages for altering the schedule and viewing statistics.
Stats page doesn't want to be displayed by default as this is supposed to work on a Raspberry Pi Zero.

The config files are set up with the expectation that the project is installed into /home/pi/flask_thermostat

flask_thermostat.service should be installed into /etc/systemd/system/ and enabled so that it runs at boot time: "sudo systemctl enable flask_thermostat"

Adding a symlink to the nginx config file from the nginx "sites-enabled" usually works to get the site up