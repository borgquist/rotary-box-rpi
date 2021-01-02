#!/bin/bash
cd /home/pi/shared/rotary-box-rpi
git reset --hard HEAD
git clean -xffd
git pull
sudo chmod 644 *.service
sudo chmod 755 gitpull.sh