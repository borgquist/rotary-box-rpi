#!/bin/bash
for i in {1..50}; do ping -c1 www.google.com &> /dev/null && break; done
sudo rm -r /home/pi/podq-box-rpi
mkdir /home/pi/podq-box-rpi
cd /home/pi/
git clone https://github.com/borgquist/podq-box-rpi.git

SERVICE="podq.py"
if pgrep -f "$SERVICE" >/dev/null
then
    echo "$SERVICE is already running"
else
    echo "$SERVICE is stopped, starting it"
    /usr/bin/python3 /home/pi/podq-box-rpi/podq.py
fi
