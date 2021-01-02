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
nohup /usr/bin/python3 resetbutton.py &

echo "starting rotarymeds.py"
nohup /usr/bin/python3 rotarymeds.py &
echo "rotarystart.sh complete"
