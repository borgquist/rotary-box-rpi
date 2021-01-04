#!/bin/bash
for i in {1..50}; do ping -c1 www.google.com &> /dev/null && break; done
sudo rm -r /home/pi/shared/rotary-box-rpi
mkdir /home/pi/shared/rotary-box-rpi
cd /home/pi/shared/
git clone https://github.com/borgquist/rotary-box-rpi.git
