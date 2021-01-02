#!/bin/bash
echo "running rotarystart.sh"
for i in {1..50}; do ping -c1 www.google.com &> /dev/null && break; done
echo "internet check complete"
cd /home/pi/shared/rotary-box-rpi
git reset --hard HEAD
git clean -xffd
git pull
echo "git pull complete"
sudo chmod 644 *.service
sudo chmod 755 rotarystart.sh
echo "file permissions set"

echo "starting restbutton.py"
/usr/bin/python3 resetbutton.py &> /dev/null

echo "starting rotarymeds.py"
/usr/bin/python3 rotarymeds.py &> /dev/null
echo "rotarystart.sh complete"