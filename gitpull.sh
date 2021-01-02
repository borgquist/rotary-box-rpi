#!/bin/bash
for i in {1..50}; do ping -c1 www.google.com &> /dev/null && break; done
cd /home/pi/shared/rotary-box-rpi
git reset --hard HEAD
git clean -xffd
git pull
sudo chmod 644 *.service
sudo chmod 755 gitpull.sh