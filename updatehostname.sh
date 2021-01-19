#!/bin/bash

filename="/etc/hosts"
filename2="/etc/hostname"

#assumes that hosts and hostname have the same value
search="$(cat /etc/hosts | grep -o 'box-[^[:blank:]]*')"

read -p "Enter the new hostname: " replace

if [[ $search != "" && $replace != "" ]]; then
sudo sed -i "s/$search/$replace/" $filename
sudo sed -i "s/$search/$replace/" $filename2
fi
