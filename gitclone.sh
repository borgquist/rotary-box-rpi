#!/bin/bash
for i in {1..50}; do ping -c1 www.google.com &> /dev/null && break; done
sudo rm -r /home/pi/rotary-box-rpi
mkdir /home/pi/rotary-box-rpi
cd /home/pi/
git clone https://github.com/borgquist/rotary-box-rpi.git
